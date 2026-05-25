# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service facade per vendite.offerte_commerciali + eccezioni +
#        utility 1:1 (CRUD iniziale, step DB 1-4 atterrati 2026-05-24).
#
#        L'offerta commerciale e' il documento pre-contrattuale: vive nel
#        ciclo BOZZA -> EMESSA -> (ACCETTATA | RIFIUTATA | SUPERATA) +
#        terminale di ritiro BOZZA -> ANNULLATA. La state machine e' enforced
#        dal trigger DB trgfn_offerte_commerciali_guard_transizione; il
#        service applica solo pre-validazioni applicative (stato corrente,
#        payload obbligatorio motivazione su RIFIUTATA/ANNULLATA) e lascia
#        al DB le invarianti complesse (listino_versione_id NULL in
#        emissione, listino non ATTIVO, transizione non ammessa, ecc.).
#
#        Out of scope iniziale (in attesa step DB 5-8):
#          - generazione codice OFC-* via sistema_codici (step 5):
#            il payload deve includere `codice` esplicito.
#          - crea_revisione (step 7), push_a_contratto (step 8): non esposti.
# ------------------------------------------------------------

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from django.db import DatabaseError, IntegrityError, transaction

from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import (
    PayloadValidator,
    map_integrity_error,
)
from apps.vendite.db.offerte_repository import OfferteRepository

logger = logging.getLogger(__name__)


# Codici errore applicativi (registrati in apps.core.services.error_policies).
# Riusiamo E_VENDITE_* per coerenza con preventivi/contratti; i codici DB
# specifici (E_OFFERTA_TRANSIZIONE_NON_AMMESSA, ecc.) emergono dal trigger
# guard e vengono mappati dal middleware API (P0001 -> 422 con codice
# applicativo passato dal RAISE EXCEPTION del DB).
E_VENDITE_VALIDATION = "E_VENDITE_VALIDATION"
E_VENDITE_NOT_FOUND = "E_VENDITE_NOT_FOUND"
E_VENDITE_DUPLICATO = "E_VENDITE_DUPLICATO"
E_VENDITE_FK = "E_VENDITE_FK"


# Pattern per estrarre il codice errore applicativo dal MESSAGE dei trigger
# DB. Convenzione progetto: `RAISE EXCEPTION USING MESSAGE='E_OFFERTA_XXX'`.
# Il primo token con underscore in maiuscolo che inizia per E_ e' il codice.
_DB_ERROR_CODE_RE = re.compile(r"\b(E_[A-Z][A-Z0-9_]+)\b")


# Codici stato documento (chiavi naturali `codice_interno` in
# config.stati_doc_offerte). Usate per:
#  - lookup id stato target via `get_stato_id_by_codice`
#  - assertion di stato corrente nelle transizioni
#  - test (fixtures + asserzioni)
class StatoOfferta:
    BOZZA = "BOZZA"
    EMESSA = "EMESSA"
    ACCETTATA = "ACCETTATA"
    RIFIUTATA = "RIFIUTATA"
    ANNULLATA = "ANNULLATA"
    SUPERATA = "SUPERATA"


# Set di stati editabili (testata, eccezioni, utility). Estraibile in futuro
# se le regole differenziassero per oggetto (oggi e' "solo BOZZA").
_STATI_EDITABILI: frozenset[str] = frozenset({StatoOfferta.BOZZA})


# Set di esiti cliente da EMESSA (used by registra_esito routing).
_ESITI_AMMESSI_DA_EMESSA: frozenset[str] = frozenset(
    {StatoOfferta.ACCETTATA, StatoOfferta.RIFIUTATA}
)


_ORDER_BY_OFFERTE: frozenset[str] = frozenset({
    "codice",
    "validita_dal",
    "validita_al",
    "data_emissione",
    "ba_ragione_sociale",
    "stato_codice",
    "data_insert",
    "data_update",
})


# Stati terminali (no editing, no transizioni uscenti).
_STATI_TERMINALI: frozenset[str] = frozenset(
    {"ACCETTATA", "RIFIUTATA", "ANNULLATA", "SUPERATA"}
)


