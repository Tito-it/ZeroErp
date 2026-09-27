# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Facade lettura template documentali. Gestisce lo scope
#        emittente derivandolo dal Django user (whitelist via
#        PermissionResolver.get_emittenti_pk_ids), valida gli input
#        (id positivi, codici stato) e mappa i 404 in
#        ServiceError(E_DOCUMENTI_NOT_FOUND).
#        Contratto write (CRUD admin) atterra in PR successive.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser

from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import PayloadValidator
from apps.core.services.permissions_resolver import PermissionResolver
from apps.documenti.db.documenti_repository import DocumentiRepository
from apps.documenti.services.storage import DocumentStorage, get_storage

E_VALIDATION = "E_DOCUMENTI_VALIDATION"

# Set CHECK chiuso v1 — coerente con DDL template_documenti_versioni.
_STATI_VERSIONE_VALIDI: frozenset[str] = frozenset({"BOZZA", "PUBBLICATA", "OBSOLETA"})


class TemplateService:
    """Facade lettura template + versioni. Risolve scope emittente operatore."""

    def __init__(
        self,
        repo: DocumentiRepository | None = None,
        storage: DocumentStorage | None = None,
    ) -> None:
        self._repo = repo or DocumentiRepository()
        self._v = PayloadValidator(validation_code=E_VALIDATION)
        self._storage_factory = (lambda: storage) if storage is not None else get_storage

    # Scopo: Lista template paginata con scope emittente automatico per
    #        l'utente loggato. Admin globale (None) vede tutto; operatore
    #        riceve la whitelist dei suoi emittenti.
    def list_templates(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        *,
        attivo: bool | None = True,
        tipo_documento_output_id: int | None = None,
        sorgente_tipo_id: int | None = None,
        emittente_fiscale_id: int | None = None,
        search: str | None = None,
        order_by: str = "codice",
        order_dir: str = "asc",
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        emittente_ids_scope = self._resolve_emittente_scope(user)
        rows, total = self._repo.list_templates(
            attivo=attivo,
            tipo_documento_output_id=tipo_documento_output_id,
            sorgente_tipo_id=sorgente_tipo_id,
            emittente_fiscale_id=emittente_fiscale_id,
            search=search,
            emittente_ids_scope=emittente_ids_scope,
            order_by=order_by,
            order_dir=order_dir,
            limit=limit,
            offset=offset,
        )
        return {"results": rows, "total_count": total}

    # Scopo: Dettaglio template per id, con scope emittente. 404 esplicito
    #        sia per id inesistente sia per scope non autorizzato (no
    #        leak di esistenza fuori scope).
    def get_template(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        template_id: int,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(template_id, field="template_id")
        emittente_ids_scope = self._resolve_emittente_scope(user)
        row = self._repo.get_template(
            template_id, emittente_ids_scope=emittente_ids_scope
        )
        ErrorManager.require(
            row is not None,
            code="E_DOCUMENTI_NOT_FOUND",
            message="Template documento non trovato.",
            detail=f"template_id={template_id}",
        )
        assert row is not None
        return row

    # Scopo: Lista versioni di un template. Pre-verifica che il template
    #        sia visibile all'utente (404 unificato) prima di proiettare
    #        le versioni.
    def list_versioni(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        template_id: int,
        *,
        attivo: bool | None = True,
        stato: str | None = None,
        search: str | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> dict[str, Any]:
        self.get_template(user, template_id)  # 404 se fuori scope
        if stato is not None and stato not in _STATI_VERSIONE_VALIDI:
            ErrorManager.raise_error(
                code="E_DOCUMENTI_VALIDATION",
                message=f"Stato versione non valido: '{stato}'.",
                detail=f"ammessi={sorted(_STATI_VERSIONE_VALIDI)!r}",
            )
            raise  # unreachable, per type checker
        rows, total = self._repo.list_versioni(
            template_id, attivo=attivo, stato=stato, search=search,
            order_by=order_by, order_dir=order_dir, limit=limit, offset=offset,
        )
        # Stessa forma di `list_templates`: la view ne fa l'envelope paginato.
        return {"results": rows, "total_count": total}

    # Scopo: Dettaglio versione (incluso payload HTML/CSS/markdown).
    #        Pre-verifica template visibile, poi recupera la versione e
    #        valida il binding template <-> versione (defense-in-depth).
    def get_versione(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        template_id: int,
        versione_id: int,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(versione_id, field="versione_id")
        self.get_template(user, template_id)  # 404 se template fuori scope
        row = self._repo.get_versione(template_id, versione_id)
        ErrorManager.require(
            row is not None,
            code="E_DOCUMENTI_NOT_FOUND",
            message="Versione template non trovata.",
            detail=f"template_id={template_id}, versione_id={versione_id}",
        )
        assert row is not None
        return row

    # Scopo: Lista asset paginata con scope emittente automatico.
    def list_asset(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        *,
        attivo: bool | None = True,
        asset_tipo_id: int | None = None,
        emittente_fiscale_id: int | None = None,
        search: str | None = None,
        order_by: str = "codice",
        order_dir: str = "asc",
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        emittente_ids_scope = self._resolve_emittente_scope(user)
        rows, total = self._repo.list_asset(
            attivo=attivo,
            asset_tipo_id=asset_tipo_id,
            emittente_fiscale_id=emittente_fiscale_id,
            search=search,
            emittente_ids_scope=emittente_ids_scope,
            order_by=order_by,
            order_dir=order_dir,
            limit=limit,
            offset=offset,
        )
        return {"results": rows, "total_count": total}

    # Scopo: Dettaglio asset per id, con scope emittente. 404 unificato
    #        sia per id inesistente sia per scope non autorizzato.
    def get_asset(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        asset_id: int,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(asset_id, field="asset_id")
        emittente_ids_scope = self._resolve_emittente_scope(user)
        row = self._repo.get_asset(
            asset_id, emittente_ids_scope=emittente_ids_scope
        )
        ErrorManager.require(
            row is not None,
            code="E_DOCUMENTI_NOT_FOUND",
            message="Asset documentale non trovato.",
            detail=f"asset_id={asset_id}",
        )
        assert row is not None
        return row

    # Scopo: Scarica il binario di un asset documentale rispettando lo
    #        stesso scope emittente del dettaglio. GET puro: nessun evento
    #        o mutazione, solo lettura da storage applicativo.
    def download_asset(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        asset_id: int,
    ) -> dict[str, Any]:
        asset = self.get_asset(user, asset_id)
        storage = self._storage_factory()
        storage_uri = storage.build_storage_uri(asset["storage_key"])
        try:
            file_bytes = storage.read(storage_uri)
        except Exception:
            ErrorManager.raise_error(
                code="E_DOCUMENTI_STORAGE_FAILED",
                message="Errore lettura asset documentale dallo storage.",
                detail=f"asset_id={asset_id}",
            )
            raise  # unreachable, per type checker

        return {
            "asset_id": asset_id,
            "file_bytes": file_bytes,
            "file_name": asset["file_name"],
            "mime_type": asset["mime_type"],
            "size_bytes": int(asset["file_size_bytes"]),
        }

    # ---- helper interni ------------------------------------------------------

    # Scopo: Risolve la lista degli emittenti autorizzati per l'utente.
    #        Admin globale + superuser = None (vede tutto). Operatore
    #        ottiene una whitelist di id `emittenti_fiscali.id` (puntiamo
    #        ad una tabella che usa la PK reale, vedi memoria
    #        feedback_emittente_pk_vs_soggetto_ruolo).
    def _resolve_emittente_scope(
        self, user: AbstractBaseUser | AnonymousUser | None,
    ) -> list[int] | None:
        if user is None or not getattr(user, "is_authenticated", False):
            # Caller non autenticato non dovrebbe arrivare qui (DomainAPIView
            # gia' applica JWT); difensivamente ritorniamo lista vuota
            # = nessun risultato, mai panel-leak.
            return []
        return PermissionResolver.get_emittenti_pk_ids(user)
