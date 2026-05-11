# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service facade per vendite.contratti + contratti_righe +
#        contratti_utilities (CRUD v5 — F2-BE-05).
#
#        Il contratto rappresenta l'accordo cliente-listino con tre
#        modalita' pricing (sviluppo-listini-v5 §5.3):
#          A: listino + variazione globale
#          B: listino + override righe
#          C: interamente negoziato (nessun listino, tutte le righe
#             devono avere prezzo_unitario)
#
#        Validazioni in ordine crescente di costo:
#          1) struttura payload (chiavi ammesse, tipi)
#          2) coerenza modalita' pre-DB (listino_id / variazione globale)
#          3) affidamento ai trigger DB per gli invarianti piu' complessi
#             (overlap cross-contratto, tipo/classe utenza dinamica,
#             attivazione modalita' C con righe incomplete).
#
#        Il numero contratto e' generato nel service via
#        `script.fn_generate_codice('contratto')` — NON va mai
#        accettato in payload (immutabile via trigger lock_columns).
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.db import DatabaseError, IntegrityError, transaction

from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import (
    PayloadValidator,
    map_integrity_error,
)
from apps.documenti.db.documenti_repository import DocumentiRepository
from apps.documenti.services.document_generation_service import (
    DocumentGenerationService,
)
from apps.vendite.db.contratti_repository import ContrattiRepository


# Codici errore (registrati in error_policies.py).
E_VENDITE_VALIDATION = "E_VENDITE_VALIDATION"
E_VENDITE_NOT_FOUND = "E_VENDITE_NOT_FOUND"
E_VENDITE_DUPLICATO = "E_VENDITE_DUPLICATO"
E_VENDITE_FK = "E_VENDITE_FK"
E_VENDITE_CONTRATTO_OVERLAP = "E_VENDITE_CONTRATTO_OVERLAP"

_CODICE_SORGENTE_CONTRATTO = "CONTRATTO"


_ORDER_BY_CONTRATTI: frozenset[str] = frozenset({
    "numero",
    "data",
    "valido_dal",
    "valido_al",
    "ba_codice",
    "ba_ragione_sociale",
    "stato_codice",
    "categoria_cliente_snapshot_codice",
    "data_insert",
    "data_update",
})


_AMBITI_VALIDI: frozenset[str] = frozenset({"COMMODITY", "COMMERCIO"})
_TIPI_VARIAZIONE: frozenset[str] = frozenset({"PERCENTUALE", "VALORE_FISSO"})


# Chiavi ammesse nel payload create testata. `numero` escluso: generato dal
# service. `stato_doc_contratto_id` escluso: stato iniziale DRAFT impostato
# dal service (cambi stato successivi via endpoint dedicato).
_CREATE_KEYS_TESTATA: frozenset[str] = frozenset({
    "billing_account_id",
    "istanza_utility_id",
    "utility_id",
    "ambito",
    "valido_dal",
    "valido_al",
    "parent_contratto_id",
    "data",
    "listino_id",
    "tipo_variazione_globale",
    "valore_variazione_globale",
    # Snapshot categoria cliente: opzionale. Se fornito, congela il valore
    # scelto dall'operatore; se omesso, il trigger DB lo popola dal BA.
    "categoria_cliente_id_snapshot",
    "meta",
    # Sub-entita' opzionale: se presente crea la riga utility 1:1 nella
    # stessa transazione. Il service NON permette payload utility senza
    # chiavi pulite (stessa whitelist _UTILITY_KEYS).
    "utility",
})

_UPDATE_KEYS_TESTATA: frozenset[str] = frozenset({
    "ambito",
    "valido_dal",
    "valido_al",
    "parent_contratto_id",
    "data",
    "listino_id",
    "tipo_variazione_globale",
    "valore_variazione_globale",
    "categoria_cliente_id_snapshot",
    "meta",
})

# Whitelist PATCH testata per stato del documento contratto. Il workflow
# operativo e' DRAFT -> ATTIVO -> CESSATO (terminale). SOSPESO e' stato
# rimosso dal modello (config.stati_doc_contratti, 2026-04-26): la sua
# semantica operativa (blocco fatturazione/proroghe/ripresa) non era
# implementata. In ATTIVO restano editabili solo `valido_al` (per
# programmare la cessazione, coerente con "data = fonte di verita'
# operativa") e `meta` (note interne, non operative). CESSATO e'
# completamente immutabile. Per cambi sostanziali in stati post-DRAFT
# serve creare un nuovo contratto (eventualmente con parent_contratto_id) —
# pattern audit-friendly.
_CONTRATTO_PATCH_ALLOWED_BY_STATE: dict[str, frozenset[str]] = {
    "DRAFT": _UPDATE_KEYS_TESTATA,
    "ATTIVO": frozenset({"valido_al", "meta"}),
    "CESSATO": frozenset(),
}

# In create: numero e stato_doc_contratto_id sono impostati dal service,
# mai in payload. In update: oltre a questi, anche gli identificativi
# (BA/istanza/utility) diventano immutabili — per cambiarli si crea un
# contratto nuovo.
_FORBIDDEN_TESTATA_CREATE: frozenset[str] = frozenset({
    "numero",
    "stato_doc_contratto_id",
})
_FORBIDDEN_TESTATA_UPDATE: frozenset[str] = frozenset({
    "numero",
    "billing_account_id",
    "istanza_utility_id",
    "utility_id",
    "stato_doc_contratto_id",
})