# UNIQUE constraints catalogati per mappare violazioni IntegrityError.
# Formato richiesto da `map_integrity_error`: tuple[error_code, message].
_UNIQUE_CONSTRAINTS: dict[str, tuple[str, str]] = {
    "uq_offerte_commerciali_codice": (
        E_VENDITE_DUPLICATO,
        "Codice offerta gia' esistente.",
    ),
    "uq_offerte_commerciali_uid": (
        E_VENDITE_DUPLICATO,
        "UID offerta gia' esistente.",
    ),
    "uq_offerte_commerciali_utilities_offerta_id": (
        E_VENDITE_DUPLICATO,
        "Esiste gia' un record utility per questa offerta (1:1).",
    ),
    "uq_offerte_eccezioni_one_eccezione_per_articolo": (
        E_VENDITE_DUPLICATO,
        "Esiste gia' un'eccezione OVERRIDE/ESCLUSIONE per questo articolo "
        "nell'offerta.",
    ),
    "uq_offerte_eccezioni_one_aggiunta_per_articolo": (
        E_VENDITE_DUPLICATO,
        "Esiste gia' un'eccezione AGGIUNTA per questo articolo nell'offerta.",
    ),
}


# FK constraints catalogati (best-effort: i nomi corrispondono a quelli
# emessi da Postgres su violazione FK).
_FK_CONSTRAINTS: dict[str, tuple[str, str]] = {
    "fk_offerte_commerciali_billing_account": (
        E_VENDITE_FK, "Billing account non trovato.",
    ),
    "fk_offerte_commerciali_emittente_fiscale": (
        E_VENDITE_FK, "Emittente fiscale non trovato.",
    ),
    "fk_offerte_commerciali_listino": (
        E_VENDITE_FK, "Listino non trovato.",
    ),
    "fk_offerte_commerciali_listino_versione": (
        E_VENDITE_FK, "Versione listino non trovata.",
    ),
    "fk_offerte_commerciali_istanza_utility": (
        E_VENDITE_FK, "Istanza utility non trovata.",
    ),
    "fk_offerte_commerciali_utility": (
        E_VENDITE_FK, "Utility non trovata.",
    ),
    "fk_offerte_eccezioni_articolo": (
        E_VENDITE_FK, "Articolo non trovato.",
    ),
    "fk_offerte_eccezioni_offerta": (
        E_VENDITE_FK, "Offerta non trovata.",
    ),
}


# Whitelist payload create offerta (testata).
_CREATE_KEYS_OFFERTA: frozenset[str] = frozenset({
    "codice",
    "emittente_fiscale_id",
    "billing_account_id",
    "istanza_utility_id",
    "utility_id",
    "listino_id",
    "listino_versione_id",
    "valore_variazione_globale",
    "tipo_variazione_globale",
    "validita_dal",
    "validita_al",
    "meta",
})


# Whitelist payload update offerta (testata). Sub-set di create (immutabili:
# codice/uid/stato_doc_offerta_id/revisione_numero/revisione_padre_id e
# tutti i campi audit/timestamp di transizione).
_UPDATE_KEYS_OFFERTA: frozenset[str] = frozenset({
    "emittente_fiscale_id",
    "billing_account_id",
    "istanza_utility_id",
    "utility_id",
    "listino_id",
    "listino_versione_id",
    "valore_variazione_globale",
    "tipo_variazione_globale",
    "validita_dal",
    "validita_al",
    "meta",
})


# Whitelist payload eccezione (create).
_CREATE_KEYS_ECCEZIONE: frozenset[str] = frozenset({
    "articolo_id",
    "tipo_eccezione",
    "tipo_erogazione",
    "fonte_quantita_attesa",
    "periodicita",
    "generazione_canone",
    "competenza_canone",
    "prezzo_unitario",
    "quantita",
    "qta_operativa",
    "uom_operativa_id",
    "factor_to_base",
    "ordine",
    "attivo",
    "meta",
})


# Whitelist payload eccezione (update): articolo_id e tipo_eccezione immutabili.
_UPDATE_KEYS_ECCEZIONE: frozenset[str] = frozenset(
    _CREATE_KEYS_ECCEZIONE - {"articolo_id", "tipo_eccezione"}
)


