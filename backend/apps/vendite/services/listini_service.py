# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Facade applicativa per il sottodominio vendite/listini.
# ------------------------------------------------------------

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from django.db import IntegrityError, transaction

from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import PayloadValidator
from apps.vendite.db.listini_repository import (
    LISTINI_ORDER_COLUMNS,
    LISTINO_CREATE_COLUMNS,
    LISTINO_UPDATE_COLUMNS,
    RIGA_CREATE_COLUMNS,
    RIGA_UPDATE_COLUMNS,
    RIGHE_ORDER_COLUMNS,
    VERSIONE_CREATE_COLUMNS,
    VERSIONE_UPDATE_COLUMNS,
    ListiniRepository,
)

_ORDER_BY_VALIDI: frozenset[str] = frozenset(LISTINI_ORDER_COLUMNS.keys())
_RIGHE_ORDER_BY_VALIDI: frozenset[str] = frozenset(RIGHE_ORDER_COLUMNS.keys())
_ORDER_DIR_VALIDI: frozenset[str] = frozenset({"asc", "desc"})
_STATI_VERSIONE_VALIDI: frozenset[str] = frozenset({"BOZZA", "ATTIVA", "CHIUSA"})
_LISTINO_NULLABLE_FIELDS: frozenset[str] = frozenset({"meta"})
_VERSIONE_NULLABLE_FIELDS: frozenset[str] = frozenset({"valido_al", "meta"})
_RIGA_NULLABLE_FIELDS: frozenset[str] = frozenset(
    {"meta"}
)
_LISTINO_CREATE_ALLOWED_KEYS: frozenset[str] = frozenset(LISTINO_CREATE_COLUMNS.keys())
_LISTINO_UPDATE_ALLOWED_KEYS: frozenset[str] = frozenset(LISTINO_UPDATE_COLUMNS.keys())
_VERSIONE_CREATE_ALLOWED_KEYS: frozenset[str] = frozenset(VERSIONE_CREATE_COLUMNS.keys())
_VERSIONE_UPDATE_ALLOWED_KEYS: frozenset[str] = frozenset(VERSIONE_UPDATE_COLUMNS.keys())
_RIGA_CREATE_ALLOWED_KEYS: frozenset[str] = frozenset(RIGA_CREATE_COLUMNS.keys())
_RIGA_UPDATE_ALLOWED_KEYS: frozenset[str] = frozenset(RIGA_UPDATE_COLUMNS.keys())

# Validator modulo-level: log_to_db=True per telemetria pipeline vendite,
# function_name override per-chiamata (riflette il metodo service specifico).
# Ref: apps/core/services/payload_helpers.py (V6-B1/V6-B2).
_V = PayloadValidator(
    validation_code="E_VENDITE_VALIDATION",
    log_to_db=True,
)


# Scopo: Normalizza il campo meta da stringa JSON o dict a dict. Stringa
#        JSON non valida o non-oggetto -> ServiceError E_VENDITE_VALIDATION
#        (review: prima bubble-ava ValueError non mappato -> 500).
def _parse_meta_json(meta_raw: Any) -> dict[str, Any]:
    if not meta_raw:
        return {}
    if isinstance(meta_raw, dict):
        return meta_raw
    if isinstance(meta_raw, str):
        try:
            parsed = json.loads(meta_raw)
        except (ValueError, TypeError) as exc:
            ErrorManager.raise_error(
                code="E_VENDITE_VALIDATION",
                message="Il campo 'meta' contiene JSON non valido.",
                context={"meta_raw": meta_raw},
                log_to_db=True,
                function_name="listini_service._parse_meta_json",
                cause=exc,
            )
            raise AssertionError("unreachable") from exc  # pragma: no cover
        if isinstance(parsed, dict):
            return parsed
    ErrorManager.raise_error(
        code="E_VENDITE_VALIDATION",
        message="Il campo 'meta' deve essere un oggetto JSON.",
        context={"meta_type": type(meta_raw).__name__},
        log_to_db=True,
        function_name="listini_service._parse_meta_json",
    )
    raise AssertionError("unreachable")  # pragma: no cover


class _MissingType:
    pass


_MISSING = _MissingType()


# Scopo: Valida paginazione e restituisce offset calcolato con codice errore vendite uniforme.
def _validate_pagination(page: int, page_size: int, function_name: str) -> int:
    ErrorManager.require(
        page >= 1,
        code="E_VENDITE_VALIDATION",
        message="Parametri paginazione non validi.",
        detail="page deve essere >= 1",
        context={"page": page},
        function_name=function_name,
        log_to_db=True,
    )
    ErrorManager.require(
        1 <= page_size <= 200,
        code="E_VENDITE_VALIDATION",
        message="Parametri paginazione non validi.",
        detail="page_size deve essere compreso tra 1 e 200",
        context={"page_size": page_size},
        function_name=function_name,
        log_to_db=True,
    )
    return (page - 1) * page_size


# Scopo: Valida ordinamento lista listini contro whitelist locale.
def _validate_order(order_by: str, order_dir: str, function_name: str) -> tuple[str, str]:
    ErrorManager.require(
        order_by in _ORDER_BY_VALIDI,
        code="E_VENDITE_VALIDATION",
        message="Parametri ordinamento non validi.",
        detail="order_by deve essere uno tra: " + ", ".join(sorted(_ORDER_BY_VALIDI)),
        context={"order_by": order_by},
        function_name=function_name,
        log_to_db=True,
    )
    ErrorManager.require(
        order_dir in _ORDER_DIR_VALIDI,
        code="E_VENDITE_VALIDATION",
        message="Parametri ordinamento non validi.",
        detail="order_dir deve essere 'asc' o 'desc'",
        context={"order_dir": order_dir},
        function_name=function_name,
        log_to_db=True,
    )
    return order_by, order_dir


# Scopo: Valida ordinamento lista righe listino contro whitelist locale.
def _validate_righe_order(order_by: str, order_dir: str, function_name: str) -> tuple[str, str]:
    ErrorManager.require(
        order_by in _RIGHE_ORDER_BY_VALIDI,
        code="E_VENDITE_VALIDATION",
        message="Parametri ordinamento non validi.",
        detail="order_by deve essere uno tra: " + ", ".join(sorted(_RIGHE_ORDER_BY_VALIDI)),
        context={"order_by": order_by},
        function_name=function_name,
        log_to_db=True,
    )
    ErrorManager.require(
        order_dir in _ORDER_DIR_VALIDI,
        code="E_VENDITE_VALIDATION",
        message="Parametri ordinamento non validi.",
        detail="order_dir deve essere 'asc' o 'desc'",
        context={"order_dir": order_dir},
        function_name=function_name,
        log_to_db=True,
    )
    return order_by, order_dir


# Scopo: Costruisce envelope uniforme count/results per collezioni figlie non paginate.
def _build_results_response(results: list[dict[str, object]]) -> dict[str, object]:
    return {"count": len(results), "results": results}


# Scopo: Delega a `PayloadValidator.validate_allowed_keys` del core. Mantiene
#        la firma storica (allowed_keys, function_name, message) per non
#        toccare i call site; V6-B2 ha centralizzato la logica.
def _validate_payload_keys(
    payload: dict[str, Any],
    *,
    allowed_keys: frozenset[str],
    function_name: str,
    message: str,
) -> None:
    _V.validate_allowed_keys(
        payload,
        allowed=allowed_keys,
        message=message,
        function_name=function_name,
    )


# Scopo: Delega a `PayloadValidator.require_string` (max_len=None: il bound
#        di lunghezza lo decide la colonna DB; qui si valida solo presenza
#        e non-vuotezza post-trim).
def _require_string(
    payload: dict[str, Any],
    key: str,
    *,
    function_name: str,
    message: str,
) -> str:
    return _V.require_string(
        payload,
        key,
        message=message,
        function_name=function_name,
    )


# Scopo: Estrae stringa presente nel payload; supporta NULL esplicito se consentito.
def _extract_string(
    payload: dict[str, Any],
    key: str,
    *,
    function_name: str,
    nullable: bool,
    message: str,
) -> str | None | _MissingType:
    if key not in payload:
        return _MISSING
    value = payload.get(key)
    if value is None:
        ErrorManager.require(
            nullable,
            code="E_VENDITE_VALIDATION",
            message=message,
            detail=f"{key} non puo' essere null.",
            context={"field": key},
            function_name=function_name,
            log_to_db=True,
        )
        return None
    ErrorManager.require(
        isinstance(value, str),
        code="E_VENDITE_VALIDATION",
        message=message,
        detail=f"{key} deve essere una stringa.",
        context={"field": key},
        function_name=function_name,
        log_to_db=True,
    )
    cleaned = value.strip()
    if nullable and cleaned == "":
        return None
    ErrorManager.require(
        bool(cleaned),
        code="E_VENDITE_VALIDATION",
        message=message,
        detail=f"{key} non puo' essere vuoto.",
        context={"field": key},
        function_name=function_name,
        log_to_db=True,
    )
    return cleaned


