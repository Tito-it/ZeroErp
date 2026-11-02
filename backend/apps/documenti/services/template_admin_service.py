# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service admin per testata `documenti.template_documenti`
#        (Tranche E). CRUD limitato a create + update — niente DELETE
#        fisica (soft enable/disable via `attivo`).
#        Validazione payload via PayloadValidator (V6-B1), mapping
#        IntegrityError DB -> codici applicativi via map_integrity_error
#        (UNIQUE codice/codice_interno per emittente+sorgente, partial
#        unique `is_default` per output+sorgente+emittente).
#        Scope emittente: l'`emittente_fiscale_id` del payload deve
#        appartenere alla whitelist dell'utente
#        (`PermissionResolver.get_emittenti_pk_ids`); update riusa il check
#        di visibilita' di TemplateService.get_template (404 unificato).
#        Validazione `context_builder_code`: solo formato (stringa non
#        vuota) — il check whitelist registry e' a carico del render
#        service (Tranche H), non della create/update template.
#        «Personalizza» (brief-db-modelli-documento-standard §6, D-2): il
#        modello di un emittente che parte da uno standard, con l'origine
#        dichiarata sulla prima versione. Lo fa il DB, in una funzione madre
#        (`fn_personalizza_template_standard`, §10.3 K-6): qui il payload e il
#        perimetro.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.db import IntegrityError

from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import (
    PayloadValidator,
    map_integrity_error,
    translate_db_errors,
)
from apps.documenti.db.documenti_repository import DocumentiRepository
from apps.documenti.services._scope import guard_emittente_in_scope_for_user
from apps.documenti.services.template_service import TemplateService

# Codici errore registrati in apps.core.services.error_policies.
E_VALIDATION = "E_DOCUMENTI_VALIDATION"
E_NOT_FOUND = "E_DOCUMENTI_NOT_FOUND"

# Chiavi ammesse in payload create. Sorgente, output ed emittente sono
# obbligatorie per identificare il template; le altre sono opzionali
# (default DB) ma il service applica defaults espliciti dove serve.
_CREATE_KEYS: frozenset[str] = frozenset({
    "tipo_documento_output_id",
    "codice",
    "codice_interno",
    "descrizione",
    "sorgente_tipo_id",
    "context_builder_code",
    "file_name_pattern",
    "emittente_fiscale_id",
    "is_default",
    "attivo",
    "meta",
})

# Chiavi ammesse in payload update. Le immutabili (output/sorgente/emittente)
# sono escluse: cambiarle equivale a creare un nuovo template, non
# aggiornarlo. Tentativo di passarle -> E_DOCUMENTI_VALIDATION.
_UPDATE_KEYS: frozenset[str] = frozenset({
    "codice",
    "codice_interno",
    "descrizione",
    "context_builder_code",
    "file_name_pattern",
    "is_default",
    "attivo",
    "meta",
})

# Chiavi ammesse in payload «personalizza»: per chi, se nasce predefinito, e
# i nomi. Tipo, sorgente, builder e nome file sono quelli dello standard: e'
# la sua copia, e li copia il DB.
# ⭐ Codice, codice interno e descrizione si possono dare (default: quelli
#    dello standard) perche' l'unicita' e' per emittente + sorgente + codice:
#    un emittente che ha gia' un suo modello con il codice dello standard, o
#    una copia dello stesso standard, altrimenti non potrebbe personalizzare.
_PERSONALIZZA_KEYS: frozenset[str] = frozenset({
    "emittente_fiscale_id",
    "is_default",
    "codice",
    "codice_interno",
    "descrizione",
})

# Limiti applicativi (DB ha varchar 120/160 ma l'UI rimane piu' contenuta).
_MAX_CODICE_LEN = 120
_MAX_CODICE_INTERNO_LEN = 120
_MAX_DESCRIZIONE_LEN = 500
_MAX_CONTEXT_BUILDER_LEN = 160
_MAX_FILE_NAME_PATTERN_LEN = 200


# Mapping UNIQUE/partial-unique constraint -> codice + messaggio applicativo.
# I nomi dei vincoli devono matchare quelli del DDL Fase A (changeset
# 20260429-53). map_integrity_error fa match case-insensitive su frammento.
_UNIQUE_CONSTRAINTS: dict[str, tuple[str, ...]] = {
    "uq_template_documenti_emittente_sorgente_codice": (
        E_VALIDATION,
        "Esiste gia' un template con questo codice per emittente e sorgente.",
        "codice",
    ),
    "uq_template_documenti_emittente_sorgente_codice_interno": (
        E_VALIDATION,
        "Esiste gia' un template con questo codice interno per emittente e sorgente.",
        "codice_interno",
    ),
    "uq_template_documenti_default_attivo": (
        E_VALIDATION,
        "Esiste gia' un template default attivo per emittente, sorgente e tipo output.",
        "is_default",
    ),
}


