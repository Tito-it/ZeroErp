# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service admin per `documenti.template_asset` (Tranche G).
#        2 metodi pubblici:
#        - upload_asset: calcola sha256 + size, costruisce storage_key
#          (estensione dal formato letto dal DB), INSERT row con dedup
#          unique (emittente, sha256), scrive su DocumentStorage (atomic).
#          Il formato dichiarato lo giudica il DB alla nascita della riga
#          (`documenti.trgfn_guard_formato_ammesso`,
#          E_DOCUMENTI_FORMATO_NON_AMMESSO): niente whitelist qui.
#          Pattern transazionale: INSERT + write dentro
#          transaction.atomic(); se il commit fallisce il file scritto si
#          cancella (file orfano, solo nel log).
#        - update_asset_metadati: PATCH solo su descrizione, valido_*,
#          attivo, meta. Trigger DB A4 (protect_file) blocca comunque
#          modifiche a storage_key/sha256/file_size/mime/file_name.
#
#        Niente sostituzione file: per cambiare contenuto di un asset
#        si carica un nuovo asset (Decisione 66).
#
#        DELETE: NON esposta. Trigger DB A3 (block_delete) blocca
#        sempre la cancellazione fisica; soft-disable via PATCH attivo=false
#        o `valido_al`.
# ------------------------------------------------------------

from __future__ import annotations

import hashlib
import logging
import os
from typing import Any

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.db import IntegrityError, transaction

from apps.core.db.formati_file import estensione_del_formato
from apps.core.services.error_manager import ErrorManager
from apps.core.services.parameter_service import ParameterService
from apps.core.services.payload_helpers import (
    PayloadValidator,
    map_integrity_error,
)
from apps.documenti.db.documenti_repository import DocumentiRepository
from apps.documenti.services._scope import guard_emittente_in_scope_for_user
from apps.documenti.services.storage import DocumentStorage, get_storage
from apps.documenti.services.template_service import TemplateService

logger = logging.getLogger(__name__)

# Codici errore registrati in apps.core.services.error_policies.
E_VALIDATION = "E_DOCUMENTI_VALIDATION"
E_NOT_FOUND = "E_DOCUMENTI_NOT_FOUND"
E_STORAGE_FAILED = "E_DOCUMENTI_STORAGE_FAILED"

# ⚠️ Le mappe `_MIME_WHITELIST_PER_TIPO` e `_MIME_EXT_FALLBACK` sono uscite il
#    2026-11-16 (BE5 di brief-db-revisione-documenti): i formati di un tipo
#    stanno nel DB (`documenti.tipi_asset_documento_formati` ⨝
#    `config.formati_file`) e il DB rifiuta quello che il tipo non ammette.

# Chiavi ammesse in payload metadati (su upload e su update).
_UPLOAD_METADATI_KEYS: frozenset[str] = frozenset({
    "codice",
    "codice_interno",
    "descrizione",
    "asset_tipo_id",
    "emittente_fiscale_id",
    "valido_dal",
    "valido_al",
    "attivo",
    "meta",
})

_UPDATE_KEYS: frozenset[str] = frozenset({
    "descrizione",
    "valido_dal",
    "valido_al",
    "attivo",
    "meta",
})

# Limiti applicativi.
_MAX_CODICE_LEN = 120
_MAX_CODICE_INTERNO_LEN = 120
_MAX_DESCRIZIONE_LEN = 500
_MAX_FILE_NAME_LEN = 255

# Mapping vincoli DB -> codici applicativi parlanti.
_UNIQUE_CONSTRAINTS: dict[str, tuple[str, ...]] = {
    "uq_template_asset_emittente_codice": (
        E_VALIDATION,
        "Esiste gia' un asset con questo codice per l'emittente.",
        "codice",
    ),
    "uq_template_asset_emittente_codice_interno": (
        E_VALIDATION,
        "Esiste gia' un asset con questo codice interno per l'emittente.",
        "codice_interno",
    ),
    "uq_template_asset_emittente_sha256": (
        E_VALIDATION,
        "Esiste gia' un asset con lo stesso contenuto (sha256) per l'emittente. Riusa quello esistente.",
    ),
}

_FK_CONSTRAINTS: dict[str, tuple[str, ...]] = {
    "asset_tipo_id_fkey": (
        E_VALIDATION,
        "asset_tipo_id non valido (FK su documenti.tipi_asset_documento).",
    ),
    "emittente_fiscale_id_fkey": (
        E_VALIDATION,
        "emittente_fiscale_id non valido (FK su anagrafiche.emittenti_fiscali).",
    ),
}