# Scopo: Estrae intero opzionale supportando NULL esplicito o stringa vuota.
def _extract_nullable_int(
    payload: dict[str, Any],
    key: str,
    *,
    function_name: str,
    message: str,
) -> int | None | _MissingType:
    if key not in payload:
        return _MISSING
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        ErrorManager.require(
            value > 0,
            code="E_VENDITE_VALIDATION",
            message=message,
            detail=f"{key} deve essere > 0 oppure null.",
            context={"field": key, "value": value},
            function_name=function_name,
            log_to_db=True,
        )
        return value
    ErrorManager.require(
        not isinstance(value, (bool, float)),
        code="E_VENDITE_VALIDATION",
        message=message,
        detail=f"{key} deve essere un intero o null.",
        context={"field": key},
        function_name=function_name,
        log_to_db=True,
    )
    try:
        normalized = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key}_invalid") from exc
    ErrorManager.require(
        normalized > 0,
        code="E_VENDITE_VALIDATION",
        message=message,
        detail=f"{key} deve essere > 0 oppure null.",
        context={"field": key, "value": normalized},
        function_name=function_name,
        log_to_db=True,
    )
    return normalized


# Scopo: Delega a `PayloadValidator.require_positive_int`. Complementare a
#        `_extract_nullable_int` per campi NOT NULL (es. utility_id, tipologia_id).
def _require_positive_int(
    payload: dict[str, Any],
    key: str,
    *,
    function_name: str,
    message: str,
) -> int:
    return _V.require_positive_int(
        payload,
        key,
        message=message,
        function_name=function_name,
    )


# Scopo: Estrae un intero positivo opzionale (ammette assenza) ma se presente
#        deve essere intero positivo e NOT NULL. Usato su PATCH per campi
#        come utility_id/tipologia_id che in DB sono NOT NULL ma facoltativi
#        nel payload di update.
def _extract_required_int_if_present(
    payload: dict[str, Any],
    key: str,
    *,
    function_name: str,
    message: str,
) -> int | _MissingType:
    if key not in payload:
        return _MISSING
    return _require_positive_int(
        payload,
        key,
        function_name=function_name,
        message=message,
    )


# Scopo: Estrae booleano presente nel payload senza inventare default impliciti.
def _extract_present_bool(
    payload: dict[str, Any],
    key: str,
    *,
    function_name: str,
    message: str,
) -> bool | _MissingType:
    if key not in payload:
        return _MISSING
    value = payload.get(key)
    ErrorManager.require(
        isinstance(value, bool),
        code="E_VENDITE_VALIDATION",
        message=message,
        detail=f"{key} deve essere booleano.",
        context={"field": key},
        function_name=function_name,
        log_to_db=True,
    )
    return value


# Scopo: Estrae e valida un campo JSON object opzionale.
def _extract_meta(
    payload: dict[str, Any],
    *,
    function_name: str,
    message: str,
) -> dict[str, Any] | None | _MissingType:
    if "meta" not in payload:
        return _MISSING
    value = payload.get("meta")
    if value is None:
        return None
    ErrorManager.require(
        isinstance(value, dict),
        code="E_VENDITE_VALIDATION",
        message=message,
        detail="meta deve essere un oggetto JSON.",
        context={"field": "meta"},
        function_name=function_name,
        log_to_db=True,
    )
    return value


# Scopo: Estrae e valida un Decimal da payload, consentendo NULL se richiesto.
def _extract_decimal(
    payload: dict[str, Any],
    key: str,
    *,
    function_name: str,
    nullable: bool,
    message: str,
) -> Decimal | None | _MissingType:
    if key not in payload:
        return _MISSING
    value = payload.get(key)
    if value is None:
        ErrorManager.require(
            nullable,
            code="E_VENDITE_VALIDATION",
            message=message,
            detail=f"{key} non puo' essere null.",
            context={"field": key},
            function_name=function_name,
            log_to_db=True,
        )
        return None
    ErrorManager.require(
        not isinstance(value, bool),
        code="E_VENDITE_VALIDATION",
        message=message,
        detail=f"{key} deve essere numerico.",
        context={"field": key},
        function_name=function_name,
        log_to_db=True,
    )
    try:
        normalized = Decimal(str(value).strip())
    except (InvalidOperation, AttributeError) as exc:
        raise ValueError(f"{key}_invalid") from exc
    return normalized


# Scopo: Estrae e valida una data ISO da payload.
def _extract_payload_date(
    payload: dict[str, Any],
    key: str,
    *,
    function_name: str,
    nullable: bool,
    message: str,
) -> date | None | _MissingType:
    if key not in payload:
        return _MISSING
    value = payload.get(key)
    if value is None:
        ErrorManager.require(
            nullable,
            code="E_VENDITE_VALIDATION",
            message=message,
            detail=f"{key} non puo' essere null.",
            context={"field": key},
            function_name=function_name,
            log_to_db=True,
        )
        return None
    if isinstance(value, date):
        return value
    ErrorManager.require(
        isinstance(value, str),
        code="E_VENDITE_VALIDATION",
        message=message,
        detail=f"{key} deve essere una data ISO YYYY-MM-DD.",
        context={"field": key},
        function_name=function_name,
        log_to_db=True,
    )
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValueError(f"{key}_invalid") from exc


# Scopo: Estrae e valida UUID da payload.
def _extract_payload_uuid(
    payload: dict[str, Any],
    key: str,
    *,
    function_name: str,
    message: str,
) -> str | _MissingType:
    if key not in payload:
        return _MISSING
    value = payload.get(key)
    if isinstance(value, UUID):
        return str(value)
    ErrorManager.require(
        isinstance(value, str),
        code="E_VENDITE_VALIDATION",
        message=message,
        detail=f"{key} deve essere un UUID valido.",
        context={"field": key},
        function_name=function_name,
        log_to_db=True,
    )
    try:
        return str(UUID(value.strip()))
    except ValueError as exc:
        raise ValueError(f"{key}_invalid") from exc


# Scopo: Estrae stringa enum e la valida contro l'insieme ammesso.
def _extract_enum_string(
    payload: dict[str, Any],
    key: str,
    *,
    function_name: str,
    allowed_values: frozenset[str],
    nullable: bool,
    message: str,
) -> str | None | _MissingType:
    value = _extract_string(
        payload,
        key,
        function_name=function_name,
        nullable=nullable,
        message=message,
    )
    if value in {_MISSING, None}:
        return value
    assert isinstance(value, str)
    ErrorManager.require(
        value in allowed_values,
        code="E_VENDITE_VALIDATION",
        message=message,
        detail=f"{key} deve essere uno tra: {', '.join(sorted(allowed_values))}",
        context={"field": key, "value": value},
        function_name=function_name,
        log_to_db=True,
    )
    return value


# Scopo: Restituisce il listino esistente o solleva not-found standardizzato.
def _get_listino_or_raise(listino_id: int, *, function_name: str) -> dict[str, Any]:
    repository = ListiniRepository()
    result = repository.get_listino(listino_id)
    ErrorManager.require(
        result is not None,
        code="E_VENDITE_LISTINO_NOT_FOUND",
        message="Listino non trovato.",
        detail=f"Nessun listino con id={listino_id}.",
        context={"listino_id": listino_id},
        function_name=function_name,
        log_to_db=False,
    )
    assert result is not None
    return result


# Scopo: Restituisce la versione esistente nel perimetro listino o solleva not-found.
def _get_versione_or_raise(listino_id: int, versione_id: int, *, function_name: str) -> dict[str, Any]:
    repository = ListiniRepository()
    result = repository.get_versione(listino_id, versione_id)
    ErrorManager.require(
        result is not None,
        code="E_VENDITE_LISTINO_VERSIONE_NOT_FOUND",
        message="Versione listino non trovata.",
        detail=f"Nessuna versione id={versione_id} per listino id={listino_id}.",
        context={"listino_id": listino_id, "versione_id": versione_id},
        function_name=function_name,
        log_to_db=False,
    )
    assert result is not None
    return result


# Scopo: Restituisce la riga esistente nel perimetro listino/versione o solleva not-found.
def _get_riga_or_raise(
    listino_id: int,
    versione_id: int,
    riga_id: int,
    *,
    function_name: str,
) -> dict[str, Any]:
    repository = ListiniRepository()
    result = repository.get_riga(listino_id, versione_id, riga_id)
    ErrorManager.require(
        result is not None,
        code="E_VENDITE_LISTINO_RIGA_NOT_FOUND",
        message="Riga listino non trovata.",
        detail=f"Nessuna riga id={riga_id} per versione id={versione_id}.",
        context={"listino_id": listino_id, "versione_id": versione_id, "riga_id": riga_id},
        function_name=function_name,
        log_to_db=False,
    )
    assert result is not None
    return result


