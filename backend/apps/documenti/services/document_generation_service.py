# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Orchestratore della generazione persistita di un documento
#        (Tranche I). Pipeline:
#         1. valida user + scope emittente (PermissionResolver);
#         2. risolve template applicabile (override esplicito via id, oppure
#            `is_default=true` per (sorgente_tipo, emittente, output));
#         3. carica versione PUBBLICATA attiva (`validita @> CURRENT_DATE`);
#         4. risolve context_builder via registry (whitelist Decisione 18+74);
#         5. richiede al builder il context (responsabilita' del dominio
#            sorgente: sicurezza, scope, lookup);
#         6. invoca render_service.render_pdf -> bytes (engine WEASYPRINT v1);
#         7. calcola hashes audit (context/template/pdf), nome_file dal
#            pattern del template e progressivo per (sorgente_tipo+uid+riga);
#         8. transazione atomica: INSERT documento_generato +
#            documento_generato_file + evento `GENERATO` + storage.write
#            dentro lo stesso `with`;
#         9. cleanup STORAGE_ORPHAN best-effort se il commit fallisce
#            post-write (file scritto, record DB rolled back).
#
#        Decisioni di design rilevate:
#         - render PRIMA del DB (Decisione 32: render fail = niente record,
#           niente evento orfano da loggare);
#         - INSERT eventi senza `tx_id` esplicito (Decisione 76);
#         - storage_key derivata da pdf_hash (dedup naturale a parita' di
#           contenuto, idempotente per re-render dello stesso input);
#         - hashes via JSON canonical (sort_keys=True, default=str) +
#           UTF-8 bytes;
#         - tipo_file via lookup codice (`PDF_FINALE`, no hardcoded ID).
# ------------------------------------------------------------

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import logging
import os
from typing import Any

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import PayloadValidator, map_integrity_error
from apps.documenti.db.documenti_repository import DocumentiRepository
from apps.documenti.services._scope import (
    guard_emittente_in_scope,
    guard_user_authenticated,
    resolve_emittente_scope,
)
from apps.documenti.services.context_builders.registry import get_builder
from apps.documenti.services.render_service import render_pdf
from apps.documenti.services.storage import DocumentStorage, get_storage
from apps.documenti.services.template_service import TemplateService

logger = logging.getLogger(__name__)

# Codici errore. Tutti gia' registrati in
# `apps.core.services.error_policies` (Tranche B + F + G).
E_VALIDATION = "E_DOCUMENTI_VALIDATION"
E_NOT_FOUND = "E_DOCUMENTI_NOT_FOUND"
E_RENDER_FAILED = "E_DOCUMENTI_RENDER_FAILED"
E_STORAGE_FAILED = "E_DOCUMENTI_STORAGE_FAILED"

# Codice del tipo file usato in v1 (seed `tipi_file_documento` Fase A).
# Memoria feedback_no_hardcoded_ids: lookup per codice, non ID numerici.
_CODICE_TIPO_FILE_PDF_FINALE = "PDF_FINALE"

# MIME canonical del file principale generato in v1.
_MIME_PDF = "application/pdf"

# Ordinamento e flag is_principale per il file principale (unico in v1).
_ORDINAMENTO_PRINCIPALE = 1
_IS_PRINCIPALE_DEFAULT = True

# Fallback ext quando il pattern file_name non termina in .pdf esplicito.
_EXT_PDF = "pdf"

# Mapping vincoli DB testata documento_generati -> codici applicativi.
# Solo i piu' probabili in scrittura runtime: i CHECK (hash_len, stato,
# titolo_non_vuoto) sono violazioni di programmazione, non di input.
_DOCUMENTO_UNIQUE_CONSTRAINTS: dict[str, tuple[str, str]] = {
    "uq_documenti_generati_sorgente_progressivo": (
        E_VALIDATION,
        "Race su progressivo sorgente: riprovare la generazione.",
    ),
}


