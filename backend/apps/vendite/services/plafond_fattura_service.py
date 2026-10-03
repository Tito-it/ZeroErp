# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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
#        Brief: docs/it/dev/work-in-progress/
#               brief-be-fe-iva-fase-3-consumatori-risolutore.md (`F3-b2`),
#               brief-db-bom-flag-quantita-e-kit-in-fattura.md §11
# ------------------------------------------------------------

from __future__ import annotations

import logging
from decimal import Context, Decimal
from typing import Any

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

    # Scopo: il giro di UNA fattura, un GRUPPO alla volta.
    # ⭐ IL GRUPPO E' L'UNITA' DEL CONSUMO (D-5, brief-db-bom-flag-quantita-e-
    #    kit-in-fattura §11): i componenti di un kit (stessa `kit_key`) si
    #    spezzano come un'unita' sola, con la stessa frazione; una riga sciolta
    #    e' un gruppo di uno. Una sola strada per entrambi: due strade di
    #    consumo sarebbero due copie delle regole di spezzatura.
    # ⚠️ I gruppi si consumano nell'ordine della loro prima riga (`riga_nr`):
    #    a plafond quasi esaurito l'ordine decide chi resta coperto, e resta
    #    quello di stampa come prima.
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
        spezzate = 0
        movimenti = 0
        # ⚠️ UN risolutore per fattura, non uno per riga: e' un oggetto senza
        #    stato ma istanziarlo dentro il ciclo nascondeva il fatto che le
        #    righe di una fattura condividono lo stesso contesto.
        from apps.vendite.services.iva_resolver_service import IvaResolverService

        resolver = IvaResolverService()
        for gruppo in _gruppi_di_consumo(righe):
            esito = self._consuma_gruppo(fattura_id, gruppo, ctx, resolver=resolver)
            spezzate += esito["spezzate"]
            movimenti += esito["movimenti"]
        return {"righe_spezzate": spezzate, "movimenti": movimenti}

    # Scopo: risolve, consuma e — se il titolo copre solo una quota — spezza
    #        ogni riga del gruppo con la stessa frazione.
    #
    # ⭐ D-5.1 (a): IL TITOLO SI GIUDICA SUL PADRE DEL KIT. Il risolutore si
    #    chiama con `kit_articolo_padre_id` e l'imponibile del kit intero: se
    #    il padre e' nell'ambito del titolo lo seguono tutti i componenti,
    #    altrimenti nessuno. E' il kit la cosa venduta (come allo stadio A,
    #    dove l'IVA dei componenti e' vincolata a quella del padre).
    #
    # ⛔ PROVVISORIO (R-DB-B13 del brief §12.5, decisione di Tid 2026-10-03):
    #    la madre oggi RIFIUTA i componenti a imponibile zero o negativo, che il
    #    modello ammette. Finche' non e' corretta, qui restano fuori dalla
    #    chiamata e si spezzano con la frazione del kit, perche' una `kit_qta`
    #    rimasta intera farebbe dare alla vista una quantita' NULL. ⚠️ Sul
    #    negativo e' anche sbagliato: la frazione esce dai soli positivi, e il
    #    kit consuma piu' del suo netto. Col fix si passano tutte le righe.
    def _consuma_gruppo(
        self,
        fattura_id: int,
        gruppo: list[dict[str, Any]],
        ctx: dict[str, Any],
        *,
        resolver: Any,
    ) -> dict[str, int]:
        consumanti = [r for r in gruppo if (_dec(r.get("imponibile_riga")) or 0) > 0]
        if not consumanti:
            # Niente da ripartire: righe a imponibile zero non consumano
            # capienza, e chiamare la madre scriverebbe un movimento vuoto.
            return {"spezzate": 0, "movimenti": 0}
        imponibile = sum(
            (_dec(r.get("imponibile_riga")) for r in consumanti), Decimal(0)
        )

        capo = gruppo[0]
        articolo = capo.get("kit_articolo_padre_id") if capo.get("kit_key") else None
        argomenti = {
            "articolo_id": str(articolo or capo["articolo_id"]),
            "billing_account_id": ctx["billing_account_id"],
            "emittente_fiscale_id": ctx["emittente_fiscale_id"],
            "data_riferimento": ctx["data_riferimento"],
        }
        # ⚠️ Qui l'imponibile SI PASSA, ed e' la differenza con la generazione
        #    delle righe: la' si chiede il trattamento «sul primo euro» perche'
        #    la spezzatura non e' ancora calcolabile, qui si chiede la
        #    ripartizione VERA perche' e' il momento in cui si decide.
        parti = resolver.risolvi(imponibile=imponibile, **argomenti)
        if not parti:
            return {"spezzate": 0, "movimenti": 0}

        # ⚠️ UNA scansione: la PARTE e' l'informazione, l'id ne discende. Due
        #    `next()` sullo stesso predicato erano due punti da tenere
        #    d'accordo, e il secondo era un `next()` senza default — cioe' uno
        #    `StopIteration` se il primo cambiava e il secondo no.
        parte_titolo = next((p for p in parti if p.get("titolo_iva_id")), None)
        if parte_titolo is None:
            # Nessun titolo: l'IVA e' quella dello stadio A, gia' scritta alla
            # generazione. Non si tocca niente e non si consuma niente.
            return {"spezzate": 0, "movimenti": 0}

        # ⭐ L'AUTORITA' E' LA MADRE CHE PRENDE IL LOCK, non il risolutore.
        #    Il risolutore e' `STABLE`: proietta il residuo che vede, e fra la
        #    proiezione e il lock un'altra transazione puo' aver consumato. La
        #    ripartizione buona e' quella che torna DA QUI — e per un kit e'
        #    lei a dare la frazione unica, con un lock solo.
        esiti = self.repository.consuma_plafond_titolo_righe(
            titolo_iva_id=int(parte_titolo["titolo_iva_id"]),
            fattura_id=fattura_id,
            fattura_riga_ids=[int(r["id"]) for r in consumanti],
            imponibili=[_dec(r.get("imponibile_riga")) for r in consumanti],
            data_movimento=ctx["data_riferimento"],
        )
        quote = {int(e["fattura_riga_id"]): e for e in esiti}
        # ⛔ Una riga senza esito resterebbe intera a meta' di un kit spezzato;
        #    due frazioni diverse sarebbero due kit diversi. Sono il contratto
        #    della madre, e lo si pretende invece di leggere la prima riga.
        frazioni = {_dec(e.get("frazione")) for e in esiti}
        _richiedi(
            len(esiti) == len(consumanti)
            and all(int(r["id"]) in quote for r in consumanti)
            and len(frazioni) == 1,
            message="Ripartizione del plafond incoerente.",
            detail=(
                f"fattura {fattura_id}: la madre ha ripartito {len(esiti)} righe "
                f"su {len(consumanti)} passate, frazioni {sorted(map(str, frazioni))}"
            ),
            fattura_id=fattura_id,
        )
        movimenti = sum(1 for e in esiti if e.get("movimento_id"))
        coperta = sum(
            ((_dec(e.get("quota_coperta")) or Decimal(0)) for e in esiti), Decimal(0)
        )
        ordinaria = sum(
            ((_dec(e.get("quota_ordinaria")) or Decimal(0)) for e in esiti), Decimal(0)
        )
        if coperta <= 0:
            # Il titolo non copriva piu' niente: il gruppo resta ordinario.
            return {"spezzate": 0, "movimenti": movimenti}

        if ordinaria <= 0:
            # Copertura piena: ogni riga resta una, con l'IVA del titolo.
            for riga in gruppo:
                self.repository.aggiorna_capofila_plafond(
                    riga_id=int(riga["id"]),
                    qta=_dec(riga.get("qta")) or Decimal(0),
                    iva_id=parte_titolo.get("iva_id"),
                    kit_qta=_dec(riga.get("kit_qta")),
                    meta=_meta_parte(dict(riga.get("meta") or {}), parte_titolo),
                )
            return {"spezzate": 0, "movimenti": movimenti}

        parte_ordinaria = self._parte_ordinaria(
            parti, resolver=resolver, argomenti=argomenti, residuo=ordinaria,
            riga_id=int(capo["id"]),
        )
        # ⭐ La frazione e' UNA per il gruppo, e la dice la madre: e' la quota
        #    coperta effettiva sul totale, quella con cui ha diviso le righe.
        frazione = next(iter(frazioni))
        _richiedi(
            frazione is not None and Decimal(0) < frazione < Decimal(1),
            message="Ripartizione del plafond incoerente.",
            detail=(
                f"fattura {fattura_id}: copertura parziale con frazione "
                f"{frazione} fuori da (0, 1)"
            ),
            fattura_id=fattura_id,
        )
        assert frazione is not None
        for riga in gruppo:
            esito = quote.get(int(riga["id"]))
            self._spezza(
                fattura_id=fattura_id,
                riga=riga,
                coperta=_dec(esito.get("quota_coperta")) if esito else None,
                frazione=frazione,
                parte_titolo=parte_titolo,
                parte_ordinaria=parte_ordinaria,
            )
        return {"spezzate": len(gruppo), "movimenti": movimenti}

    # Scopo: la PARTE non coperta — aliquota e origine insieme, mai separate.
    # ⚠️ Di norma la porta il risolutore nella seconda parte. Ma se la madre ha
    #    coperto MENO di quanto il risolutore proiettava — un'altra transazione
    #    ha consumato nel frattempo — quella seconda parte puo' non esserci, e
    #    va richiesta. ⭐ Si richiede alla STESSA autorita', non si inventa: a
    #    plafond ormai esaurito il risolutore risponde con lo stadio A.
    #
    # ⛔ E SE NEMMENO LA SECONDA RISPOSTA HA UNA PARTE SENZA TITOLO, CI SI
    #    FERMA. Il ripiego «prendi la prima parte» era un difetto vero: quella
    #    prima parte e' proprio quella DEL TITOLO, quindi avrebbe scritto
    #    l'aliquota agevolata sulla quota che il plafond NON copre — cioe'
    #    un'esenzione non dovuta, su una fattura, senza nessun sintomo.
    def _parte_ordinaria(
        self,
        parti: list[dict[str, Any]],
        *,
        resolver: Any,
        argomenti: dict[str, Any],
        residuo: Decimal,
        riga_id: int,
    ) -> dict[str, Any]:
        for p in parti:
            if not p.get("titolo_iva_id"):
                return p
        logger.warning(
            "plafond: la copertura effettiva e' minore della proiezione, "
            "la parte ordinaria viene richiesta di nuovo (riga=%s residuo=%s)",
            riga_id, residuo,
        )
        for p in resolver.risolvi(imponibile=residuo, **argomenti):
            if not p.get("titolo_iva_id"):
                return p
        ErrorManager.raise_error(
            code=_E_VALIDATION,
            message="Trattamento IVA non determinabile.",
            detail=(
                f"riga {riga_id}: il titolo copre solo una quota ma il "
                "risolutore non restituisce una parte ordinaria per il residuo "
                f"{residuo}"
            ),
            context={"riga_id": riga_id},
            function_name=_FN,
            log_to_db=True,
        )

    # Scopo: scrive le due parti. La CAPOFILA resta la riga esistente e prende
    #        la quota coperta; la parte nuova prende il resto.
    #
    # ⭐ LA QUANTITA' SI DERIVA DALL'IMPONIBILE, ed e' il metodo scelto da Tid:
    #    `qta = imponibile / prezzo_effettivo` e' l'inverso esatto della formula
    #    con cui il DB calcola `imponibile_riga`. In aritmetica esatta
    #    l'imponibile ricalcolato E' la quota, e il centesimo sparisce.
    #    Una riga che non ha consumato (`coperta` None: imponibile zero o
    #    negativo, solo in un kit) non ha una quota da invertire: prende la
    #    frazione del kit sulla quantita'.
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
        qta_totale = _dec(riga.get("qta")) or Decimal(0)
        if coperta is None:
            qta_coperta = _ESATTO.multiply(qta_totale, frazione)
        else:
            prezzo_eff = _prezzo_effettivo(riga)
            _richiedi(
                prezzo_eff is not None and prezzo_eff > 0,
                message="Riga non spezzabile.",
                detail=(
                    f"riga {riga.get('id')}: prezzo effettivo nullo o negativo, "
                    "la quantita' della parte coperta non e' derivabile"
                ),
                fattura_id=fattura_id,
                riga_id=riga.get("id"),
            )
            assert prezzo_eff is not None
            qta_coperta = coperta / prezzo_eff
        qta_residua = qta_totale - qta_coperta

        kit_qta = _dec(riga.get("kit_qta"))
        kit_qta_coperta = (
            None if kit_qta is None else _ESATTO.multiply(kit_qta, frazione)
        )
        kit_qta_residua = (
            None if kit_qta is None else _ESATTO.subtract(kit_qta, kit_qta_coperta)
        )

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


# Scopo: le righe di una fattura raggruppate per CONSUMO: i componenti di un
#        kit (stessa `kit_key`) insieme, ogni riga sciolta da sola.
# ⚠️ Nell'ordine della prima riga di ogni gruppo, e dentro il gruppo in quello
#    di arrivo (`riga_nr`): e' l'ordine in cui la madre li vuole (R-BE-P3) e
#    quello in cui il plafond si consuma fra gruppi.
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