# Scopo: Traduce i vincoli DB piu' comuni del sottodominio listini in errori applicativi leggibili.
def _translate_integrity_error(exc: IntegrityError, *, function_name: str, entity: str) -> None:
    error_text = str(exc)
    constraint_map: tuple[tuple[str, str, str], ...] = (
        ("fk_listini_utility", "Utility non valida.", "utility_id non corrisponde a nessuna utility in config.utilities."),
        (
            # Nome generato da PostgreSQL (pattern <table>_<col>_fkey) dalla
            # migration 20260413-05 che usa ADD COLUMN ... REFERENCES senza
            # CONSTRAINT esplicito. Se la migration viene rinominata, aggiornare.
            "listini_tipologia_id_fkey",
            "Tipologia listino non valida.",
            "tipologia_id non corrisponde a nessuna tipologia in config.listini_tipologie.",
        ),
        ("uq_listini_codice", "Codice listino duplicato.", "Esiste gia' un listino con lo stesso codice."),
        (
            "uq_listini_versioni_listino_codice",
            "Codice versione duplicato.",
            "Esiste gia' una versione con lo stesso codice per questo listino.",
        ),
        (
            "chk_listini_versioni_stato",
            "Stato versione non valido.",
            "stato deve essere BOZZA, ATTIVA o CHIUSA.",
        ),
        (
            "ex_listini_versioni_no_overlap",
            "Intervallo versione sovrapposto.",
            "Esiste gia' una versione ATTIVA sovrapposta per il listino. "
            "Usa il pattern di sostituzione: chiudi la vecchia "
            "(valido_al = nuova_valido_dal - 1) e poi attiva la nuova.",
        ),
        (
            "chk_listini_versioni_date",
            "Intervallo versione non valido.",
            "valido_al deve essere maggiore di valido_dal.",
        ),
        (
            "uq_listini_righe_key_attiva",
            "Riga prezzo duplicata.",
            "Esiste gia' una riga attiva con lo stesso articolo/UoM/perimetro.",
        ),
        (
            "chk_listini_righe_prezzo",
            "Prezzo riga non valido.",
            "prezzo deve essere >= 0.",
        ),
    )
    for constraint_name, message, detail in constraint_map:
        if constraint_name in error_text:
            ErrorManager.raise_error(
                code="E_VENDITE_VALIDATION",
                message=message,
                detail=detail,
                context={"constraint": constraint_name, "entity": entity},
                function_name=function_name,
                log_to_db=True,
            )
    if "violates foreign key constraint" in error_text:
        ErrorManager.raise_error(
            code="E_VENDITE_VALIDATION",
            message="Riferimento non valido.",
            detail="Uno dei riferimenti collegati non esiste o non e' piu' attivo.",
            context={"entity": entity},
            function_name=function_name,
            log_to_db=True,
        )
    raise exc


# Scopo: Normalizza payload create listino.
def _extract_listino_payload(
    payload: dict[str, Any],
    *,
    for_update: bool,
    function_name: str,
) -> dict[str, Any]:
    message = "Payload listino non valido."
    allowed_keys = _LISTINO_UPDATE_ALLOWED_KEYS if for_update else _LISTINO_CREATE_ALLOWED_KEYS
    _validate_payload_keys(
        payload,
        allowed_keys=allowed_keys,
        function_name=function_name,
        message=message,
    )
    data: dict[str, Any] = {}

    if not for_update:
        data["codice"] = _require_string(
            payload,
            "codice",
            function_name=function_name,
            message=message,
        )
        data["descrizione"] = _require_string(
            payload,
            "descrizione",
            function_name=function_name,
            message=message,
        )
        # utility_id: NOT NULL (ogni listino appartiene a una utility; Base id=5 per commercio).
        data["utility_id"] = _require_positive_int(
            payload,
            "utility_id",
            function_name=function_name,
            message=message,
        )
        # tipologia_id: NOT NULL (ogni listino ha una tipologia esplicita).
        data["tipologia_id"] = _require_positive_int(
            payload,
            "tipologia_id",
            function_name=function_name,
            message=message,
        )
        # emittente_soggetto_ruolo_id: NOT NULL (pricing v5 §3.1 — dimensione
        # del listino). Un listino vale per un solo emittente fiscale.
        data["emittente_soggetto_ruolo_id"] = _require_positive_int(
            payload,
            "emittente_soggetto_ruolo_id",
            function_name=function_name,
            message=message,
        )
    else:
        descrizione = _extract_string(
            payload,
            "descrizione",
            function_name=function_name,
            nullable=False,
            message=message,
        )
        if descrizione is not _MISSING:
            data["descrizione"] = descrizione

        # utility_id: ammesso in update ma NOT NULL (trigger DB valida matrice).
        utility_id_val = _extract_required_int_if_present(
            payload,
            "utility_id",
            function_name=function_name,
            message=message,
        )
        if utility_id_val is not _MISSING:
            data["utility_id"] = utility_id_val

        # tipologia_id: ammesso in update ma NOT NULL (trigger DB valida matrice).
        tipologia_id_val = _extract_required_int_if_present(
            payload,
            "tipologia_id",
            function_name=function_name,
            message=message,
        )
        if tipologia_id_val is not _MISSING:
            data["tipologia_id"] = tipologia_id_val

        # emittente_soggetto_ruolo_id: ammesso in update ma NOT NULL.
        emittente_val = _extract_required_int_if_present(
            payload,
            "emittente_soggetto_ruolo_id",
            function_name=function_name,
            message=message,
        )
        if emittente_val is not _MISSING:
            data["emittente_soggetto_ruolo_id"] = emittente_val

    attivo = _extract_present_bool(
        payload,
        "attivo",
        function_name=function_name,
        message=message,
    )
    if attivo is not _MISSING:
        data["attivo"] = attivo

    meta = _extract_meta(payload, function_name=function_name, message=message)
    if meta is not _MISSING:
        data["meta"] = meta

    return data


# Scopo: Normalizza payload create/update versione con regole temporali minime.
def _extract_versione_payload(
    payload: dict[str, Any],
    *,
    for_update: bool,
    function_name: str,
) -> dict[str, Any]:
    message = "Payload versione listino non valido."
    allowed_keys = _VERSIONE_UPDATE_ALLOWED_KEYS if for_update else _VERSIONE_CREATE_ALLOWED_KEYS
    _validate_payload_keys(
        payload,
        allowed_keys=allowed_keys,
        function_name=function_name,
        message=message,
    )
    data: dict[str, Any] = {}

    codice_versione = _extract_string(
        payload,
        "codice_versione",
        function_name=function_name,
        nullable=False,
        message=message,
    )
    if codice_versione is not _MISSING:
        data["codice_versione"] = codice_versione
    elif not for_update:
        data["codice_versione"] = _require_string(
            payload,
            "codice_versione",
            function_name=function_name,
            message=message,
        )

    valido_dal = _extract_payload_date(
        payload,
        "valido_dal",
        function_name=function_name,
        nullable=False,
        message=message,
    )
    if valido_dal is not _MISSING:
        data["valido_dal"] = valido_dal
    elif not for_update:
        ErrorManager.require(
            False,
            code="E_VENDITE_VALIDATION",
            message=message,
            detail="valido_dal obbligatorio.",
            context={"field": "valido_dal"},
            function_name=function_name,
            log_to_db=True,
        )

    valido_al = _extract_payload_date(
        payload,
        "valido_al",
        function_name=function_name,
        nullable=True,
        message=message,
    )
    if valido_al is not _MISSING:
        data["valido_al"] = valido_al

    attivo = _extract_present_bool(
        payload,
        "attivo",
        function_name=function_name,
        message=message,
    )
    if attivo is not _MISSING:
        data["attivo"] = attivo

    meta = _extract_meta(payload, function_name=function_name, message=message)
    if meta is not _MISSING:
        data["meta"] = meta

    effective_valido_dal = data.get("valido_dal")
    effective_valido_al = data.get("valido_al")
    if effective_valido_dal is not None and effective_valido_al is not None:
        assert isinstance(effective_valido_dal, date)
        assert isinstance(effective_valido_al, date)
        ErrorManager.require(
            effective_valido_al > effective_valido_dal,
            code="E_VENDITE_VALIDATION",
            message=message,
            detail="valido_al deve essere maggiore di valido_dal.",
            context={"valido_dal": effective_valido_dal, "valido_al": effective_valido_al},
            function_name=function_name,
            log_to_db=True,
        )

    return data


# Scopo: Normalizza payload create/update riga prezzo e impone prezzo >= 0.
def _extract_riga_payload(
    payload: dict[str, Any],
    *,
    for_update: bool,
    function_name: str,
) -> dict[str, Any]:
    message = "Payload riga listino non valido."
    allowed_keys = _RIGA_UPDATE_ALLOWED_KEYS if for_update else _RIGA_CREATE_ALLOWED_KEYS
    _validate_payload_keys(
        payload,
        allowed_keys=allowed_keys,
        function_name=function_name,
        message=message,
    )
    data: dict[str, Any] = {}

    if not for_update:
        articolo_id = _extract_payload_uuid(
            payload,
            "articolo_id",
            function_name=function_name,
            message=message,
        )
        ErrorManager.require(
            articolo_id is not _MISSING,
            code="E_VENDITE_VALIDATION",
            message=message,
            detail="articolo_id obbligatorio.",
            context={"field": "articolo_id"},
            function_name=function_name,
            log_to_db=True,
        )
        assert articolo_id is not _MISSING
        data["articolo_id"] = articolo_id

        uom_id = _extract_nullable_int(
            payload,
            "uom_id",
            function_name=function_name,
            message=message,
        )
        ErrorManager.require(
            uom_id is not _MISSING and uom_id is not None,
            code="E_VENDITE_VALIDATION",
            message=message,
            detail="uom_id obbligatorio.",
            context={"field": "uom_id"},
            function_name=function_name,
            log_to_db=True,
        )
        assert uom_id is not _MISSING
        data["uom_id"] = uom_id

    # Pricing v5: BA/utility/emittente sono droppati da listini_righe
    # (F1-DB-25). Eventuali valori residui nel payload sono ignorati
    # silenziosamente (retrocompatibilita' chiamanti pre-v5).

    prezzo = _extract_decimal(
        payload,
        "prezzo",
        function_name=function_name,
        nullable=False,
        message=message,
    )
    if prezzo is not _MISSING:
        assert prezzo is not None
        ErrorManager.require(
            prezzo >= Decimal("0"),
            code="E_VENDITE_VALIDATION",
            message=message,
            detail="prezzo deve essere >= 0.",
            context={"field": "prezzo", "value": str(prezzo)},
            function_name=function_name,
            log_to_db=True,
        )
        data["prezzo"] = prezzo

    attivo = _extract_present_bool(
        payload,
        "attivo",
        function_name=function_name,
        message=message,
    )
    if attivo is not _MISSING:
        data["attivo"] = attivo

    meta = _extract_meta(payload, function_name=function_name, message=message)
    if meta is not _MISSING:
        data["meta"] = meta

    return data


