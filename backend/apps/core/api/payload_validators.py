from __future__ import annotations

from typing import Any
from uuid import UUID

from apps.core.api.request_parsers import parse_iso_date

# Validator centralizzati payload API (riusabili cross-domain).


# Scopo: Valida e converte il campo opzionale `int` mantenendo `None` se assente.
def optional_int(payload: dict[str, Any], key: str, *, zero_as_none: bool = False) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    if zero_as_none and value in (0, "0"):
        return None
    if isinstance(value, bool):
        raise ValueError(f"{key}_invalid")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    raise ValueError(f"{key}_invalid")


# Scopo: Valida e converte il campo opzionale `bool` mantenendo `None` se assente.
def optional_bool(payload: dict[str, Any], key: str, default: bool = False) -> bool:
    value = payload.get(key)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
    raise ValueError(f"{key}_invalid")


# Scopo: Valida e converte il campo opzionale `iso_date` mantenendo `None` se assente.
def optional_iso_date(payload: dict[str, Any], key: str):
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key}_invalid")
    return parse_iso_date(value)


# Scopo: Valida e converte il campo opzionale `uuid` mantenendo `None` se assente.
def optional_uuid(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    # Per compatibilita` input legacy/UI: 0 o stringa vuota => NULL.
    if value in (0, "0", ""):
        return None
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None
        try:
            return str(UUID(candidate))
        except ValueError as exc:
            raise ValueError(f"{key}_invalid") from exc
    raise ValueError(f"{key}_invalid")
