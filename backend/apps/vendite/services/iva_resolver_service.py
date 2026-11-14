# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Facade del risolutore IVA di riga — la SEDE UNICA da cui i domini
#        vendite (preventivi, ordini, DDT, e poi la fattura) ottengono il
#        trattamento fiscale di una riga.
#
#        ⛔ LA REGOLA CHE QUESTO MODULO ESISTE PER TENERE: mai leggere
#        `catalogo.articoli.iva_id` in un service di dominio. E' il gemello
#        della regola gia' scritta per `PricingService` («mai leggere
#        `listini_righe.prezzo`»), e nasce dallo stesso difetto: tre
#        `onArticoloSelect` e una proiezione di pipeline che rispondevano
#        ognuno per conto suo alla stessa domanda.
#
#        Il risolutore vive INTERAMENTE nel DB (`vendite.fn_resolve_iva_riga`,
#        due stadi + guscio che smista per paese). Qui si fa solo: il guard
#        di chiamata, la traduzione degli errori DB, e la normalizzazione del
#        composito per il trasporto JSON.
#
#        Brief: docs/it/dev/work-in-progress/
#               brief-be-fe-iva-fase-3-consumatori-risolutore.md (F2-a)
# ------------------------------------------------------------

from __future__ import annotations

import logging
from datetime import date
from typing import Any
from uuid import UUID

from django.db import transaction

from apps.anagrafiche.db.billing_account_repository import BillingAccountRepository
from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import translate_db_errors
from apps.vendite.db.iva_resolver_repository import IvaResolverRepository

__all__ = [
    "IvaResolverService",
    "ORIGINE_ASSENTE",
    "ORIGINE_MANUALE",
    "ORIGINE_TITOLO",
]

logger = logging.getLogger(__name__)

# ⭐ Guard di parametro su valori che NESSUNA interfaccia puo' produrre.
#    TECNICO e non DATO_ERRATO: se arrivano, e' rotto il chiamante e
#    l'operatore non ha niente da correggere. E' la sede dichiarata dal
#    catalogo per questa specie — non si riusa `E_PARAMETRO_INVALIDO`, che
#    e' uno split rimandato (D11 di brief-db-be-classe-codici-errore).
_E_CHIAMATA = "E_VENDITE_CHIAMATA_NON_VALIDA"

# Il vocabolario di `origine` e' del DB ed e' APERTO: qui si nominano i due
# valori su cui il backend prende una decisione, non tutti. Gli altri
# viaggiano verso il client come stringhe e il frontend li risolve con
# ripiego sul codice grezzo.
ORIGINE_ASSENTE = "ASSENTE"
ORIGINE_TITOLO = "TITOLO"
# ⛔ VALORE NOSTRO, NON DEL VOCABOLARIO DB. `origine` a catalogo dice da dove
#    viene l'aliquota (`ARTICOLO`, `TIPO_UTENZA`, `TITOLO`, `ASSENTE`) e non ha
#    un valore per «l'ha scelto una persona» — non puo' averlo, perche' il
#    risolutore non sa che esiste un operatore. Sta nel `meta`, che e' roba
#    nostra, e va cercato qui e non in `config`.
ORIGINE_MANUALE = "MANUALE"

_FN = "iva_resolver_service.risolvi"