# Scopo: Valida la coerenza articolo/UoM prima di creare o aggiornare righe prezzo.
def _validate_riga_articolo_uom(articolo_id: UUID | str, uom_id: int, *, function_name: str) -> None:
    repository = ListiniRepository()
    validation = repository.get_articolo_uom_validation(articolo_id, uom_id)
    ErrorManager.require(
        validation["articolo_attivo"],
        code="E_VENDITE_VALIDATION",
        message="Riga listino non valida.",
        detail=f"articolo_id={articolo_id} non trovato o non attivo.",
        context={"articolo_id": str(articolo_id)},
        function_name=function_name,
        log_to_db=True,
    )
    ErrorManager.require(
        validation["uom_attiva"],
        code="E_VENDITE_VALIDATION",
        message="Riga listino non valida.",
        detail=f"uom_id={uom_id} non trovata o non attiva.",
        context={"uom_id": uom_id},
        function_name=function_name,
        log_to_db=True,
    )
    ErrorManager.require(
        validation["uom_compatibile"],
        code="E_VENDITE_VALIDATION",
        message="Riga listino non valida.",
        detail="La UoM non e' compatibile con l'articolo selezionato.",
        context={"articolo_id": str(articolo_id), "uom_id": uom_id},
        function_name=function_name,
        log_to_db=True,
    )


# Scopo: Whitelist campi PATCH versione ammessi in base allo stato corrente.
#        - BOZZA  : tutti i campi modificabili (allineato a _VERSIONE_UPDATE_ALLOWED_KEYS)
#        - ATTIVA : solo valido_al (programmazione chiusura)
#        - CHIUSA : nessun campo (stato terminale, modifiche vietate)
#        Risponde all'esigenza di immutabilita' delle versioni operative dopo
#        l'attivazione, evitando drift tra listino e snapshot in commesse_attivita.
#        Il set BOZZA e' derivato da _VERSIONE_UPDATE_ALLOWED_KEYS per evitare
#        drift silenzioso quando si aggiungono nuove colonne a VERSIONE_UPDATE_COLUMNS.
_VERSIONE_PATCH_ALLOWED_BY_STATE: dict[str, frozenset[str]] = {
    "BOZZA": _VERSIONE_UPDATE_ALLOWED_KEYS,
    "ATTIVA": frozenset({"valido_al"}),
    "CHIUSA": frozenset(),
}


def _assert_versione_patch_allowed(
    versione: dict[str, Any],
    data: dict[str, Any],
    *,
    function_name: str,
) -> None:
    stato = str(versione["stato"])
    allowed = _VERSIONE_PATCH_ALLOWED_BY_STATE.get(stato, frozenset())
    presenti = set(data.keys())
    non_ammessi = sorted(presenti - allowed)
    ErrorManager.require(
        not non_ammessi,
        code="E_VENDITE_VALIDATION",
        message="Aggiornamento versione non consentito.",
        detail=(
            f"In stato {stato} sono modificabili solo: "
            f"{sorted(allowed) if allowed else 'nessun campo'}. "
            f"Campi non ammessi nel payload: {non_ammessi}."
        ),
        context={
            "versione_id": versione["id"],
            "stato": stato,
            "campi_non_ammessi": non_ammessi,
            "campi_ammessi": sorted(allowed),
        },
        function_name=function_name,
        log_to_db=True,
    )


# Scopo: Guard fail-fast che impedisce CRUD righe su versioni non in stato BOZZA.
#        Le righe di una versione ATTIVA sono immutabili (snapshot in commesse_attivita
#        e attivita_fatturabili gia` propagati). Le righe di una versione CHIUSA sono
#        congelate per audit storico. Solo BOZZA accetta create/update/delete righe.
def _assert_versione_bozza_for_riga_op(
    versione: dict[str, Any],
    *,
    function_name: str,
) -> None:
    stato = str(versione["stato"])
    ErrorManager.require(
        stato == "BOZZA",
        code="E_VENDITE_VALIDATION",
        message="Operazione su righe non consentita.",
        detail=(
            "Le righe sono modificabili solo su versioni in stato BOZZA. "
            f"Stato corrente: {stato}."
        ),
        context={"versione_id": versione["id"], "stato": stato},
        function_name=function_name,
        log_to_db=True,
    )


# Scopo: Applica la guard di transizione stato versione in modo esplicito lato service.
#        L'unica transizione manuale ammessa e' BOZZA -> ATTIVA (attivazione).
#        La transizione ATTIVA -> CHIUSA non e' piu' manuale: la chiusura si
#        effettua via PATCH valido_al; lo stato CHIUSA viene sincronizzato dal
#        DB (trigger/job) quando valido_al scende sotto la data corrente.
#        Vedi brief-db-listini-stato-chiusa-sync.md per il dettaglio DB.
def _validate_versione_state_transition(
    versione: dict[str, Any],
    nuovo_stato: str,
    *,
    function_name: str,
) -> None:
    stato_corrente = str(versione["stato"])
    if stato_corrente == nuovo_stato:
        return

    allowed_transitions: dict[str, frozenset[str]] = {
        "BOZZA": frozenset({"ATTIVA"}),
        "ATTIVA": frozenset(),
        "CHIUSA": frozenset(),
    }
    # Messaggio dedicato per il caso ATTIVA -> CHIUSA: l'operazione esiste
    # ancora ma si esegue via PATCH valido_al. Dirottare l'operatore sul path
    # corretto invece di un generico "transizione non ammessa". Allineato col
    # messaggio concordato con il team DB: lato DB esiste la guard speculare
    # con codice E_VERSIONE_STATO_TRANSIZIONE_INVALIDA (defense-in-depth).
    if stato_corrente == "ATTIVA" and nuovo_stato == "CHIUSA":
        ErrorManager.raise_error(
            code="E_VENDITE_VALIDATION",
            message="Chiusura versione non consentita via cambio stato.",
            detail=(
                "Per chiudere impostare valido_al (PATCH); la chiusura "
                "avviene automaticamente a finestra scaduta."
            ),
            context={"stato_corrente": stato_corrente, "nuovo_stato": nuovo_stato},
            function_name=function_name,
            log_to_db=True,
        )
    ErrorManager.require(
        nuovo_stato in allowed_transitions.get(stato_corrente, frozenset()),
        code="E_VENDITE_VALIDATION",
        message="Transizione stato versione non valida.",
        detail=f"Transizione non ammessa: {stato_corrente} -> {nuovo_stato}.",
        context={"stato_corrente": stato_corrente, "nuovo_stato": nuovo_stato},
        function_name=function_name,
        log_to_db=True,
    )


# Scopo: Restituisce lista listini paginata con filtri e ordinamento validati.
def fn_list_listini(
    *,
    utility_id: int | None = None,
    tipologia_id: int | None = None,
    attivo: bool | None = None,
    search: str | None = None,
    order_by: str = "codice",
    order_dir: str = "asc",
    limit: int = 25,
    offset: int = 0,
) -> tuple[list[dict[str, object]], int]:
    function_name = "vendite.listini_service.fn_list_listini"
    if utility_id is not None:
        ErrorManager.require(
            isinstance(utility_id, int) and utility_id > 0,
            code="E_VENDITE_VALIDATION",
            message="Filtro utility non valido.",
            detail="utility_id deve essere un intero positivo.",
            context={"utility_id": utility_id},
            function_name=function_name,
            log_to_db=True,
        )
    if tipologia_id is not None:
        ErrorManager.require(
            isinstance(tipologia_id, int) and tipologia_id > 0,
            code="E_VENDITE_VALIDATION",
            message="Filtro tipologia non valido.",
            detail="tipologia_id deve essere un intero positivo.",
            context={"tipologia_id": tipologia_id},
            function_name=function_name,
            log_to_db=True,
        )
    order_by, order_dir = _validate_order(order_by, order_dir, function_name)
    repository = ListiniRepository()
    return repository.list_listini(
        utility_id=utility_id,
        tipologia_id=tipologia_id,
        attivo=attivo,
        search=search,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset,
    )


# Scopo: Restituisce le tipologie listino ammesse per una utility dalla matrice
#        config.listini_tipologie_utilities. Usato dal drawer per popolare il
#        Select tipologia al cambio utility.
def fn_list_tipologie_per_utility(utility_id: int) -> list[dict[str, object]]:
    function_name = "vendite.listini_service.fn_list_tipologie_per_utility"
    ErrorManager.require(
        isinstance(utility_id, int) and utility_id > 0,
        code="E_VENDITE_VALIDATION",
        message="Parametro utility non valido.",
        detail="utility_id deve essere un intero positivo.",
        context={"utility_id": utility_id},
        function_name=function_name,
        log_to_db=True,
    )
    repository = ListiniRepository()
    return repository.list_tipologie_per_utility(utility_id)


# Scopo: Restituisce il dettaglio completo del listino con versioni nidificate.
#        Il concetto di "associazioni" (tabella `listini_associazioni`) e'
#        stato rimosso in F2-BE-13: nel modello v5 il listino e' selezionato
#        dalla matrice `categorie_clienti_listini` o dal contratto, non piu'
#        da una tabella di associazione dedicata.
def fn_get_listino_dettaglio(listino_id: int) -> dict[str, object]:
    function_name = "vendite.listini_service.fn_get_listino_dettaglio"
    repository = ListiniRepository()
    listino = _get_listino_or_raise(listino_id, function_name=function_name)
    listino["versioni"] = repository.list_versioni(listino_id)
    return listino


