# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il consumo del plafond dei titoli IVA sulle fatture di un lotto, e la
#        SPEZZATURA delle righe che il plafond copre solo in parte.
#
#        ⛔ E' la seconda meta' di `I4`, e la prima cosa da sapere e' PERCHE'
#        la riga si spezza: una riga FatturaPA porta UNA `AliquotaIVA` e UNA
#        `Natura`. Due trattamenti sullo stesso imponibile sono due
#        `DettaglioLinee`, per OBBLIGO DI FORMATO. La spezzatura non si puo'
#        evitare: si puo' solo decidere chi la regge — e la decisione `N3` (a')
#        dice due `fatture_righe` sorelle, con `riga_capofila_id` sulla parte.
#
#        ⛔ IL MOMENTO E' OBBLIGATO. Si gira mentre la fattura e' ancora
#        `EMESSA`: `trgfn_fattura_satellite_guard_congelamento` legge lo stato
#        VIVO al momento della scrittura, quindi dopo la DEFINITIVA la
#        spezzatura verrebbe rifiutata.
#
#        ⭐ UN KIT SI SPEZZA COME UN'UNITA' SOLA (D-5, dal 2026-10-03): i suoi
#        componenti si consumano come un gruppo, con la stessa frazione, e
#        il titolo si giudica sull'articolo PADRE (D-5.1). Una riga sciolta
#        e' un gruppo di uno, sulla stessa strada.
#
#        ⭐ IL PLAFOND SI CONSUMA SUL NETTO (decisione C, dal 2026-10-04): le
#        righe positive consumano, le negative restituiscono, e la madre lo
#        fa per tutte le righe di un titolo in una chiamata.
#
#        Brief: docs/it/dev/work-in-progress/
#               brief-be-fe-iva-fase-3-consumatori-risolutore.md (`F3-b2`),
#               brief-db-bom-flag-quantita-e-kit-in-fattura.md §11, §13
# ------------------------------------------------------------

from __future__ import annotations

import logging
from decimal import Context, Decimal
from typing import Any, NamedTuple, cast

from django.db import transaction

from apps.core.services.error_manager import ErrorManager
from apps.vendite.db.pipeline_repository import VenditePipelineRepository

logger = logging.getLogger(__name__)

_E_VALIDATION = "E_PIPELINE_VALIDATION"
_FN = "vendite.plafond_fattura_service.consuma_lotto"
# ⚠️ Il contesto dei prodotti che devono restare ESATTI (`kit_qta × frazione`):
#    la precisione di default (28 cifre) puo' arrotondare il prodotto di una
#    frazione lunga, e due componenti direbbero due numeri di kit diversi.
_ESATTO = Context(prec=100)