class DocumentGenerationService:
    """Orchestratore generazione persistita di un documento."""

    # Scopo: Costruzione con dipendenze iniettabili. Storage e parameters
    #        sono lazy: i test mockano repo + storage senza toccare il
    #        filesystem, e il render_pdf e' patchabile dal modulo.
    def __init__(
        self,
        repo: DocumentiRepository | None = None,
        reader: TemplateService | None = None,
        storage: DocumentStorage | None = None,
    ) -> None:
        self._repo = repo or DocumentiRepository()
        self._reader = reader or TemplateService(repo=self._repo)
        self._storage_factory = (lambda: storage) if storage else get_storage
        self._v = PayloadValidator(validation_code=E_VALIDATION)

    # =================================================================
    # Comando pubblico: genera documento persistito
    # =================================================================

    # Scopo: Genera e persiste un documento PDF a partire da una sorgente.
    #        Il caller fornisce gli identificativi della sorgente
    #        (`sorgente_tipo_id`, `sorgente_uid`, opzionale `sorgente_riga`)
    #        e l'`emittente_fiscale_id`. Il template si risolve per
    #        default (`is_default=true`) oppure tramite override esplicito
    #        `template_documento_id`. Ritorna un dict con id+uid+nome_file
    #        del documento generato + storage_uri del file persistito.
    def genera_documento(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        *,
        emittente_fiscale_id: int,
        sorgente_tipo_id: int,
        sorgente_id: int,
        sorgente_uid: str,
        sorgente_riga: int | None = None,
        tipo_documento_output_id: int | None = None,
        template_documento_id: int | None = None,
        locale: str = "it-IT",
    ) -> dict[str, Any]:
        # 0) guard input scalari (errore parlante PRIMA dei round-trip DB).
        self._v.guard_positive_int(emittente_fiscale_id, field="emittente_fiscale_id")
        self._v.guard_positive_int(sorgente_tipo_id, field="sorgente_tipo_id")
        self._v.guard_positive_int(sorgente_id, field="sorgente_id")
        self._v.guard_non_empty_string(sorgente_uid, field="sorgente_uid")
        if sorgente_riga is not None:
            self._v.guard_positive_int(sorgente_riga, field="sorgente_riga")

        # 1) auth + cache scope (un solo round-trip per l'intera invocazione,
        #    riusato in `_resolve_template`). Helper di dominio condivisi
        #    con admin testata/asset (`apps.documenti.services._scope`).
        guard_user_authenticated(user)
        assert user is not None
        scope = resolve_emittente_scope(user)
        guard_emittente_in_scope(scope, emittente_fiscale_id)

        # 2) risolve template applicabile (override esplicito o default)
        template = self._resolve_template(
            user,
            scope=scope,
            emittente_fiscale_id=emittente_fiscale_id,
            sorgente_tipo_id=sorgente_tipo_id,
            tipo_documento_output_id=tipo_documento_output_id,
            template_documento_id=template_documento_id,
        )
        # Defense-in-depth: anche se il template e' fuori scope il
        # _resolve_template ha gia' applicato lo scope; questo controllo
        # blocca eventuali incongruenze di input (es. caller passa
        # emittente=11 ma template_documento_id punta a un template di
        # emittente=22 dentro lo scope dell'admin).
        if template["emittente_fiscale_id"] != emittente_fiscale_id:
            ErrorManager.raise_error(
                code=E_VALIDATION,
                message="Template non coerente con l'emittente richiesto.",
                detail=(
                    f"emittente_richiesto={emittente_fiscale_id} "
                    f"emittente_template={template['emittente_fiscale_id']}"
                ),
            )
            raise  # unreachable
        if template["sorgente_tipo_id"] != sorgente_tipo_id:
            ErrorManager.raise_error(
                code=E_VALIDATION,
                message="Template non coerente con il tipo sorgente richiesto.",
                detail=(
                    f"sorgente_tipo_richiesto={sorgente_tipo_id} "
                    f"sorgente_tipo_template={template['sorgente_tipo_id']}"
                ),
            )
            raise  # unreachable

        # 3) carica versione PUBBLICATA attiva
        versione = self._resolve_versione_pubblicata(template["id"])

        # 4+5) risolve builder + costruisce context
        context = self._build_context_for_sorgente(
            user, template, sorgente_id, locale=locale,
        )

        # 6) render PDF (fuori transazione: render fail = niente record DB)
        pdf_bytes = render_pdf(template_versione=versione, context=context)
        if not pdf_bytes:
            ErrorManager.raise_error(
                code=E_RENDER_FAILED,
                message="Render ha restituito output PDF vuoto.",
            )
            raise  # unreachable

        # 7) compute hashes + nome_file + progressivo + storage_key.
        #    Il context viene normalizzato JSON-safe una sola volta:
        #    - serve sia per il context_hash deterministico (hash su rappresentazione
        #      canonica) sia per `documenti_generati.context_json` (jsonb DDL),
        #      che psycopg serializza a json.dumps -> TypeError su Decimal/date
        #      se passassimo il context raw del builder.
        context_canonical = self._json_canonical(context)
        context_json_safe = json.loads(context_canonical)
        context_hash = self._sha256_text(context_canonical)
        template_hash = self._compute_template_hash(versione)
        pdf_hash = self._sha256_bytes(pdf_bytes)
        nome_file = self._format_nome_file(template, context)
        titolo = self._build_titolo(template)
        ext = self._resolve_extension(nome_file)
        storage_key = f"documenti/{emittente_fiscale_id}/{pdf_hash}.{ext}"

        # 8) lookup tipo_file PDF_FINALE (no ID hardcoded)
        tipo_file = self._repo.get_tipo_file_documento_by_codice(
            _CODICE_TIPO_FILE_PDF_FINALE
        )
        ErrorManager.require(
            tipo_file is not None and tipo_file.get("attivo"),
            code=E_VALIDATION,
            message="Tipo file 'PDF_FINALE' non configurato o non attivo.",
        )
        assert tipo_file is not None
        tipo_file_id = tipo_file["id"]

        # 9) sequenza atomica: INSERT 3 record + storage.write
        progressivo = self._repo.next_progressivo_sorgente(
            sorgente_tipo_id=sorgente_tipo_id,
            sorgente_uid=sorgente_uid,
            sorgente_riga=sorgente_riga,
        )

        documento_data: dict[str, Any] = {
            "tipo_documento_output_id": template["tipo_documento_output_id"],
            "template_documento_id": template["id"],
            "template_versione_id": versione["id"],
            "sorgente_tipo_id": sorgente_tipo_id,
            "sorgente_uid": sorgente_uid,
            "sorgente_riga": sorgente_riga,
            "progressivo_sorgente": progressivo,
            "stato": "GENERATO",
            "titolo": titolo,
            "nome_file": nome_file,
            "context_json": context_json_safe,
            "context_hash": context_hash,
            "template_hash": template_hash,
            "pdf_hash": pdf_hash,
            "generato_da_user_id": getattr(user, "id", None),
            "emittente_fiscale_id": emittente_fiscale_id,
            "meta": {},
        }
        file_data: dict[str, Any] = {
            "file_tipo_id": tipo_file_id,
            "mime_type": _MIME_PDF,
            "file_name": nome_file,
            "file_size_bytes": len(pdf_bytes),
            "storage_key": storage_key,
            "sha256": pdf_hash,
            "ordinamento": _ORDINAMENTO_PRINCIPALE,
            "is_principale": _IS_PRINCIPALE_DEFAULT,
            "meta": {},
        }
        evento_data_template: dict[str, Any] = {
            "evento_tipo": "GENERATO",
            "user_id": getattr(user, "id", None),
            "esito": "OK",
            "messaggio": None,
            "detail": {
                "size_bytes": len(pdf_bytes),
                "pdf_hash": pdf_hash,
            },
            "meta": {},
        }

        storage = self._storage_factory()
        storage_uri: str | None = None
        need_cleanup = False
        try:
            with transaction.atomic():
                try:
                    documento_id, documento_uid = self._repo.create_documento_generato(
                        documento_data,
                    )
                except IntegrityError as exc:
                    map_integrity_error(
                        exc,
                        unique_constraints=_DOCUMENTO_UNIQUE_CONSTRAINTS,
                        fallback_code=E_VALIDATION,
                        fallback_message="Violazione vincolo DB su documento generato.",
                        context={
                            "sorgente_tipo_id": sorgente_tipo_id,
                            "sorgente_uid": sorgente_uid,
                            "progressivo": progressivo,
                        },
                    )
                file_data["documento_generato_id"] = documento_id
                self._repo.create_documento_generato_file(file_data)

                evento_data = {
                    **evento_data_template,
                    "documento_generato_id": documento_id,
                }
                self._repo.emit_evento_documento(evento_data)

                # write storage solo dopo INSERT OK: se write fallisce,
                # transaction.atomic fa rollback dei 3 record DB ->
                # nessun stato incoerente.
                storage_uri = storage.write(
                    storage_key, pdf_bytes, content_type=_MIME_PDF,
                )
                # Da questo punto in poi: l'uscita dal `with` fa il commit;
                # se il commit fallisce, il file e' gia' su disk -> cleanup
                # nel finally. Il record DB risulta rolled back, l'evento
                # STORAGE_ORPHAN non e' linkabile (FK NOT NULL su
                # documento_generato_id) -> log warning + cleanup file.
                need_cleanup = True
            need_cleanup = False  # commit OK
        finally:
            if need_cleanup and storage_uri:
                try:
                    storage.delete(storage_uri)
                    logger.warning(
                        "documenti.documento.storage_orphan_cleanup_ok "
                        "storage_uri=%s pdf_hash=%s",
                        storage_uri, pdf_hash,
                    )
                except Exception:
                    logger.exception(
                        "documenti.documento.storage_orphan_cleanup_failed "
                        "storage_uri=%s pdf_hash=%s",
                        storage_uri, pdf_hash,
                    )

        # `generato_at` non viene incluso nel return: il valore autoritativo
        # e' lato DB (default `now()`); il caller fa lookup se gli serve.
        return {
            "id": documento_id,
            "uid": documento_uid,
            "nome_file": nome_file,
            "titolo": titolo,
            "pdf_hash": pdf_hash,
            "storage_uri": storage_uri,
            "size_bytes": len(pdf_bytes),
            "progressivo_sorgente": progressivo,
            "template_documento_id": template["id"],
            "template_versione_id": versione["id"],
        }

    # =================================================================
    # Comandi pubblici aggiuntivi (Tranche K)
    # =================================================================

    # Scopo: Anteprima PDF a richiesta (Decisione 30): renderizza il
    #        documento ma NON lo persiste (no INSERT, no storage.write,
    #        no evento). Ritorna i bytes per streaming response. Il
    #        caller decide il `Content-Disposition` (inline vs attachment)
    #        e, in genere, NON chiama dopo `genera_documento` perche' la
    #        timeline non logga `ANTEPRIMA` (set chiuso v1).
    def anteprima_documento(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        *,
        emittente_fiscale_id: int,
        sorgente_tipo_id: int,
        sorgente_id: int,
        tipo_documento_output_id: int | None = None,
        template_documento_id: int | None = None,
        locale: str = "it-IT",
    ) -> dict[str, Any]:
        # Stessa pipeline di `genera_documento` step 0..6 senza persist.
        self._v.guard_positive_int(emittente_fiscale_id, field="emittente_fiscale_id")
        self._v.guard_positive_int(sorgente_tipo_id, field="sorgente_tipo_id")
        self._v.guard_positive_int(sorgente_id, field="sorgente_id")
        guard_user_authenticated(user)
        assert user is not None
        scope = resolve_emittente_scope(user)
        guard_emittente_in_scope(scope, emittente_fiscale_id)

        template = self._resolve_template(
            user,
            scope=scope,
            emittente_fiscale_id=emittente_fiscale_id,
            sorgente_tipo_id=sorgente_tipo_id,
            tipo_documento_output_id=tipo_documento_output_id,
            template_documento_id=template_documento_id,
        )
        if template["emittente_fiscale_id"] != emittente_fiscale_id:
            ErrorManager.raise_error(
                code=E_VALIDATION,
                message="Template non coerente con l'emittente richiesto.",
            )
            raise  # unreachable
        if template["sorgente_tipo_id"] != sorgente_tipo_id:
            ErrorManager.raise_error(
                code=E_VALIDATION,
                message="Template non coerente con il tipo sorgente richiesto.",
            )
            raise  # unreachable

        versione = self._resolve_versione_pubblicata(template["id"])
        context = self._build_context_for_sorgente(
            user, template, sorgente_id, locale=locale,
        )
        pdf_bytes = render_pdf(template_versione=versione, context=context)
        if not pdf_bytes:
            ErrorManager.raise_error(
                code=E_RENDER_FAILED,
                message="Render anteprima ha restituito output PDF vuoto.",
            )
            raise  # unreachable

        nome_file = self._format_nome_file(template, context)
        return {
            "pdf_bytes": pdf_bytes,
            "nome_file": nome_file,
            "size_bytes": len(pdf_bytes),
            "mime_type": _MIME_PDF,
        }

    # Scopo: Lista paginata documenti generati per una sorgente (es. tutti
    #        i PDF generati a partire da un dato preventivo). Building
    #        block riusabile da qualsiasi dominio sorgente: il caller
    #        applica i propri permessi a livello view + scope emittente
    #        applicato qui via `PermissionResolver`.
    def list_documenti_per_sorgente(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        *,
        sorgente_tipo_id: int,
        sorgente_uid: str,
        sorgente_riga: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(sorgente_tipo_id, field="sorgente_tipo_id")
        self._v.guard_non_empty_string(sorgente_uid, field="sorgente_uid")
        if sorgente_riga is not None:
            self._v.guard_positive_int(sorgente_riga, field="sorgente_riga")
        guard_user_authenticated(user)
        assert user is not None
        scope = resolve_emittente_scope(user)
        rows, total = self._repo.list_documenti_per_sorgente(
            sorgente_tipo_id=sorgente_tipo_id,
            sorgente_uid=sorgente_uid,
            sorgente_riga=sorgente_riga,
            emittente_ids_scope=scope,
            limit=limit,
            offset=offset,
        )
        return {"results": rows, "total_count": total}

    # Scopo: Download PDF persistito + emit evento `SCARICATO` (Decisione 31:
    #        log ad ogni download). Pipeline:
    #         1. guard id + auth + scope;
    #         2. lookup `documenti_generati` (404 unificato no leak);
    #         3. lookup file principale (404 se mai persistito);
    #         4. read storage tramite `storage.read(build_storage_uri(key))`;
    #         5. emit evento `SCARICATO/OK` in transazione separata
    #            (non bloccare il download se l'INSERT log fallisce: il
    #            file e' la priorita');
    #         6. ritorna bytes + metadati per FileResponse del caller.
    def download_documento(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        documento_id: int,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(documento_id, field="documento_id")
        guard_user_authenticated(user)
        assert user is not None
        scope = resolve_emittente_scope(user)

        documento = self._repo.get_documento_generato(
            documento_id, emittente_ids_scope=scope,
        )
        ErrorManager.require(
            documento is not None,
            code=E_NOT_FOUND,
            message="Documento generato non trovato.",
            detail=f"documento_id={documento_id}",
        )
        assert documento is not None

        file_row = self._repo.get_documento_generato_file_principale(documento_id)
        ErrorManager.require(
            file_row is not None,
            code=E_NOT_FOUND,
            message="File principale del documento non trovato.",
            detail=f"documento_id={documento_id}",
        )
        assert file_row is not None

        storage = self._storage_factory()
        storage_uri = storage.build_storage_uri(file_row["storage_key"])
        try:
            pdf_bytes = storage.read(storage_uri)
        except Exception:
            ErrorManager.raise_error(
                code=E_STORAGE_FAILED,
                message="Errore lettura file documento dallo storage.",
                detail=f"documento_id={documento_id}",
            )
            raise  # unreachable

        # Emit evento SCARICATO in tx separata: il download e' la priorita'.
        # Se il log fallisce (es. tx rollback per FK race) il file e' gia'
        # tornato al client, l'audit e' best-effort.
        try:
            with transaction.atomic():
                self._repo.emit_evento_documento({
                    "documento_generato_id": documento_id,
                    "evento_tipo": "SCARICATO",
                    "user_id": getattr(user, "id", None),
                    "esito": "OK",
                    "messaggio": None,
                    "detail": {
                        "size_bytes": len(pdf_bytes),
                        "pdf_hash": documento.get("pdf_hash"),
                    },
                    "meta": {},
                })
        except Exception:
            logger.exception(
                "documenti.documento.evento_scaricato_fallito documento_id=%s",
                documento_id,
            )

        return {
            "pdf_bytes": pdf_bytes,
            "nome_file": documento["nome_file"],
            "mime_type": file_row["mime_type"],
            "size_bytes": int(file_row["file_size_bytes"]),
            "documento_id": documento_id,
        }

    # =================================================================
    # Helpers privati
    # =================================================================

    # Scopo: Risolve il template da generare. Tre casi:
    #         a) caller passa `template_documento_id` -> get_template via
    #            reader (404 unificato + scope automatico);
    #         b) caller passa `tipo_documento_output_id` (e/o
    #            sorgente_tipo+emittente) -> repo.find_template_applicabile
    #            con `is_default=true`;
    #         c) caller passa solo sorgente_tipo+emittente -> idem (b).
    #        Se nessun template matcha -> E_DOCUMENTI_NOT_FOUND.
    def _resolve_template(
        self,
        user: AbstractBaseUser | AnonymousUser,
        *,
        scope: list[int] | None,
        emittente_fiscale_id: int,
        sorgente_tipo_id: int,
        tipo_documento_output_id: int | None,
        template_documento_id: int | None,
    ) -> dict[str, Any]:
        if template_documento_id is not None:
            # Scope + 404 gia' applicati dal reader.
            return self._reader.get_template(user, template_documento_id)

        row = self._repo.find_template_applicabile(
            sorgente_tipo_id=sorgente_tipo_id,
            emittente_fiscale_id=emittente_fiscale_id,
            tipo_documento_output_id=tipo_documento_output_id,
            emittente_ids_scope=scope,
        )
        if row is None:
            # Discrimina due casi diversi (UX: il fix richiesto e' diverso).
            # 1) esistono template per la coppia ma nessuno e' marcato default
            #    -> messaggio "manca predefinito", admin attiva il flag
            # 2) non esiste alcun template -> messaggio "carica template",
            #    admin deve creare il record da capo
            templates_no_default = self._repo.count_templates_attivi_no_default(
                sorgente_tipo_id=sorgente_tipo_id,
                emittente_fiscale_id=emittente_fiscale_id,
                tipo_documento_output_id=tipo_documento_output_id,
                emittente_ids_scope=scope,
            )
            if templates_no_default > 0:
                message = (
                    "Esistono template per questa sorgente/emittente, "
                    "ma nessuno e' impostato come predefinito. "
                    "Marcare un template come 'predefinito' per renderlo applicabile."
                )
            else:
                message = "Nessun template applicabile per la sorgente."
            ErrorManager.require(
                False,
                code=E_NOT_FOUND,
                message=message,
                detail=(
                    f"sorgente_tipo_id={sorgente_tipo_id} "
                    f"emittente_fiscale_id={emittente_fiscale_id} "
                    f"tipo_documento_output_id={tipo_documento_output_id!r} "
                    f"templates_attivi_senza_default={templates_no_default}"
                ),
            )
        assert row is not None
        return row

    # Scopo: Carica la versione PUBBLICATA attiva su CURRENT_DATE. La data
    #        viene presa dal DB-side via `CURRENT_DATE` (passata come
    #        parametro per testabilita': il service mocka `today`).
    def _resolve_versione_pubblicata(
        self, template_documento_id: int,
    ) -> dict[str, Any]:
        today = self._today()
        row = self._repo.get_versione_pubblicata_attiva(
            template_documento_id, today=today,
        )
        ErrorManager.require(
            row is not None,
            code=E_NOT_FOUND,
            message="Nessuna versione PUBBLICATA attiva per il template.",
            detail=(
                f"template_documento_id={template_documento_id} "
                f"today={today.isoformat()}"
            ),
        )
        assert row is not None
        return row

    # Scopo: Risolve il context_builder via registry e invoca
    #        `build_context(sorgente_id)`. Se `context_builder_code` del
    #        template non e' registrato lato backend (whitelist Decisione
    #        18+74) il registry solleva E_DOCUMENTI_VALIDATION.
    def _build_context_for_sorgente(
        self,
        user: AbstractBaseUser | AnonymousUser,
        template: dict[str, Any],
        sorgente_id: int,
        *,
        locale: str,
    ) -> dict[str, Any]:
        code = template.get("context_builder_code") or ""
        if not code:
            ErrorManager.raise_error(
                code=E_VALIDATION,
                message="Template senza context_builder_code configurato.",
                detail=f"template_id={template['id']}",
            )
            raise  # unreachable
        builder = get_builder(code)
        return builder.build_context(
            sorgente_id,
            auth_user_id=getattr(user, "id", None),
            locale=locale,
        )

    # Scopo: Espande il pattern `file_name_pattern` del template con il
    #        context. v1: usa `str.format(**context)` (no Jinja qui — il
    #        pattern e' una stringa breve, non un template HTML). KeyError
    #        / IndexError -> E_DOCUMENTI_RENDER_FAILED parlante.
    def _format_nome_file(
        self, template: dict[str, Any], context: dict[str, Any],
    ) -> str:
        pattern = template.get("file_name_pattern") or ""
        if not pattern:
            # Fallback deterministico se pattern assente: codice template
            # + estensione PDF (e' garantito non vuoto da DDL CHECK).
            return f"{template['codice']}.pdf"
        try:
            return str.format(pattern, **context)
        except (KeyError, IndexError) as exc:
            ErrorManager.raise_error(
                code=E_RENDER_FAILED,
                message=(
                    "Variabile mancante nel context per il pattern "
                    f"file_name '{pattern}'."
                ),
                detail=f"missing={exc!r}",
            )
            raise  # unreachable

    # Scopo: Titolo applicativo del documento generato. v1: descrizione
    #        del template (sempre valorizzata) come fallback codice.
    def _build_titolo(self, template: dict[str, Any]) -> str:
        descr = (template.get("descrizione") or "").strip()
        if descr:
            return descr
        return str(template.get("codice") or "Documento")

    # Scopo: SHA256 hex su stringa UTF-8.
    def _sha256_text(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    # Scopo: SHA256 hex su bytes.
    def _sha256_bytes(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    # Scopo: Serializzazione JSON canonica del context (sort_keys + default=str
    #        per oggetti non-serializzabili come Decimal/date). Il risultato
    #        e' deterministico: stesso context -> stesso `context_hash`.
    def _json_canonical(self, value: Any) -> str:
        return json.dumps(
            value, sort_keys=True, ensure_ascii=False, default=str,
        )

    # Scopo: SHA256 della concatenazione html|css|markdown. Il template_hash
    #        identifica univocamente il payload-template usato per quel
    #        render: utile per auditing e riconoscimento di re-render dopo
    #        cambio versione.
    #        Separator: NULL byte (`\x00`) — non puo' apparire in HTML/CSS/
    #        markdown valido (collision-proof rispetto a separator
    #        markdown-style come `--CSS--`).
    def _compute_template_hash(self, versione: dict[str, Any]) -> str:
        html = versione.get("html_template") or ""
        css = versione.get("css_template") or ""
        markdown = versione.get("markdown_template") or ""
        composite = f"{html}\x00{css}\x00{markdown}"
        return self._sha256_text(composite)

    # Scopo: Estrae estensione lower-case dal nome_file (default 'pdf').
    def _resolve_extension(self, nome_file: str) -> str:
        _, ext = os.path.splitext(nome_file or "")
        ext = ext.lstrip(".").lower().strip()
        if ext and ext.isalnum() and len(ext) <= 10:
            return ext
        return _EXT_PDF

    # Scopo: Hook per testabilita' della data corrente. Default = oggi
    #        (timezone-aware) lato Python; il filtro DB usa
    #        `validita @> %s::date` con questo valore.
    def _today(self) -> _dt.date:
        return timezone.localdate()