# Scopo: Crea il listino e restituisce il dettaglio aggiornato.
def fn_create_listino(payload: dict[str, Any]) -> dict[str, object]:
    function_name = "vendite.listini_service.fn_create_listino"
    data = _extract_listino_payload(payload, for_update=False, function_name=function_name)
    repository = ListiniRepository()
    try:
        listino_id = repository.create_listino(data)
    except IntegrityError as exc:
        _translate_integrity_error(exc, function_name=function_name, entity="listino")
    return fn_get_listino_dettaglio(listino_id)


# Scopo: Aggiorna il listino sui soli campi presenti nel payload e restituisce il dettaglio.
def fn_update_listino(listino_id: int, payload: dict[str, Any]) -> dict[str, object]:
    function_name = "vendite.listini_service.fn_update_listino"
    data = _extract_listino_payload(payload, for_update=True, function_name=function_name)
    ErrorManager.require(
        bool(data),
        code="E_VENDITE_VALIDATION",
        message="Payload listino non valido.",
        detail="Nessun campo aggiornabile presente nel payload.",
        context={"allowed_nullable_fields": sorted(_LISTINO_NULLABLE_FIELDS)},
        function_name=function_name,
        log_to_db=True,
    )
    repository = ListiniRepository()
    try:
        updated = repository.update_listino(listino_id, data)
    except IntegrityError as exc:
        _translate_integrity_error(exc, function_name=function_name, entity="listino")
    ErrorManager.require(
        updated,
        code="E_VENDITE_LISTINO_NOT_FOUND",
        message="Listino non trovato.",
        detail=f"Nessun listino con id={listino_id}.",
        context={"listino_id": listino_id},
        function_name=function_name,
        log_to_db=False,
    )
    return fn_get_listino_dettaglio(listino_id)


# Scopo: Elimina un listino mai usato (zero versioni).
#        Decisione O3 (sviluppo-listini-v2): caso d'uso = listini di test creati
#        per errore. Per disattivare un listino con figli, usare PATCH attivo=false.
#        F2-BE-13: rimosso il check su `associazioni_count` (tabella eliminata).
def fn_delete_listino(listino_id: int) -> dict[str, object]:
    function_name = "vendite.listini_service.fn_delete_listino"
    listino = _get_listino_or_raise(listino_id, function_name=function_name)
    versioni_count = int(listino.get("versioni_count") or 0)
    ErrorManager.require(
        versioni_count == 0,
        code="E_VENDITE_VALIDATION",
        message="Eliminazione listino non consentita.",
        detail=(
            "Solo i listini senza versioni possono essere eliminati. "
            f"Versioni: {versioni_count}. "
            "Per disattivare un listino con figli, usa PATCH attivo=false."
        ),
        context={
            "listino_id": listino_id,
            "versioni_count": versioni_count,
        },
        function_name=function_name,
        log_to_db=True,
    )
    repository = ListiniRepository()
    try:
        deleted = repository.delete_listino(listino_id)
    except IntegrityError as exc:
        _translate_integrity_error(exc, function_name=function_name, entity="listino")
    ErrorManager.require(
        deleted,
        code="E_VENDITE_LISTINO_NOT_FOUND",
        message="Listino non trovato.",
        detail=f"Nessun listino con id={listino_id}.",
        context={"listino_id": listino_id},
        function_name=function_name,
        log_to_db=False,
    )
    return {"deleted": True, "id": listino_id}


# Scopo: Restituisce la lista versioni del listino con envelope uniforme.
def fn_list_versioni(listino_id: int) -> dict[str, object]:
    function_name = "vendite.listini_service.fn_list_versioni"
    _get_listino_or_raise(listino_id, function_name=function_name)
    repository = ListiniRepository()
    return _build_results_response(repository.list_versioni(listino_id))


# Scopo: Restituisce il dettaglio singolo di una versione del listino.
def fn_get_versione(listino_id: int, versione_id: int) -> dict[str, object]:
    function_name = "vendite.listini_service.fn_get_versione"
    return _get_versione_or_raise(listino_id, versione_id, function_name=function_name)


# Scopo: Crea una nuova versione in stato iniziale BOZZA e restituisce il dettaglio.
def fn_create_versione(listino_id: int, payload: dict[str, Any]) -> dict[str, object]:
    function_name = "vendite.listini_service.fn_create_versione"
    _get_listino_or_raise(listino_id, function_name=function_name)
    data = _extract_versione_payload(payload, for_update=False, function_name=function_name)
    repository = ListiniRepository()
    try:
        versione_id = repository.create_versione(listino_id, data)
    except IntegrityError as exc:
        _translate_integrity_error(exc, function_name=function_name, entity="versione")
    return fn_get_versione(listino_id, versione_id)


# Scopo: Aggiorna la versione sui soli campi modificabili e restituisce il dettaglio.
def fn_update_versione(listino_id: int, versione_id: int, payload: dict[str, Any]) -> dict[str, object]:
    function_name = "vendite.listini_service.fn_update_versione"
    versione = _get_versione_or_raise(listino_id, versione_id, function_name=function_name)
    data = _extract_versione_payload(payload, for_update=True, function_name=function_name)
    ErrorManager.require(
        bool(data),
        code="E_VENDITE_VALIDATION",
        message="Payload versione listino non valido.",
        detail="Nessun campo aggiornabile presente nel payload.",
        context={"allowed_nullable_fields": sorted(_VERSIONE_NULLABLE_FIELDS)},
        function_name=function_name,
        log_to_db=True,
    )
    _assert_versione_patch_allowed(versione, data, function_name=function_name)
    repository = ListiniRepository()
    try:
        updated = repository.update_versione(listino_id, versione_id, data)
    except IntegrityError as exc:
        _translate_integrity_error(exc, function_name=function_name, entity="versione")
    ErrorManager.require(
        updated,
        code="E_VENDITE_LISTINO_VERSIONE_NOT_FOUND",
        message="Versione listino non trovata.",
        detail=f"Nessuna versione id={versione_id} per listino id={listino_id}.",
        context={"listino_id": listino_id, "versione_id": versione_id},
        function_name=function_name,
        log_to_db=False,
    )
    return fn_get_versione(listino_id, versione_id)


# Scopo: Clona una versione esistente in una nuova versione BOZZA dello stesso listino.
#        Workflow operativo "cambio prezzi": l'utente clona V001 in V002, modifica
#        i prezzi che cambiano, attiva V002. La versione sorgente non viene toccata.
#        Vincolo D2 (decisioni listini v2): la nuova versione puo' essere retroattiva
#        ma valido_dal non puo' essere inferiore al valido_dal della sorgente. Le
#        retroattive sui documenti gia` emessi richiedono il dominio rettifiche DB-L4.
def fn_clone_versione(
    listino_id: int,
    src_versione_id: int,
    payload: dict[str, Any],
) -> dict[str, object]:
    function_name = "vendite.listini_service.fn_clone_versione"
    src_versione = _get_versione_or_raise(listino_id, src_versione_id, function_name=function_name)

    # Riusa la pipeline di validazione per_create della versione: garantisce
    # codice_versione+valido_dal obbligatori, valido_al > valido_dal.
    # Filtra i campi a quelli effettivamente clonabili (esclude attivo/meta dal clone).
    target_data = _extract_versione_payload(payload, for_update=False, function_name=function_name)
    clonable_fields = {"codice_versione", "valido_dal", "valido_al"}
    target_data = {key: value for key, value in target_data.items() if key in clonable_fields}

    # Vincolo D2: la nuova decorrenza non puo' essere inferiore alla decorrenza
    # della sorgente. Cio' protegge da cloni "indietro nel tempo" che precederebbero
    # l'inizio della versione che si vuole sostituire.
    src_valido_dal = src_versione.get("valido_dal")
    target_valido_dal = target_data.get("valido_dal")
    assert isinstance(src_valido_dal, date)
    assert isinstance(target_valido_dal, date)
    ErrorManager.require(
        target_valido_dal >= src_valido_dal,
        code="E_VENDITE_VALIDATION",
        message="Data di decorrenza non valida.",
        detail=(
            f"valido_dal della nuova versione ({target_valido_dal.isoformat()}) "
            f"non puo' essere inferiore alla decorrenza della versione sorgente "
            f"({src_valido_dal.isoformat()})."
        ),
        context={
            "src_versione_id": src_versione_id,
            "src_valido_dal": src_valido_dal,
            "target_valido_dal": target_valido_dal,
        },
        function_name=function_name,
        log_to_db=True,
    )

    repository = ListiniRepository()
    try:
        with transaction.atomic():
            target_versione_id = repository.clone_versione(
                listino_id=listino_id,
                src_versione_id=src_versione_id,
                target_data=target_data,
            )
    except IntegrityError as exc:
        _translate_integrity_error(exc, function_name=function_name, entity="versione")

    return fn_get_versione(listino_id, target_versione_id)