# Righe contratto: chiavi ammesse create/update.
_CREATE_KEYS_RIGA: frozenset[str] = frozenset({
    "articolo_id",
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

_UPDATE_KEYS_RIGA: frozenset[str] = frozenset({
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

# In create: contratto_id arriva dall'URL, non da payload. articolo_id e'
# obbligatorio e accettato. In update: articolo_id diventa immutabile.
_FORBIDDEN_RIGA_CREATE: frozenset[str] = frozenset({"contratto_id"})
_FORBIDDEN_RIGA_UPDATE: frozenset[str] = frozenset({"articolo_id", "contratto_id"})


# Utility 1:1: chiavi ammesse in create/update. istanza_utility_id e
# utility_id sono derivati dal contratto in create; immutabili in update.
# Utility 1:1: istanza_utility_id e utility_id derivano dalla testata,
# NON dal payload (evita incoerenze silenziose).
_UTILITY_CREATE_KEYS: frozenset[str] = frozenset({
    "istanza_dati_precontrattuali_id",
    "tipo_utenza_id",
    "classe_utenza_id",
    "param_1_num",
    "param_2_txt",
    "meta",
})

_UTILITY_UPDATE_KEYS: frozenset[str] = frozenset({
    "istanza_dati_precontrattuali_id",
    "tipo_utenza_id",
    "classe_utenza_id",
    "param_1_num",
    "param_2_txt",
    "meta",
})

_UTILITY_IMMUTABLE_KEYS: frozenset[str] = frozenset({
    "contratto_id",
    "istanza_utility_id",
    "utility_id",
})


_MESSAGE = "Payload contratto non valido."
_MESSAGE_RIGA = "Payload riga contratto non valido."
_MESSAGE_UTILITY = "Payload utility contratto non valido."

# Codice stato iniziale (FK config.stati_doc_contratti.codice_interno). Deve
# esistere a seed (migrations_v2/80_data). La costante esplicita evita il
# magic string in create_contratto.
_STATO_INIZIALE_CODICE = "DRAFT"


# Mapping UNIQUE/EXCLUDE/FK -> codici errore applicativi.
_UNIQUE_CONSTRAINTS: dict[str, tuple[str, str]] = {
    "uq_contratti_numero": (
        E_VENDITE_DUPLICATO,
        "Numero contratto gia' esistente.",
    ),
    "ex_contratti_no_overlap": (
        E_VENDITE_CONTRATTO_OVERLAP,
        "Esiste gia' un contratto sovrapposto per questa combinazione "
        "cliente/istanza/utility/ambito nel periodo indicato.",
    ),
    "uq_contratti_utilities_contratto_id": (
        E_VENDITE_DUPLICATO,
        "Questo contratto ha gia' una riga utility associata.",
    ),
}
_FK_CONSTRAINTS: dict[str, tuple[str, str]] = {
    "fk_contratti_billing_account": (E_VENDITE_FK, "Billing account inesistente."),
    "fk_contratti_istanza": (E_VENDITE_FK, "Istanza utility inesistente."),
    "fk_contratti_utility": (E_VENDITE_FK, "Utility inesistente."),
    "fk_contratti_listino": (E_VENDITE_FK, "Listino inesistente."),
    "fk_contratti_parent": (E_VENDITE_FK, "Contratto padre inesistente."),
    "fk_v_contratti_stato_ddt": (E_VENDITE_FK, "Stato documento inesistente."),
    "fk_contrighe_articoli": (E_VENDITE_FK, "Articolo inesistente."),
    "fk_contrighe_contratti": (E_VENDITE_FK, "Contratto inesistente."),
    "fk_contratti_righe_uom_operativa_id": (E_VENDITE_FK, "UoM operativa inesistente."),
    "fk_contratti_utilities_classi_utenze": (E_VENDITE_FK, "Classe utenza inesistente."),
    "fk_contratti_utilities_tipo_utenza": (E_VENDITE_FK, "Tipo utenza inesistente."),
    "fk_contratti_utilities_istanze_utilities": (E_VENDITE_FK, "Istanza utility inesistente."),
    "fk_contratti_utilities_istanze_dati_precontrattuali": (
        E_VENDITE_FK,
        "Istanza dati precontrattuali inesistente.",
    ),
    "fk_contratti_utilities_contratti": (E_VENDITE_FK, "Contratto inesistente."),
    # FK creata con REFERENCES inline: PG auto-genera il nome. Mappiamo sia
    # la convenzione progetto (fk_*) sia il formato PG ({table}_{col}_fkey).
    "fk_contratti_categoria_cliente_snapshot": (
        E_VENDITE_FK,
        "Categoria cliente (snapshot) inesistente.",
    ),
    "contratti_categoria_cliente_id_snapshot_fkey": (
        E_VENDITE_FK,
        "Categoria cliente (snapshot) inesistente.",
    ),
}


# Marker di identificazione codici P0001 dai trigger. Match multi-substring
# stretto (tutti i marker della tupla devono comparire nel MESSAGE).
# Coerente con pricing_service._KNOWN_DB_ERROR_MARKERS.
_KNOWN_DB_ERROR_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "E_CONTRATTO_MODALITA_C_SENZA_RIGHE",
        ("modalita' C senza righe attive",),
    ),
    (
        "E_CONTRATTO_MODALITA_C_RIGHE_INCOMPLETE",
        ("modalita' C", "prive di prezzo_unitario"),
    ),
    (
        "E_CONTRATTO_MODALITA_C_RIGA_SENZA_PREZZO",
        ("modalita' C", "prezzo_unitario obbligatorio"),
    ),
    (
        "E_CONTRATTO_UTILITY_TIPO_CLASSE_OBBLIGATORI",
        ("tipo_utenza_id e classe_utenza_id sono obbligatori",),
    ),
    (
        "E_CONTRATTO_CLASSE_TIPO_INCOERENTE",
        ("appartiene al tipo", "ma il contratto dichiara tipo"),
    ),
    (
        "E_CONTRATTO_UTILITY_SENZA_DIMENSIONE_TIPO_CLASSE_VIETATI",
        ("senza dimensione tipo/classe", "devono essere NULL"),
    ),
)


class ContrattiService:
    """Service CRUD contratti v5 (F2-BE-05)."""

    def __init__(self) -> None:
        self._repo = ContrattiRepository()
        self._v = PayloadValidator(
            validation_code=E_VENDITE_VALIDATION,
            log_to_db=True,
            function_name="contratti_service",
        )

    # =================================================================
    # Guard DB errors uniforme (map IntegrityError + P0001 trigger)
    # =================================================================

    # Scopo: Context manager che normalizza errori DB sollevati dentro il
    #        blocco in `ServiceError` applicativi. Concentra in un unico
    #        posto la catena try/except duplicata per tutti i mutatori.
    @contextmanager
    def _db_errors(
        self,
        context: dict[str, Any],
        *,
        fallback_message: str = "Violazione vincolo DB su contratto.",
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
            self._raise_db_error(exc, context=context)

    # =================================================================
    # Lista e dettaglio
    # =================================================================

    # Scopo: Lista paginata contratti con filtri standard espliciti.
    #        Il backend non applica default temporali impliciti: eventuali
    #        default visibili all'operatore sono responsabilita' della UI.
    def list_contratti(
        self,
        *,
        search: str | None = None,
        billing_account_id: int | None = None,
        stato_doc_contratto_id: int | None = None,
        utility_id: int | None = None,
        ambito: str | None = None,
        listino_id: int | None = None,
        data_da: date | None = None,
        data_a: date | None = None,
        scadenza_mese: str | None = None,
        limit: int = 25,
        offset: int = 0,
        order_by: str = "data",
        order_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        self._v.validate_order_by(order_by, allowed=_ORDER_BY_CONTRATTI)
        if ambito is not None:
            ErrorManager.require(
                ambito in _AMBITI_VALIDI,
                code=E_VENDITE_VALIDATION,
                message="Filtro ambito non valido.",
                detail=f"Ammessi: {', '.join(sorted(_AMBITI_VALIDI))}.",
                context={"ambito": ambito},
            )
        # Validazione scadenza_mese: formato YYYY-MM, mese >= mese corrente.
        if scadenza_mese is not None:
            import re
            ErrorManager.require(
                bool(re.match(r"^\d{4}-\d{2}$", scadenza_mese)),
                code=E_VENDITE_VALIDATION,
                message="Formato scadenza_mese non valido.",
                detail="Atteso YYYY-MM (es. 2026-07).",
                context={"scadenza_mese": scadenza_mese},
            )
        return self._repo.list_contratti(
            search=search,
            billing_account_id=billing_account_id,
            stato_doc_contratto_id=stato_doc_contratto_id,
            utility_id=utility_id,
            ambito=ambito,
            listino_id=listino_id,
            data_da=data_da,
            data_a=data_a,
            scadenza_mese=scadenza_mese,
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_dir=order_dir,
        )

    # Scopo: Dettaglio completo contratto (testata + utility 1:1 + righe +
    #        capabilities). Le capability (available_actions con default_date/
    #        min_date per "cessa", can_change_state, can_edit_*, non_editable_fields)
    #        sono calcolate da script.fn_available_actions_contratto: il backend
    #        non duplica la logica, spalma il blob JSONB nel detail per consumo
    #        diretto dal frontend (Fase 1.B2 refactor frontend vendite).
    def get_contratto(self, contratto_id: int) -> dict[str, Any]:
        self._v.guard_positive_int(contratto_id, field="contratto_id")
        testata = self._repo.get_contratto(contratto_id)
        ErrorManager.require(
            testata is not None,
            code=E_VENDITE_NOT_FOUND,
            message="Contratto non trovato.",
            context={"contratto_id": contratto_id},
        )
        assert testata is not None
        testata["utility"] = self._repo.get_utility(contratto_id)
        testata["righe"] = self._repo.list_righe(contratto_id)
        capabilities = self._repo.get_capabilities(contratto_id)
        testata.update(capabilities)
        return testata

    # =================================================================
    # Creazione testata
    # =================================================================

    # Scopo: Crea un nuovo contratto. Genera numero via fn_generate_codice,
    #        risolve stato iniziale DRAFT, valida modalita' A/B/C pre-DB,
    #        opzionalmente crea la riga utility 1:1 nella stessa
    #        transazione (trigger DB gestira' fail-fast su coerenze
    #        dinamiche).
    def create_contratto(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._v.reject_keys(
            payload,
            forbidden=_FORBIDDEN_TESTATA_CREATE,
            reason="Campi gestiti dal sistema non modificabili in payload create.",
            detail_prefix=(
                "numero e stato_doc_contratto_id sono assegnati dal service. "
                "Campi rifiutati"
            ),
        )
        self._v.validate_allowed_keys(payload, allowed=_CREATE_KEYS_TESTATA, message=_MESSAGE)

        data = self._build_create_data_testata(payload)
        utility_payload = payload.get("utility")
        if utility_payload is not None:
            self._validate_utility_payload_shape(utility_payload, for_create=True)

        # Numero + stato iniziale risolti prima dell'INSERT.
        data["numero"] = self._repo.generate_numero()
        stato_draft_id = self._repo.get_stato_id_by_codice(_STATO_INIZIALE_CODICE)
        ErrorManager.require(
            stato_draft_id is not None,
            code=E_VENDITE_VALIDATION,
            message=f"Stato iniziale {_STATO_INIZIALE_CODICE} non configurato in config.stati_doc_contratti.",
            context={"codice_interno": _STATO_INIZIALE_CODICE},
        )
        assert stato_draft_id is not None
        data["stato_doc_contratto_id"] = stato_draft_id

        with self._db_errors({"numero": data.get("numero")}):
            new_id = self._repo.create_contratto(data)
            if utility_payload is not None:
                utility_data = self._build_utility_data(
                    utility_payload,
                    istanza_utility_id=data["istanza_utility_id"],
                    utility_id=data["utility_id"],
                    for_create=True,
                )
                self._repo.create_utility(new_id, utility_data)

        return self.get_contratto(new_id)

    # =================================================================
    # Aggiornamento testata
    # =================================================================

    # Scopo: Aggiorna una testata contratto sui soli campi mutabili.
    #        Validazione modalita' A/B/C pre-DB. Il cambio stato passa
    #        da cambia_stato().
    def update_contratto(
        self, contratto_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        self._v.guard_positive_int(contratto_id, field="contratto_id")
        self._v.reject_keys(
            payload,
            forbidden=_FORBIDDEN_TESTATA_UPDATE,
            reason="Identificativi contratto non modificabili.",
            detail_prefix=(
                "numero, billing_account_id, istanza_utility_id, utility_id "
                "e stato_doc_contratto_id non modificabili. Campi rifiutati"
            ),
            context_extra={"contratto_id": contratto_id},
        )
        self._v.validate_allowed_keys(payload, allowed=_UPDATE_KEYS_TESTATA, message=_MESSAGE)

        # Leggiamo la testata esistente PRIMA di validare la modalita': serve
        # al validator per sapere il listino_id corrente quando il payload
        # patch non lo include (es. patch solo su variazione globale).
        existing = self._repo.get_contratto(contratto_id)
        ErrorManager.require(
            existing is not None,
            code=E_VENDITE_NOT_FOUND,
            message="Contratto non trovato.",
            context={"contratto_id": contratto_id},
        )
        assert existing is not None

        # Guard whitelist PATCH per stato. In ATTIVO ammessi solo
        # `valido_al` (programma cessazione) e `meta` (note interne); in
        # CESSATO nulla; in DRAFT tutto. categoria_cliente_id_snapshot non
        # appare nelle whitelist non-DRAFT, quindi viene rifiutato implicitamente
        # con messaggio coerente. Errore parlante con detail che lista i campi
        # ammessi per lo stato corrente.
        stato_corrente = str(existing.get("stato_codice") or "")
        allowed_for_state = _CONTRATTO_PATCH_ALLOWED_BY_STATE.get(stato_corrente, frozenset())
        non_ammessi = sorted(set(payload.keys()) - allowed_for_state)
        if non_ammessi:
            ErrorManager.raise_error(
                code="E_CONTRATTO_NON_MODIFICABILE",
                message="Modifica contratto non consentita nello stato corrente.",
                detail=(
                    f"In stato {stato_corrente or 'sconosciuto'} sono modificabili solo: "
                    f"{sorted(allowed_for_state) if allowed_for_state else 'nessun campo'}. "
                    f"Campi non ammessi nel payload: {non_ammessi}. "
                    f"Per modifiche sostanziali su contratti post-DRAFT creare un nuovo contratto."
                ),
                context={
                    "contratto_id": contratto_id,
                    "stato_codice": stato_corrente,
                    "campi_non_ammessi": non_ammessi,
                    "campi_ammessi": sorted(allowed_for_state),
                },
            )

        data = self._build_update_data_testata(payload, existing=existing)

        ErrorManager.require(
            bool(data),
            code=E_VENDITE_VALIDATION,
            message="Nessun campo aggiornabile presente nel payload.",
            context={"allowed_keys": sorted(_UPDATE_KEYS_TESTATA)},
        )

        with self._db_errors({"contratto_id": contratto_id}):
            updated = self._repo.update_contratto(contratto_id, data)

        ErrorManager.require(
            updated,
            code=E_VENDITE_NOT_FOUND,
            message="Contratto non trovato.",
            context={"contratto_id": contratto_id},
        )
        return self.get_contratto(contratto_id)

    # =================================================================
    # Cambio stato
    # =================================================================

    # Scopo: Cambia lo stato del contratto al codice_interno richiesto.
    #        Se target=CESSATO viene applicata la regola fail-safe data-driven
    #        (analoga a listini-versioni, vedi feedback_stato_terminale_con_data):
    #          - valido_al obbligatorio (no cessazione "senza data")
    #          - valido_al >= valido_dal (anti CHK constraint DB)
    #          - valido_al < CURRENT_DATE -> cessazione immediata: applica
    #            entrambi PATCH+UPDATE in transazione atomica
    #          - valido_al >= CURRENT_DATE -> CESSAZIONE PROGRAMMATA: applica
    #            solo PATCH valido_al; lo stato resta ATTIVO. Il job
    #            notturno DB allineera' lo stato a CESSATO quando la data
    #            scade. Coerente con il principio "data = fonte di verita'
    #            operativa, stato = flag informativo eventualmente stantio".
    #        Per le altre transizioni (DRAFT->ATTIVO, ecc.) e per cessazioni
    #        senza valido_al, il flusso e' lineare (UPDATE stato + opzionale
    #        PATCH valido_al). L'attivazione in modalita' C senza righe/prezzi
    #        e' bloccata dal trigger DB trgfn_contratti_guard_modalita_c_
    #        activation → traduciamo il P0001 in ServiceError parlante.
    def cambia_stato(
        self,
        contratto_id: int,
        *,
        codice_interno: str,
        valido_al: date | None = None,
        user: AbstractBaseUser | AnonymousUser | None = None,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(contratto_id, field="contratto_id")
        ErrorManager.require(
            isinstance(codice_interno, str) and codice_interno.strip() != "",
            code=E_VENDITE_VALIDATION,
            message="codice_interno dello stato obbligatorio.",
            context={"field": "codice_interno"},
        )
        codice_norm = codice_interno.strip()
        target_stato_id = self._repo.get_stato_id_by_codice(codice_norm)
        ErrorManager.require(
            target_stato_id is not None,
            code=E_VENDITE_VALIDATION,
            message=f"Stato '{codice_interno}' non configurato.",
            context={"codice_interno": codice_interno},
        )
        assert target_stato_id is not None
        stato_corrente = self._repo.get_stato_codice(contratto_id)
        ErrorManager.require(
            stato_corrente is not None,
            code=E_VENDITE_NOT_FOUND,
            message="Contratto non trovato.",
            context={"contratto_id": contratto_id},
        )

        # Pre-validazione data-driven per CESSATO (regola fail-safe):
        # - valido_al obbligatorio
        # - valido_al >= valido_dal
        # - se valido_al >= today -> cessazione programmata (no cambio stato)
        cessazione_programmata = False
        if codice_norm == "CESSATO":
            ErrorManager.require(
                valido_al is not None,
                code=E_VENDITE_VALIDATION,
                message="Data cessazione obbligatoria.",
                detail=(
                    "Per portare il contratto in stato CESSATO e' necessaria "
                    "la data di cessazione (valido_al)."
                ),
                context={"contratto_id": contratto_id},
            )
            existing = self._repo.get_contratto(contratto_id)
            ErrorManager.require(
                existing is not None,
                code=E_VENDITE_NOT_FOUND,
                message="Contratto non trovato.",
                context={"contratto_id": contratto_id},
            )
            assert existing is not None and valido_al is not None
            existing_valido_dal = existing.get("valido_dal")
            if isinstance(existing_valido_dal, date):
                ErrorManager.require(
                    valido_al >= existing_valido_dal,
                    code=E_VENDITE_VALIDATION,
                    message="Data cessazione non valida.",
                    detail=(
                        f"valido_al ({valido_al.isoformat()}) deve essere >= "
                        f"valido_dal del contratto ({existing_valido_dal.isoformat()})."
                    ),
                    context={
                        "contratto_id": contratto_id,
                        "valido_al": valido_al,
                        "valido_dal": existing_valido_dal,
                    },
                )
            # Cessazione programmata: data >= oggi -> NON cambiamo lo stato.
            # Applichiamo solo PATCH valido_al e lasciamo che il job notturno
            # DB allinei lo stato quando la data scade. Speculare al guard
            # DB che rifiuta la transizione ATTIVO->CESSATO con valido_al
            # futuro (defense-in-depth, vedi brief team DB).
            if valido_al >= date.today():
                cessazione_programmata = True

        with self._db_errors(
            {"contratto_id": contratto_id, "codice_interno": codice_norm},
            fallback_message="Violazione vincolo DB su cambio stato.",
        ):
            with transaction.atomic():
                if valido_al is not None:
                    self._repo.update_contratto(contratto_id, {"valido_al": valido_al})
                if cessazione_programmata:
                    # Solo PATCH valido_al, niente UPDATE stato. Il chiamante
                    # ricevera' lo stato corrente invariato + valido_al
                    # programmato; FE distingue scenario via valido_al > today.
                    pass
                else:
                    updated = self._repo.update_stato(contratto_id, target_stato_id)
                    ErrorManager.require(
                        updated,
                        code=E_VENDITE_NOT_FOUND,
                        message="Contratto non trovato.",
                        context={"contratto_id": contratto_id},
                    )
                    if codice_norm == "ATTIVO" and stato_corrente == "DRAFT":
                        self._genera_pdf_attivazione(contratto_id, user=user)
        return self.get_contratto(contratto_id)

    # Scopo: genera e persiste il PDF canonico del contratto al momento
    #        dell'attivazione. Chiamato dentro la stessa transaction.atomic
    #        del cambio stato DRAFT->ATTIVO: un errore render/storage fa
    #        propagare l'eccezione e rollbacka anche il cambio stato.
    def _genera_pdf_attivazione(
        self,
        contratto_id: int,
        *,
        user: AbstractBaseUser | AnonymousUser | None,
    ) -> None:
        contratto = self._repo.get_for_documento_generation(contratto_id)
        ErrorManager.require(
            contratto is not None,
            code=E_VENDITE_NOT_FOUND,
            message="Contratto non trovato per generazione PDF.",
            context={"contratto_id": contratto_id},
        )
        assert contratto is not None
        ErrorManager.require(
            contratto.get("emittente_fiscale_id") is not None,
            code="E_DOCUMENTI_VALIDATION",
            message="Emittente fiscale non risolto per il contratto.",
            context={"contratto_id": contratto_id},
        )

        doc_repo = DocumentiRepository()
        sorgente = doc_repo.get_sorgente_tipo_id_by_codice(_CODICE_SORGENTE_CONTRATTO)
        ErrorManager.require(
            sorgente is not None and sorgente.get("attivo"),
            code="E_DOCUMENTI_VALIDATION",
            message="Sorgente 'CONTRATTO' non configurata o non attiva.",
            context={"contratto_id": contratto_id},
        )
        assert sorgente is not None

        DocumentGenerationService().genera_documento(
            user,
            emittente_fiscale_id=int(contratto["emittente_fiscale_id"]),
            sorgente_tipo_id=int(sorgente["id"]),
            sorgente_id=int(contratto["id"]),
            sorgente_uid=str(contratto["uid"]),
        )

    # =================================================================
    # Righe contratto - preview pricing applicato
    # =================================================================

    # Scopo: Restituisce le righe operative del contratto per modalita' A/B,
    #        cioe' la lista articoli con prezzo finale applicato (variazione
    #        globale o override). Per modalita' C ritorna lista vuota: in C
    #        le righe vivono in `contratti_righe` e sono lette da list_righe.
    #
    #        Il calcolo e' delegato a `repository.list_righe_preview` (single
    #        SQL pass) che applica la stessa formula della funzione resolver
    #        DB nello stadio CONTRATTO_LISTINO. Per modalita' A tutte le
    #        righe hanno origine='DA_LISTINO'; per B alcune avranno
    #        origine='OVERRIDE' (override esistente in contratti_righe).
    #
    #        L'envelope include la testata sintetica (modalita', listino,
    #        variazione globale) per permettere al FE di renderizzare il
    #        banner contesto senza ulteriori chiamate.
    def list_righe_preview(self, contratto_id: int) -> dict[str, Any]:
        self._v.guard_positive_int(contratto_id, field="contratto_id")
        contratto = self._repo.get_contratto(contratto_id)
        ErrorManager.require(
            contratto is not None,
            code=E_VENDITE_NOT_FOUND,
            message="Contratto non trovato.",
            context={"contratto_id": contratto_id},
        )
        assert contratto is not None

        # Modalita' derivata (non persistita): listino_id NULL -> C, altrimenti
        # B se almeno un override in contratti_righe, A se nessun override.
        # La query preview ritorna gia' le origini riga, sfruttiamole per
        # evitare un round-trip extra di conteggio.
        listino_id = contratto.get("listino_id")
        preview_rows: list[dict[str, Any]] = (
            self._repo.list_righe_preview(contratto_id) if listino_id else []
        )
        if listino_id is None:
            modalita = "C"
        else:
            has_overrides = any(r.get("origine") == "OVERRIDE" for r in preview_rows)
            modalita = "B" if has_overrides else "A"

        # Flag per il FE: distingue il caso "listino senza versione operativa
        # oggi" da modalita' C (lista vuota by design) e dal caso B con
        # override extra-listino (righe presenti ma origine='OVERRIDE',
        # nessuna 'DA_LISTINO'). Il flag e' True se il contratto ha listino
        # ma la query non ha prodotto nemmeno una riga 'DA_LISTINO'
        # (cioe' nessuna versione operativa o nessuna riga attiva).
        listino_senza_versione_oggi = (
            listino_id is not None
            and not any(r.get("origine") == "DA_LISTINO" for r in preview_rows)
        )

        return {
            "contratto_id": contratto_id,
            "modalita": modalita,
            "listino_id": listino_id,
            "listino_codice": contratto.get("listino_codice"),
            "listino_descrizione": contratto.get("listino_descrizione"),
            "tipo_variazione_globale": contratto.get("tipo_variazione_globale"),
            "valore_variazione_globale": contratto.get("valore_variazione_globale"),
            "listino_senza_versione_oggi": listino_senza_versione_oggi,
            "righe": preview_rows,
        }

    # =================================================================
    # Guard sotto-entita' (righe + utility): solo DRAFT
    # =================================================================

    # Scopo: Verifica che il contratto sia in stato DRAFT prima di accettare
    #        operazioni CRUD su righe/utility. In stati post-DRAFT le sotto
    #        entita' sono congelate per audit (Profilo A): per modifiche serve
    #        creare un nuovo contratto. Solleva E_CONTRATTO_NON_MODIFICABILE
    #        con stato corrente nel context.
    def _assert_contratto_draft(self, contratto_id: int, *, op_label: str) -> None:
        contratto = self._repo.get_contratto(contratto_id)
        ErrorManager.require(
            contratto is not None,
            code=E_VENDITE_NOT_FOUND,
            message="Contratto non trovato.",
            context={"contratto_id": contratto_id},
        )
        assert contratto is not None
        stato = str(contratto.get("stato_codice") or "")
        if stato != "DRAFT":
            ErrorManager.raise_error(
                code="E_CONTRATTO_NON_MODIFICABILE",
                message="Operazione non consentita nello stato corrente.",
                detail=(
                    f"{op_label} ammessa solo su contratti in stato DRAFT. "
                    f"Stato corrente: {stato}. Per modifiche su contratti post-DRAFT "
                    f"creare un nuovo contratto."
                ),
                context={"contratto_id": contratto_id, "stato_codice": stato, "op": op_label},
            )

    # Scopo: Risale al contratto dalla riga e applica il guard DRAFT.
    def _assert_contratto_draft_from_riga(self, riga_id: int, *, op_label: str) -> None:
        riga = self._repo.get_riga(riga_id)
        ErrorManager.require(
            riga is not None,
            code=E_VENDITE_NOT_FOUND,
            message="Riga contratto non trovata.",
            context={"riga_id": riga_id},
        )
        assert riga is not None
        self._assert_contratto_draft(int(riga["contratto_id"]), op_label=op_label)

    # =================================================================
    # Righe contratto
    # =================================================================

    # Scopo: Aggiunge una riga al contratto. Il trigger guard modalita' C
    #        impone prezzo_unitario NOT NULL se contratto gia' ATTIVO in
    #        modalita' C — gestito con traduzione P0001.
    def create_riga(self, contratto_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        self._v.guard_positive_int(contratto_id, field="contratto_id")
        self._assert_contratto_draft(contratto_id, op_label="Aggiunta riga contratto")
        self._v.reject_keys(
            payload,
            forbidden=_FORBIDDEN_RIGA_CREATE,
            reason="contratto_id arriva dall'URL, non dal payload.",
            detail_prefix="Campi rifiutati",
        )
        self._v.validate_allowed_keys(payload, allowed=_CREATE_KEYS_RIGA, message=_MESSAGE_RIGA)
        data = self._build_data_riga(payload, for_create=True)

        with self._db_errors(
            {"contratto_id": contratto_id},
            fallback_message="Violazione vincolo DB su riga contratto.",
        ):
            new_id = self._repo.create_riga(contratto_id, data)

        result = self._repo.get_riga(new_id)
        assert result is not None
        return result

    # Scopo: Aggiorna una riga contratto. articolo_id immutabile.
    def update_riga(
        self, riga_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        self._v.guard_positive_int(riga_id, field="riga_id")
        self._assert_contratto_draft_from_riga(riga_id, op_label="Modifica riga contratto")
        self._v.reject_keys(
            payload,
            forbidden=_FORBIDDEN_RIGA_UPDATE,
            reason="articolo_id e contratto_id immutabili: per rimpiazzarli eliminare la riga e crearne una nuova.",
            detail_prefix="Campi rifiutati",
        )
        self._v.validate_allowed_keys(payload, allowed=_UPDATE_KEYS_RIGA, message=_MESSAGE_RIGA)
        data = self._build_data_riga(payload, for_create=False)

        ErrorManager.require(
            bool(data),
            code=E_VENDITE_VALIDATION,
            message="Nessun campo aggiornabile presente nel payload riga.",
            context={"allowed_keys": sorted(_UPDATE_KEYS_RIGA)},
        )

        with self._db_errors(
            {"riga_id": riga_id},
            fallback_message="Violazione vincolo DB su riga contratto.",
        ):
            updated = self._repo.update_riga(riga_id, data)

        ErrorManager.require(
            updated,
            code=E_VENDITE_NOT_FOUND,
            message="Riga contratto non trovata.",
            context={"riga_id": riga_id},
        )
        result = self._repo.get_riga(riga_id)
        assert result is not None
        return result

    # Scopo: Elimina una riga contratto (hard delete). Eventuali note
    #        collegate bloccano la cancellazione via trigger DB.
    def delete_riga(self, riga_id: int) -> None:
        self._v.guard_positive_int(riga_id, field="riga_id")
        self._assert_contratto_draft_from_riga(riga_id, op_label="Eliminazione riga contratto")
        with self._db_errors(
            {"riga_id": riga_id},
            fallback_message="Impossibile eliminare la riga (dipendenze).",
        ):
            deleted = self._repo.delete_riga(riga_id)
        ErrorManager.require(
            deleted,
            code=E_VENDITE_NOT_FOUND,
            message="Riga contratto non trovata.",
            context={"riga_id": riga_id},
        )

    # =================================================================
    # Utility 1:1
    # =================================================================

    # Scopo: Crea la riga utility associata al contratto. Richiede che
    #        istanza_utility_id / utility_id coincidano con quelli della
    #        testata (controllo anticipato lato service).
    def create_utility(self, contratto_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        self._v.guard_positive_int(contratto_id, field="contratto_id")
        testata = self._repo.get_contratto(contratto_id)
        ErrorManager.require(
            testata is not None,
            code=E_VENDITE_NOT_FOUND,
            message="Contratto non trovato.",
            context={"contratto_id": contratto_id},
        )
        assert testata is not None
        # Guard Profilo A: utility 1:1 modificabile solo in DRAFT.
        stato_corrente = str(testata.get("stato_codice") or "")
        if stato_corrente != "DRAFT":
            ErrorManager.raise_error(
                code="E_CONTRATTO_NON_MODIFICABILE",
                message="Operazione non consentita nello stato corrente.",
                detail=(
                    f"Aggiunta utility ammessa solo su contratti in stato DRAFT. "
                    f"Stato corrente: {stato_corrente}."
                ),
                context={"contratto_id": contratto_id, "stato_codice": stato_corrente},
            )

        self._validate_utility_payload_shape(payload, for_create=True)
        data = self._build_utility_data(
            payload,
            istanza_utility_id=int(testata["istanza_utility_id"]),
            utility_id=int(testata["utility_id"]),
            for_create=True,
        )

        with self._db_errors(
            {"contratto_id": contratto_id},
            fallback_message="Violazione vincolo DB su utility contratto.",
        ):
            self._repo.create_utility(contratto_id, data)

        result = self._repo.get_utility(contratto_id)
        assert result is not None
        return result

    # Scopo: Aggiorna la riga utility (1:1 con il contratto). I campi
    #        identificativi contratto/istanza/utility sono immutabili.
    def update_utility(self, contratto_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        self._v.guard_positive_int(contratto_id, field="contratto_id")
        # Guard Profilo A: utility modificabile solo in DRAFT.
        self._assert_contratto_draft(contratto_id, op_label="Modifica utility contratto")
        existing = self._repo.get_utility(contratto_id)
        ErrorManager.require(
            existing is not None,
            code=E_VENDITE_NOT_FOUND,
            message="Riga utility non trovata per il contratto.",
            context={"contratto_id": contratto_id},
        )
        assert existing is not None

        self._v.reject_keys(
            payload,
            forbidden=_UTILITY_IMMUTABLE_KEYS,
            reason="Identificativi utility immutabili.",
            detail_prefix="Campi rifiutati",
        )
        self._v.validate_allowed_keys(payload, allowed=_UTILITY_UPDATE_KEYS, message=_MESSAGE_UTILITY)
        self._validate_utility_payload_shape(payload, for_create=False)
        data = self._build_utility_data(
            payload,
            istanza_utility_id=int(existing["istanza_utility_id"]),
            utility_id=int(existing["utility_id"]),
            for_create=False,
        )
        ErrorManager.require(
            bool(data),
            code=E_VENDITE_VALIDATION,
            message="Nessun campo aggiornabile presente nel payload utility.",
            context={"allowed_keys": sorted(_UTILITY_UPDATE_KEYS)},
        )

        with self._db_errors(
            {"contratto_id": contratto_id},
            fallback_message="Violazione vincolo DB su utility contratto.",
        ):
            updated = self._repo.update_utility(int(existing["id"]), data)

        ErrorManager.require(
            updated,
            code=E_VENDITE_NOT_FOUND,
            message="Riga utility non trovata.",
            context={"contratto_id": contratto_id},
        )
        result = self._repo.get_utility(contratto_id)
        assert result is not None
        return result

    # =================================================================
    # Helpers privati — payload testata
    # =================================================================

    # Scopo: Compone il dict di create testata validando campi e modalita'.
    def _build_create_data_testata(self, payload: dict[str, Any]) -> dict[str, Any]:
        data: dict[str, Any] = {
            "billing_account_id": self._v.require_positive_int(
                payload, "billing_account_id", message=_MESSAGE,
            ),
            "istanza_utility_id": self._v.require_positive_int(
                payload, "istanza_utility_id", message=_MESSAGE,
            ),
            "utility_id": self._v.require_positive_int(
                payload, "utility_id", message=_MESSAGE,
            ),
            "valido_dal": self._v.require_date(payload, "valido_dal", message=_MESSAGE),
        }
        # valido_al e ambito opzionali in create (ambito ha default DB
        # 'COMMODITY', valido_al puo' essere aperto).
        if "valido_al" in payload and payload["valido_al"] is not None:
            valido_al = self._v.require_date(payload, "valido_al", message=_MESSAGE)
            data["valido_al"] = valido_al
            ErrorManager.require(
                valido_al >= data["valido_dal"],
                code=E_VENDITE_VALIDATION,
                message=_MESSAGE,
                detail="valido_al deve essere >= valido_dal.",
                context={"valido_dal": data["valido_dal"], "valido_al": valido_al},
            )
        if "ambito" in payload:
            data["ambito"] = self._extract_ambito(payload)
        self._apply_optional_positive_int(
            payload, data, "parent_contratto_id", message=_MESSAGE,
        )
        if "data" in payload:
            data["data"] = self._v.require_date(payload, "data", message=_MESSAGE)
        self._apply_optional_positive_int(
            payload, data, "listino_id", message=_MESSAGE,
        )
        self._apply_variazione_globale(payload, data)
        self._validate_modalita_coerente(data, existing=None)
        # Snapshot categoria cliente: opzionale, nullable. Se fornito
        # congela il valore scelto dall'operatore; se omesso il trigger
        # DB lo popola dal BA.
        self._apply_optional_positive_int(
            payload, data, "categoria_cliente_id_snapshot", message=_MESSAGE,
        )
        # Snapshot categoria cliente: opzionale, nullable. Se fornito
        # congela il valore scelto dall'operatore; se omesso il trigger
        # DB lo popola dal BA.
        self._apply_optional_positive_int(
            payload, data, "categoria_cliente_id_snapshot", message=_MESSAGE,
        )
        if "meta" in payload:
            meta = self._v.optional_meta(payload)
            if meta is not None:
                data["meta"] = meta
        return data

    # Scopo: Compone il dict di update testata. Rivalida modalita' con
    #        la foto attuale (listino_id puo' cambiare liberamente in
    #        DRAFT; il trigger attivazione re-bilancia su transizione).
    #        `existing` e' la riga corrente dal DB: serve per calcolare la
    #        modalita' effettiva quando il patch tocca solo una dimensione
    #        (es. variazione globale senza listino_id nel payload).
    def _build_update_data_testata(
        self, payload: dict[str, Any], *, existing: dict[str, Any]
    ) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if "ambito" in payload:
            data["ambito"] = self._extract_ambito(payload)
        if "valido_dal" in payload:
            data["valido_dal"] = self._v.require_date(payload, "valido_dal", message=_MESSAGE)
        if "valido_al" in payload:
            if payload["valido_al"] is None:
                data["valido_al"] = None
            else:
                data["valido_al"] = self._v.require_date(payload, "valido_al", message=_MESSAGE)
        if "valido_dal" in data and "valido_al" in data and data["valido_al"] is not None:
            ErrorManager.require(
                data["valido_al"] >= data["valido_dal"],
                code=E_VENDITE_VALIDATION,
                message=_MESSAGE,
                detail="valido_al deve essere >= valido_dal.",
                context={"valido_dal": data["valido_dal"], "valido_al": data["valido_al"]},
            )
        self._apply_optional_positive_int(
            payload, data, "parent_contratto_id", message=_MESSAGE,
        )
        if "data" in payload:
            data["data"] = self._v.require_date(payload, "data", message=_MESSAGE)
        self._apply_optional_positive_int(
            payload, data, "listino_id", message=_MESSAGE,
        )
        self._apply_variazione_globale(payload, data)
        # Valida modalita' sulla foto post-update merge (delta data + existing).
        # Se il patch tocca una delle 3 dimensioni (listino o variazione),
        # rivalida la coerenza combinando i campi presenti con lo stato corrente.
        if (
            "listino_id" in data
            or "tipo_variazione_globale" in data
            or "valore_variazione_globale" in data
        ):
            self._validate_modalita_coerente(data, existing=existing)
        # Categoria snapshot: ammessa in PATCH solo in DRAFT (guard gia' sopra).
        self._apply_optional_positive_int(
            payload, data, "categoria_cliente_id_snapshot", message=_MESSAGE,
        )
        if "meta" in payload:
            meta = self._v.optional_meta(payload)
            if meta is not None:
                data["meta"] = meta
        return data

    # Scopo: Normalizza ambito a uppercase e valida contro whitelist.
    def _extract_ambito(self, payload: dict[str, Any]) -> str:
        raw = payload.get("ambito")
        ErrorManager.require(
            isinstance(raw, str) and raw.strip() != "",
            code=E_VENDITE_VALIDATION,
            message=_MESSAGE,
            detail="ambito deve essere una stringa non vuota.",
            context={"field": "ambito"},
        )
        assert isinstance(raw, str)
        value = raw.strip().upper()
        ErrorManager.require(
            value in _AMBITI_VALIDI,
            code=E_VENDITE_VALIDATION,
            message=_MESSAGE,
            detail=f"ambito deve essere uno tra: {', '.join(sorted(_AMBITI_VALIDI))}.",
            context={"ambito": value},
        )
        return value

    # Scopo: Estrae e applica la coppia (tipo/valore) variazione globale
    #        nel data dict. Coerenza coppia validata in contesto modalita'.
    def _apply_variazione_globale(
        self, payload: dict[str, Any], data: dict[str, Any]
    ) -> None:
        tipo_present = "tipo_variazione_globale" in payload
        valore_present = "valore_variazione_globale" in payload
        tipo = None
        valore = None
        if tipo_present:
            raw = payload.get("tipo_variazione_globale")
            if raw is None:
                data["tipo_variazione_globale"] = None
            else:
                ErrorManager.require(
                    isinstance(raw, str),
                    code=E_VENDITE_VALIDATION,
                    message=_MESSAGE,
                    detail="tipo_variazione_globale deve essere una stringa o NULL.",
                    context={"field": "tipo_variazione_globale"},
                )
                tipo = raw.strip().upper()
                ErrorManager.require(
                    tipo in _TIPI_VARIAZIONE,
                    code=E_VENDITE_VALIDATION,
                    message=_MESSAGE,
                    detail=f"tipo_variazione_globale deve essere uno tra: {', '.join(sorted(_TIPI_VARIAZIONE))}.",
                    context={"tipo_variazione_globale": tipo},
                )
                data["tipo_variazione_globale"] = tipo
        if valore_present:
            raw = payload.get("valore_variazione_globale")
            if raw is None:
                data["valore_variazione_globale"] = None
            else:
                valore = self._coerce_decimal(raw, field="valore_variazione_globale")
                data["valore_variazione_globale"] = valore

    # Scopo: Verifica coerenza modalita' A/B/C pre-DB. Il CHECK DB enforcera'
    #        lo stesso invariante ma il messaggio parlante e' piu' utile qui.
    #
    #        Regole (sviluppo-listini-v5 §5.1):
    #          - se listino_id IS NULL (modalita' C) -> tipo/valore globali
    #            DEVONO essere NULL.
    #          - tipo/valore globali devono essere entrambi NULL o entrambi
    #            NOT NULL (coppia coerente).
    def _validate_modalita_coerente(
        self, data: dict[str, Any], *, existing: dict[str, Any] | None
    ) -> None:
        listino_id = data.get("listino_id") if "listino_id" in data else (
            existing.get("listino_id") if existing else None
        )
        tipo = data.get("tipo_variazione_globale") if "tipo_variazione_globale" in data else (
            existing.get("tipo_variazione_globale") if existing else None
        )
        valore = data.get("valore_variazione_globale") if "valore_variazione_globale" in data else (
            existing.get("valore_variazione_globale") if existing else None
        )
        if listino_id is None:
            ErrorManager.require(
                tipo is None and valore is None,
                code=E_VENDITE_VALIDATION,
                message=_MESSAGE,
                detail="Contratto modalita' C (listino_id NULL): tipo/valore variazione globale devono essere NULL.",
                context={
                    "listino_id": listino_id,
                    "tipo_variazione_globale": tipo,
                    "valore_variazione_globale": str(valore) if valore is not None else None,
                },
            )
        # Coppia coerente (tipo e valore entrambi NULL o entrambi NOT NULL).
        pair_complete = (tipo is None) == (valore is None)
        ErrorManager.require(
            pair_complete,
            code=E_VENDITE_VALIDATION,
            message=_MESSAGE,
            detail="tipo_variazione_globale e valore_variazione_globale devono essere entrambi presenti o entrambi NULL.",
            context={
                "tipo_variazione_globale": tipo,
                "valore_variazione_globale": str(valore) if valore is not None else None,
            },
        )

    # =================================================================
    # Helpers privati — righe
    # =================================================================

    # Scopo: Compone il dict CRUD per contratti_righe. articolo_id
    #        obbligatorio in create; mutazione dei campi commerciali
    #        solo sui campi presenti.
    def _build_data_riga(self, payload: dict[str, Any], *, for_create: bool) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if for_create:
            data["articolo_id"] = self._v.require_uuid(
                payload, "articolo_id", message=_MESSAGE_RIGA,
            )
        # Numeric opzionali.
        for field in ("prezzo_unitario", "quantita", "qta_operativa", "factor_to_base"):
            if field in payload:
                raw = payload[field]
                if raw is None:
                    data[field] = None
                else:
                    data[field] = self._coerce_decimal(
                        raw, field=field, message=_MESSAGE_RIGA,
                    )
        self._apply_optional_positive_int(
            payload, data, "uom_operativa_id", message=_MESSAGE_RIGA,
        )
        if "ordine" in payload:
            value = self._v.optional_smallint(payload, "ordine", min_val=0)
            if value is not None:
                data["ordine"] = value
        if "attivo" in payload:
            value = self._v.optional_bool(payload, "attivo")
            if value is not None:
                data["attivo"] = value
        # Stringhe opzionali (varchar libere lato DB: CHECK constraint sul DB
        # per enum — traduciamo un eventuale IntegrityError.
        for field in (
            "tipo_erogazione",
            "fonte_quantita_attesa",
            "periodicita",
            "generazione_canone",
            "competenza_canone",
        ):
            if field in payload:
                raw = payload[field]
                if raw is None:
                    data[field] = None
                else:
                    ErrorManager.require(
                        isinstance(raw, str),
                        code=E_VENDITE_VALIDATION,
                        message=_MESSAGE_RIGA,
                        detail=f"{field} deve essere stringa o NULL.",
                        context={"field": field},
                    )
                    assert isinstance(raw, str)
                    data[field] = raw.strip().upper()
        if "meta" in payload:
            meta = self._v.optional_meta(payload)
            if meta is not None:
                data["meta"] = meta
        return data

    # =================================================================
    # Helpers privati — utility 1:1
    # =================================================================

    # Scopo: Verifica struttura payload utility. Il controllo di coerenza
    #        tipo/classe dinamico e' delegato al trigger DB.
    def _validate_utility_payload_shape(
        self, payload: dict[str, Any], *, for_create: bool
    ) -> None:
        allowed = _UTILITY_CREATE_KEYS if for_create else _UTILITY_UPDATE_KEYS
        self._v.validate_allowed_keys(
            payload, allowed=allowed, message=_MESSAGE_UTILITY,
        )

    # Scopo: Compone il dict CRUD per contratti_utilities. istanza_utility_id
    #        e utility_id sono derivati dal contratto, non dal payload.
    def _build_utility_data(
        self,
        payload: dict[str, Any],
        *,
        istanza_utility_id: int,
        utility_id: int,
        for_create: bool,
    ) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if for_create:
            data["istanza_utility_id"] = istanza_utility_id
            data["utility_id"] = utility_id
        for fk_field in ("istanza_dati_precontrattuali_id", "tipo_utenza_id", "classe_utenza_id"):
            self._apply_optional_positive_int(
                payload, data, fk_field, message=_MESSAGE_UTILITY,
            )
        if "param_1_num" in payload:
            raw = payload["param_1_num"]
            data["param_1_num"] = (
                None
                if raw is None
                else self._coerce_decimal(
                    raw, field="param_1_num", message=_MESSAGE_UTILITY,
                )
            )
        if "param_2_txt" in payload:
            raw = payload["param_2_txt"]
            if raw is None:
                data["param_2_txt"] = None
            else:
                ErrorManager.require(
                    isinstance(raw, str),
                    code=E_VENDITE_VALIDATION,
                    message=_MESSAGE_UTILITY,
                    detail="param_2_txt deve essere stringa o NULL.",
                    context={"field": "param_2_txt"},
                )
                assert isinstance(raw, str)
                data["param_2_txt"] = raw.strip()
        if "meta" in payload:
            meta = self._v.optional_meta(payload)
            if meta is not None:
                data["meta"] = meta
        return data

    # =================================================================
    # Helpers privati — numeri e DB errors
    # =================================================================

    # Scopo: Converte valore in Decimal rifiutando bool e stringhe non numeriche.
    #        `message` e' il titolo mostrato al frontend e deve riflettere la
    #        sub-entita' chiamante (contratto / riga / utility) per una UX
    #        coerente col form di provenienza.
    def _coerce_decimal(
        self, raw: Any, *, field: str, message: str = _MESSAGE
    ) -> Decimal:
        ErrorManager.require(
            not isinstance(raw, bool),
            code=E_VENDITE_VALIDATION,
            message=message,
            detail=f"{field} deve essere numerico.",
            context={"field": field, "value": raw},
        )
        try:
            return Decimal(str(raw).strip())
        except (InvalidOperation, AttributeError) as exc:
            ErrorManager.raise_error(
                code=E_VENDITE_VALIDATION,
                message=message,
                detail=f"{field} non e' un numero valido.",
                context={"field": field, "value": raw},
                cause=exc,
            )
            raise AssertionError("unreachable") from exc  # pragma: no cover

    # Scopo: Helper per campi int opzionali nullable. Estrae dal payload,
    #        accetta None esplicito, valida positivita' altrimenti. Applica
    #        al data dict solo se la chiave e' presente nel payload.
    def _apply_optional_positive_int(
        self,
        payload: dict[str, Any],
        data: dict[str, Any],
        field: str,
        *,
        message: str,
    ) -> None:
        if field not in payload:
            return
        raw = payload[field]
        if raw is None:
            data[field] = None
            return
        data[field] = self._v.require_positive_int(payload, field, message=message)

    # Scopo: Traduce DatabaseError (P0001 via fn_log_and_raise_error) nel
    #        codice domain-specifico se matcha un marker noto; altrimenti
    #        fallback E_VENDITE_VALIDATION con detail originale.
    def _raise_db_error(self, exc: DatabaseError, *, context: dict[str, Any]) -> None:
        msg = str(exc)
        matched_code: str | None = None
        for code_candidate, markers in _KNOWN_DB_ERROR_MARKERS:
            if all(marker in msg for marker in markers):
                matched_code = code_candidate
                break
        code = matched_code or E_VENDITE_VALIDATION
        ErrorManager.raise_error(
            code=code,
            message="Violazione vincolo contrattuale." if matched_code else _MESSAGE,
            detail=msg,
            context=context,
            cause=exc,
            log_to_db=True,
            function_name="contratti_service.db_error",
        )
        raise AssertionError("unreachable")  # pragma: no cover