class PlafondFatturaService:
    # Scopo: Inizializza la istanza.
    def __init__(self, repository: VenditePipelineRepository | None = None) -> None:
        self.repository = repository or VenditePipelineRepository()

    # Scopo: consuma il plafond dei titoli IVA su tutte le fatture del lotto e
    #        spezza le righe coperte solo in parte.
    # Risultato: conteggi del giro, per il diario del task.
    #
    # ⛔ L'ORDINE DELLE FATTURE E' UN REQUISITO FISCALE (`P5` / `D15-bis`), non
    #    una comodita': il lock di riga sul titolo impedisce a due transazioni
    #    di andare sotto zero insieme, ma non sa che esiste una fattura
    #    ANTERIORE non ancora arrivata. Senza l'ordine, a plafond quasi
    #    esaurito e' la FORTUNA a decidere quale cliente resta scoperto. Lo
    #    impone il repository, e questo giro non lo ri-ordina.
    def consuma_lotto(self, lotto_id: int) -> dict[str, int]:
        _richiedi(
            isinstance(lotto_id, int) and lotto_id > 0,
            message="Parametro lotto non valido.",
            detail="lotto_id obbligatorio e > 0",
            lotto_id=lotto_id,
        )
        fattura_ids = self.repository.list_fatture_by_lotto_ordinate(lotto_id)
        if not fattura_ids:
            return {"fatture": 0, "righe_spezzate": 0, "movimenti": 0}

        ctx_map = self.repository.batch_get_fattura_iva_context(fattura_ids)
        spezzate = 0
        movimenti = 0
        # ⛔ UNA transazione per TUTTO il lotto, e non per fattura come fanno i
        #    task vicini (`_run_per_fattura_task` isola gli errori per
        #    documento). Qui l'isolamento sarebbe il difetto: un giro che si
        #    ferma a meta' lascerebbe plafond CONSUMATO su alcune fatture e
        #    righe non spezzate su altre — cioe' un registro fiscale che dice
        #    una cosa e i documenti un'altra, e nessun rilancio saprebbe da dove
        #    riprendere. Meglio non consumare niente che consumare a meta'.
        with transaction.atomic():
            for fattura_id in fattura_ids:
                esito = self._consuma_fattura(fattura_id, ctx_map.get(fattura_id) or {})
                spezzate += esito["righe_spezzate"]
                movimenti += esito["movimenti"]
        return {
            "fatture": len(fattura_ids),
            "righe_spezzate": spezzate,
            "movimenti": movimenti,
        }

    # Scopo: il giro di UNA fattura: risolve ogni gruppo, consuma una volta
    #        per titolo, scrive le righe.
    #
    # ⭐ IL GRUPPO E' L'UNITA' DEL TRATTAMENTO (D-5): i componenti di un kit
    #    (stessa `kit_key`) prendono lo stesso titolo e la stessa frazione;
    #    una riga sciolta e' un gruppo di uno.
    #
    # ⭐ IL TITOLO E' L'UNITA' DEL CONSUMO (decisione C, brief-db-bom-flag-
    #    quantita-e-kit-in-fattura §13): il plafond si consuma sul NETTO della
    #    fattura, e il netto si conosce solo guardando INSIEME tutte le righe
    #    di un titolo — uno sconto restituisce cio' che la merce consuma. Per
    #    questo UNA chiamata alla madre per titolo, con tutto il suo secchio.
    #    L'ordine fra i gruppi lo decide la madre (quello di stampa), non qui.
    def _consuma_fattura(
        self, fattura_id: int, ctx: dict[str, Any]
    ) -> dict[str, int]:
        # ⛔ `P3`: senza emittente il calcolo si FERMA. La funzione DB e'
        #    `SECURITY INVOKER` e legge una tabella con RLS: senza contesto
        #    emittente legge zero titoli e risponde con l'aliquota ORDINARIA
        #    senza sollevare — cioe' nessun plafond consumato, su un documento
        #    che nessuno segnalera'.
        _richiedi(
            ctx.get("emittente_fiscale_id") is not None,
            message="Contesto fiscale incompleto.",
            detail=(
                f"emittente fiscale non risolvibile per la fattura {fattura_id}: "
                "il plafond non e' consumabile"
            ),
            fattura_id=fattura_id,
        )
        righe = self.repository.list_righe_per_plafond(fattura_id)
        # ⚠️ UN risolutore per fattura, non uno per gruppo: e' un oggetto senza
        #    stato ma istanziarlo dentro il ciclo nascondeva il fatto che le
        #    righe di una fattura condividono lo stesso contesto.
        from apps.vendite.services.iva_resolver_service import IvaResolverService

        resolver = IvaResolverService()
        secchi: dict[int, list[_Gruppo]] = {}
        for righe_gruppo in _gruppi_di_consumo(righe):
            parti = self._risolvi_gruppo(righe_gruppo, ctx, resolver=resolver)
            parte_titolo = parti[0] if parti[0].get("titolo_iva_id") else None
            if parte_titolo is None:
                # Nessun titolo: l'IVA e' quella dello stadio A, gia' scritta
                # alla generazione. Non si tocca niente e non si consuma niente.
                continue
            if len(parti) == 1:
                # ⭐ Titolo SENZA tetto: copre tutto e non ha un registro da
                #    scrivere, quindi la madre non si chiama.
                self._applica(righe_gruppo, parte_titolo)
                continue
            secchi.setdefault(int(parte_titolo["titolo_iva_id"]), []).append(
                _Gruppo(righe_gruppo, parte_titolo, parti[1])
            )

        spezzate = 0
        movimenti = 0
        # ⚠️ In ordine di titolo: ogni chiamata prende il lock di riga del suo
        #    titolo fino alla fine della transazione del lotto, e un ordine
        #    fisso evita che due fatture prendano gli stessi due lock in versi
        #    opposti dentro lo stesso giro. Il risultato non cambia: le
        #    capienze di due titoli sono indipendenti.
        for titolo_iva_id, gruppi in sorted(secchi.items()):
            esito = self._consuma_titolo(fattura_id, titolo_iva_id, gruppi, ctx)
            spezzate += esito["spezzate"]
            movimenti += esito["movimenti"]
        return {"righe_spezzate": spezzate, "movimenti": movimenti}

    # Scopo: la domanda di CONSUMO al risolutore per un gruppo.
    #
    # ⭐ D-5.1 (a): IL TITOLO SI GIUDICA SUL PADRE DEL KIT. Se il padre e'
    #    nell'ambito del titolo lo seguono tutti i componenti, altrimenti
    #    nessuno: e' il kit la cosa venduta (come allo stadio A, dove l'IVA dei
    #    componenti e' vincolata a quella del padre).
    # ⚠️ Nessun importo: il consumo non proietta sul residuo (lo farebbe per
    #    riga, e sul netto per riga e' sbagliato). Risponde quale titolo vale e
    #    i suoi due trattamenti; la forma la garantisce `risolvi`.
    def _risolvi_gruppo(
        self,
        righe_gruppo: list[dict[str, Any]],
        ctx: dict[str, Any],
        *,
        resolver: Any,
    ) -> list[dict[str, Any]]:
        capo = righe_gruppo[0]
        # ⚠️ Scelta ESPLICITA, senza ripiego sul componente: su una riga di kit
        #    il padre lo garantisce `chk_fatture_righe_kit_coerente`, e se un
        #    giorno mancasse giudicare il kit sul primo componente sarebbe la
        #    violazione silenziosa di D-5.1. Un `None` lo ferma il guard del
        #    risolutore.
        articolo = (
            capo.get("kit_articolo_padre_id") if capo.get("kit_key")
            else capo.get("articolo_id")
        )
        return resolver.risolvi(
            consumo=True,
            articolo_id=articolo,
            billing_account_id=ctx["billing_account_id"],
            emittente_fiscale_id=ctx["emittente_fiscale_id"],
            data_riferimento=ctx["data_riferimento"],
        )

    # Scopo: consuma il plafond di UN titolo per tutti i gruppi del suo secchio
    #        e scrive ogni gruppo secondo la sua frazione.
    #
    # ⭐ L'AUTORITA' E' LA MADRE CHE PRENDE IL LOCK. E' lei a fare il netto, a
    #    ordinare i gruppi, a decidere chi resta coperto e a dare la frazione
    #    di ogni gruppo: qui la si legge e la si applica, non la si ricalcola.
    # ⚠️ Gli importi passati sono quelli delle righe lette, negativi e zeri
    #    compresi: la madre li confronta con la riga e si ferma se divergono
    #    (la riga e' cambiata dopo la lettura).
    def _consuma_titolo(
        self,
        fattura_id: int,
        titolo_iva_id: int,
        gruppi: list[_Gruppo],
        ctx: dict[str, Any],
    ) -> dict[str, int]:
        righe = [r for g in gruppi for r in g.righe]
        esiti = self.repository.consuma_plafond_titolo_righe(
            titolo_iva_id=titolo_iva_id,
            fattura_id=fattura_id,
            fattura_riga_ids=[int(r["id"]) for r in righe],
            # `fatture_righe.imponibile_riga` e' NOT NULL: `_dec` qui non da' None.
            imponibili=cast(
                list[Decimal], [_dec(r.get("imponibile_riga")) for r in righe],
            ),
            data_movimento=ctx["data_riferimento"],
        )
        quote = {int(e["fattura_riga_id"]): e for e in esiti}
        # ⛔ Una riga senza esito resterebbe col trattamento dell'anteprima, che
        #    puo' essere il titolo su una quota che il plafond non copre; una
        #    quota NULL letta come zero darebbe una capofila vuota. E' il
        #    contratto della madre («una riga per riga passata», quota sempre
        #    valorizzata): lo si pretende invece di supporlo.
        _richiedi(
            len(esiti) == len(righe)
            and all(int(r["id"]) in quote for r in righe)
            and all(e.get("quota_coperta") is not None for e in esiti),
            message="Ripartizione del plafond incoerente.",
            detail=(
                f"fattura {fattura_id}, titolo {titolo_iva_id}: la madre ha "
                f"ripartito {len(esiti)} righe su {len(righe)} passate, "
                f"{sum(1 for e in esiti if e.get('quota_coperta') is None)} "
                "senza quota"
            ),
            fattura_id=fattura_id,
        )
        spezzate = 0
        for gruppo in gruppi:
            frazione = _frazione_del_gruppo(fattura_id, gruppo, quote)
            if frazione == 1:
                self._applica(gruppo.righe, gruppo.parte_titolo)
            elif frazione == 0:
                # ⚠️ L'ordinario si SCRIVE, non si lascia: la riga e' nata con
                #    il trattamento dell'anteprima, che a plafond ancora
                #    capiente era il titolo.
                self._applica(gruppo.righe, gruppo.parte_ordinaria)
            else:
                for riga in gruppo.righe:
                    self._spezza(
                        fattura_id=fattura_id,
                        riga=riga,
                        coperta=_dec(quote[int(riga["id"])]["quota_coperta"]),
                        frazione=frazione,
                        parte_titolo=gruppo.parte_titolo,
                        parte_ordinaria=gruppo.parte_ordinaria,
                    )
                spezzate += len(gruppo.righe)
        movimenti = sum(1 for e in esiti if e.get("movimento_id"))
        return {"spezzate": spezzate, "movimenti": movimenti}

    # Scopo: un trattamento solo per tutte le righe di un gruppo: nessuna
    #        spezzatura, quantita' e `kit_qta` invariate.
    def _applica(self, righe: list[dict[str, Any]], parte: dict[str, Any]) -> None:
        for riga in righe:
            self.repository.aggiorna_capofila_plafond(
                riga_id=int(riga["id"]),
                qta=_dec(riga.get("qta")) or Decimal(0),
                iva_id=parte.get("iva_id"),
                kit_qta=_dec(riga.get("kit_qta")),
                meta=_meta_parte(dict(riga.get("meta") or {}), parte),
            )

    # Scopo: scrive le due parti. La CAPOFILA resta la riga esistente e prende
    #        la quota coperta; la parte nuova prende il resto.
    #
    # ⭐ LA QUANTITA' SI DERIVA DALL'IMPONIBILE, ed e' il metodo scelto da Tid:
    #    `qta = quota / prezzo_effettivo` e' l'inverso esatto della formula con
    #    cui il DB calcola `imponibile_riga`, quindi la capofila ricalcola
    #    PROPRIO la quota — che e' il movimento scritto nel registro. ⚠️ Non
    #    `qta × quota / imponibile`: `imponibile_riga` e' ARROTONDATO
    #    (`trgfn_fatture_righe_importo`), e quel rapporto sposterebbe la
    #    capofila di un centesimo dal suo movimento; al rilancio la madre
    #    vedrebbe una frazione diversa da 1 e spezzerebbe di nuovo.
    #    Vale per ogni segno: su una riga negativa quota e prezzo (o quota e
    #    quantita') hanno segni che si compensano. Solo a prezzo effettivo ZERO
    #    (un omaggio, uno sconto del 100%) non c'e' una quota da invertire — e'
    #    zero — e la riga si divide con la frazione del gruppo.
    #
    # ⛔ E LA QUANTITA' DELLA PARTE NON PASSA PER L'ARROTONDAMENTO DI RIGA
    #    (`arrotondamento_quantita_dec`). Applicarlo rimetterebbe la deriva, e
    #    la rimetterebbe NEL VERSO SBAGLIATO: lascerebbe plafond non consumato,
    #    cioe' ridurrebbe in silenzio un diritto documentato del cliente.
    #
    # ⭐ IL CENTESIMO VA SULLA PARTE RESIDUA, e qui e' vero PER COSTRUZIONE: la
    #    quantita' del resto e' `qta_totale - qta_coperta`, quindi le due parti
    #    sommano esattamente la riga di partenza, comunque cada la divisione.
    #
    # ⭐ `kit_qta` (R-BE-P4) segue la FRAZIONE, non la quantita' del
    #    componente: `kit_qta × f` alla capofila, il resto alla parte. Con la
    #    stessa `f` su ogni riga del kit, la vista somma per componente lo
    #    stesso numero di kit su ogni meta' («1,2» e «1,8»). Il prodotto e'
    #    ESATTO (contesto `_ESATTO`): un arrotondamento qui farebbe dire ai
    #    componenti numeri diversi, e la vista darebbe al kit quantita' NULL.
    def _spezza(
        self,
        *,
        fattura_id: int,
        riga: dict[str, Any],
        coperta: Decimal | None,
        frazione: Decimal,
        parte_titolo: dict[str, Any],
        parte_ordinaria: dict[str, Any],
    ) -> None:
        qta_totale = _dec(riga.get("qta"))
        prezzo_eff = _prezzo_effettivo(riga)
        # ⛔ `qta` e `prezzo_unitario` sono NOT NULL: un NULL qui e' una
        #    proiezione rotta, non un prezzo zero. Ripiegare su zero avrebbe
        #    diviso la riga con la frazione invece che con la quota, e la
        #    capofila non avrebbe piu' ricalcolato il suo movimento.
        _richiedi(
            qta_totale is not None and prezzo_eff is not None and coperta is not None,
            message="Riga non spezzabile.",
            detail=(
                f"riga {riga.get('id')}: quantita', prezzo o quota coperta "
                "assenti"
            ),
            fattura_id=fattura_id,
            riga_id=riga.get("id"),
        )
        assert qta_totale is not None and prezzo_eff is not None and coperta is not None
        if prezzo_eff == 0:
            qta_coperta = _ESATTO.multiply(qta_totale, frazione)
        else:
            qta_coperta = coperta / prezzo_eff
        qta_residua = qta_totale - qta_coperta

        kit_qta = _dec(riga.get("kit_qta"))
        kit_qta_coperta: Decimal | None = None
        kit_qta_residua: Decimal | None = None
        if kit_qta is not None:
            kit_qta_coperta = _ESATTO.multiply(kit_qta, frazione)
            kit_qta_residua = _ESATTO.subtract(kit_qta, kit_qta_coperta)

        meta_base = dict(riga.get("meta") or {})
        self.repository.aggiorna_capofila_plafond(
            riga_id=int(riga["id"]),
            qta=qta_coperta,
            iva_id=parte_titolo.get("iva_id"),
            kit_qta=kit_qta_coperta,
            # ⛔ NIENTE marcatore «e' una spezzatura» nel `meta`, ed e' una
            #    correzione: ce l'avevo messo per spiegare la quantita' non
            #    tonda, ma quel fatto lo dice gia' `riga_capofila_id` — ed e'
            #    da li' che `vw_fattura_righe_esposte` deriva
            #    `tipo_riga = 'PARTE_PLAFOND'`. Due sorgenti per lo stesso
            #    fatto sono due sorgenti che divergono: basta un `UPDATE` sulla
            #    colonna senza il `meta` (o viceversa) e la riga si racconta in
            #    due modi, senza che niente sollevi.
            meta=_meta_parte(meta_base, parte_titolo),
        )
        self.repository.insert_parte_plafond(
            riga_capofila_id=int(riga["id"]),
            riga_nr=self.repository.get_next_fattura_riga_nr(fattura_id),
            qta=qta_residua,
            iva_id=parte_ordinaria.get("iva_id"),
            kit_qta=kit_qta_residua,
            meta=_meta_parte(meta_base, parte_ordinaria),
        )