class TemplateAssetAdminService:
    """Service admin write per asset documentali (upload + update metadati)."""

    def __init__(
        self,
        repo: DocumentiRepository | None = None,
        reader: TemplateService | None = None,
        storage: DocumentStorage | None = None,
        params: ParameterService | None = None,
    ) -> None:
        self._repo = repo or DocumentiRepository()
        self._reader = reader or TemplateService(repo=self._repo)
        # Storage e parameters resolved lazily se non iniettati: cosi' i test
        # possono mockarli senza toccare DB/filesystem reali.
        self._storage_factory = (lambda: storage) if storage else get_storage
        self._params = params or ParameterService()
        self._v = PayloadValidator(validation_code=E_VALIDATION)

    # =================================================================
    # Upload asset (multipart)
    # =================================================================

    # Scopo: Crea un nuovo asset caricando il file binario.
    #        Sequenza:
    #         1. validate payload + scope emittente
    #         2. legge il tipo asset coi formati che ammette (404-like se
    #            l'id non esiste)
    #         3. valida size <= documenti_asset_upload_max_mb
    #         4. calcola sha256 + costruisce storage_key
    #         5. INSERT row dentro transaction.atomic() — dedup naturale via
    #            unique (emittente, sha256)
    #         6. write file su storage (atomic write filesystem)
    #         7. commit (uscita dal with): in caso di errore commit, il
    #            file scritto si cancella (file orfano, solo nel log)
    def upload_asset(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        metadati: dict[str, Any],
        file_bytes: bytes,
        client_mime_type: str,
        client_file_name: str,
    ) -> dict[str, Any]:
        # 1) validate payload (campi obbligatori) + scope.
        self._v.validate_allowed_keys(
            metadati,
            allowed=_UPLOAD_METADATI_KEYS,
            message="Metadati asset non validi.",
        )
        data = self._build_upload_metadati(metadati)
        self._guard_emittente_in_scope(user, data["emittente_fiscale_id"])

        # 2) il tipo asset coi suoi formati. Il formato dichiarato lo giudica
        #    il DB all'INSERT (E_DOCUMENTI_FORMATO_NON_AMMESSO): un MIME che
        #    il tipo non ammette non arriva mai a scrivere il file.
        formati = self._formati_del_tipo_asset(data["asset_tipo_id"])
        normalized_mime = (client_mime_type or "").strip().lower()

        # 3) size check (params: documenti_asset_upload_max_mb, default 25).
        size = len(file_bytes)
        if size <= 0:
            ErrorManager.raise_error(
                code=E_VALIDATION,
                message="File asset vuoto.",
            )
        max_mb = self._params.get_parameter_int("documenti_asset_upload_max_mb")
        max_bytes = max_mb * 1024 * 1024
        if size > max_bytes:
            ErrorManager.raise_error(
                code=E_VALIDATION,
                message=f"File asset troppo grande. Limite: {max_mb} MB.",
                detail=f"size_bytes={size} max_bytes={max_bytes}",
            )

        # 4) sha256 + storage_key stabile.
        sha = hashlib.sha256(file_bytes).hexdigest()
        ext = self._resolve_extension(client_file_name, normalized_mime, formati)
        storage_key = f"assets/{data['emittente_fiscale_id']}/{sha}.{ext}"
        sanitized_file_name = self._sanitize_file_name(client_file_name)

        data["mime_type"] = normalized_mime
        data["file_name"] = sanitized_file_name
        data["file_size_bytes"] = size
        data["sha256"] = sha
        data["storage_key"] = storage_key

        # 5+6) INSERT + write storage in transazione atomica.
        storage = self._storage_factory()
        storage_uri: str | None = None
        need_cleanup = False
        try:
            with transaction.atomic():
                try:
                    new_id = self._repo.create_asset(data)
                except IntegrityError as exc:
                    # Dedup naturale (sha256) o vincolo unique codice/codice_interno.
                    map_integrity_error(
                        exc,
                        unique_constraints=_UNIQUE_CONSTRAINTS,
                        fk_constraints=_FK_CONSTRAINTS,
                        fallback_code=E_VALIDATION,
                        fallback_message="Violazione vincolo DB su asset documento.",
                        context={
                            "codice": data.get("codice"),
                            "codice_interno": data.get("codice_interno"),
                            "sha256": sha,
                        },
                    )
                # write storage solo dopo INSERT OK: se write fallisce,
                # transaction.atomic fa rollback del row -> niente stato
                # incoerente.
                storage_uri = storage.write(
                    storage_key, file_bytes, content_type=normalized_mime
                )
                # Da questo punto in poi: l'uscita dal `with` fa il commit;
                # se il commit dovesse fallire silenziosamente, il file e'
                # gia' su disk -> cleanup nel finally.
                need_cleanup = True
            need_cleanup = False  # commit OK, niente cleanup
        finally:
            if need_cleanup and storage_uri:
                # File orfano: scritto, ma il commit DB e' fallito.
                # Best-effort: log + delete. Non solleviamo per non mascherare
                # l'eccezione originale del commit.
                try:
                    storage.delete(storage_uri)
                    logger.warning(
                        "documenti.asset.storage_orphan_cleanup_ok "
                        "storage_uri=%s sha256=%s",
                        storage_uri, sha,
                    )
                except Exception:
                    logger.exception(
                        "documenti.asset.storage_orphan_cleanup_failed "
                        "storage_uri=%s sha256=%s",
                        storage_uri, sha,
                    )

        return self._reader.get_asset(user, new_id)

    # =================================================================
    # Update metadati (no sostituzione file)
    # =================================================================

    # Scopo: PATCH metadati asset. Il trigger DB A4 (protect_file) e' la
    #        difesa finale contro UPDATE su storage_key/sha256/file_size/
    #        mime/file_name; ASSET_UPDATE_COLUMNS le esclude per design,
    #        e _UPDATE_KEYS rifiuta esplicitamente quelle chiavi nel
    #        payload con messaggio parlante.
    def update_asset_metadati(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        asset_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._v.guard_positive_int(asset_id, field="asset_id")
        # 404 unificato (no leak fuori scope).
        self._reader.get_asset(user, asset_id)

        # Reject immutabili PRIMA del normale flow per messaggio parlante.
        immutabili_file = {
            "storage_key", "sha256", "file_size_bytes", "mime_type", "file_name",
        }
        immutabili_anag = {"codice", "codice_interno", "asset_tipo_id", "emittente_fiscale_id"}
        intersect = sorted(set(payload.keys()) & (immutabili_file | immutabili_anag))
        if intersect:
            ErrorManager.raise_error(
                code=E_VALIDATION,
                message="Campi non aggiornabili presenti nel payload.",
                detail=f"campi_immutabili={intersect!r}",
            )

        self._v.validate_allowed_keys(
            payload,
            allowed=_UPDATE_KEYS,
            message="Payload asset non valido.",
        )
        data = self._build_update_data(payload)
        self._v.require_campi_da_aggiornare(
            data,
            detail=f"allowed_keys={sorted(_UPDATE_KEYS)!r}",
        )

        try:
            updated = self._repo.update_asset_metadati(asset_id, data)
        except IntegrityError as exc:
            map_integrity_error(
                exc,
                unique_constraints=_UNIQUE_CONSTRAINTS,
                fallback_code=E_VALIDATION,
                fallback_message="Violazione vincolo DB su asset documento.",
                context={"asset_id": asset_id},
            )
        ErrorManager.require(
            updated,
            code=E_NOT_FOUND,
            message="Asset documentale non trovato.",
            detail=f"asset_id={asset_id}",
        )
        return self._reader.get_asset(user, asset_id)

    # =================================================================
    # Helpers privati
    # =================================================================

    # Scopo: I formati che il tipo asset ammette, letti dal DB (BB
    #        `sql_formati_ammessi` dentro `get_tipo_asset`). Un id che non
    #        esiste e' un dato errato, detto prima dell'INSERT.
    #        ⚠️ Niente controllo «tipo non attivo» dal 2026-11-16 (BE11): il
    #        vocabolario non ha `attivo`, un tipo c'e' o non c'e'.
    def _formati_del_tipo_asset(self, asset_tipo_id: int) -> list[dict[str, Any]]:
        row = self._repo.get_tipo_asset(asset_tipo_id)
        if row is None:
            ErrorManager.raise_error(
                code=E_VALIDATION,
                message="asset_tipo_id non valido.",
                detail=f"asset_tipo_id={asset_tipo_id}",
            )
        assert row is not None
        return list(row.get("formati") or [])

    # Scopo: Verifica che `emittente_fiscale_id` sia nello scope dell'utente.
    #        Helper centralizzato in `apps.documenti.services._scope` per
    #        evitare duplicazioni con admin testata + orchestrator generazione.
    def _guard_emittente_in_scope(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        emittente_fiscale_id: int,
    ) -> None:
        guard_emittente_in_scope_for_user(user, emittente_fiscale_id)

    # Scopo: Estrae estensione lower-case da file_name; ripiego
    #        sull'estensione del formato (dal DB), poi `bin`.
    def _resolve_extension(
        self, file_name: str, mime: str, formati: list[dict[str, Any]],
    ) -> str:
        _, ext = os.path.splitext(file_name or "")
        ext = ext.lstrip(".").lower().strip()
        if ext and ext.isalnum() and len(ext) <= 10:
            return ext
        return estensione_del_formato(formati, mime) or "bin"

    # Scopo: Sanitizza il file_name fornito dal client. Trim + rimuove path
    #        separator per evitare iniezione nello storage_key (anche se
    #        non lo usiamo come path, il file_name resta in DB).
    def _sanitize_file_name(self, file_name: str) -> str:
        if not file_name:
            ErrorManager.raise_error(
                code=E_VALIDATION,
                message="file_name vuoto.",
            )
        # Solo basename (no path traversal).
        safe = os.path.basename(file_name).strip()
        if not safe:
            ErrorManager.raise_error(
                code=E_VALIDATION,
                message="file_name non valido.",
                detail=f"file_name={file_name!r}",
            )
        if len(safe) > _MAX_FILE_NAME_LEN:
            safe = safe[:_MAX_FILE_NAME_LEN]
        return safe

    # Scopo: Compone il dict da passare al repository per create.
    #        Campi obbligatori: codice, codice_interno, descrizione,
    #        asset_tipo_id, emittente_fiscale_id. valido_dal default DB
    #        (`fn_data_operativa()`, l'oggi dell'azienda).
    def _build_upload_metadati(self, payload: dict[str, Any]) -> dict[str, Any]:
        data: dict[str, Any] = {}
        data["codice"] = self._v.require_string(
            payload, "codice", max_len=_MAX_CODICE_LEN
        )
        data["codice_interno"] = self._v.require_string(
            payload, "codice_interno", max_len=_MAX_CODICE_INTERNO_LEN
        )
        data["descrizione"] = self._v.require_string(
            payload, "descrizione", max_len=_MAX_DESCRIZIONE_LEN
        )
        data["asset_tipo_id"] = self._v.require_positive_int(
            payload, "asset_tipo_id"
        )
        data["emittente_fiscale_id"] = self._v.require_positive_int(
            payload, "emittente_fiscale_id"
        )
        if "valido_dal" in payload:
            data["valido_dal"] = self._v.optional_date(payload, "valido_dal")
        if "valido_al" in payload:
            data["valido_al"] = self._v.optional_date(payload, "valido_al")
        # L'ordine delle date lo giudica il DB: guard comune
        # `script.trgfn_guard_date_validita`, E_DATA_AL_MINORE_DAL col campo
        # `valido_al` (dal 2026-09-23).
        if "attivo" in payload:
            v = self._v.optional_bool(payload, "attivo")
            data["attivo"] = bool(v) if v is not None else True
        if "meta" in payload:
            m = self._v.optional_meta(payload)
            if m is not None:
                data["meta"] = m
        return data

    # Scopo: Compone il dict per update metadati ignorando chiavi assenti.
    def _build_update_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if "descrizione" in payload:
            data["descrizione"] = self._v.require_string(
                payload, "descrizione", max_len=_MAX_DESCRIZIONE_LEN
            )
        if "valido_dal" in payload:
            data["valido_dal"] = self._v.optional_date(payload, "valido_dal")
        if "valido_al" in payload:
            data["valido_al"] = self._v.optional_date(payload, "valido_al")
        # L'ordine delle date lo giudica il DB: guard comune
        # `script.trgfn_guard_date_validita`, E_DATA_AL_MINORE_DAL col campo
        # `valido_al` (dal 2026-09-23).
        if "attivo" in payload:
            v = self._v.optional_bool(payload, "attivo")
            ErrorManager.require(
                v is not None,
                code=E_VALIDATION,
                message="Il campo 'attivo' non puo' essere NULL.",
                detail="field=attivo",
            )
            data["attivo"] = bool(v)
        if "meta" in payload:
            m = self._v.optional_meta(payload)
            if m is not None:
                data["meta"] = m
        return data

