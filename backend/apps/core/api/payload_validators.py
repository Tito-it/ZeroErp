from __future__ import annotations

import math
from typing import Any
from uuid import UUID

from apps.core.api.request_parsers import parse_iso_date

# Validator centralizzati payload API (riusabili cross-domain).


# ------------------------------------------------------------------
# Helper query-params GET (riusabili da qualsiasi view GET)
# ------------------------------------------------------------------

# Scopo: Normalizza parametro booleano da query string con default configurabile.
def qp_bool(raw: str | None, default: bool = True) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "n", "off"}


# Scopo: Normalizza parametro intero da query string con default configurabile.
def qp_int(raw: str | None, default: int) -> int:
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except (ValueError, AttributeError):
        return default


# Scopo: Converte parametro intero da query string; solleva ValueError se non numerico.
def qp_int_strict(raw: str | None, name: str, default: int) -> int:
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except (ValueError, AttributeError):
        raise ValueError(f"{name}_invalid")


# Scopo: Normalizza parametro stringa da query string (strip + None se vuoto).
def qp_str(raw: str | None) -> str | None:
    if raw is None:
        return None
    cleaned = raw.strip()
    return cleaned or None


# ------------------------------------------------------------------
# Envelope paginato standard (riusabile da qualsiasi service)
# ------------------------------------------------------------------

# Scopo: Costruisce l'envelope paginato standard con count, page, page_size, total_pages, results.
def paginated_envelope(
    results: list, total_count: int, page: int, page_size: int,
) -> dict[str, Any]:
    total_pages = math.ceil(total_count / page_size) if page_size > 0 else 0
    return {
        "count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "results": results,
    }


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