# Scopo: un gruppo nel secchio di un titolo, con i due trattamenti che il
#        risolutore gli ha dato. ⚠️ I trattamenti sono PER GRUPPO e non per
#        titolo: due gruppi sotto lo stesso titolo possono avere ordinari
#        diversi (un articolo al 22%, un altro al 10%).
class _Gruppo(NamedTuple):
    righe: list[dict[str, Any]]
    parte_titolo: dict[str, Any]
    parte_ordinaria: dict[str, Any]


# Scopo: la frazione di un gruppo, letta dalla madre e pretesa coerente.
# ⛔ La frazione e' UNA per il gruppo: due frazioni sarebbero due kit diversi,
#    e una fuori da [0, 1] una quota che supera l'imponibile. Ci si ferma,
#    invece di fidarsi della prima riga.
def _frazione_del_gruppo(
    fattura_id: int, gruppo: _Gruppo, quote: dict[int, dict[str, Any]]
) -> Decimal:
    frazioni = {_dec(quote[int(r["id"])].get("frazione")) for r in gruppo.righe}
    frazione = next(iter(frazioni)) if len(frazioni) == 1 else None
    _richiedi(
        frazione is not None and Decimal(0) <= frazione <= Decimal(1),
        message="Ripartizione del plafond incoerente.",
        detail=(
            f"fattura {fattura_id}: frazioni del gruppo della riga "
            f"{gruppo.righe[0].get('id')}: {sorted(map(str, frazioni))}"
        ),
        fattura_id=fattura_id,
    )
    assert frazione is not None
    return frazione