class IvaResolverService:
    def __init__(
        self,
        repo: IvaResolverRepository | None = None,
        ba_repo: BillingAccountRepository | None = None,
    ) -> None:
        # Repository iniettabili per i test; nessuno stato condiviso fra
        # chiamate (`feedback_estrarre_non_condividere_stato`).
        self._repo = repo or IvaResolverRepository()
        self._ba_repo = ba_repo or BillingAccountRepository()

    # Scopo: Restituisce la RIPARTIZIONE del trattamento IVA di una riga —
    #        obiettivo, perimetro e risultato atteso.
    #
    #        Obiettivo: dare al chiamante il composito che il DB ha risolto
    #        (aliquota, natura, inversione contabile, esigibilita', split
    #        payment, riferimento normativo, origine, titolo), gia' pronto
    #        per essere scritto su una riga o serializzato.
    #
    #        Perimetro: SOLA LETTURA. Il risolutore e' `STABLE` e NON consuma
    #        il plafond (D14): dice quale titolo vale, non quanto copre. Il
    #        consumo e' un'altra funzione, e avviene all'emissione.
    #
    #        Risultato: una lista di 1 o 2 parti. **Due solo nella domanda di
    #        consumo** (`consumo=True`) e solo con un titolo a tetto: prima il
    #        titolo, poi l'ordinario. Nell'anteprima la lista ha sempre un
    #        elemento solo (P1).
    #
    #        ⛔ Niente piu' importo. La domanda di PROIEZIONE (la spezzatura sul
    #        residuo del momento) aveva un solo chiamante, il giro del plafond,
    #        che e' passato al consumo sul netto (decisione C, brief-db-bom-
    #        flag-quantita-e-kit-in-fattura §13): sul netto la proiezione per
    #        riga e' sbagliata per costruzione, perche' il netto lo sa solo chi
    #        consuma.
    #
    #        ⛔ `emittente_fiscale_id` E' OBBLIGATORIO, ed e' la ragione per
    #        cui questo metodo esiste invece di lasciar chiamare il repo.
    #        La funzione DB e' SECURITY INVOKER e legge una tabella con RLS:
    #        senza contesto emittente legge ZERO titoli e risponde con
    #        l'aliquota ordinaria SENZA sollevare. Non e' una lista piu'
    #        corta: e' un'imposta applicata dove non andava, su un documento
    #        che nessuno segnalera'. Un operatore ha SEMPRE un emittente
    #        (decisione di Tid, P3): se manca, qui ci si ferma.
    def risolvi(
        self,
        *,
        articolo_id: UUID | str,
        data_riferimento: date,
        emittente_fiscale_id: int,
        consumo: bool = False,
        billing_account_id: int | None = None,
        utility_id: int | None = None,
        soggetto_id: UUID | str | None = None,
    ) -> list[dict[str, Any]]:
        self._guard_chiamata(
            articolo_id=articolo_id,
            data_riferimento=data_riferimento,
            emittente_fiscale_id=emittente_fiscale_id,
            consumo=consumo,
        )

        # ⛔ IL SOGGETTO SI DERIVA DAL BA, E NON E' UNA COMODITA'.
        #    `fn_resolve_iva_riga_it` applica lo STADIO B — i titoli
        #    documentati, cioe' le dichiarazioni d'intento — solo quando
        #    riceve INSIEME soggetto ed emittente, e il soggetto dal billing
        #    account NON lo deriva (a differenza del paese, che il guscio
        #    deriva da se'). Un chiamante che ha in mano il solo BA — il caso
        #    ordinario di un form — otterrebbe l'aliquota ordinaria e NIENTE
        #    segnalerebbe che i titoli non sono stati nemmeno guardati.
        # ⭐ Si deriva QUI e non in ogni consumatore: e' la ragione per cui
        #    questo BB esiste. Lasciarlo ai chiamanti vuol dire che il primo
        #    che se lo dimentica applica l'IVA piena a un cliente esportatore
        #    abituale, e il documento non porta traccia dell'omissione.
        if soggetto_id is None and billing_account_id is not None:
            soggetto_id = self._ba_repo.get_soggetto_id(billing_account_id)

        # ⭐ Nessun elenco di codici da riconoscere, e non e' una semplifica-
        #    zione: dal 2026-08-05 il codice di dominio viaggia in un CAMPO
        #    STRUTTURATO dell'eccezione (`CONSTRAINT` su SQLSTATE P0001), che
        #    `translate_db_errors` legge da se'. Ricopiare qui i codici del
        #    risolutore sarebbe duplicare il catalogo — ed e' esattamente il
        #    debito che `pricing_service._KNOWN_DB_ERROR_MARKERS` dichiara nel
        #    proprio commento come «da togliere quando quel refactor sara'
        #    fatto». E' fatto.
        with translate_db_errors(
            context={"op": _FN, "articolo_id": str(articolo_id)},
            fallback_code=_E_CHIAMATA,
            fallback_message=(
                "Il risolutore IVA non ha potuto rispondere per questa riga."
            ),
        ):
            parti = self._repo.resolve(
                articolo_id=articolo_id,
                data_riferimento=data_riferimento,
                consumo=consumo,
                billing_account_id=billing_account_id,
                utility_id=utility_id,
                soggetto_id=soggetto_id,
                emittente_fiscale_id=emittente_fiscale_id,
            )

        # ⛔ Zero righe e' un'INVARIANTE ROTTA, non un «nessun risultato»: il
        #    contratto della funzione e' «una riga esce sempre», e quando non
        #    trova nulla lo dice con `origine = 'ASSENTE'` invece di tacere.
        #    Senza questo guard il chiamante leggerebbe «nessuna IVA» dove in
        #    realta' non ha letto niente. Stessa forma del guard gemello di
        #    `PricingRepository.resolve_prezzo_listino_v2_esito`.
        ErrorManager.require(
            bool(parti),
            code=_E_CHIAMATA,
            message="Il risolutore IVA non ha restituito nessuna riga.",
            context={"op": _FN, "articolo_id": str(articolo_id)},
            function_name=_FN,
        )

        # ⚠️ La FORMA della risposta e' contratto, e chi la legge non deve
        #    poterla fraintendere:
        #    * anteprima -> UNA parte. Se ne arrivassero due il ramo si sarebbe
        #      rotto, e il difetto sarebbe MUTO: il chiamante prende la prima e
        #      non sa di aver perso l'altra;
        #    * consumo -> una parte (nessun titolo, o titolo senza tetto) o due,
        #      la prima COL titolo e la seconda SENZA. Il giro scrive la seconda
        #      sulla quota che il plafond non copre: un titolo anche li' sarebbe
        #      un'esenzione non dovuta, senza nessun sintomo.
        ErrorManager.require(
            len(parti) == 1
            or (
                consumo
                and len(parti) == 2
                and bool(parti[0].get("titolo_iva_id"))
                and not parti[1].get("titolo_iva_id")
            ),
            code=_E_CHIAMATA,
            message="Il risolutore IVA ha restituito una ripartizione non attesa.",
            context={"op": _FN, "parti": len(parti), "consumo": consumo},
            function_name=_FN,
        )
        return parti

    # Scopo: Il trattamento «sul primo euro» per un form — una parte sola,
    #        mai una ripartizione. E' la forma che i DOCUMENTI usano (P1) e
    #        quella che alimenta l'anteprima del frontend.
    #
    #        ⚠️ Non e' la domanda di consumo presa alla prima parte: quella
    #        darebbe il titolo anche a plafond esaurito (il consumo non legge
    #        il residuo) e applicherebbe l'esenzione a tutta la riga — il
    #        difetto opposto a quello che P1 evita.
    def risolvi_anteprima(
        self,
        *,
        articolo_id: UUID | str,
        data_riferimento: date,
        emittente_fiscale_id: int,
        billing_account_id: int | None = None,
        utility_id: int | None = None,
        soggetto_id: UUID | str | None = None,
    ) -> dict[str, Any]:
        parti = self.risolvi(
            articolo_id=articolo_id,
            data_riferimento=data_riferimento,
            emittente_fiscale_id=emittente_fiscale_id,
            consumo=False,
            billing_account_id=billing_account_id,
            utility_id=utility_id,
            soggetto_id=soggetto_id,
        )
        return parti[0]

    # Scopo: Il sottoinsieme del composito che sopravvive sulla RIGA di
    #        documento, da fondere nel suo `meta` (P2).
    #
    #        ⭐ Due chiavi e non nove, e la scelta ha un criterio: qui stanno
    #        i fatti che NESSUNO puo' ricostruire dopo — perche' l'ha decisi
    #        il risolutore in quel momento. Aliquota, natura e riferimento
    #        normativo si DERIVANO da `iva_id` con il JOIN su `config.iva`
    #        che i repository di riga fanno gia': copiarli qui creerebbe una
    #        frase che invecchia, ed e' il difetto per cui
    #        `fatture_righe.iva_perc` era stata tolta.
    @staticmethod
    def meta_riga(parte: dict[str, Any]) -> dict[str, Any]:
        return {
            "iva_origine": parte.get("origine"),
            "iva_titolo_id": parte.get("titolo_iva_id"),
        }

    # Scopo: Guard di chiamata — i valori che nessuna interfaccia produce.
    @staticmethod
    def _guard_chiamata(
        *,
        articolo_id: UUID | str,
        data_riferimento: date,
        emittente_fiscale_id: int,
        consumo: bool,
    ) -> None:
        ErrorManager.require(
            bool(articolo_id),
            code=_E_CHIAMATA,
            message="Parametro obbligatorio mancante: articolo_id.",
            context={"op": _FN, "parametro": "articolo_id"},
            function_name=_FN,
        )
        ErrorManager.require(
            isinstance(data_riferimento, date),
            code=_E_CHIAMATA,
            message="Parametro obbligatorio mancante o non valido: data_riferimento.",
            context={"op": _FN, "parametro": "data_riferimento"},
            function_name=_FN,
        )
        # ⛔ Il guard che vale tutti gli altri (P3). Vedi il docstring di
        #    `risolvi`: senza emittente il DB non sbaglia — risponde bene a
        #    una domanda diversa da quella che gli e' stata fatta.
        ErrorManager.require(
            isinstance(emittente_fiscale_id, int)
            and not isinstance(emittente_fiscale_id, bool)
            and emittente_fiscale_id > 0,
            code=_E_CHIAMATA,
            message=(
                "Parametro obbligatorio mancante o non valido: "
                "emittente_fiscale_id."
            ),
            context={"op": _FN, "parametro": "emittente_fiscale_id"},
            function_name=_FN,
        )
        # ⚠️ Il NULL lo rifiuta anche il DB; qui si intercetta prima per non
        #    spendere un round-trip su una chiamata rotta.
        ErrorManager.require(
            isinstance(consumo, bool),
            code=_E_CHIAMATA,
            message="Parametro non valido: consumo.",
            context={"op": _FN, "parametro": "consumo"},
            function_name=_FN,
        )

    # Scopo: Decidere l'`iva_id` da scrivere su una riga di DOCUMENTO e il
    #        `meta` che lo spiega — obiettivo, perimetro, risultato.
    #
    #        Obiettivo: dare ai tre service di dominio (preventivi, ordini,
    #        DDT) un solo punto in cui l'IVA di riga si decide, invece di tre
    #        copie della stessa regola.
    #
    #        ⭐ LA REGOLA E' «IL PAYLOAD VINCE, MA SI REGISTRA COSA AVREBBE
    #        DETTO IL RISOLUTORE» (decisione di Tid, 2026-08-31, opzione B).
    #        Finche' `I6` non chiude la casella, l'operatore puo' ancora
    #        scegliere l'aliquota a mano: ignorare quella scelta la farebbe
    #        sparire SENZA DIRLO, e renderebbe `I6` una chiusura senza niente
    #        da chiudere. Con questa forma `I6` diventa letteralmente «togli
    #        la chiave dalla whitelist», e nient'altro.
    #
    #        ⚠️ LE DUE RISOLUZIONI NON HANNO LO STESSO PESO, ed e' il pezzo che
    #        non si vede leggendo il codice in fretta:
    #
    #        * payload SENZA `iva_id` -> la risoluzione e' AUTORITATIVA e gli
    #          errori PASSANO. Se il risolutore non sa rispondere, la riga non
    #          si scrive con un'IVA inventata: si ferma;
    #        * payload CON `iva_id` -> la risoluzione e' di AUDIT, best-effort,
    #          dentro un savepoint. Un titolo ambiguo o un paese non
    #          implementato non devono bloccare un salvataggio che l'operatore
    #          ha gia' determinato (era lo stesso idioma dell'audit del
    #          prezzo al push, ritirato il 2026-11-14).
    #
    #        Risultato: `(iva_id, meta_patch)` — il secondo da fondere nel
    #        `meta` della riga.
    def applica_riga_documento(
        self,
        *,
        payload_iva_id: int | None,
        articolo_id: UUID | str,
        data_riferimento: date,
        emittente_fiscale_id: int,
        billing_account_id: int | None = None,
        utility_id: int | None = None,
        soggetto_id: UUID | str | None = None,
    ) -> tuple[int | None, dict[str, Any]]:
        argomenti = {
            "articolo_id": articolo_id,
            "data_riferimento": data_riferimento,
            "emittente_fiscale_id": emittente_fiscale_id,
            "billing_account_id": billing_account_id,
            "utility_id": utility_id,
            "soggetto_id": soggetto_id,
        }

        # 📌 DAL 2026-08-31 (`I6`) I TRE DOMINI PASSANO SEMPRE `None`, e
        #    `make_risolvi_iva_riga` RIFIUTA il resto: il ramo di audit qui
        #    sotto e' quindi IRRAGGIUNGIBILE dai documenti di vendita.
        # ⚠️ Non e' stato tolto — e' la decisione `P10-bis` (opzione B) resa in
        #    codice, e serve al primo chiamante che avesse un override
        #    legittimo. Ma va saputo: i suoi test provano una strada che oggi
        #    nessuno percorre, quindi non difendono nessun percorso vivo.
        #    Il ritiro e' una decisione di Tid, non una pulizia da fare qui.
        if payload_iva_id is None:
            # Autoritativa: se non sa rispondere, meglio fermarsi che scrivere
            # una riga senza IVA fingendo che sia una scelta.
            parte = self.risolvi_anteprima(**argomenti)  # type: ignore[arg-type]
            return parte.get("iva_id"), self.meta_riga(parte)

        parte_audit: dict[str, Any] | None = None
        try:
            # Savepoint isolato: l'audit non deve abortire la transazione di
            # chi sta salvando la riga.
            with transaction.atomic():
                parte_audit = self.risolvi_anteprima(**argomenti)  # type: ignore[arg-type]
        except Exception as exc:  # best-effort: l'audit e' diagnostico
            logger.warning(
                "Audit IVA non risolto (il salvataggio prosegue) articolo_id=%s: %s: %s",
                articolo_id, type(exc).__name__, exc,
            )

        if parte_audit is None:
            return payload_iva_id, {}

        meta = self.meta_riga(parte_audit)
        # ⚠️ «Diverge» e non «e' stato passato»: se l'operatore conferma il
        #    valore che il risolutore proponeva, non ha sovrascritto niente —
        #    e marcarlo `MANUALE` renderebbe manuale l'intero traffico del
        #    form, cioe' toglierebbe al campo ogni capacita' di dire qualcosa.
        if parte_audit.get("iva_id") != payload_iva_id:
            meta["iva_origine"] = ORIGINE_MANUALE
            meta["iva_titolo_id"] = None
        return payload_iva_id, meta