# Whitelist payload utility (create).
_CREATE_KEYS_UTILITY: frozenset[str] = frozenset({
    "istanza_utility_id",
    "utility_id",
    "istanza_dati_precontrattuali_id",
    "tipo_utenza_id",
    "classe_utenza_id",
    "param_1_num",
    "param_2_txt",
    "meta",
})


# Whitelist payload utility (update): istanza_utility_id/utility_id immutabili.
_UPDATE_KEYS_UTILITY: frozenset[str] = frozenset(
    _CREATE_KEYS_UTILITY - {"istanza_utility_id", "utility_id"}
)


class OfferteService:
    """Service CRUD offerte commerciali (D4: solo scope DB consegnato)."""

    def __init__(self) -> None:
        self._repo = OfferteRepository()
        self._v = PayloadValidator(
            validation_code=E_VENDITE_VALIDATION,
            log_to_db=True,
            function_name="offerte_service",
        )

    # =================================================================
    # Guard DB errors uniforme
    # =================================================================

    # Scopo: Normalizza errori DB (IntegrityError + DatabaseError P0001 dei
    #        trigger guard) in ServiceError. Il trigger
    #        trgfn_offerte_commerciali_guard_transizione solleva con codici
    #        applicativi gia' parlanti (E_OFFERTA_*), che il middleware
    #        propaga al client come 422.
    @contextmanager
    def _db_errors(
        self,
        context: dict[str, Any],
        *,
        fallback_message: str = "Violazione vincolo DB su offerta.",
    ) -> Iterator[None]:
        try:
            yield
        except IntegrityError as exc:
            map_integrity_error(
                exc,
                unique_constraints=_UNIQUE_CONSTRAINTS,
                fk_constraints=_FK_CONSTRAINTS,
                fallback_code=E_VENDITE_VALIDATION,
                fallback_message=fallback_message,
                context=context,
            )
        except DatabaseError as exc:
            # I trigger guard sollevano con codici E_OFFERTA_* parlanti come
            # MESSAGE del RAISE EXCEPTION. Li estraiamo dal messaggio dell'
            # eccezione cosi' che il FE possa fare routing UI specifico
            # (es. mostrare dialog "versione listino non ATTIVA" diverso da
            # "transizione non ammessa"). Se non troviamo il codice (es.
            # errore tecnico non dei nostri trigger) cade su E_VENDITE_VALIDATION.
            exc_text = str(exc)
            match = _DB_ERROR_CODE_RE.search(exc_text)
            code = match.group(1) if match else E_VENDITE_VALIDATION
            ErrorManager.raise_error(
                code=code,
                message=exc_text.split("\n", maxsplit=1)[0].strip()
                or fallback_message,
                detail=exc_text,
                context=context,
            )

    # =================================================================
    # Lista e dettaglio
    # =================================================================

    # Scopo: Lista paginata offerte. Niente default temporali impliciti: la UI
    #        applica i propri (es. validita_dal_min = inizio anno-1).
    def list_offerte(
        self,
        *,
        search: str | None = None,
        billing_account_id: int | None = None,
        stato_codice_interno: str | None = None,
        utility_id: int | None = None,
        listino_id: int | None = None,
        validita_dal_min: str | None = None,
        validita_dal_max: str | None = None,
        limit: int = 25,
        offset: int = 0,
        order_by: str = "data_insert",
        order_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        self._v.validate_order_by(order_by, allowed=_ORDER_BY_OFFERTE)
        # `search` vuoto/whitespace-only -> trattato come "no filter" (coerente
        # con come la UI passa il campo: stringa vuota = filtro non applicato).
        # Solo se l'utente fornisce una stringa non vuota richiediamo >=3 char.
        search_norm = search.strip() if isinstance(search, str) else None
        if search_norm:
            ErrorManager.require(
                len(search_norm) >= 3,
                code=E_VENDITE_VALIDATION,
                message="Ricerca testuale: minimo 3 caratteri.",
                context={"search_len": len(search_norm)},
            )
        else:
            search_norm = None
        filters: dict[str, Any] = {
            "billing_account_id": billing_account_id,
            "stato_codice_interno": stato_codice_interno,
            "utility_id": utility_id,
            "listino_id": listino_id,
            "validita_dal_min": validita_dal_min,
            "validita_dal_max": validita_dal_max,
            "search": search_norm,
        }
        rows = self._repo.list_offerte(
            **filters,
            order_by=order_by,
            order_dir=order_dir,
            limit=limit,
            offset=offset,
        )
        total = self._repo.count_offerte(**filters)
        return rows, total

    # Scopo: Dettaglio offerta + eccezioni + utility 1:1 (read-after-write
    #        amichevole per il drawer FE).
    def get_offerta(self, offerta_id: int) -> dict[str, Any]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        row = self._repo.get_offerta(offerta_id)
        ErrorManager.require(
            row is not None,
            code=E_VENDITE_NOT_FOUND,
            message="Offerta non trovata.",
            context={"offerta_id": offerta_id},
        )
        assert row is not None
        row["eccezioni"] = self._repo.list_eccezioni(offerta_id)
        row["utility"] = self._repo.get_utility(offerta_id)
        return row

    # =================================================================
    # Create / Update / Delete testata
    # =================================================================

    # Scopo: Crea offerta in stato BOZZA. Il `codice` arriva dal payload
    #        finche' lo step 5 brief DB (numerazione OFC-*) non e' atterrato:
    #        in v1 lo genera la UI o e' obbligatorio dal client. Lo stato
    #        BOZZA si risolve via lookup `codice_interno`.
    def crea_offerta(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._v.validate_allowed_keys(payload, allowed=_CREATE_KEYS_OFFERTA)
        # Validazioni applicative minime (il DB rifinisce gli invarianti via
        # CHECK chk_offerte_*).
        for required in (
            "codice",
            "emittente_fiscale_id",
            "billing_account_id",
            "istanza_utility_id",
            "utility_id",
            "listino_id",
            "validita_dal",
        ):
            ErrorManager.require(
                required in payload and payload[required] not in (None, ""),
                code=E_VENDITE_VALIDATION,
                message=f"Campo '{required}' obbligatorio in creazione.",
                context={"field": required},
            )
        stato_bozza_id = self._repo.get_stato_id_by_codice(StatoOfferta.BOZZA)
        ErrorManager.require(
            stato_bozza_id is not None,
            code=E_VENDITE_VALIDATION,
            message="Stato BOZZA non configurato in config.stati_doc_offerte.",
        )
        assert stato_bozza_id is not None
        data: dict[str, Any] = dict(payload)
        data["stato_doc_offerta_id"] = stato_bozza_id
        # `revisione_numero` ha default DB = 1 (vedi tabella offerte_commerciali).
        # Non e' in _CREATE_KEYS_OFFERTA quindi un payload con quella chiave
        # avrebbe gia' fallito la whitelist. Niente setdefault qui.
        with self._db_errors({"codice": payload.get("codice")}):
            with transaction.atomic():
                offerta_id = self._repo.create_offerta(data)
        return self.get_offerta(offerta_id)

    # Scopo: Aggiorna la testata di un'offerta. Editabilita' solo in stato
    #        BOZZA — defense-in-depth applicativa; il trigger DB blocca
    #        comunque cambi su stati terminali. Payload vuoto -> 400 (no-op
    #        silenzioso evitato).
    def aggiorna_offerta(
        self, offerta_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._v.validate_allowed_keys(payload, allowed=_UPDATE_KEYS_OFFERTA)
        self._guard_payload_non_vuoto(payload, op="aggiorna_offerta")
        self._assert_stato_corrente(offerta_id, expected=_STATI_EDITABILI)
        with self._db_errors({"offerta_id": offerta_id}):
            with transaction.atomic():
                self._repo.update_offerta(offerta_id, payload)
        return self.get_offerta(offerta_id)

    # Scopo: Elimina un'offerta in stato BOZZA (hard delete). L'annullamento
    #        "di processo" passa invece da `annulla` (BOZZA -> ANNULLATA).
    #        Il `delete` qui resta come pulizia tecnica di bozze "vuote".
    def elimina_offerta(self, offerta_id: int) -> None:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._assert_stato_corrente(offerta_id, expected=_STATI_EDITABILI)
        with self._db_errors({"offerta_id": offerta_id}):
            with transaction.atomic():
                deleted = self._repo.delete_offerta(offerta_id)
                ErrorManager.require(
                    deleted,
                    code=E_VENDITE_NOT_FOUND,
                    message="Offerta non trovata.",
                    context={"offerta_id": offerta_id},
                )

    # =================================================================
    # Transizioni di stato manuali
    # =================================================================

    # Scopo: BOZZA -> EMESSA. Il trigger DB verifica `listino_versione_id`
    #        NOT NULL e versione ATTIVA + valorizza `data_emissione`.
    def emetti(self, offerta_id: int) -> dict[str, Any]:
        return self._cambia_stato_manuale(
            offerta_id,
            target_codice=StatoOfferta.EMESSA,
            expected_from=_STATI_EDITABILI,
        )

    # Scopo: EMESSA -> ACCETTATA (esito cliente positivo). Il trigger DB
    #        valorizza `data_accettazione`.
    def registra_accettazione(self, offerta_id: int) -> dict[str, Any]:
        return self._cambia_stato_manuale(
            offerta_id,
            target_codice=StatoOfferta.ACCETTATA,
            expected_from=frozenset({StatoOfferta.EMESSA}),
        )

    # Scopo: EMESSA -> RIFIUTATA (esito cliente negativo). Motivazione
    #        obbligatoria. Il trigger DB valorizza `data_rifiuto` +
    #        `motivazione_rifiuto`.
    def registra_rifiuto(
        self, offerta_id: int, *, motivazione: str
    ) -> dict[str, Any]:
        self._v.guard_non_empty_string(motivazione, field="motivazione")
        return self._cambia_stato_manuale(
            offerta_id,
            target_codice=StatoOfferta.RIFIUTATA,
            expected_from=frozenset({StatoOfferta.EMESSA}),
            motivazione=motivazione.strip(),
        )

    # Scopo: Esito cliente unificato (ACCETTATA o RIFIUTATA, da EMESSA). La
    #        view si limita a passare il payload, il routing per esito vive
    #        qui — coerente con i due metodi specifici sopra (mantenuti per
    #        chi vuole l'API esplicita).
    def registra_esito(
        self, offerta_id: int, *, esito: str, motivazione: str | None = None
    ) -> dict[str, Any]:
        ErrorManager.require(
            esito in _ESITI_AMMESSI_DA_EMESSA,
            code=E_VENDITE_VALIDATION,
            message="Esito non valido.",
            detail=f"Atteso uno tra {sorted(_ESITI_AMMESSI_DA_EMESSA)}, ricevuto {esito!r}.",
            context={"offerta_id": offerta_id, "esito": esito},
        )
        if esito == StatoOfferta.ACCETTATA:
            return self.registra_accettazione(offerta_id)
        return self.registra_rifiuto(offerta_id, motivazione=motivazione or "")

    # Scopo: BOZZA -> ANNULLATA (ritiro interno prima dell'emissione).
    #        Motivazione obbligatoria. Pattern simmetrico al contratto
    #        "annulla DRAFT". Il trigger DB valorizza `data_annullamento` +
    #        `motivazione_rifiuto`.
    def annulla(self, offerta_id: int, *, motivazione: str) -> dict[str, Any]:
        self._v.guard_non_empty_string(motivazione, field="motivazione")
        return self._cambia_stato_manuale(
            offerta_id,
            target_codice=StatoOfferta.ANNULLATA,
            expected_from=_STATI_EDITABILI,
            motivazione=motivazione.strip(),
        )

    # =================================================================
    # CRUD eccezioni (solo in BOZZA)
    # =================================================================

    # Scopo: Lista eccezioni di un'offerta (qualsiasi stato — la lettura
    #        non e' bloccata; il guard BOZZA si applica solo in scrittura).
    def list_eccezioni(self, offerta_id: int) -> list[dict[str, Any]]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        # Verifica esistenza offerta per 404 esplicito.
        ErrorManager.require(
            self._repo.get_stato_codice(offerta_id) is not None,
            code=E_VENDITE_NOT_FOUND,
            message="Offerta non trovata.",
            context={"offerta_id": offerta_id},
        )
        return self._repo.list_eccezioni(offerta_id)

    # Scopo: Crea un'eccezione. Solo in stato BOZZA.
    def crea_eccezione(
        self, offerta_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._v.validate_allowed_keys(payload, allowed=_CREATE_KEYS_ECCEZIONE)
        self._assert_stato_corrente(offerta_id, expected=_STATI_EDITABILI)
        for required in ("articolo_id", "tipo_eccezione", "fonte_quantita_attesa"):
            ErrorManager.require(
                required in payload and payload[required] not in (None, ""),
                code=E_VENDITE_VALIDATION,
                message=f"Campo '{required}' obbligatorio.",
                context={"field": required},
            )
        with self._db_errors({"offerta_id": offerta_id}):
            with transaction.atomic():
                eccezione_id = self._repo.create_eccezione(offerta_id, payload)
        row = self._repo.get_eccezione(eccezione_id)
        assert row is not None
        return row

    # Scopo: Aggiorna un'eccezione. Solo se offerta in BOZZA. Payload vuoto
    #        -> 400 (no-op silenzioso evitato).
    def aggiorna_eccezione(
        self, offerta_id: int, eccezione_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._v.guard_positive_int(eccezione_id, field="eccezione_id")
        self._v.validate_allowed_keys(payload, allowed=_UPDATE_KEYS_ECCEZIONE)
        self._guard_payload_non_vuoto(payload, op="aggiorna_eccezione")
        self._assert_stato_corrente(offerta_id, expected=_STATI_EDITABILI)
        existing = self._repo.get_eccezione(eccezione_id)
        ErrorManager.require(
            existing is not None and existing.get("offerta_id") == offerta_id,
            code=E_VENDITE_NOT_FOUND,
            message="Eccezione non trovata o non appartenente all'offerta.",
            context={"offerta_id": offerta_id, "eccezione_id": eccezione_id},
        )
        with self._db_errors({"eccezione_id": eccezione_id}):
            with transaction.atomic():
                self._repo.update_eccezione(eccezione_id, payload)
        row = self._repo.get_eccezione(eccezione_id)
        assert row is not None
        return row

    # Scopo: Cancella un'eccezione. Solo se offerta in BOZZA.
    def elimina_eccezione(self, offerta_id: int, eccezione_id: int) -> None:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._v.guard_positive_int(eccezione_id, field="eccezione_id")
        self._assert_stato_corrente(offerta_id, expected=_STATI_EDITABILI)
        existing = self._repo.get_eccezione(eccezione_id)
        ErrorManager.require(
            existing is not None and existing.get("offerta_id") == offerta_id,
            code=E_VENDITE_NOT_FOUND,
            message="Eccezione non trovata o non appartenente all'offerta.",
            context={"offerta_id": offerta_id, "eccezione_id": eccezione_id},
        )
        with self._db_errors({"eccezione_id": eccezione_id}):
            with transaction.atomic():
                self._repo.delete_eccezione(eccezione_id)

    # =================================================================
    # Utility 1:1 (solo in BOZZA per write)
    # =================================================================

    # Scopo: Legge il record utility 1:1 di un'offerta (read libero).
    def get_utility(self, offerta_id: int) -> dict[str, Any] | None:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        ErrorManager.require(
            self._repo.get_stato_codice(offerta_id) is not None,
            code=E_VENDITE_NOT_FOUND,
            message="Offerta non trovata.",
            context={"offerta_id": offerta_id},
        )
        return self._repo.get_utility(offerta_id)

    # Scopo: Crea il record utility 1:1. UNIQUE su offerta_id: doppio create
    #        rilevato e mappato a E_VENDITE_DUPLICATO. Solo in BOZZA.
    def crea_utility(
        self, offerta_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._v.validate_allowed_keys(payload, allowed=_CREATE_KEYS_UTILITY)
        self._assert_stato_corrente(offerta_id, expected=_STATI_EDITABILI)
        for required in ("istanza_utility_id", "utility_id"):
            ErrorManager.require(
                required in payload and payload[required] is not None,
                code=E_VENDITE_VALIDATION,
                message=f"Campo '{required}' obbligatorio.",
                context={"field": required},
            )
        with self._db_errors({"offerta_id": offerta_id}):
            with transaction.atomic():
                self._repo.create_utility(offerta_id, payload)
        row = self._repo.get_utility(offerta_id)
        assert row is not None
        return row

    # Scopo: Aggiorna il record utility (campi business). Solo in BOZZA.
    #        Payload vuoto -> 400 (no-op silenzioso evitato).
    def aggiorna_utility(
        self, offerta_id: int, utility_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._v.guard_positive_int(utility_id, field="utility_id")
        self._v.validate_allowed_keys(payload, allowed=_UPDATE_KEYS_UTILITY)
        self._guard_payload_non_vuoto(payload, op="aggiorna_utility")
        self._assert_stato_corrente(offerta_id, expected=_STATI_EDITABILI)
        existing = self._repo.get_utility(offerta_id)
        ErrorManager.require(
            existing is not None and existing.get("id") == utility_id,
            code=E_VENDITE_NOT_FOUND,
            message="Record utility non trovato per questa offerta.",
            context={"offerta_id": offerta_id, "utility_id": utility_id},
        )
        with self._db_errors({"offerta_id": offerta_id}):
            with transaction.atomic():
                self._repo.update_utility(utility_id, payload)
        row = self._repo.get_utility(offerta_id)
        assert row is not None
        return row

    # =================================================================
    # Helper interni
    # =================================================================

    # Scopo: Fail-fast su payload vuoto in update. Senza questo guard, il
    #        repository ritorna False senza errori, ma il service restituisce
    #        comunque `get_offerta(...)` — l'operatore vedrebbe un "successo"
    #        ingannevole sul tasto Salva quando in realta' non e' stato
    #        scritto nulla.
    def _guard_payload_non_vuoto(
        self, payload: dict[str, Any], *, op: str
    ) -> None:
        ErrorManager.require(
            bool(payload),
            code=E_VENDITE_VALIDATION,
            message="Nessun campo da aggiornare.",
            detail=f"Operazione {op}: il payload e' vuoto.",
            context={"op": op},
        )

    # Scopo: Verifica che l'offerta esista e sia in uno degli stati attesi.
    #        Solleva 404 se offerta inesistente, 422 se stato fuori scope.
    def _assert_stato_corrente(
        self, offerta_id: int, *, expected: set[str] | frozenset[str]
    ) -> str:
        stato = self._repo.get_stato_codice(offerta_id)
        ErrorManager.require(
            stato is not None,
            code=E_VENDITE_NOT_FOUND,
            message="Offerta non trovata.",
            context={"offerta_id": offerta_id},
        )
        assert stato is not None
        ErrorManager.require(
            stato in expected,
            code=E_VENDITE_VALIDATION,
            message=(
                "Operazione non consentita: stato corrente "
                f"'{stato}', atteso uno tra {sorted(expected)}."
            ),
            context={
                "offerta_id": offerta_id,
                "stato_corrente": stato,
                "stati_attesi": sorted(expected),
            },
        )
        return stato

    # Scopo: Esegue una transizione di stato manuale. Il guard pre-condizione
    #        (`expected_from`) e' difesa applicativa; il trigger DB rifinisce
    #        ulteriormente (es. BOZZA->EMESSA fallisce se listino_versione_id
    #        NULL o versione non ATTIVA).
    def _cambia_stato_manuale(
        self,
        offerta_id: int,
        *,
        target_codice: str,
        expected_from: set[str] | frozenset[str],
        motivazione: str | None = None,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(offerta_id, field="offerta_id")
        self._assert_stato_corrente(offerta_id, expected=expected_from)
        target_stato_id = self._repo.get_stato_id_by_codice(target_codice)
        ErrorManager.require(
            target_stato_id is not None,
            code=E_VENDITE_VALIDATION,
            message=f"Stato '{target_codice}' non configurato.",
            context={"target_codice": target_codice},
        )
        assert target_stato_id is not None
        with self._db_errors(
            {"offerta_id": offerta_id, "target_codice": target_codice},
            fallback_message="Cambio stato offerta non consentito.",
        ):
            with transaction.atomic():
                self._repo.update_stato(
                    offerta_id,
                    target_stato_id,
                    motivazione_rifiuto=motivazione,
                )
        return self.get_offerta(offerta_id)