# Mapping FK -> codice + messaggio. Il match avviene sul nome del vincolo
# generato da Postgres (es. `template_documenti_tipo_documento_output_id_fkey`).
_FK_CONSTRAINTS: dict[str, tuple[str, ...]] = {
    "tipo_documento_output_id_fkey": (
        E_VALIDATION,
        "tipo_documento_output_id non valido (FK su documenti.tipi_documento_output).",
    ),
    "sorgente_tipo_id_fkey": (
        E_VALIDATION,
        "sorgente_tipo_id non valido (FK su config.sorgenti).",
    ),
    "emittente_fiscale_id_fkey": (
        E_VALIDATION,
        "emittente_fiscale_id non valido (FK su anagrafiche.emittenti_fiscali).",
    ),
}


class TemplateAdminService:
    """Service admin write per testata template documentale."""

    def __init__(
        self,
        repo: DocumentiRepository | None = None,
        reader: TemplateService | None = None,
    ) -> None:
        self._repo = repo or DocumentiRepository()
        # Reader riusato per il check visibilita' / 404 unificato in update
        # e per ritornare il dettaglio post-mutazione.
        self._reader = reader or TemplateService(repo=self._repo)
        self._v = PayloadValidator(validation_code=E_VALIDATION)

    # =================================================================
    # Create
    # =================================================================

    # Scopo: Crea testata template. Valida payload, applica scope emittente
    #        sul `emittente_fiscale_id`, esegue INSERT e mappa eventuali
    #        violazioni unique/FK su codici applicativi parlanti.
    def create_template(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._v.validate_allowed_keys(
            payload,
            allowed=_CREATE_KEYS,
            message="Payload template documento non valido.",
        )
        data = self._build_create_data(payload)
        self._guard_emittente_in_scope(user, data["emittente_fiscale_id"])
        new_id = self._inserisci_testata(data)
        return self._reader.get_template(user, new_id)

    # =================================================================
    # Update
    # =================================================================

    # Scopo: Aggiorna testata template sui soli campi presenti nel payload.
    #        Pre-verifica visibilita' (404 se template fuori scope o
    #        inesistente) prima di toccare il DB. Le colonne immutabili
    #        (output/sorgente/emittente) sollevano E_DOCUMENTI_VALIDATION
    #        prima della validazione delle altre chiavi.
    def update_template(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        template_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._v.guard_positive_int(template_id, field="template_id")
        # 404 unificato se id inesistente o fuori scope (no leak):
        # ri-usa la stessa logica della read.
        self._reader.get_template(user, template_id)

        # Reject immutabili PRIMA del normale flow per messaggio parlante.
        immutabili = {"tipo_documento_output_id", "sorgente_tipo_id", "emittente_fiscale_id"}
        intersect = sorted(set(payload.keys()) & immutabili)
        if intersect:
            ErrorManager.raise_error(
                code=E_VALIDATION,
                message="Campi immutabili presenti in payload update.",
                detail=f"campi non aggiornabili={intersect!r}",
            )

        self._v.validate_allowed_keys(
            payload,
            allowed=_UPDATE_KEYS,
            message="Payload template documento non valido.",
        )
        data = self._build_update_data(payload)

        self._v.require_campi_da_aggiornare(
            data,
            detail=f"allowed_keys={sorted(_UPDATE_KEYS)!r}",
        )

        try:
            updated = self._repo.update_template(template_id, data)
        except IntegrityError as exc:
            map_integrity_error(
                exc,
                unique_constraints=_UNIQUE_CONSTRAINTS,
                fallback_code=E_VALIDATION,
                fallback_message="Violazione vincolo DB su template documento.",
                context={"template_id": template_id},
            )
        # `updated == False` qui significherebbe race con DELETE concorrente
        # tra il get_template iniziale e l'UPDATE: in v1 niente DELETE
        # fisica, quindi caso teoricamente irraggiungibile, ma il check
        # difensivo costa poco.
        ErrorManager.require(
            updated,
            code=E_NOT_FOUND,
            message="Template documento non trovato.",
            detail=f"template_id={template_id}",
        )
        return self._reader.get_template(user, template_id)

    # =================================================================
    # Personalizza (copia dello standard per un emittente)
    # =================================================================

    # Scopo: Crea il modello dell'emittente partendo da uno standard (D-2:
    #        lo standard si cambia solo coi changeSet, chi lo vuole diverso
    #        se ne fa una copia dichiarata). Lo fa la funzione madre del DB
    #        (`repo.personalizza_template_standard`, §10.3 K-6), tutto o
    #        niente: la testata, e la versione 1 in BOZZA copiata dalla
    #        versione con cui lo standard stampa OGGI, con
    #        `derivata_da_versione_id` (Q-5: e' da li' che la vista dello
    #        scarto misura quanto la copia resta indietro).
    #        Qui restano la forma del payload e il PERIMETRO: lo standard si
    #        legge (404 se non e' un modello visibile) e l'emittente deve
    #        essere fra quelli dell'utente.
    #        Ritorna il dettaglio del modello nuovo.
    # ⭐ `is_default` si passa SOLO se l'operatore lo indica (D-6): senza, il
    #    DB la fa nascere predefinita se l'azienda non ne ha gia' una sua per
    #    la coppia, e non predefinita se ce l'ha. Fino al 2026-10-21 il service
    #    la forzava a vero, e chi aveva gia' un predefinito incontrava l'unico.
    #    Finche' la bozza non e' pubblicata la copia non puo' stampare e
    #    l'emittente resta sullo standard (`-26`).
    # ⚠️ Rifiuti del DB, col loro codice: E_DOCUMENTI_PERSONALIZZA_NON_STANDARD
    #    (il modello e' gia' di un'azienda), E_DOCUMENTI_TEMPLATE_NON_STAMPABILE
    #    (lo standard oggi non stampa: spento, o senza versione valida). Le
    #    unicita' (`uq_template_documenti_emittente_sorgente_codice`, il
    #    predefinito chiesto a vero dove ce n'e' gia' uno) coi messaggi
    #    parlanti di `_UNIQUE_CONSTRAINTS`.
    def personalizza_template(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        template_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._v.guard_positive_int(template_id, field="template_id")
        self._v.validate_allowed_keys(
            payload,
            allowed=_PERSONALIZZA_KEYS,
            message="Payload personalizzazione modello non valido.",
        )
        # 404 unificato se inesistente o fuori scope (lo standard e' di tutti).
        self._reader.get_template(user, template_id)
        emittente_fiscale_id = self._v.require_positive_int(payload, "emittente_fiscale_id")
        self._guard_emittente_in_scope(user, emittente_fiscale_id)
        codice = self._v.optional_string(payload, "codice", max_len=_MAX_CODICE_LEN)
        codice_interno = self._v.optional_string(
            payload, "codice_interno", max_len=_MAX_CODICE_INTERNO_LEN,
        )
        descrizione = self._v.optional_string(
            payload, "descrizione", max_len=_MAX_DESCRIZIONE_LEN,
        )
        is_default = self._v.optional_bool(payload, "is_default")

        # Un punto solo per i due canali del DB: le unicita' (IntegrityError,
        # messaggi di `_UNIQUE_CONSTRAINTS`) e i rifiuti della madre (P0001,
        # col codice e l'hint del catalogo).
        with translate_db_errors(
            context={
                "template_id": template_id,
                "emittente_fiscale_id": emittente_fiscale_id,
                "codice": codice,
                "codice_interno": codice_interno,
            },
            unique_constraints=_UNIQUE_CONSTRAINTS,
            fk_constraints=_FK_CONSTRAINTS,
            fallback_code=E_VALIDATION,
            fallback_message="Violazione vincolo DB su template documento.",
        ):
            new_id = self._repo.personalizza_template_standard(
                template_id,
                emittente_fiscale_id=emittente_fiscale_id,
                codice=codice,
                codice_interno=codice_interno,
                descrizione=descrizione,
                is_default=is_default,
            )
        return self._reader.get_template(user, new_id)

    # =================================================================
    # Helpers privati
    # =================================================================

    # Scopo: INSERT della testata con le violazioni unique/FK tradotte nei
    #        codici parlanti. Ritorna l'id nuovo.
    def _inserisci_testata(self, data: dict[str, Any]) -> int:
        try:
            return self._repo.create_template(data)
        except IntegrityError as exc:
            map_integrity_error(
                exc,
                unique_constraints=_UNIQUE_CONSTRAINTS,
                fk_constraints=_FK_CONSTRAINTS,
                fallback_code=E_VALIDATION,
                fallback_message="Violazione vincolo DB su template documento.",
                context={
                    "codice": data.get("codice"),
                    "codice_interno": data.get("codice_interno"),
                    "emittente_fiscale_id": data.get("emittente_fiscale_id"),
                },
            )

    # Scopo: Verifica che `emittente_fiscale_id` sia nello scope dell'utente.
    #        Admin globale (scope=None) passa qualunque id valido (la FK
    #        DB blocca id inesistenti). Operatore: id deve essere nella
    #        whitelist; altrimenti E_DOCUMENTI_VALIDATION (no 403/404 leak).
    #        Helper centralizzato in `apps.documenti.services._scope` per
    #        evitare duplicazioni con admin asset + orchestrator generazione.
    def _guard_emittente_in_scope(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        emittente_fiscale_id: int,
    ) -> None:
        guard_emittente_in_scope_for_user(user, emittente_fiscale_id)

    # Scopo: Compone il dict da passare al repository per create.
    #        Campi obbligatori: tipo_documento_output_id, codice,
    #        codice_interno, descrizione, sorgente_tipo_id,
    #        context_builder_code, emittente_fiscale_id.
    #        Default applicativi: is_default=False, attivo=True.
    def _build_create_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        data: dict[str, Any] = {}
        data["tipo_documento_output_id"] = self._v.require_positive_int(
            payload, "tipo_documento_output_id"
        )
        data["sorgente_tipo_id"] = self._v.require_positive_int(
            payload, "sorgente_tipo_id"
        )
        data["emittente_fiscale_id"] = self._v.require_positive_int(
            payload, "emittente_fiscale_id"
        )
        data["codice"] = self._v.require_string(
            payload, "codice", max_len=_MAX_CODICE_LEN
        )
        data["codice_interno"] = self._v.require_string(
            payload, "codice_interno", max_len=_MAX_CODICE_INTERNO_LEN
        )
        data["descrizione"] = self._v.require_string(
            payload, "descrizione", max_len=_MAX_DESCRIZIONE_LEN
        )
        data["context_builder_code"] = self._v.require_string(
            payload, "context_builder_code", max_len=_MAX_CONTEXT_BUILDER_LEN
        )

        if "file_name_pattern" in payload:
            value = payload["file_name_pattern"]
            data["file_name_pattern"] = (
                None if value is None else self._v.require_string(
                    payload, "file_name_pattern", max_len=_MAX_FILE_NAME_PATTERN_LEN
                )
            )

        is_default = self._v.optional_bool(payload, "is_default")
        data["is_default"] = bool(is_default) if is_default is not None else False

        attivo = self._v.optional_bool(payload, "attivo")
        data["attivo"] = bool(attivo) if attivo is not None else True

        meta = self._v.optional_meta(payload)
        if meta is not None:
            data["meta"] = meta

        return data

    # Scopo: Compone il dict per update ignorando chiavi assenti. Per i
    #        bool/string non si ammette None esplicito in update (i campi
    #        DB sono NOT NULL): valore presente -> validato, key assente -> skip.
    def _build_update_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if "codice" in payload:
            data["codice"] = self._v.require_string(
                payload, "codice", max_len=_MAX_CODICE_LEN
            )
        if "codice_interno" in payload:
            data["codice_interno"] = self._v.require_string(
                payload, "codice_interno", max_len=_MAX_CODICE_INTERNO_LEN
            )
        if "descrizione" in payload:
            data["descrizione"] = self._v.require_string(
                payload, "descrizione", max_len=_MAX_DESCRIZIONE_LEN
            )
        if "context_builder_code" in payload:
            data["context_builder_code"] = self._v.require_string(
                payload, "context_builder_code", max_len=_MAX_CONTEXT_BUILDER_LEN
            )
        if "file_name_pattern" in payload:
            value = payload["file_name_pattern"]
            data["file_name_pattern"] = (
                None if value is None else self._v.require_string(
                    payload, "file_name_pattern", max_len=_MAX_FILE_NAME_PATTERN_LEN
                )
            )
        if "is_default" in payload:
            value = self._v.optional_bool(payload, "is_default")
            ErrorManager.require(
                value is not None,
                code=E_VALIDATION,
                message="Il campo 'is_default' non puo' essere NULL.",
                detail="field=is_default",
            )
            data["is_default"] = bool(value)
        if "attivo" in payload:
            value = self._v.optional_bool(payload, "attivo")
            ErrorManager.require(
                value is not None,
                code=E_VALIDATION,
                message="Il campo 'attivo' non puo' essere NULL.",
                detail="field=attivo",
            )
            data["attivo"] = bool(value)
        if "meta" in payload:
            meta = self._v.optional_meta(payload)
            if meta is not None:
                data["meta"] = meta
        return data
