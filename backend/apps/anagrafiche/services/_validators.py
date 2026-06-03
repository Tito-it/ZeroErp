# Scopo: Helper di validazione/estrazione condivisi per i service anagrafiche.
#        require_str, optional_str, extract_optional_fields, require_found,
#        create_with_dedup, create_with_constraint_mapping, update_with_dedup.

from __future__ import annotations

from typing import Any

from django.db import IntegrityError

from apps.core.api.payload_validators import optional_bool, optional_int, optional_iso_date
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


def extract_optional_fields(
    payload: dict,
    *,
    ints: tuple[str, ...] = (),
    bools: tuple[str, ...] = (),
    strings: tuple[str, ...] = (),
    numeric: tuple[str, ...] = (),
    dates: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Costruisce un dict coi soli campi opzionali valorizzati nel payload.

    Centralizza il pattern _extract_*_data (fornitori/emittenti): per categoria
    applica il parser appropriato e include la chiave solo se il valore non e'
    None — così il DB usa i propri default sui campi assenti.
      - ints:    optional_int
      - bools:   optional_bool (solo se la chiave e' presente e non-None)
      - strings: optional_str (strip + None se vuoto)
      - numeric: valore grezzo (float/decimal), solo se presente e non-None
      - dates:   optional_iso_date
    """
    data: dict[str, Any] = {}
    for key in ints:
        val = optional_int(payload, key)
        if val is not None:
            data[key] = val
    for key in bools:
        if key in payload and payload[key] is not None:
            data[key] = optional_bool(payload, key)
    for key in strings:
        val = optional_str(payload, key)
        if val is not None:
            data[key] = val
    for key in numeric:
        if key in payload and payload[key] is not None:
            data[key] = payload[key]
    for key in dates:
        val = optional_iso_date(payload, key)
        if val is not None:
            data[key] = val
    return data


def require_found(entity: dict | None, message: str) -> dict:
    """Solleva E_ANAG_NOT_FOUND se entity e' None, altrimenti la ritorna.

    Centralizza il pattern get → require not-found → assert (per il type checker)
    → return, identico nei get_* di clienti/fornitori/soggetti/emittenti.
    """
    ErrorManager.require(entity is not None, code=E_ANAG_NOT_FOUND, message=message)
    assert entity is not None
    return entity


def create_with_dedup(fn: Any, duplicate_message: str) -> dict:
    """Esegue fn (create) gestendo IntegrityError come duplicato."""
    try:
        return fn()
    except IntegrityError as exc:
        raise ServiceError(code=E_ANAG_DUPLICATO, message=duplicate_message, detail=str(exc)) from exc


def create_with_constraint_mapping(
    fn: Any,
    constraint_messages: dict[str, str],
    default_message: str | None = None,
) -> Any:
    """Esegue fn (create) mappando le violazioni UNIQUE su messaggi per-constraint.

    Per tabelle con piu' vincoli UNIQUE: evita il mascheramento di
    `create_with_dedup` (che riconduce qualsiasi IntegrityError a un unico
    messaggio). Sul primo nome-constraint presente in `str(exc)` solleva
    ServiceError(E_ANAG_DUPLICATO, messaggio). Se nessun constraint matcha:
    se `default_message` e' dato lo solleva, altrimenti RILANCIA l'IntegrityError
    (no mascheramento; il middleware lo gestisce) — pattern coerente con clienti.
    """
    try:
        return fn()
    except IntegrityError as exc:
        detail = str(exc)
        for constraint, message in constraint_messages.items():
            if constraint in detail:
                raise ServiceError(code=E_ANAG_DUPLICATO, message=message, detail=detail) from exc
        if default_message is not None:
            raise ServiceError(code=E_ANAG_DUPLICATO, message=default_message, detail=detail) from exc
        raise


def update_with_dedup(fn: Any, duplicate_message: str, not_found_message: str) -> dict:
    """Esegue fn (update) gestendo IntegrityError e not found."""
    try:
        updated = fn()
    except IntegrityError as exc:
        raise ServiceError(code=E_ANAG_DUPLICATO, message=duplicate_message, detail=str(exc)) from exc
    ErrorManager.require(updated, code=E_ANAG_NOT_FOUND, message=not_found_message)
    return {"updated": True}