# Scopo: Elimina una versione in stato BOZZA con tutte le sue righe (cascata).
#        Decisione O2 (sviluppo-listini-v2): solo BOZZA e' eliminabile, perche'
#        non e' mai stata visibile al pricing e nessuno snapshot e' propagato.
#        Versioni ATTIVA/CHIUSA sono storiche e immutabili.
def fn_delete_versione(listino_id: int, versione_id: int) -> dict[str, object]:
    function_name = "vendite.listini_service.fn_delete_versione"
    versione = _get_versione_or_raise(listino_id, versione_id, function_name=function_name)
    stato = str(versione["stato"])
    ErrorManager.require(
        stato == "BOZZA",
        code="E_VENDITE_VALIDATION",
        message="Eliminazione versione non consentita.",
        detail=(
            "Solo le versioni in stato BOZZA possono essere eliminate. "
            f"Stato corrente: {stato}."
        ),
        context={"versione_id": versione_id, "stato": stato},
        function_name=function_name,
        log_to_db=True,
    )
    repository = ListiniRepository()
    try:
        with transaction.atomic():
            deleted = repository.delete_versione(listino_id, versione_id)
    except IntegrityError as exc:
        _translate_integrity_error(exc, function_name=function_name, entity="versione")
    ErrorManager.require(
        deleted,
        code="E_VENDITE_LISTINO_VERSIONE_NOT_FOUND",
        message="Versione listino non trovata.",
        detail=f"Nessuna versione id={versione_id} per listino id={listino_id}.",
        context={"listino_id": listino_id, "versione_id": versione_id},
        function_name=function_name,
        log_to_db=False,
    )
    return {"deleted": True, "id": versione_id}


# Scopo: Pianifica le conseguenze di una transizione di stato versione.
#        Per BOZZA -> ATTIVA calcola l'elenco delle versioni precedenti da chiudere
#        e la nuova valido_al. Per altre transizioni torna ([], None).
#
#        Guard critico (CHK constraint vendite.chk_listini_versioni_date richiede
#        valido_al > valido_dal STRETTAMENTE): se una precedente ha
#        valido_dal >= nuova.valido_dal - 1 (cioe' gap < 2 giorni), l'autoclose
#        produrrebbe valido_al <= valido_dal e violerebbe il CHECK. Solleviamo
#        un errore esplicito invece di lasciar scattare un IntegrityError generico.
def _plan_versione_state_change(
    *,
    repository: "ListiniRepository",
    versione: dict[str, Any],
    nuovo_stato: str,
    listino_id: int,
    versione_id: int,
    function_name: str,
) -> tuple[list[dict[str, Any]], date | None]:
    if nuovo_stato != "ATTIVA":
        return [], None

    ErrorManager.require(
        bool(versione["attivo"]),
        code="E_VENDITE_VALIDATION",
        message="Transizione stato versione non valida.",
        detail="Una versione inattiva non puo' essere attivata.",
        context={"versione_id": versione_id},
        function_name=function_name,
        log_to_db=True,
    )
    righe_count = repository.count_active_righe_versione(versione_id)
    ErrorManager.require(
        righe_count > 0,
        code="E_VENDITE_VALIDATION",
        message="Transizione stato versione non valida.",
        detail="Una versione BOZZA deve avere almeno una riga attiva prima di diventare ATTIVA.",
        context={"versione_id": versione_id, "righe_count": righe_count},
        function_name=function_name,
        log_to_db=True,
    )

    nuova_valido_dal = versione.get("valido_dal")
    assert isinstance(nuova_valido_dal, date)
    candidates = repository.find_versioni_per_autoclose(
        listino_id=listino_id,
        exclude_versione_id=versione_id,
        nuova_valido_dal=nuova_valido_dal,
    )
    nuova_valido_al = nuova_valido_dal - timedelta(days=1)

    # Guard CHK: per ogni precedente, l'autoclose deve produrre valido_al > valido_dal.
    # nuova_valido_al = nuova_valido_dal - 1, quindi serve precedente.valido_dal < nuova_valido_dal - 1.
    for row in candidates:
        prec_valido_dal = row.get("valido_dal")
        assert isinstance(prec_valido_dal, date)
        ErrorManager.require(
            nuova_valido_al > prec_valido_dal,
            code="E_VENDITE_VALIDATION",
            message="Autoclose versione precedente non possibile.",
            detail=(
                f"La versione precedente '{row.get('codice_versione')}' inizia il "
                f"{prec_valido_dal.isoformat()}: per chiuderla all'attivazione "
                f"servirebbe valido_al={nuova_valido_al.isoformat()}, ma il vincolo "
                f"valido_al > valido_dal lo impedisce. La nuova versione deve "
                f"iniziare almeno 2 giorni dopo l'inizio della precedente "
                f"(decorrenza minima ammessa: {(prec_valido_dal + timedelta(days=2)).isoformat()})."
            ),
            context={
                "precedente_id": int(row["id"]),
                "precedente_valido_dal": prec_valido_dal,
                "nuova_valido_dal": nuova_valido_dal,
            },
            function_name=function_name,
            log_to_db=True,
        )

    return candidates, nuova_valido_al


# Scopo: Cambia stato versione con guard su transizioni e presenza righe in attivazione.
#        Decisione D3 (sviluppo-listini-v2): la transizione BOZZA -> ATTIVA innesca
#        l'auto-close delle versioni precedenti dello stesso listino (versioni in
#        stato ATTIVA + attivo con valido_dal < nuova.valido_dal e che si sovrappongono
#        al nuovo intervallo). La chiusura avviene nella stessa transazione DB:
#        prima si imposta valido_al = nuova.valido_dal - 1 sulle precedenti, poi si
#        attiva la nuova. Questo ordine e' necessario per non urtare il vincolo
#        ex_listini_versioni_no_overlap (GIST exclusion).
#
#        Modalita` dry_run: se payload contiene `dry_run=true`, la funzione esegue
#        tutte le validazioni e calcola le versioni che verrebbero auto-chiuse, ma
#        NON tocca il DB. Restituisce un envelope di preview per il dialog UI.
def fn_change_versione_state(listino_id: int, versione_id: int, payload: dict[str, Any]) -> dict[str, object]:
    function_name = "vendite.listini_service.fn_change_versione_state"
    versione = _get_versione_or_raise(listino_id, versione_id, function_name=function_name)
    nuovo_stato = _extract_enum_string(
        payload,
        "stato",
        function_name=function_name,
        allowed_values=_STATI_VERSIONE_VALIDI,
        nullable=False,
        message="Payload stato versione non valido.",
    )
    ErrorManager.require(
        nuovo_stato not in {_MISSING, None},
        code="E_VENDITE_VALIDATION",
        message="Payload stato versione non valido.",
        detail="stato obbligatorio.",
        context={"field": "stato"},
        function_name=function_name,
        log_to_db=True,
    )
    assert isinstance(nuovo_stato, str)
    # dry_run strict: accetta solo bool True esplicito (no stringhe truthy)
    dry_run = payload.get("dry_run", False) is True
    _validate_versione_state_transition(versione, nuovo_stato, function_name=function_name)

    repository = ListiniRepository()
    if str(versione["stato"]) == nuovo_stato:
        return fn_get_versione(listino_id, versione_id)

    # Pianificazione transizione: per BOZZA -> ATTIVA calcola anche l'autoclose
    # delle precedenti. Restituisce (autoclose_candidates, nuova_valido_al).
    # Per ATTIVA -> CHIUSA torna ([], None).
    autoclose_candidates, nuova_valido_al = _plan_versione_state_change(
        repository=repository,
        versione=versione,
        nuovo_stato=nuovo_stato,
        listino_id=listino_id,
        versione_id=versione_id,
        function_name=function_name,
    )

    # Modalita` preview: niente UPDATE, restituisco la sintesi delle conseguenze.
    if dry_run:
        return {
            "dry_run": True,
            "versione_id": versione_id,
            "nuovo_stato": nuovo_stato,
            "auto_close": [
                {
                    "id": int(row["id"]),
                    "codice_versione": row.get("codice_versione"),
                    "valido_dal": row.get("valido_dal"),
                    "valido_al_prima": row.get("valido_al"),
                    "valido_al_dopo": nuova_valido_al,
                }
                for row in autoclose_candidates
            ],
        }

    try:
        with transaction.atomic():
            # 1) Auto-close precedenti PRIMA di attivare la nuova: il vincolo
            #    GIST exclusion ex_listini_versioni_no_overlap viene verificato
            #    al COMMIT, ma per chiarezza di intent eseguiamo gli UPDATE in
            #    quest'ordine. Senza l'auto-close, l'UPDATE che attiva la nuova
            #    fallirebbe per overlap con le precedenti aperte.
            if autoclose_candidates and nuova_valido_al is not None:
                for row in autoclose_candidates:
                    repository.set_versione_valido_al(
                        listino_id=listino_id,
                        versione_id=int(row["id"]),
                        valido_al=nuova_valido_al,
                    )

            changed = repository.change_versione_state(listino_id, versione_id, nuovo_stato)
    except IntegrityError as exc:
        _translate_integrity_error(exc, function_name=function_name, entity="versione")
    ErrorManager.require(
        changed,
        code="E_VENDITE_LISTINO_VERSIONE_NOT_FOUND",
        message="Versione listino non trovata.",
        detail=f"Nessuna versione id={versione_id} per listino id={listino_id}.",
        context={"listino_id": listino_id, "versione_id": versione_id},
        function_name=function_name,
        log_to_db=False,
    )
    return fn_get_versione(listino_id, versione_id)


