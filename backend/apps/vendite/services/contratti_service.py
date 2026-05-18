# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service facade per vendite.contratti + contratti_righe +
#        contratti_utilities (CRUD v5 — F2-BE-05).
#
#        Modello contratto post refactor 2026-05-15: un unico tipo di
#        contratto con due forme derivate (non scelte dall'operatore):
#          - "con_listino"  : `listino_id` valorizzato. Le righe del listino
#                             sono lette via resolver (versione fissata
#                             all'attivazione). Le eccezioni vivono in
#                             `contratti_righe` come OVERRIDE / ESCLUSIONE /
#                             AGGIUNTA. Variazione globale opzionale.
#          - "senza_listino": `listino_id` NULL. Tutte le righe sono AGGIUNTA
#                             con prezzo manuale, governate dal contratto
#                             stesso.
#
#        Validazioni in ordine crescente di costo:
#          1) struttura payload (chiavi ammesse, tipi)
#          2) coerenza coppia variazione globale (tipo+valore entrambi
#             NULL o entrambi NOT NULL)
#          3) affidamento ai trigger DB per gli invarianti piu' complessi
#             (overlap cross-contratto, tipo/classe utenza dinamica, lock
#             post-attivazione, validita' versione listino fissata).
#
#        Il numero contratto e' generato nel service via
#        `script.fn_generate_codice('contratto')` — NON va mai
#        accettato in payload (immutabile via trigger lock_columns).
# ------------------------------------------------------------

from __future__ import annotations

import logging
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
from apps.vendite.db.listini_repository import ListiniRepository
from apps.vendite.services._componenti_service_helpers import (
    normalize_componenti_overrides,
    resolve_emittente_sr_id_for_testata,
)
from apps.vendite.services._approvazioni_prezzo_constants import (
    SORGENTE_CONTRATTO,
    STATO_APPROVAZIONE_PENDING,
)
from apps.vendite.services._pricing_gate_helpers import (
    check_limite_variazione_globale,
    guard_uom_id_positive,
    resolve_or_check_override_prezzo,
)

logger = logging.getLogger(__name__)


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
# Tipi variazione ammessi sulla variazione GLOBALE della testata contratto.
# Decisione 2026-05-18 (§3-bis-E refactor): solo PERCENTUALE. VALORE_FISSO
# resta ammesso unicamente per OVERRIDE su singola riga (semantica "prezzo
# fisso sostitutivo per quell'articolo") — non per la testata, dove non
# avrebbe significato applicativo coerente coi gate L2 % e con la formula
# di applicazione cross-articolo del listino.
_TIPI_VARIAZIONE_GLOBALE_AMMESSI: frozenset[str] = frozenset({"PERCENTUALE"})


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


# Righe contratto: chiavi ammesse create/update. tipo_eccezione e' la
# classificazione introdotta dal refactor 2026-05-15: distingue OVERRIDE,
# ESCLUSIONE, AGGIUNTA. Obbligatoria in create (NOT NULL nello schema),
# immutabile in update (per cambiare tipo serve DELETE + INSERT — meno
# zone grigie di un cambio di semantica in-place).
_CREATE_KEYS_RIGA: frozenset[str] = frozenset({
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
    # Modello unificato BoM 2026-05-13: override prezzi componenti per
    # auto-init post-create_riga su articoli compositi. Forma:
    # {componente_id_uuid: prezzo_numeric}. Validato/normalizzato da
    # `_normalize_componenti_overrides` prima dell'init.
    "componenti_overrides",
    # Workflow L3 (refactor 2026-05-19 BE porting gate riga contratti): flag
    # opt-in con cui il client conferma di voler aprire una pratica di
    # approvazione quando il prezzo viola L2. Estratto e consumato da
    # create_riga prima di `_build_data_riga` (non finisce nella tabella).
    "richiesta_approvazione",
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
    # Workflow L3: vedi commento _CREATE_KEYS_RIGA. update_riga lo gestisce
    # alla stessa stregua per `prezzo_unitario` modificato che viola L2.
    "richiesta_approvazione",
})

# In create: contratto_id arriva dall'URL, non da payload. articolo_id e
# tipo_eccezione sono obbligatori e accettati. In update: articolo_id e
# tipo_eccezione diventano immutabili (cambio tipo = DELETE + INSERT).
_FORBIDDEN_RIGA_CREATE: frozenset[str] = frozenset({"contratto_id"})
_FORBIDDEN_RIGA_UPDATE: frozenset[str] = frozenset({
    "articolo_id", "contratto_id", "tipo_eccezione",
})

