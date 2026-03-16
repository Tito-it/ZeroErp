# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service layer per CRUD generico tabelle config.
#        Validazione rel in whitelist, IntegrityError, metadata.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import IntegrityError

from apps.core.db.config_crud_repository import ConfigCrudRepository
from apps.core.db.config_metadata_repository import ConfigMetadataRepository
from apps.core.db.dbops_repository import _REL_CONSENTITE
from apps.core.services.error_manager import ErrorManager
from apps.core.services.service_errors import ServiceError

E_CONFIG_VALIDATION = "E_CORE_VALIDATION"
E_CONFIG_NOT_FOUND = "E_ANAG_NOT_FOUND"
E_CONFIG_DUPLICATO = "E_ANAG_DUPLICATO"


def _parse_rel(rel: str) -> tuple[str, str]:
    """Valida rel e restituisce (schema, table)."""
    ErrorManager.require(
        rel in _REL_CONSENTITE,
        code=E_CONFIG_VALIDATION,
        message=f"Tabella '{rel}' non consentita.",
    )
    schema, table = rel.split(".", 1)
    return schema, table


class ConfigCrudService:
    """Service CRUD generico per tabelle config whitelisted."""

    def __init__(self) -> None:
        self._repo = ConfigCrudRepository()
        self._meta = ConfigMetadataRepository()

    # Scopo: Lista tabelle disponibili.
    def list_tables(self) -> list[dict[str, str]]:
        return ConfigCrudRepository.list_available_tables()

    # Scopo: Metadata colonne di una tabella.
    def get_metadata(self, rel: str) -> list[dict[str, Any]]:
        schema, table = _parse_rel(rel)
        return self._meta.get_table_columns(schema, table)

    # Scopo: Dettaglio record.
    def get_record(self, rel: str, record_id: int) -> dict[str, Any]:
        schema, table = _parse_rel(rel)
        result = self._repo.get_record(schema, table, record_id)
        ErrorManager.require(result is not None, code=E_CONFIG_NOT_FOUND, message="Record non trovato.")
        assert result is not None
        return result

    # Scopo: Crea record con gestione IntegrityError.
    def create_record(self, rel: str, payload: dict[str, Any]) -> dict[str, Any]:
        schema, table = _parse_rel(rel)
        try:
            return self._repo.create_record(schema, table, payload)
        except IntegrityError as exc:
            raise ServiceError(code=E_CONFIG_DUPLICATO, message="Record gia' esistente.", detail=str(exc)) from exc

    # Scopo: Aggiorna record con gestione IntegrityError.
    def update_record(self, rel: str, record_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        schema, table = _parse_rel(rel)
        try:
            updated = self._repo.update_record(schema, table, record_id, payload)
        except IntegrityError as exc:
            raise ServiceError(code=E_CONFIG_DUPLICATO, message="Record gia' esistente.", detail=str(exc)) from exc
        ErrorManager.require(updated, code=E_CONFIG_NOT_FOUND, message="Record non trovato.")
        return {"updated": True}