# Scopo: Restituisce la lista paginata righe prezzo della versione con filtri opzionali.
def fn_list_righe(
    listino_id: int,
    versione_id: int,
    *,
    search: str | None = None,
    billing_account_id: int | None = None,
    utility_id: int | None = None,
    attivo: bool | None = True,
    order_by: str = "articolo_descrizione",
    order_dir: str = "asc",
    limit: int = 25,
    offset: int = 0,
) -> tuple[list[dict[str, object]], int]:
    function_name = "vendite.listini_service.fn_list_righe"
    _get_versione_or_raise(listino_id, versione_id, function_name=function_name)
    order_by, order_dir = _validate_righe_order(order_by, order_dir, function_name)
    repository = ListiniRepository()
    return repository.list_righe(
        listino_id,
        versione_id,
        search=search,
        billing_account_id=billing_account_id,
        utility_id=utility_id,
        attivo=attivo,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset,
    )


# Scopo: Crea una nuova riga prezzo dopo validazione articolo/UoM e restituisce il dettaglio.
def fn_create_riga(listino_id: int, versione_id: int, payload: dict[str, Any]) -> dict[str, object]:
    function_name = "vendite.listini_service.fn_create_riga"
    versione = _get_versione_or_raise(listino_id, versione_id, function_name=function_name)
    _assert_versione_bozza_for_riga_op(versione, function_name=function_name)
    data = _extract_riga_payload(payload, for_update=False, function_name=function_name)
    articolo_id = data["articolo_id"]
    uom_id = data["uom_id"]
    assert isinstance(articolo_id, str)
    assert isinstance(uom_id, int)
    _validate_riga_articolo_uom(articolo_id, uom_id, function_name=function_name)

    repository = ListiniRepository()
    try:
        riga_id = repository.create_riga(versione_id, data)
    except IntegrityError as exc:
        _translate_integrity_error(exc, function_name=function_name, entity="riga")
    return _get_riga_or_raise(listino_id, versione_id, riga_id, function_name=function_name)


# Scopo: Aggiorna una riga prezzo mantenendo coerenza articolo/UoM quando necessario.
def fn_update_riga(listino_id: int, versione_id: int, riga_id: int, payload: dict[str, Any]) -> dict[str, object]:
    function_name = "vendite.listini_service.fn_update_riga"
    versione = _get_versione_or_raise(listino_id, versione_id, function_name=function_name)
    _assert_versione_bozza_for_riga_op(versione, function_name=function_name)
    current = _get_riga_or_raise(listino_id, versione_id, riga_id, function_name=function_name)
    data = _extract_riga_payload(payload, for_update=True, function_name=function_name)
    ErrorManager.require(
        bool(data),
        code="E_VENDITE_VALIDATION",
        message="Payload riga listino non valido.",
        detail="Nessun campo aggiornabile presente nel payload.",
        context={"allowed_nullable_fields": sorted(_RIGA_NULLABLE_FIELDS)},
        function_name=function_name,
        log_to_db=True,
    )
    articolo_id = str(current["articolo_id"])
    uom_id = int(current["uom_id"])
    _validate_riga_articolo_uom(articolo_id, uom_id, function_name=function_name)
    repository = ListiniRepository()
    try:
        updated = repository.update_riga(listino_id, versione_id, riga_id, data)
    except IntegrityError as exc:
        _translate_integrity_error(exc, function_name=function_name, entity="riga")
    ErrorManager.require(
        updated,
        code="E_VENDITE_LISTINO_RIGA_NOT_FOUND",
        message="Riga listino non trovata.",
        detail=f"Nessuna riga id={riga_id} per versione id={versione_id}.",
        context={"listino_id": listino_id, "versione_id": versione_id, "riga_id": riga_id},
        function_name=function_name,
        log_to_db=False,
    )
    return _get_riga_or_raise(listino_id, versione_id, riga_id, function_name=function_name)


# Scopo: Elimina una riga prezzo esistente restituendo esito uniforme.
def fn_delete_riga(listino_id: int, versione_id: int, riga_id: int) -> dict[str, object]:
    function_name = "vendite.listini_service.fn_delete_riga"
    versione = _get_versione_or_raise(listino_id, versione_id, function_name=function_name)
    _assert_versione_bozza_for_riga_op(versione, function_name=function_name)
    _get_riga_or_raise(listino_id, versione_id, riga_id, function_name=function_name)
    repository = ListiniRepository()
    deleted = repository.delete_riga(listino_id, versione_id, riga_id)
    ErrorManager.require(
        deleted,
        code="E_VENDITE_LISTINO_RIGA_NOT_FOUND",
        message="Riga listino non trovata.",
        detail=f"Nessuna riga id={riga_id} per versione id={versione_id}.",
        context={"listino_id": listino_id, "versione_id": versione_id, "riga_id": riga_id},
        function_name=function_name,
        log_to_db=False,
    )
    return {"deleted": True, "id": riga_id}


# --- N2: Alert scadenze versioni ---

_ALERT_GIORNI_DEFAULT = 15
_ALERT_GIORNI_MIN = 1
_ALERT_GIORNI_MAX = 365


# Scopo: Restituisce lista versioni ATTIVE in scadenza entro N giorni senza successore.
def fn_alert_scadenze(giorni: int | None = None) -> dict[str, object]:
    function_name = "vendite.listini_service.fn_alert_scadenze"
    if giorni is None:
        giorni = _ALERT_GIORNI_DEFAULT
    ErrorManager.require(
        _ALERT_GIORNI_MIN <= giorni <= _ALERT_GIORNI_MAX,
        code="E_VENDITE_VALIDATION",
        message="Parametro giorni non valido.",
        detail=f"giorni deve essere tra {_ALERT_GIORNI_MIN} e {_ALERT_GIORNI_MAX}.",
        context={"giorni": giorni},
        function_name=function_name,
        log_to_db=False,
    )
    repository = ListiniRepository()
    results = repository.listini_in_scadenza(giorni)
    return {"results": results, "count": len(results), "giorni": giorni}


# --- N6: Rettifica controllata su riga ATTIVA non propagata ---


# Scopo: Consente la modifica del prezzo di una riga in versione ATTIVA solo se
#        la riga non e` mai stata propagata in commesse o attivita` fatturabili.
#        Lock pessimistico FOR UPDATE + check non-propagazione nella stessa transazione.
#        Motivo obbligatorio. Audit in meta.rettifiche_controllate[].
def fn_rettifica_controllata_riga(
    listino_id: int,
    versione_id: int,
    riga_id: int,
    payload: dict[str, Any],
) -> dict[str, object]:
    function_name = "vendite.listini_service.fn_rettifica_controllata_riga"

    # --- Guard 1 (applicativa): versione esiste e non e` in BOZZA ---
    # Lo stato BOZZA e` monotono in ingresso (una versione parte BOZZA e va ad
    # ATTIVA, non torna indietro) quindi non soggetto a drift. E` safe usarlo
    # come discriminante applicativo: su BOZZA si usa il PATCH ordinario, non la
    # rettifica controllata.
    versione = _get_versione_or_raise(listino_id, versione_id, function_name=function_name)
    ErrorManager.require(
        str(versione["stato"]) != "BOZZA",
        code="E_VENDITE_VALIDATION",
        message="Rettifica controllata non ammessa su versioni BOZZA.",
        detail="Per versioni BOZZA usare il PATCH ordinario sulla riga.",
        context={"versione_id": versione_id, "stato": versione["stato"]},
        function_name=function_name,
        log_to_db=True,
    )

    # --- Guard 2 (operativa): la versione deve essere attiva oggi ---
    # Il check si basa su validita` (valido_dal <= today <= valido_al), non
    # sullo `stato` persistito: lo stato e` solo flag informativo eventualmente
    # stantio (principio fail-safe: data = fonte di verita` operativa).
    today = date.today()
    valido_dal = versione.get("valido_dal")
    valido_al = versione.get("valido_al")
    is_operativa_oggi = (
        isinstance(valido_dal, date)
        and valido_dal <= today
        and (valido_al is None or (isinstance(valido_al, date) and valido_al >= today))
    )
    ErrorManager.require(
        is_operativa_oggi,
        code="E_VENDITE_VALIDATION",
        message="Rettifica controllata ammessa solo su versioni operativamente attive oggi.",
        detail=(
            f"La versione non e` operativa alla data odierna. "
            f"valido_dal={valido_dal}, valido_al={valido_al}. "
            f"Per versioni scadute, creare una nuova versione con prezzi corretti."
        ),
        context={
            "versione_id": versione_id,
            "valido_dal": valido_dal,
            "valido_al": valido_al,
            "today": today,
        },
        function_name=function_name,
        log_to_db=True,
    )

    # --- Guard: riga esiste ---
    riga = _get_riga_or_raise(listino_id, versione_id, riga_id, function_name=function_name)

    # --- Parsing payload ---
    raw_prezzo = payload.get("prezzo")
    ErrorManager.require(
        raw_prezzo is not None,
        code="E_VENDITE_VALIDATION",
        message="Parametro obbligatorio mancante.",
        detail="prezzo e` obbligatorio.",
        context={"field": "prezzo"},
        function_name=function_name,
        log_to_db=True,
    )
    try:
        nuovo_prezzo = Decimal(str(raw_prezzo))
    except (InvalidOperation, TypeError, ValueError):
        ErrorManager.raise_error(
            code="E_VENDITE_VALIDATION",
            message="Prezzo non valido.",
            detail=f"prezzo deve essere numerico, ricevuto: {raw_prezzo!r}.",
            context={"field": "prezzo"},
            function_name=function_name,
            log_to_db=True,
        )
    assert isinstance(nuovo_prezzo, Decimal)

    ErrorManager.require(
        nuovo_prezzo > 0,
        code="E_VENDITE_VALIDATION",
        message="Prezzo non valido.",
        detail="Il prezzo deve essere maggiore di zero.",
        context={"prezzo": str(nuovo_prezzo)},
        function_name=function_name,
        log_to_db=True,
    )

    motivo = payload.get("motivo")
    ErrorManager.require(
        motivo and isinstance(motivo, str) and motivo.strip(),
        code="E_VENDITE_VALIDATION",
        message="Motivo obbligatorio.",
        detail="Il campo motivo e` obbligatorio per la rettifica controllata.",
        context={"field": "motivo"},
        function_name=function_name,
        log_to_db=True,
    )
    assert isinstance(motivo, str)
    motivo = motivo.strip()
    ErrorManager.require(
        len(motivo) <= 500,
        code="E_VENDITE_VALIDATION",
        message="Motivo troppo lungo.",
        detail="Massimo 500 caratteri.",
        context={"field": "motivo", "length": len(motivo)},
        function_name=function_name,
        log_to_db=False,
    )

    repository = ListiniRepository()

    # --- Livello 1+2: lock pessimistico + check non-propagazione in transazione ---
    with transaction.atomic():
        locked = repository.lock_riga_for_update(versione_id, riga_id)
        ErrorManager.require(
            locked,
            code="E_VENDITE_LISTINO_RIGA_NOT_FOUND",
            message="Riga non trovata.",
            detail=f"Riga id={riga_id} non trovata nella versione id={versione_id}.",
            context={"riga_id": riga_id, "versione_id": versione_id},
            function_name=function_name,
            log_to_db=False,
        )

        propagata = repository.check_riga_propagata(riga_id)
        ErrorManager.require(
            not propagata,
            code="E_VENDITE_RIGA_GIA_PROPAGATA",
            message="Rettifica bloccata: riga gia` propagata.",
            detail=(
                "La riga e` stata usata in almeno una commessa o attivita` fatturabile. "
                "Per correggere il prezzo, clonare la versione."
            ),
            context={"riga_id": riga_id},
            function_name=function_name,
            log_to_db=True,
        )

        # --- Audit in meta ---
        meta_corrente = _parse_meta_json(riga.get("meta"))
        rettifiche = list(meta_corrente.get("rettifiche_controllate", []))
        rettifiche.append({
            "data": datetime.now(timezone.utc).isoformat(),
            "prezzo_precedente": str(riga["prezzo"]),
            "prezzo_nuovo": str(nuovo_prezzo),
            "motivo": motivo,
        })
        meta_corrente["rettifiche_controllate"] = rettifiche

        repository.update_riga_prezzo_rettifica(
            riga_id=riga_id,
            nuovo_prezzo=str(nuovo_prezzo),
            meta_aggiornata=meta_corrente,
        )

    return {
        "riga_id": riga_id,
        "prezzo_precedente": str(riga["prezzo"]),
        "prezzo_nuovo": str(nuovo_prezzo),
        "motivo": motivo,
    }