# Scopo: le righe di una fattura raggruppate per TRATTAMENTO: i componenti di
#        un kit (stessa `kit_key`) insieme, ogni riga sciolta da sola. Serve a
#        chiedere il titolo una volta per gruppo (un kit sul padre, D-5.1).
# ⚠️ E' la stessa regola con cui la madre raggruppa da se', ed e' voluto che
#    coincida: un kit diviso fra due titoli la madre lo rifiuterebbe («kit
#    incompleto»). L'ORDINE invece non conta piu': fra i gruppi lo decide la
#    madre (decisione C, R-BE-C5).
def _gruppi_di_consumo(righe: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    gruppi: list[list[dict[str, Any]]] = []
    per_kit: dict[str, list[dict[str, Any]]] = {}
    for riga in righe:
        kit_key = riga.get("kit_key")
        if kit_key is None:
            gruppi.append([riga])
        elif kit_key in per_kit:
            per_kit[kit_key].append(riga)
        else:
            per_kit[kit_key] = [riga]
            gruppi.append(per_kit[kit_key])
    return gruppi


# Scopo: il `meta` di una parte — i due fatti che nessuno puo' ricostruire dopo.
# ⛔ SCRITTO UNA VOLTA SOLA, e non per brevita': il ramo «copertura piena» e i
#    due rami della spezzatura componevano lo stesso dizionario a mano, e tre
#    copie della stessa forma sono tre punti in cui dimenticare una chiave —
#    dimenticanza che non da' errore, da' una riga che non sa spiegarsi.
# ⛔ E l'`origine` la dice sempre il RISOLUTORE: il vocabolario e' del DB ed e'
#    APERTO. Sulla parte residua puo' valere `ASSENTE`, e allora deve fermarla
#    il cancello all'emissione — non un `ARTICOLO` scritto da noi, che gliela
#    farebbe passare sotto il naso.
def _meta_parte(base: dict[str, Any], parte: dict[str, Any]) -> dict[str, Any]:
    return {
        **base,
        "iva_origine": parte.get("origine"),
        "iva_titolo_id": parte.get("titolo_iva_id"),
    }


# Scopo: il guard del giro, scritto una volta: stesso codice, stessa funzione,
#        sempre nel diario. Cambia solo la frase e il contesto.
def _richiedi(condizione: bool, *, message: str, detail: str, **context: Any) -> None:
    ErrorManager.require(
        condizione,
        code=_E_VALIDATION,
        message=message,
        detail=detail,
        context=context,
        function_name=_FN,
        log_to_db=True,
    )


# Scopo: Decimal difensivo — il driver puo' restituire numerici come stringa.
def _dec(valore: Any) -> Decimal | None:
    if valore is None:
        return None
    return valore if isinstance(valore, Decimal) else Decimal(str(valore))


# Scopo: il prezzo al netto dello sconto di riga, cioe' il divisore con cui il
#        DB ha costruito `imponibile_riga`.
def _prezzo_effettivo(riga: dict[str, Any]) -> Decimal | None:
    prezzo = _dec(riga.get("prezzo_unitario"))
    if prezzo is None:
        return None
    sconto = _dec(riga.get("sconto_percentuale")) or Decimal(0)
    return prezzo * (Decimal(1) - sconto / Decimal(100))
