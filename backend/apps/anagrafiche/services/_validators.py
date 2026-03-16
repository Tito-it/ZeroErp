# Scopo: Helper di validazione condivisi per i service del modulo anagrafiche.
#        Centralizza _require_str, _optional_str, _create_with_dedup, _update_with_dedup.

from __future__ import annotations

from typing import Any

from django.db import IntegrityError

from apps.core.services.error_manager import ErrorManager
from apps.core.services.service_errors import ServiceError
from apps.anagrafiche.error_codes import E_ANAG_DUPLICATO, E_ANAG_NOT_FOUND, E_ANAG_VALIDAZIONE


def require_str(payload: dict, key: str, message: str) -> str:
    """Estrae, strippa e valida campo stringa obbligatorio."""
    value = (payload.get(key) or "").strip()
    ErrorManager.require(bool(value), code=E_ANAG_VALIDAZIONE, message=message)
    return value


def optional_str(payload: dict, key: str, message: str | None = None) -> str | None:
    """Estrae e strippa campo stringa opzionale. Se fornito e vuoto dopo strip, errore."""
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if message:
            ErrorManager.require(bool(value), code=E_ANAG_VALIDAZIONE, message=message)
        return value or None
    return None


def create_with_dedup(fn: Any, duplicate_message: str) -> dict:
    """Esegue fn (create) gestendo IntegrityError come duplicato."""
    try:
        return fn()
    except IntegrityError as exc:
        raise ServiceError(code=E_ANAG_DUPLICATO, message=duplicate_message, detail=str(exc)) from exc


def update_with_dedup(fn: Any, duplicate_message: str, not_found_message: str) -> dict:
    """Esegue fn (update) gestendo IntegrityError e not found."""
    try:
        updated = fn()
    except IntegrityError as exc:
        raise ServiceError(code=E_ANAG_DUPLICATO, message=duplicate_message, detail=str(exc)) from exc
    ErrorManager.require(updated, code=E_ANAG_NOT_FOUND, message=not_found_message)
    return {"updated": True}