# --- N8a: Variazione percentuale massa su versione BOZZA ---

_VARIAZIONE_PCT_MIN = Decimal("-99")
_VARIAZIONE_PCT_MAX = Decimal("1000")
_ARROT_DECIMALI_MIN = 0
_ARROT_DECIMALI_MAX = 10
_ARROT_DECIMALI_DEFAULT = 4


# Scopo: Applica una variazione percentuale ai prezzi delle righe attive di una versione
#        BOZZA. Con dry_run=True restituisce la preview senza applicare modifiche.
#        Guard: solo BOZZA, range percentuale ammesso, arrotondamento 0-10.
def fn_applica_variazione_percentuale(
    listino_id: int,
    versione_id: int,
    payload: dict[str, Any],
) -> dict[str, object]:
    function_name = "vendite.listini_service.fn_applica_variazione_percentuale"

    # --- Guard: versione esiste e stato BOZZA ---
    versione = _get_versione_or_raise(listino_id, versione_id, function_name=function_name)
    _assert_versione_bozza_for_riga_op(versione, function_name=function_name)

    # --- Parsing e validazione payload ---
    raw_pct = payload.get("variazione_percentuale")
    ErrorManager.require(
        raw_pct is not None,
        code="E_VENDITE_VALIDATION",
        message="Parametro obbligatorio mancante.",
        detail="variazione_percentuale e` obbligatoria.",
        context={"field": "variazione_percentuale"},
        function_name=function_name,
        log_to_db=True,
    )
    try:
        variazione_pct = Decimal(str(raw_pct))
    except (InvalidOperation, TypeError, ValueError):
        ErrorManager.raise_error(
            code="E_VENDITE_VALIDATION",
            message="Parametro non valido.",
            detail=f"variazione_percentuale deve essere un numero, ricevuto: {raw_pct!r}.",
            context={"field": "variazione_percentuale", "value": str(raw_pct)},
            function_name=function_name,
            log_to_db=True,
        )
    assert isinstance(variazione_pct, Decimal)

    ErrorManager.require(
        _VARIAZIONE_PCT_MIN <= variazione_pct <= _VARIAZIONE_PCT_MAX,
        code="E_VENDITE_VALIDATION",
        message="Variazione percentuale fuori dal range ammesso.",
        detail=(
            f"variazione_percentuale deve essere tra {_VARIAZIONE_PCT_MIN} e "
            f"{_VARIAZIONE_PCT_MAX}. Ricevuto: {variazione_pct}."
        ),
        context={"variazione_percentuale": str(variazione_pct)},
        function_name=function_name,
        log_to_db=True,
    )

    raw_dec = payload.get("arrotondamento_decimali", _ARROT_DECIMALI_DEFAULT)
    try:
        arrotondamento_decimali = int(raw_dec)
    except (TypeError, ValueError):
        ErrorManager.raise_error(
            code="E_VENDITE_VALIDATION",
            message="Parametro non valido.",
            detail=f"arrotondamento_decimali deve essere intero, ricevuto: {raw_dec!r}.",
            context={"field": "arrotondamento_decimali", "value": str(raw_dec)},
            function_name=function_name,
            log_to_db=True,
        )
    assert isinstance(arrotondamento_decimali, int)

    ErrorManager.require(
        _ARROT_DECIMALI_MIN <= arrotondamento_decimali <= _ARROT_DECIMALI_MAX,
        code="E_VENDITE_VALIDATION",
        message="Arrotondamento decimali fuori dal range ammesso.",
        detail=(
            f"arrotondamento_decimali deve essere tra {_ARROT_DECIMALI_MIN} e "
            f"{_ARROT_DECIMALI_MAX}. Ricevuto: {arrotondamento_decimali}."
        ),
        context={"arrotondamento_decimali": arrotondamento_decimali},
        function_name=function_name,
        log_to_db=True,
    )

    # --- Filtro articoli (opzionale) ---
    raw_filtro = payload.get("filtro_articoli")
    filtro_articoli: list[UUID] | None = None
    if raw_filtro is not None:
        ErrorManager.require(
            isinstance(raw_filtro, list),
            code="E_VENDITE_VALIDATION",
            message="Parametro non valido.",
            detail="filtro_articoli deve essere un array di UUID o null.",
            context={"field": "filtro_articoli"},
            function_name=function_name,
            log_to_db=True,
        )
        assert isinstance(raw_filtro, list)
        try:
            filtro_articoli = [UUID(str(x)) for x in raw_filtro]
        except (ValueError, TypeError):
            ErrorManager.raise_error(
                code="E_VENDITE_VALIDATION",
                message="Parametro non valido.",
                detail="filtro_articoli contiene valori non UUID.",
                context={"field": "filtro_articoli"},
                function_name=function_name,
                log_to_db=True,
            )

    dry_run = bool(payload.get("dry_run", False))

    # --- Esecuzione ---
    repository = ListiniRepository()
    filtro_str = [str(a) for a in filtro_articoli] if filtro_articoli else None

    if dry_run:
        count, preview = repository.applica_variazione_percentuale(
            versione_id=versione_id,
            variazione_pct=str(variazione_pct),
            arrotondamento_decimali=arrotondamento_decimali,
            filtro_articoli=filtro_str,
            dry_run=True,
        )
        return {
            "dry_run": True,
            "righe_coinvolte": count,
            "preview": preview,
            "variazione_percentuale": str(variazione_pct),
            "arrotondamento_decimali": arrotondamento_decimali,
        }

    with transaction.atomic():
        count, _ = repository.applica_variazione_percentuale(
            versione_id=versione_id,
            variazione_pct=str(variazione_pct),
            arrotondamento_decimali=arrotondamento_decimali,
            filtro_articoli=filtro_str,
            dry_run=False,
        )
        # Audit sulla meta della versione
        meta_versione = _parse_meta_json(versione.get("meta"))
        variazioni_pct = list(meta_versione.get("variazioni_percentuali", []))
        variazioni_pct.append({
            "data": datetime.now(timezone.utc).isoformat(),
            "variazione_percentuale": str(variazione_pct),
            "arrotondamento_decimali": arrotondamento_decimali,
            "righe_aggiornate": count,
            "filtro_articoli": filtro_str,
        })
        meta_versione["variazioni_percentuali"] = variazioni_pct
        repository.update_versione(
            listino_id=listino_id,
            versione_id=versione_id,
            data={"meta": meta_versione},
        )

    return {
        "righe_aggiornate": count,
        "variazione_percentuale": str(variazione_pct),
        "arrotondamento_decimali": arrotondamento_decimali,
    }