# Tipi eccezione ammessi su contratti_righe (refactor 2026-05-15).
_TIPI_ECCEZIONE: frozenset[str] = frozenset({"OVERRIDE", "ESCLUSIONE", "AGGIUNTA"})
# Sottoinsieme che richiede il passaggio per il gate L1+L2+L3 (refactor
# 2026-05-19 BE porting gate riga contratti). ESCLUSIONE ha prezzo NULL per
# design e salta i gate; OVERRIDE/AGGIUNTA passano al BB
# `resolve_or_check_override_prezzo_riga_contratto` con la matrice
# Alternativa B (L1 sempre, L2/L3 condizionali al resolver).
_TIPI_ECCEZIONE_CON_GATE: frozenset[str] = frozenset({"OVERRIDE", "AGGIUNTA"})


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
    "uq_contratti_no_overlap": (
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
    # Refactor modalita 2026-05-15: i vecchi marker E_CONTRATTO_MODALITA_C_*
    # sono stati droppati dal team DB con i trigger correlati. I nuovi
    # marker coprono il modello unificato a 3 eccezioni + lock attivazione.
    (
        "E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE",
        ("contratto senza listino", "almeno un'AGGIUNTA"),
    ),
    (
        "E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO",
        ("AGGIUNTA", "gia' presente nel listino"),
    ),
    (
        "E_ARTICOLO_ESCLUSO_DA_CONTRATTO",
        ("articolo escluso dal contratto",),
    ),
    (
        "E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE",
        ("contratto ATTIVO", "campi bloccati"),
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
        righe = self._repo.list_righe(contratto_id)
        testata["righe"] = righe
        # Il badge FE "Gestisci righe" deve riflettere la lista effettiva
        # mostrata dal sub-drawer: in A/B e' preview listino+override, in C
        # sono le righe negoziate persistite in contratti_righe.
        if testata.get("listino_id"):
            testata["righe_count"] = len(self._repo.list_righe_preview(contratto_id))
        else:
            testata["righe_count"] = len(righe)
        capabilities = self._repo.get_capabilities(contratto_id)
        testata.update(capabilities)
        return testata

    # =================================================================
    # Creazione testata
    # =================================================================

    # Scopo: Crea un nuovo contratto. Genera numero via fn_generate_codice,
    #        risolve stato iniziale DRAFT, valida coerenza coppia variazione
    #        globale pre-DB, opzionalmente crea la riga utility 1:1 nella
    #        stessa transazione (trigger DB gestira' fail-fast su coerenze
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
    #        Validazione coerenza coppia variazione globale pre-DB.
    #        `auth_user_id`: usato dal gate L2 sulla variazione globale
    #        (refactor 2026-05-15 §3-bis-E) per risolvere la soglia con la
    #        cascata user→categoria→group→emittente. None = gate L2 skip.
    def update_contratto(
        self,
        contratto_id: int,
        payload: dict[str, Any],
        *,
        auth_user_id: int | None = None,
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

        # Leggiamo la testata esistente PRIMA di validare la coppia variazione
        # globale: serve al validator per sapere il listino_id corrente quando
        # il payload patch non lo include (es. patch solo su variazione globale).
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

        # Refactor modalita 2026-05-15 §3-bis-E: se il PATCH tocca la
        # variazione globale e il tipo e' PERCENTUALE, applichiamo il gate L2
        # sulla soglia configurata per (utente, categoria cliente, ...).
        # Per VALORE_FISSO il gate non e' applicabile (non e' una percentuale)
        # e viene saltato — decisione operativa §3-bis-E "decisione brief DB".
        self._check_limite_variazione_globale(
            existing=existing,
            data=data,
            auth_user_id=auth_user_id,
        )

        # Refactor modalita 2026-05-15 §3-bis-F: se il PATCH rimuove il
        # listino_id (NOT NULL -> NULL) e esistono eccezioni OVERRIDE o
        # ESCLUSIONE attive, blocca con 422 — il significato di quelle
        # eccezioni dipende dal listino e cancellarle silenziosamente sarebbe
        # un cambio di semantica nascosto. AGGIUNTA non blocca (vale anche
        # senza listino). L'operatore deve prima rimuovere/sostituire le
        # eccezioni esplicitamente.
        sta_rimuovendo_listino = (
            "listino_id" in data
            and data["listino_id"] is None
            and existing.get("listino_id") is not None
        )
        if sta_rimuovendo_listino:
            counts = self._repo.count_eccezioni_bloccanti(contratto_id)
            n_override = counts.get("OVERRIDE", 0)
            n_esclusione = counts.get("ESCLUSIONE", 0)
            if n_override > 0 or n_esclusione > 0:
                totale = n_override + n_esclusione
                dettagli = []
                if n_override:
                    dettagli.append(f"{n_override} OVERRIDE")
                if n_esclusione:
                    dettagli.append(f"{n_esclusione} ESCLUSIONE")
                ErrorManager.raise_error(
                    code="E_CONTRATTO_LISTINO_RIMOZIONE_CON_ECCEZIONI",
                    message="Impossibile rimuovere il listino di riferimento dal contratto.",
                    detail=(
                        f"{totale} eccezioni ({', '.join(dettagli)}) sono ancora "
                        f"associate. Rimuovi prima le eccezioni o sostituiscile "
                        f"con AGGIUNTA per articoli fuori-listino."
                    ),
                    context={
                        "contratto_id": contratto_id,
                        "override_count": n_override,
                        "esclusione_count": n_esclusione,
                    },
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
    #        PATCH valido_al). L'attivazione di un contratto "senza_listino"
    #        privo di righe AGGIUNTA e' bloccata dai trigger DB del refactor
    #        2026-05-15 (E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE, lock
    #        post-attivazione su listino_versione_id): traduciamo i P0001
    #        in ServiceError parlanti via `_KNOWN_DB_ERROR_MARKERS`.
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
    # Contesto pricing (banner FE)
    # =================================================================

    # Scopo: Restituisce il contesto pricing applicato al contratto (forma,
    #        listino + versione fissata/corrente, variazione globale,
    #        categoria cliente). Mutuato dal pattern preventivi
    #        `get_contesto_pricing` per la simmetria UI: l'header del drawer
    #        contratto mostra un badge con questi dati per audit visivo del
    #        path resolver applicato. Lettura puramente informativa.
    def get_contesto_pricing(
        self, contratto_id: int,
    ) -> dict[str, Any] | None:
        self._v.guard_positive_int(contratto_id, field="contratto_id")
        return self._repo.resolve_contesto_pricing_contratto(contratto_id)

    # =================================================================
    # Righe contratto - preview pricing applicato
    # =================================================================

    # Scopo: Restituisce le righe operative del contratto in forma "con_listino",
    #        cioe' la lista articoli con prezzo finale applicato (righe del
    #        listino + eccezioni OVERRIDE/ESCLUSIONE/AGGIUNTA). Per forma
    #        "senza_listino" ritorna lista vuota: in quel caso le righe
    #        vivono solo in `contratti_righe` e sono lette da list_righe.
    #
    #        Il calcolo e' delegato a `repository.list_righe_preview` (single
    #        SQL pass) che applica la stessa formula del resolver pricing.
    #        Origini possibili: 'DA_LISTINO' (riga del listino senza eccezione),
    #        'OVERRIDE' / 'ESCLUSIONE' / 'AGGIUNTA' (eccezione contrattuale).
    #
    #        L'envelope include la testata sintetica (forma, listino, versione
    #        listino fissata, variazione globale) per permettere al FE di
    #        renderizzare il banner contesto senza ulteriori chiamate.
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

        # Forma derivata (non persistita) post refactor modalita 2026-05-15:
        #   "con_listino"  : contratto ha un listino_id (variazione globale +
        #                    eccezioni OVERRIDE/ESCLUSIONE/AGGIUNTA sono campi
        #                    opzionali liberi)
        #   "senza_listino": contratto interamente negoziato (le righe in
        #                    `contratti_righe` sono tutte AGGIUNTA)
        # Le vecchie modalita' A/B/C sono state rimosse — non esistono piu'
        # nel modello dati ne' nell'UX.
        listino_id = contratto.get("listino_id")
        preview_rows: list[dict[str, Any]] = (
            self._repo.list_righe_preview(contratto_id) if listino_id else []
        )
        forma = "con_listino" if listino_id is not None else "senza_listino"

        # Flag per il FE: distingue il caso "listino senza versione operativa
        # oggi" dal caso "senza_listino" (lista vuota by design) e dal caso
        # con listino ma solo eccezioni extra-listino (righe presenti ma
        # origine OVERRIDE/AGGIUNTA, nessuna 'DA_LISTINO'). Il flag e' True
        # se il contratto ha listino ma la query non ha prodotto nemmeno una
        # riga 'DA_LISTINO' (nessuna versione operativa o nessuna riga attiva).
        listino_senza_versione_oggi = (
            listino_id is not None
            and not any(r.get("origine") == "DA_LISTINO" for r in preview_rows)
        )

        return {
            "contratto_id": contratto_id,
            "forma": forma,
            "listino_id": listino_id,
            "listino_versione_id": contratto.get("listino_versione_id"),
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

    # Scopo: Aggiunge una riga al contratto. I trigger DB del refactor
    #        2026-05-15 governano la coerenza dell'eccezione
    #        (tipo_eccezione vs prezzo_unitario, AGGIUNTA non duplicabile su
    #        articoli del listino, lock post-attivazione): traduzione P0001
    #        via `_KNOWN_DB_ERROR_MARKERS`.
    def create_riga(
        self, contratto_id: int, payload: dict[str, Any],
        *, auth_user_id: int | None = None,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(contratto_id, field="contratto_id")
        self._assert_contratto_draft(contratto_id, op_label="Aggiunta riga contratto")
        self._v.reject_keys(
            payload,
            forbidden=_FORBIDDEN_RIGA_CREATE,
            reason="contratto_id arriva dall'URL, non dal payload.",
            detail_prefix="Campi rifiutati",
        )
        self._v.validate_allowed_keys(payload, allowed=_CREATE_KEYS_RIGA, message=_MESSAGE_RIGA)
        # `componenti_overrides` non e' campo di `contratti_righe`: estraiamo
        # PRIMA di `_build_data_riga` cosi' non finisce nell'INSERT.
        componenti_overrides_raw = payload.pop("componenti_overrides", None)
        componenti_overrides = normalize_componenti_overrides(
            componenti_overrides_raw,
            function_name="contratti_service.create_riga",
            error_code=E_VENDITE_VALIDATION,
        )
        # Flag opt-in workflow L3 (richiesta approvazione). Estratto qui per
        # non finire nel data_riga.
        richiesta_approvazione = bool(payload.pop("richiesta_approvazione", False))

        data = self._build_data_riga(payload, for_create=True)

        articolo_id = payload.get("articolo_id")
        tipo_eccezione = data.get("tipo_eccezione")

        # Gate L1+L2+L3: solo OVERRIDE/AGGIUNTA. Helper riusato da update_riga.
        # `testata_gate` riusato sotto per il ramo composito (1 round-trip
        # DB risparmiato).
        pratica_id_l3: int | None = None
        testata_gate: dict[str, Any] | None = None
        if tipo_eccezione in _TIPI_ECCEZIONE_CON_GATE:
            pratica_id_l3, testata_gate = self._apply_pricing_gate_riga(
                contratto_id=contratto_id,
                articolo_id=articolo_id,
                uom_id=data.get("uom_operativa_id"),
                data=data,
                auth_user_id=auth_user_id,
                richiesta_approvazione=richiesta_approvazione,
                riga_id_for_link=None,  # riga_id non noto qui
                function_name="contratti_service.create_riga",
            )

        # Transazione atomica: create_riga + (se composito) auto-init
        # componenti. Stesso pattern di preventivi_service. Senza atomic, una
        # riga padre composito potrebbe restare senza componenti se la fn DB
        # `fn_contratto_riga_componenti_init` solleva (es. BoM scaduta).
        with transaction.atomic(), self._db_errors(
            {"contratto_id": contratto_id},
            fallback_message="Violazione vincolo DB su riga contratto.",
        ):
            new_id = self._repo.create_riga(contratto_id, data)

            # Link riga<->pratica L3: post-create_riga, riga_id ora noto.
            # link_riga_a_pratica aggiunge `riga_contratto_id` al meta della
            # pratica per permettere all'approver di risalire dalla coda
            # (UI ApprovazioniPrezzoListView routing su /righe-contratto/...).
            if pratica_id_l3 is not None:
                from apps.vendite.services.approvazioni_prezzo_service import (
                    link_riga_a_pratica,
                )
                link_riga_a_pratica(
                    pratica_id=pratica_id_l3,
                    riga_id=new_id,
                    sorgente=SORGENTE_CONTRATTO,
                )

            if articolo_id and self._repo.is_articolo_composito(str(articolo_id)):
                # Riusa la testata letta dal gate (sopra) se disponibile;
                # altrimenti (gate skip per ESCLUSIONE) la carica adesso.
                testata = testata_gate or self._repo.get_contratto(contratto_id)
                assert testata is not None
                emittente_sr_id = self._resolve_emittente_sr_id_for_contratto(
                    testata, auth_user_id,
                )
                valido_dal_raw = testata.get("valido_dal")
                # Skip silenzioso ammesso solo se mancano emittente o
                # valido_dal: l'admin potra' ri-eseguire l'init manualmente.
                # Logghiamo warning per audit (gap visibile in produzione).
                if emittente_sr_id is None or valido_dal_raw is None:
                    logger.warning(
                        "contratti.create_riga.auto_init_componenti_skipped "
                        "contratto_id=%s riga_id=%s articolo_id=%s "
                        "motivo=%s — la riga padre composita resta senza "
                        "componenti; init manuale richiesto.",
                        contratto_id, new_id, articolo_id,
                        ("emittente_non_risolvibile" if emittente_sr_id is None
                         else "valido_dal_null"),
                    )
                else:
                    data_riferimento = (
                        valido_dal_raw if isinstance(valido_dal_raw, date)
                        else date.fromisoformat(str(valido_dal_raw))
                    )
                    self._repo.init_componenti_riga(
                        riga_id=new_id,
                        emittente_soggetto_ruolo_id=emittente_sr_id,
                        data_riferimento=data_riferimento,
                        componenti_overrides=componenti_overrides,
                    )

        result = self._repo.get_riga(new_id)
        assert result is not None
        return result

    # Scopo: Risolve emittente_soggetto_ruolo_id per le operazioni componenti
    # del contratto. Thin wrapper su `resolve_emittente_sr_id_for_testata`
    # (helper Fase H) per non duplicare la logica di lookup + fallback.
    def _resolve_emittente_sr_id_for_contratto(
        self,
        testata: dict[str, Any],
        auth_user_id: int | None,
    ) -> int | None:
        return resolve_emittente_sr_id_for_testata(
            testata, auth_user_id,
            repo_get_sr_id_by_fiscale_id=self._repo.get_emittente_sr_id_by_fiscale_id,
        )

    # Scopo: Helper unificato per il gate L1+L2+L3 su righe contratto.
    #        Riusato da create_riga e update_riga (refactor 2026-05-19,
    #        rimuove ~30 righe duplicate). Pipeline:
    #          1) get_contratto + invoca BB `resolve_or_check_override_prezzo_riga_contratto`
    #          2) normalizza `data["prezzo_unitario"]` col valore ritornato
    #          3) merge `data["meta"]` con `prezzo_meta` (con fallback opzionale
    #             al meta della riga esistente — case update_riga)
    #          4) se workflow L3 (`richiesta_approvazione_pending`): orchestra
    #             pratica + popola `data["stato_approvazione_prezzo"]` +
    #             `data["pratica_approvazione_prezzo_id"]`. Per create il
    #             `riga_id_for_link=None` (link post-INSERT); per update il
    #             riga_id e' gia' noto.
    #        Ritorna `(pratica_id_l3 | None, testata_gate)`: la testata viene
    #        restituita perche' il caller create_riga la riusa nel ramo
    #        composito evitando un double-fetch.
    def _apply_pricing_gate_riga(
        self,
        *,
        contratto_id: int,
        articolo_id: Any,
        uom_id: Any,
        data: dict[str, Any],
        auth_user_id: int | None,
        richiesta_approvazione: bool,
        riga_id_for_link: int | None,
        function_name: str,
        fallback_meta: dict[str, Any] | None = None,
    ) -> tuple[int | None, dict[str, Any]]:
        testata_gate = self._repo.get_contratto(contratto_id)
        assert testata_gate is not None
        prezzo_finale, prezzo_meta = resolve_or_check_override_prezzo_riga_contratto(
            testata=testata_gate,
            articolo_id=articolo_id,
            uom_id=uom_id,
            payload_prezzo=data.get("prezzo_unitario"),
            auth_user_id=auth_user_id,
            function_name=function_name,
            richiesta_approvazione=richiesta_approvazione,
        )
        # Override prezzo col valore normalizzato dal BB (auto-fill se
        # payload era None + resolver ha prezzo, oppure prezzo manuale
        # confermato dall'L1).
        if prezzo_finale is not None:
            data["prezzo_unitario"] = prezzo_finale
        # Merge meta riga: il BB ritorna `prezzo_meta` con audit pricing.
        # Va mergiato sul `meta` corrente del data_riga (priorita': payload
        # > fallback existing meta) senza sovrascrivere chiavi gia' presenti.
        if prezzo_meta:
            merged_meta = dict(data.get("meta") or fallback_meta or {})
            merged_meta.update(prezzo_meta)
            data["meta"] = merged_meta
        # Workflow L3: il BB ha segnalato violazione + richiesta. Crea pratica
        # PRIMA dell'INSERT/UPDATE riga per ottenere la FK; il link riga<->pratica
        # avviene nel caller (post-INSERT per create, inline per update).
        pratica_id_l3: int | None = None
        if prezzo_meta and prezzo_meta.get("richiesta_approvazione_pending"):
            pratica_id_l3 = _orchestrate_l3_request_contratto(
                contratto_id=contratto_id,
                articolo_id=articolo_id,
                prezzo_finale=prezzo_finale,
                prezzo_meta=prezzo_meta,
                auth_user_id=auth_user_id,
                riga_id_for_link=riga_id_for_link,
            )
            data["stato_approvazione_prezzo"] = STATO_APPROVAZIONE_PENDING
            data["pratica_approvazione_prezzo_id"] = pratica_id_l3
        return pratica_id_l3, testata_gate

    # Scopo: Aggiorna una riga contratto. articolo_id e tipo_eccezione
    #        immutabili (refactor 2026-05-15: per cambiare tipo serve
    #        DELETE + INSERT, meno zone grigie di un cambio di semantica
    #        in-place). Gate L1+L2+L3 attivo quando il PATCH tocca
    #        `prezzo_unitario` su una riga OVERRIDE/AGGIUNTA (refactor
    #        2026-05-19 BE porting gate riga contratti).
    def update_riga(
        self, riga_id: int, payload: dict[str, Any],
        *, auth_user_id: int | None = None,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(riga_id, field="riga_id")
        self._assert_contratto_draft_from_riga(riga_id, op_label="Modifica riga contratto")
        self._v.reject_keys(
            payload,
            forbidden=_FORBIDDEN_RIGA_UPDATE,
            reason="articolo_id, contratto_id e tipo_eccezione immutabili: per rimpiazzarli eliminare la riga e crearne una nuova.",
            detail_prefix="Campi rifiutati",
        )
        self._v.validate_allowed_keys(payload, allowed=_UPDATE_KEYS_RIGA, message=_MESSAGE_RIGA)
        # Flag opt-in L3 estratto pre-build_data (non e' una colonna riga).
        richiesta_approvazione = bool(payload.pop("richiesta_approvazione", False))
        data = self._build_data_riga(payload, for_create=False)

        ErrorManager.require(
            bool(data),
            code=E_VENDITE_VALIDATION,
            message="Nessun campo aggiornabile presente nel payload riga.",
            context={"allowed_keys": sorted(_UPDATE_KEYS_RIGA)},
        )

        # Coerenza prezzo_unitario / tipo_eccezione (refactor 2026-05-15):
        # se il PATCH tocca prezzo_unitario, valida contro il tipo_eccezione
        # della riga esistente (immutabile). Pre-validation parlante invece
        # del fallback E_DATABASE sul CHECK DB chk_contrighe_prezzo_per_tipo_eccezione.
        # Refactor 2026-05-19: il caricamento di `existing_riga` serve anche
        # al gate L1+L2+L3 sotto — fatto qui per evitare double-fetch.
        existing_riga: dict[str, Any] | None = None
        tipo_existing: str | None = None
        if "prezzo_unitario" in data:
            existing_riga = self._repo.get_riga(riga_id)
            ErrorManager.require(
                existing_riga is not None,
                code=E_VENDITE_NOT_FOUND,
                message="Riga contratto non trovata.",
                context={"riga_id": riga_id},
            )
            assert existing_riga is not None
            tipo_existing = existing_riga.get("tipo_eccezione")
            nuovo_prezzo = data["prezzo_unitario"]
            if tipo_existing == "ESCLUSIONE":
                ErrorManager.require(
                    nuovo_prezzo is None,
                    code=E_VENDITE_VALIDATION,
                    message=_MESSAGE_RIGA,
                    detail=(
                        "ESCLUSIONE: prezzo_unitario deve essere NULL "
                        "(l'articolo non e' disponibile per questo contratto). "
                        "Per cambiare tipo, eliminare la riga e crearne una nuova."
                    ),
                    context={"riga_id": riga_id, "tipo_eccezione": tipo_existing},
                )
            elif tipo_existing in ("OVERRIDE", "AGGIUNTA"):
                ErrorManager.require(
                    nuovo_prezzo is not None,
                    code=E_VENDITE_VALIDATION,
                    message=_MESSAGE_RIGA,
                    detail=(
                        f"{tipo_existing}: prezzo_unitario obbligatorio. "
                        f"Per escludere l'articolo, eliminare la riga e "
                        f"crearne una nuova come ESCLUSIONE."
                    ),
                    context={"riga_id": riga_id, "tipo_eccezione": tipo_existing},
                )

        # Gate L1+L2+L3 (refactor 2026-05-19): scatta solo se il PATCH tocca
        # `prezzo_unitario` su una riga OVERRIDE o AGGIUNTA. Per ESCLUSIONE
        # la coerenza prezzo NULL e' gia' garantita dal check sopra; nessun
        # gate ulteriore. Riusiamo `existing_riga` per evitare double-fetch.
        # riga_id noto subito: link inline alla pratica (no post-INSERT).
        if (
            "prezzo_unitario" in data
            and tipo_existing in _TIPI_ECCEZIONE_CON_GATE
        ):
            assert existing_riga is not None
            self._apply_pricing_gate_riga(
                contratto_id=int(existing_riga["contratto_id"]),
                articolo_id=existing_riga.get("articolo_id"),
                uom_id=(
                    data.get("uom_operativa_id")
                    if "uom_operativa_id" in data
                    else existing_riga.get("uom_operativa_id")
                ),
                data=data,
                auth_user_id=auth_user_id,
                richiesta_approvazione=richiesta_approvazione,
                riga_id_for_link=riga_id,
                function_name="contratti_service.update_riga",
                fallback_meta=existing_riga.get("meta"),
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
    # Componenti BoM riga contratto (modello unificato 2026-05-13)
    # =================================================================
    # Specchio simmetrico del pattern preventivi. I componenti vivono in
    # `vendite.contratti_righe_componenti`; l'init e' invocato automaticamente
    # da `create_riga` quando l'articolo e' composito. Helper di
    # normalizzazione overrides + resolve emittente in
    # `_componenti_service_helpers.py` (Fase H BB).

    # Scopo: Helper privato condiviso da update/delete componente. Esegue
    # guard + scope check (riga_id URL + contratto_id) + stato contratto
    # modificabile in UN'unica query JOIN componente→riga→contratto (Fix #2
    # refactor-componenti.md). Solleva `E_VENDITE_NOT_FOUND` su componente
    # inesistente o fuori scope, `E_CONTRATTO_NON_MODIFICABILE` se contratto
    # post-DRAFT.
    def _load_componente_for_modification(
        self,
        *,
        contratto_id: int,
        riga_id: int,
        componente_id: int,
        function_name: str,
    ) -> None:
        scope = self._repo.load_componente_with_scope(componente_id)
        ErrorManager.require(
            scope is not None,
            code=E_VENDITE_NOT_FOUND,
            message="Componente contratto non trovato.",
            detail=f"componente_id={componente_id}",
            function_name=function_name,
        )
        assert scope is not None

        # Anti-tampering URL: riga_id dalla rotta deve matchare riga reale.
        riga_reale = int(scope["riga_contratto_id"])
        ErrorManager.require(
            riga_reale == riga_id,
            code=E_VENDITE_NOT_FOUND,
            message="Componente contratto non trovato.",
            detail=(
                f"componente_id={componente_id} non appartiene a "
                f"riga_id={riga_id} (riga reale={riga_reale})"
            ),
            function_name=function_name,
        )

        # Scope contratto: defense-in-depth contro URL forgiati.
        ErrorManager.require(
            int(scope["contratto_id"]) == contratto_id,
            code=E_VENDITE_NOT_FOUND,
            message="Componente contratto non trovato.",
            detail=(
                f"componente_id={componente_id} fuori scope "
                f"contratto_id={contratto_id}"
            ),
            function_name=function_name,
        )

        # Guard stato modificabile: contratti_righe_componenti seguono la
        # stessa policy delle righe padre (solo DRAFT modificabile). Lo
        # stato e' gia' nella tupla del JOIN — nessun round-trip extra.
        stato = str(scope.get("stato_codice") or "")
        if stato != "DRAFT":
            ErrorManager.raise_error(
                code="E_CONTRATTO_NON_MODIFICABILE",
                message="Operazione non consentita nello stato corrente.",
                detail=(
                    "Modifica componente riga contratto ammessa solo su "
                    f"contratti in stato DRAFT. Stato corrente: {stato}. "
                    "Per modifiche su contratti post-DRAFT creare un nuovo contratto."
                ),
                context={
                    "contratto_id": contratto_id,
                    "stato_codice": stato,
                    "op": "Modifica componente riga contratto",
                },
            )

    # Scopo: Preview componenti BoM per drawer riga contratto (ComponentiDialog
    # FE). Read-only: il FE invoca PRIMA del save di una riga composita per
    # ottenere prezzi suggeriti dei componenti. Per ogni componente:
    # `prezzo_suggerito` + `origine_prezzo`, oppure NULL +
    # `resolver_error_reason` se il listino manca per quel componente.
    # `auth_user_id`: utente loggato. L'emittente_soggetto_ruolo_id viene
    # risolto internamente (precedenza emittente esplicito sulla testata >
    # operatore loggato). Pattern simmetrico preventivi: la view non deve
    # accedere a membri privati del service per risolvere l'emittente.
    # Solleva `E_VENDITE_NOT_FOUND` se contratto inesistente, `E_VENDITE_VALIDATION`
    # se data/utility/emittente non risolvibili.
    def preview_componenti_riga(
        self,
        contratto_id: int,
        *,
        articolo_id: str,
        uom_operativa_id: int | None,
        quantita: Any,
        auth_user_id: int | None = None,
    ) -> list[dict[str, Any]]:
        self._v.guard_positive_int(contratto_id, field="contratto_id")
        ctx = _load_contratto_context_for_pricing(
            contratto_id, auth_user_id,
            function_name="contratti_service.preview_componenti_riga",
            repo=self._repo,
        )

        return self._repo.preview_componenti_riga(
            articolo_id=str(articolo_id),
            uom_id=uom_operativa_id,
            quantita_padre=quantita,
            data_riferimento=ctx["data_riferimento"],
            ba_id=ctx["ba_id"],
            utility_id=ctx["utility_id"],
            emittente_soggetto_ruolo_id=ctx["emittente_sr_id"],
        )

    # Scopo: Lista componenti BoM di una riga padre composita contratto.
    # Guard di esistenza: la riga deve appartenere al contratto richiesto.
    # `solo_attivi=True` (default backcompat): solo componenti attivi.
    # `solo_attivi=False` (EDIT panel): include opzionali disattivati.
    def list_componenti_riga(
        self,
        contratto_id: int, riga_id: int,
        *, solo_attivi: bool = True,
    ) -> list[dict[str, Any]]:
        self._v.guard_positive_int(contratto_id, field="contratto_id")
        self._v.guard_positive_int(riga_id, field="riga_id")
        riga = self._repo.get_riga(riga_id)
        ErrorManager.require(
            riga is not None,
            code=E_VENDITE_NOT_FOUND,
            message="Riga contratto non trovata.",
            detail=f"riga_id={riga_id}",
            function_name="contratti_service.list_componenti_riga",
        )
        assert riga is not None
        ErrorManager.require(
            int(riga.get("contratto_id") or 0) == contratto_id,
            code=E_VENDITE_NOT_FOUND,
            message="Riga contratto non trovata.",
            detail=(
                f"riga_id={riga_id} non appartiene a contratto_id={contratto_id}"
            ),
            function_name="contratti_service.list_componenti_riga",
        )
        return self._repo.list_componenti_riga(riga_id, solo_attivi=solo_attivi)

    # Scopo: Modifica componente riga contratto esistente. Guard stato
    # contratto modificabile + esistenza componente + match URL
    # anti-tampering. Whitelist campi via repo.
    def update_componente_riga(
        self,
        contratto_id: int, riga_id: int, componente_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._v.guard_positive_int(contratto_id, field="contratto_id")
        self._v.guard_positive_int(riga_id, field="riga_id")
        self._v.guard_positive_int(componente_id, field="componente_id")
        self._load_componente_for_modification(
            contratto_id=contratto_id, riga_id=riga_id,
            componente_id=componente_id,
            function_name="contratti_service.update_componente_riga",
        )
        with self._db_errors(
            {"componente_id": componente_id, "riga_id": riga_id},
            fallback_message="Violazione vincolo DB su componente riga contratto.",
        ):
            updated = self._repo.update_componente(componente_id, **payload)
        ErrorManager.require(
            updated,
            code=E_VENDITE_VALIDATION,
            message="Nessun campo aggiornato sul componente.",
            detail="Payload vuoto o senza campi nella whitelist.",
            function_name="contratti_service.update_componente_riga",
        )
        return {"status": "ok", "componente_id": componente_id}

    # Scopo: Soft delete componente riga contratto (`attivo=FALSE`). Guard
    # stato + esistenza + match URL anti-tampering. Il trigger DB di
    # ricalcolo padre esclude i componenti inattivi dalla SUM.
    def delete_componente_riga(
        self,
        contratto_id: int, riga_id: int, componente_id: int,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(contratto_id, field="contratto_id")
        self._v.guard_positive_int(riga_id, field="riga_id")
        self._v.guard_positive_int(componente_id, field="componente_id")
        self._load_componente_for_modification(
            contratto_id=contratto_id, riga_id=riga_id,
            componente_id=componente_id,
            function_name="contratti_service.delete_componente_riga",
        )
        with self._db_errors(
            {"componente_id": componente_id, "riga_id": riga_id},
            fallback_message="Impossibile eliminare il componente (dipendenze).",
        ):
            deleted = self._repo.delete_componente(componente_id)
        return {
            "status": "ok",
            "componente_id": componente_id,
            "deleted": deleted,
        }

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

    # Scopo: Compone il dict di create testata validando campi e coerenza
    #        della coppia variazione globale (tipo+valore entrambi NULL o
    #        entrambi NOT NULL).
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
        self._guard_listino_ha_versione_attiva(data.get("listino_id"))
        self._apply_variazione_globale(payload, data)
        self._validate_variazione_globale_coppia_coerente(data, existing=None)
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

    # Scopo: Compone il dict di update testata. Rivalida coerenza coppia
    #        variazione globale con la foto attuale (listino_id puo' cambiare
    #        liberamente in DRAFT; il trigger attivazione fissa
    #        `listino_versione_id` su transizione DRAFT -> ATTIVO).
    #        `existing` e' la riga corrente dal DB: serve per applicare il
    #        validator alla coppia effettiva quando il patch tocca solo una
    #        dimensione (es. variazione globale senza listino_id nel payload).
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
        # Gate listino selezionabile (decisione 2026-05-18 §4.4): se il PATCH
        # cambia il listino_id (NULL o nuovo id), il listino deve avere almeno
        # una versione ATTIVA. Skip se `listino_id` non e' nel patch (non
        # vogliamo invalidare contratti gia' creati su listini che potrebbero
        # essere stati chiusi in seguito — quello e' lock post-attivazione DB).
        if "listino_id" in data:
            self._guard_listino_ha_versione_attiva(data["listino_id"])
        self._apply_variazione_globale(payload, data)
        # Valida coerenza coppia variazione globale sulla foto post-update merge
        # (delta data + existing). Se il patch tocca listino_id o una delle 2
        # componenti della variazione, rivalida combinando i campi presenti
        # con lo stato corrente.
        if (
            "listino_id" in data
            or "tipo_variazione_globale" in data
            or "valore_variazione_globale" in data
        ):
            self._validate_variazione_globale_coppia_coerente(data, existing=existing)
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

    # Scopo: Estrae e applica la coppia (tipo/valore) variazione globale nel
    #        data dict. Coerenza coppia validata da
    #        `_validate_variazione_globale_coppia_coerente`.
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
                    tipo in _TIPI_VARIAZIONE_GLOBALE_AMMESSI,
                    code=E_VENDITE_VALIDATION,
                    message=_MESSAGE,
                    detail=(
                        f"tipo_variazione_globale deve essere uno tra: "
                        f"{', '.join(sorted(_TIPI_VARIAZIONE_GLOBALE_AMMESSI))}. "
                        "VALORE_FISSO non e' ammesso sulla testata contratto: "
                        "per prezzi fissi su singolo articolo usa una riga "
                        "OVERRIDE."
                    ),
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

    # Scopo: Gate L2 sulla variazione globale del contratto al PATCH testata
    #        (refactor 2026-05-15 §3-bis-E). Wrapper sottile sul BB condiviso
    #        `_pricing_gate_helpers.check_limite_variazione_globale` che
    #        contiene la logica (cascata user→categoria→group→emittente,
    #        superuser bypass, PERCENTUALE-only, raise retryable).
    #        Qui ci limitiamo a estrarre i campi dal merge (data + existing)
    #        prima di delegare.
    def _check_limite_variazione_globale(
        self,
        *,
        existing: dict[str, Any],
        data: dict[str, Any],
        auth_user_id: int | None,
    ) -> None:
        # Skip se il PATCH non tocca la variazione globale.
        if "valore_variazione_globale" not in data:
            return
        tipo_post = data.get("tipo_variazione_globale") if "tipo_variazione_globale" in data else (
            existing.get("tipo_variazione_globale")
        )
        check_limite_variazione_globale(
            auth_user_id=auth_user_id,
            tipo_variazione=tipo_post,
            valore_variazione=data["valore_variazione_globale"],
            function_name="contratti_service._check_limite_variazione_globale",
            ba_id=existing.get("billing_account_id"),
        )

    # Scopo: Gate selezionabilita' listino come riferimento contratto
    #        (decisione 2026-05-18 §4.4 refactor-contratti-modalita).
    #        Un listino senza versione ATTIVA non e' selezionabile: non
    #        avrebbe righe da applicare e il contratto sarebbe formalmente
    #        "con listino" ma operativamente vuoto. Skip se listino_id=None
    #        (forma `senza_listino` legittima).
    def _guard_listino_ha_versione_attiva(self, listino_id: int | None) -> None:
        if listino_id is None:
            return
        ha_versione = ListiniRepository().has_versione_attiva(int(listino_id))
        ErrorManager.require(
            ha_versione,
            code="E_CONTRATTO_LISTINO_SENZA_VERSIONE_ATTIVA",
            message=(
                "Listino non selezionabile: nessuna versione ATTIVA."
            ),
            detail=(
                f"Il listino_id={listino_id} non ha versioni in stato ATTIVA. "
                "Solo listini con una versione pubblicata e attiva possono "
                "essere associati a un contratto."
            ),
            context={"listino_id": listino_id},
        )

    # Scopo: Verifica coerenza della coppia variazione globale (tipo + valore).
    #        Post refactor modalita' (2026-05-15): non c'e' piu' il vincolo
    #        "listino_id NULL -> tipo/valore NULL" — il modello unificato
    #        ammette qualunque combinazione di listino + variazione + eccezioni.
    #        Resta solo il vincolo strutturale: tipo e valore devono essere
    #        coppia (entrambi NULL o entrambi NOT NULL) per dare semantica a
    #        `valore_variazione_globale`.
    def _validate_variazione_globale_coppia_coerente(
        self, data: dict[str, Any], *, existing: dict[str, Any] | None
    ) -> None:
        tipo = data.get("tipo_variazione_globale") if "tipo_variazione_globale" in data else (
            existing.get("tipo_variazione_globale") if existing else None
        )
        valore = data.get("valore_variazione_globale") if "valore_variazione_globale" in data else (
            existing.get("valore_variazione_globale") if existing else None
        )
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

    # Scopo: Compone il dict CRUD per contratti_righe. articolo_id e
    #        tipo_eccezione sono obbligatori in create; mutazione dei campi
    #        commerciali solo sui campi presenti. Il check di coerenza
    #        (ESCLUSIONE -> prezzo NULL, OVERRIDE/AGGIUNTA -> prezzo NOT NULL)
    #        e' enforced dal CHECK DB chk_contrighe_prezzo_per_tipo_eccezione,
    #        pre-validato qui per messaggio parlante.
    def _build_data_riga(self, payload: dict[str, Any], *, for_create: bool) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if for_create:
            data["articolo_id"] = self._v.require_uuid(
                payload, "articolo_id", message=_MESSAGE_RIGA,
            )
            # tipo_eccezione obbligatorio in create (NOT NULL nello schema).
            tipo_eccezione_raw = payload.get("tipo_eccezione")
            ErrorManager.require(
                tipo_eccezione_raw is not None,
                code=E_VENDITE_VALIDATION,
                message=_MESSAGE_RIGA,
                detail=(
                    "tipo_eccezione obbligatorio: uno tra "
                    f"{', '.join(sorted(_TIPI_ECCEZIONE))}."
                ),
                context={"field": "tipo_eccezione"},
            )
            ErrorManager.require(
                isinstance(tipo_eccezione_raw, str),
                code=E_VENDITE_VALIDATION,
                message=_MESSAGE_RIGA,
                detail="tipo_eccezione deve essere una stringa.",
                context={"field": "tipo_eccezione"},
            )
            tipo_eccezione = tipo_eccezione_raw.strip().upper()
            ErrorManager.require(
                tipo_eccezione in _TIPI_ECCEZIONE,
                code=E_VENDITE_VALIDATION,
                message=_MESSAGE_RIGA,
                detail=(
                    f"tipo_eccezione deve essere uno tra: "
                    f"{', '.join(sorted(_TIPI_ECCEZIONE))}."
                ),
                context={"tipo_eccezione": tipo_eccezione},
            )
            data["tipo_eccezione"] = tipo_eccezione

            # Coerenza prezzo_unitario / tipo_eccezione (pre-DB):
            # - ESCLUSIONE -> prezzo NULL (l'articolo non e' disponibile)
            # - OVERRIDE / AGGIUNTA -> prezzo NOT NULL (e' il prezzo finale)
            prezzo_raw = payload.get("prezzo_unitario")
            if tipo_eccezione == "ESCLUSIONE":
                ErrorManager.require(
                    prezzo_raw is None,
                    code=E_VENDITE_VALIDATION,
                    message=_MESSAGE_RIGA,
                    detail=(
                        "ESCLUSIONE: prezzo_unitario deve essere NULL "
                        "(l'articolo non e' disponibile per questo contratto)."
                    ),
                    context={"tipo_eccezione": tipo_eccezione},
                )
            else:
                # OVERRIDE / AGGIUNTA richiedono prezzo_unitario presente.
                ErrorManager.require(
                    prezzo_raw is not None,
                    code=E_VENDITE_VALIDATION,
                    message=_MESSAGE_RIGA,
                    detail=(
                        f"{tipo_eccezione}: prezzo_unitario obbligatorio."
                    ),
                    context={"tipo_eccezione": tipo_eccezione},
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


# ────────────────────────────────────────────────────────────────────────
# Pricing per riga contratto — entry point + gate 3-livelli (BE 2.0)
# ────────────────────────────────────────────────────────────────────────
#
# Simmetrico al pattern preventivi (`suggerisci_prezzo_riga` +
# `_resolve_or_check_override_prezzo`). Le funzioni qui sotto NON sono
# ancora cablate nei flussi `create_riga`/`update_riga` di
# `ContrattiService`: il wiring avviene in BE 2.2 (introduzione delle
# operazioni eccezione OVERRIDE/AGGIUNTA dove il prezzo manuale ha senso).
# Esposte ora come BB testabile in isolamento.


# Scopo: Suggerisce il prezzo unitario per una riga contratto, dato
#        l'articolo, l'UoM e il contesto del contratto (BA, utility, data,
#        emittente). Simmetrica a `preventivi_service.suggerisci_prezzo_riga`.
#
#        Differenze rispetto ai preventivi:
#          - Data di riferimento: `valido_dal` del contratto (non `data`
#            documento). Coerente con `preview_componenti_riga` e con la
#            semantica "il contratto e' una promessa valida per il range
#            valido_dal/valido_al".
#          - Emittente: delegato a `resolve_emittente_sr_id_for_testata`
#            (helper Fase H) che gestisce precedenza emittente esplicito
#            sulla testata vs derivato da auth_user_id.
#
#        Solleva `E_VENDITE_VALIDATION` su input mancanti o non risolubili,
#        `E_VENDITE_NOT_FOUND` su contratto inesistente, e propaga errori
#        ServiceError dal `PricingService.resolve_prezzo` (es.
#        `E_PREZZO_LISTINO_NON_TROVATO`).
# Scopo: Helper module-level. Risolve il contesto di pricing per un
#        contratto: lookup testata + emittente + validazione BA/utility/data,
#        parsing `valido_dal` a `date`. Riusato da
#        `contratti_suggerisci_prezzo_riga` (pricing singola riga) e da
#        `ContrattiService.preview_componenti_riga` (pricing BoM components).
#        Centralizza il pattern condiviso ed evita drift fra i due caller.
#
#        Ritorna dict con: `testata`, `ba_id`, `utility_id`,
#        `emittente_sr_id`, `data_riferimento`.
#
#        Errori:
#          - `E_VENDITE_NOT_FOUND` se contratto inesistente
#          - `E_VENDITE_VALIDATION` se manca BA/utility/valido_dal o
#            emittente non risolvibile
def _load_contratto_context_for_pricing(
    contratto_id: int,
    auth_user_id: int | None,
    *,
    function_name: str,
    repo: ContrattiRepository | None = None,
) -> dict[str, Any]:
    if repo is None:
        repo = ContrattiRepository()
    testata = repo.get_contratto(contratto_id)
    ErrorManager.require(
        testata is not None,
        code=E_VENDITE_NOT_FOUND,
        message="Contratto non trovato.",
        function_name=function_name,
    )
    assert testata is not None

    ba_id_raw = testata.get("billing_account_id")
    ErrorManager.require(
        ba_id_raw is not None,
        code=E_VENDITE_VALIDATION,
        message="Contratto senza billing_account: impossibile risolvere il prezzo.",
        function_name=function_name,
    )
    utility_id_raw = testata.get("utility_id")
    ErrorManager.require(
        utility_id_raw is not None,
        code=E_VENDITE_VALIDATION,
        message="Contratto senza utility: impossibile risolvere il prezzo.",
        function_name=function_name,
    )
    # Data di riferimento: `valido_dal` del contratto. Il resolver bundle-aware
    # cerca prezzi/promo/categoria validi a quella data; coerente col fatto che
    # il contratto e' una promessa contrattuale valida per il range.
    valido_dal_raw = testata.get("valido_dal")
    ErrorManager.require(
        valido_dal_raw is not None,
        code=E_VENDITE_VALIDATION,
        message="Contratto senza valido_dal: impossibile risolvere il prezzo.",
        function_name=function_name,
    )
    assert valido_dal_raw is not None
    data_riferimento = (
        valido_dal_raw if isinstance(valido_dal_raw, date)
        else date.fromisoformat(str(valido_dal_raw))
    )

    # Emittente: precedenza emittente esplicito sulla testata > derivato
    # dall'operatore (modello operatore-emittenti 1-a-1). Helper Fase H.
    emittente_sr_id = resolve_emittente_sr_id_for_testata(
        testata, auth_user_id,
        repo_get_sr_id_by_fiscale_id=repo.get_emittente_sr_id_by_fiscale_id,
    )
    ErrorManager.require(
        emittente_sr_id is not None,
        code=E_VENDITE_VALIDATION,
        message="Impossibile risolvere l'emittente fiscale per il pricing.",
        function_name=function_name,
    )
    assert emittente_sr_id is not None

    return {
        "testata": testata,
        "ba_id": int(ba_id_raw),
        "utility_id": int(utility_id_raw),
        "emittente_sr_id": emittente_sr_id,
        "data_riferimento": data_riferimento,
    }


def contratti_suggerisci_prezzo_riga(
    contratto_id: int,
    *,
    articolo_id: str,
    uom_id: int,
    auth_user_id: int | None,
) -> dict[str, Any]:
    from apps.vendite.services.pricing_service import PricingService

    function_name = "contratti_service.contratti_suggerisci_prezzo_riga"

    ErrorManager.require(
        articolo_id is not None and str(articolo_id).strip() != "",
        code=E_VENDITE_VALIDATION,
        message="articolo_id obbligatorio.",
        function_name=function_name,
    )
    guard_uom_id_positive(
        uom_id, error_code=E_VENDITE_VALIDATION, function_name=function_name,
    )

    ctx = _load_contratto_context_for_pricing(
        contratto_id, auth_user_id, function_name=function_name,
    )

    result = PricingService().resolve_prezzo(
        articolo_id=str(articolo_id),
        uom_id=int(uom_id),
        data_riferimento=ctx["data_riferimento"],
        ba_id=ctx["ba_id"],
        utility_id=ctx["utility_id"],
        emittente_soggetto_ruolo_id=ctx["emittente_sr_id"],
    )

    # Normalizzazione Decimal/date → string per stabilita' JSON (coerente
    # con preventivi_service.suggerisci_prezzo_riga).
    def _normalize(v: Any) -> Any:
        if isinstance(v, Decimal):
            return str(v)
        if isinstance(v, date):
            return v.isoformat()
        return v

    return {k: _normalize(v) for k, v in result.items()}


# Scopo: Orchestratore 3 gate prezzo (L1+L2+L3) per riga contratto.
#        Thin wrapper sul BB `_pricing_gate_helpers.resolve_or_check_override_prezzo`,
#        simmetrico al wrapper omonimo di `preventivi_service`. Cabla
#        direttamente `contratti_suggerisci_prezzo_riga` come resolver_fn
#        (la signature e' gia' quella attesa dal BB) + il codice errore di
#        validazione del dominio (`E_VENDITE_VALIDATION`).
#
#        Normalizzazione testata: il BB usa `testata["data"]` nel guard
#        skip-context (riga ~401 di _pricing_gate_helpers). La testata
#        contratto espone invece `valido_dal`. Aliasiamo qui per
#        incapsulare la differenza nel wrapper di dominio invece di
#        contaminare il BB con conoscenza per-sorgente.
def resolve_or_check_override_prezzo_riga_contratto(
    *,
    testata: dict[str, Any],
    articolo_id: Any,
    uom_id: Any,
    payload_prezzo: Any,
    auth_user_id: int | None,
    function_name: str,
    richiesta_approvazione: bool = False,
) -> tuple[Any, dict[str, Any] | None]:
    testata_normalized = (
        testata if testata.get("data") is not None
        else {**testata, "data": testata.get("valido_dal")}
    )
    return resolve_or_check_override_prezzo(
        testata=testata_normalized,
        articolo_id=articolo_id,
        uom_id=uom_id,
        payload_prezzo=payload_prezzo,
        auth_user_id=auth_user_id,
        function_name=function_name,
        resolver_fn=contratti_suggerisci_prezzo_riga,
        error_code_validazione=E_VENDITE_VALIDATION,
        richiesta_approvazione=richiesta_approvazione,
    )


# Scopo: orchestratore L3 simmetrico a `preventivi_service._orchestrate_l3_request`
#        per le righe contratto (refactor 2026-05-19 BE porting gate riga
#        contratti). Crea la pratica APPROVAZIONE_PREZZO via
#        `approvazioni_prezzo_service.crea_richiesta_approvazione_contratto`,
#        opzionalmente collega riga_id (per update_riga il riga_id e' gia'
#        noto; per create_riga il link avviene post-INSERT). Ritorna pratica_id.
def _orchestrate_l3_request_contratto(
    *,
    contratto_id: int,
    articolo_id: Any,
    prezzo_finale: Any,
    prezzo_meta: dict[str, Any],
    auth_user_id: int | None,
    riga_id_for_link: int | None = None,
) -> int:
    # Import lazy: il service approvazioni importa contratti_service per
    # `ContrattiRepository.update_riga` nel dispatch sorgente-agnostico.
    from apps.vendite.services.approvazioni_prezzo_service import (
        crea_richiesta_approvazione_contratto,
        link_riga_a_pratica,
    )
    pratica_id = crea_richiesta_approvazione_contratto(
        contratto_id=contratto_id,
        riga_id=riga_id_for_link,
        articolo_id=str(articolo_id) if articolo_id is not None else "",
        prezzo_resolver=Decimal(prezzo_meta["prezzo_base_resolver"])
        if prezzo_meta.get("prezzo_base_resolver") else None,
        prezzo_manuale=Decimal(str(prezzo_finale)),
        violazione=prezzo_meta["violazione_l2"],
        auth_user_id=auth_user_id,
    )
    if riga_id_for_link is not None:
        link_riga_a_pratica(
            pratica_id=pratica_id,
            riga_id=riga_id_for_link,
            sorgente=SORGENTE_CONTRATTO,
        )
    return pratica_id
