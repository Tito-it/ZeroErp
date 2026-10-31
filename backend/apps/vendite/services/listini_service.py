# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Facade applicativa per il sottodominio vendite/listini.
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, NoReturn
from uuid import UUID

from django.db import DatabaseError, IntegrityError, transaction

from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.services.error_manager import ErrorManager
from apps.core.services.list_helpers import validate_order_params
from apps.core.services.payload_helpers import (
    MISSING as _MISSING,
    MissingType as _MissingType,
    PayloadValidator,
    map_integrity_error,
)
from apps.vendite.db.listini_repository import (
    LISTINI_ORDER_COLUMNS,
    LISTINO_CREATE_COLUMNS,
    LISTINO_UPDATE_COLUMNS,
    RIGA_CREATE_COLUMNS,
    RIGA_UPDATE_COLUMNS,
    RIGHE_ORDER_COLUMNS,
    STATO_VERSIONE_ATTIVA,
    VERSIONE_CREATE_COLUMNS,
    VERSIONE_UPDATE_COLUMNS,
    VERSIONI_ORDER_COLUMNS,
    ListiniRepository,
)

_ORDER_BY_VALIDI: frozenset[str] = frozenset(LISTINI_ORDER_COLUMNS.keys())
_RIGHE_ORDER_BY_VALIDI: frozenset[str] = frozenset(RIGHE_ORDER_COLUMNS.keys())
_VERSIONI_ORDER_BY_VALIDI: frozenset[str] = frozenset(VERSIONI_ORDER_COLUMNS.keys())
_LISTINO_NULLABLE_FIELDS: frozenset[str] = frozenset({"meta"})
_VERSIONE_NULLABLE_FIELDS: frozenset[str] = frozenset({"valido_al", "meta"})
_RIGA_NULLABLE_FIELDS: frozenset[str] = frozenset(
    {"meta"}
)
_LISTINO_CREATE_ALLOWED_KEYS: frozenset[str] = frozenset(LISTINO_CREATE_COLUMNS.keys())
_LISTINO_UPDATE_ALLOWED_KEYS: frozenset[str] = frozenset(LISTINO_UPDATE_COLUMNS.keys())
_VERSIONE_CREATE_ALLOWED_KEYS: frozenset[str] = frozenset(VERSIONE_CREATE_COLUMNS.keys())
_VERSIONE_UPDATE_ALLOWED_KEYS: frozenset[str] = frozenset(VERSIONE_UPDATE_COLUMNS.keys())
# I parametri del verbo `vendite.fn_clona_versione_listino`, oltre la sorgente.
_VERSIONE_CLONE_ALLOWED_KEYS: frozenset[str] = frozenset({"codice_versione", "valido_dal", "valido_al"})
_RIGA_CREATE_ALLOWED_KEYS: frozenset[str] = frozenset(RIGA_CREATE_COLUMNS.keys())
_RIGA_UPDATE_ALLOWED_KEYS: frozenset[str] = frozenset(RIGA_UPDATE_COLUMNS.keys())

# Codici errore applicativi (registrati in core.error_policies). Costanti
# modulo-level per simmetria col pattern di `contratti_service.py` e per
# evitare stringhe magic nelle mappe `map_integrity_error`.
E_VENDITE_VALIDATION = "E_VENDITE_VALIDATION"
E_VENDITE_DUPLICATO = "E_VENDITE_DUPLICATO"
E_VENDITE_FK = "E_VENDITE_FK"
E_VENDITE_LISTINO_VERSIONE_OVERLAP = "E_VENDITE_LISTINO_VERSIONE_OVERLAP"
E_VENDITE_LISTINO_RIGA_COMP_OVERLAP = "E_VENDITE_LISTINO_RIGA_COMP_OVERLAP"
E_LISTINO_RIGA_COMP_BOM_INCOERENTE = "E_LISTINO_RIGA_COMP_BOM_INCOERENTE"

# Validator modulo-level: log_to_db=True per telemetria pipeline vendite,
# function_name override per-chiamata (riflette il metodo service specifico).
# Ref: apps/core/services/payload_helpers.py (V6-B1/V6-B2).
_V = PayloadValidator(
    validation_code=E_VENDITE_VALIDATION,
    log_to_db=True,
)


# Scopo: Valida ordinamento lista listini contro whitelist locale.
def _validate_order(order_by: str, order_dir: str | None, function_name: str) -> tuple[str, str | None]:
    return validate_order_params(
        order_by,
        order_dir,
        allowed_columns=_ORDER_BY_VALIDI,
        error_code="E_VENDITE_VALIDATION",
        # `nullable`: direzione assente -> `None` e decide il default del
        # repository (`parse_list_params` non inventa piu' "asc", 2026-09-26).
        nullable=True,
        function_name=function_name,
    )


# Scopo: Valida ordinamento lista righe listino contro whitelist locale.
def _validate_righe_order(order_by: str, order_dir: str | None, function_name: str) -> tuple[str, str | None]:
    return validate_order_params(
        order_by,
        order_dir,
        allowed_columns=_RIGHE_ORDER_BY_VALIDI,
        error_code="E_VENDITE_VALIDATION",
        # `nullable`: direzione assente -> `None` e decide il default del
        # repository (`parse_list_params` non inventa piu' "asc", 2026-09-26).
        nullable=True,
        function_name=function_name,
    )


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
    return _V.extract_optional_string(
        payload,
        key,
        nullable=nullable,
        message=message,
        function_name=function_name,
        log_to_db=True,
    )


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
    assert isinstance(value, bool)
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
    assert isinstance(value, str)
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


# Scopo: Traduce i vincoli DB del sottodominio listini in errori applicativi
#        parlanti via il building block `map_integrity_error` (catalogo BB
#        backend §Services). Codici differenziati per categoria di constraint:
#        UNIQUE → E_VENDITE_DUPLICATO (409), FK → E_VENDITE_FK (400),
#        CHECK → E_VENDITE_VALIDATION (400), overlap versioni →
#        E_VENDITE_LISTINO_VERSIONE_OVERLAP (409, pattern simmetrico a
#        E_VENDITE_PROMO_OVERLAP / E_CONTRATTO_OVERLAP_ESISTENTE), temporal FK
#        coerenza BoM (PG18) → E_LISTINO_RIGA_COMP_BOM_INCOERENTE (400,
#        sostituisce guard 6 trigger rimosso con migration 20260514-13).
def _translate_integrity_error(exc: IntegrityError, *, function_name: str, entity: str) -> NoReturn:
    map_integrity_error(
        exc,
        unique_constraints={
            "uq_listini_codice": (
                E_VENDITE_DUPLICATO,
                "Codice listino duplicato: esiste gia' un listino con lo stesso codice.",
                "codice",
            ),
            "uq_listini_versioni_listino_codice": (
                E_VENDITE_DUPLICATO,
                "Codice versione duplicato per questo listino.",
                "codice_versione",
            ),
            "uq_listini_righe_key_attiva": (
                E_VENDITE_DUPLICATO,
                "Riga prezzo duplicata: esiste gia' una riga attiva con lo stesso articolo/UoM/perimetro.",
            ),
            # EXCLUDE GIST con WHERE attivo+stato=ATTIVA: non migrabile a temporal
            # UNIQUE (vedi piano-miglioramenti-db-pg18.md §3.4). Match nominale
            # comunque tramite la mappa unique_constraints (map_integrity_error
            # cerca il nome nel msg dell'eccezione, indipendentemente dal tipo).
            "ex_listini_versioni_no_overlap": (
                E_VENDITE_LISTINO_VERSIONE_OVERLAP,
                # Allineato a error_policies.E_VENDITE_LISTINO_VERSIONE_OVERLAP.user_message:
                # error_translator preferisce ServiceError.message su policy.user_message,
                # quindi i due testi DEVONO coincidere per UX consistente.
                "Esiste gia' una versione ATTIVA sovrapposta per il listino. "
                "Chiudi la vecchia (valido_al = nuova_valido_dal - 1) e poi "
                "attiva la nuova: la nuova decorrenza deve essere almeno 1 "
                "giorno dopo l'inizio della precedente.",
            ),
            # EXCLUDE GIST parziale WHERE attivo=TRUE (ripristino enforcement
            # 2026-06-02, migration 20260602-01; governato dal framework
            # automazione_overlap). Blocca due righe bundle ATTIVE sovrapposte
            # sullo stesso (versione, padre, componente). Match nominale via
            # map_integrity_error (cerca il nome nel msg, qualsiasi sia il tipo).
            # Pattern simmetrico a E_VENDITE_PROMO_OVERLAP / E_VENDITE_LISTINO_VERSIONE_OVERLAP.
            "ex_listini_righe_comp_no_overlap": (
                E_VENDITE_LISTINO_RIGA_COMP_OVERLAP,
                # Testo allineato a error_policies (error_translator preferisce
                # ServiceError.message su policy.user_message: devono coincidere).
                "Esiste gia' un prezzo bundle attivo sovrapposto per questo "
                "componente nel periodo indicato. Disattiva o chiudi quello "
                "esistente prima di salvare il nuovo prezzo.",
            ),
        },
        fk_constraints={
            "fk_listini_utility": (
                E_VENDITE_FK,
                "Utility non valida: utility_id non corrisponde a nessuna utility in config.utilities.",
            ),
            # Nome generato da PostgreSQL (pattern <table>_<col>_fkey) dalla
            # migration 20260413-05 che usa ADD COLUMN ... REFERENCES senza
            # CONSTRAINT esplicito. Se la migration viene rinominata, aggiornare.
            "listini_tipologia_id_fkey": (
                E_VENDITE_FK,
                "Tipologia listino non valida.",
            ),
            # La periodicita' della riga (G-0-bis): fuori vocabolario e' un
            # dato del form, col campo, come su contratto e offerta.
            "fk_listini_righe_periodicita": (
                E_VENDITE_FK,
                "Periodicità inesistente.",
                "periodicita",
            ),
            # La periodicita' del kit sul listino (D-2-bis (B)): stesso campo.
            "fk_listini_kit_periodicita": (
                E_VENDITE_FK,
                "Periodicità inesistente.",
                "periodicita",
            ),
            # Temporal FK PG18 (migration 20260514-12) — sostituisce il guard
            # trigger di coerenza BoM (guard 6 rimosso con migration 20260514-13).
            "fk_listrighe_comp_articoli_comp_temporal": (
                E_LISTINO_RIGA_COMP_BOM_INCOERENTE,
                "Prezzo bundle riferito a un componente non presente nella "
                "distinta base del padre composito alla data o per l'intervallo richiesto.",
            ),
        },
        check_constraints={
            "chk_listini_righe_prezzo": (
                E_VENDITE_VALIDATION,
                "Prezzo riga non valido: prezzo deve essere >= 0.",
            ),
        },
        fallback_code=E_VENDITE_VALIDATION,
        fallback_message="Violazione vincolo DB su listino.",
        context={"entity": entity, "function": function_name},
    )


# Scopo: Un rifiuto del DB su una versione (verbo dell'attivazione, guard per
#        stato) arriva al client col codice che il DB ha scelto e la sua frase
#        (BB `ErrorManager.raise_from_database_error`): le regole sono del DB
#        dal giro 12 (L-4, L-5), qui si trasporta soltanto.
#        ⛔ Nessun ripiego: un errore senza codice del catalogo (deadlock,
#        timeout, RAISE nudo) torna al middleware com'e', e non diventa un 400
#        «dato errato» sul form.
def _rifiuto_del_db_su_versione(
    exc: DatabaseError, *, message: str, context: dict[str, Any], function_name: str,
) -> NoReturn:
    ErrorManager.raise_from_database_error(
        exc,
        known_markers=(),
        fallback_code=None,
        message=message,
        context=context,
        function_name=function_name,
    )


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

    # ⚠️ Fino al 2026-09-18 la copia locale sollevava `ValueError` su un prezzo
    #    non numerico: il middleware lo traduceva in `E_VALIDATION_INPUT`
    #    generico, non nel codice del dominio. Il BB solleva `E_VENDITE_VALIDATION`.
    prezzo = _V.extract_optional_decimal(
        payload,
        "prezzo",
        function_name=function_name,
        nullable=False,
        message=message,
    )
    if not isinstance(prezzo, _MissingType):
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

    # La periodicita' del canone: un codice del vocabolario o NULL, letto col
    # BB `optional_upper` come sulle righe di contratto e offerta
    # (`normalizza_codici_riga`). Il vocabolario lo dice la FK
    # (`fk_listini_righe_periodicita`); fuori bozza la riga e' ferma dal guard
    # di stato della versione.
    if "periodicita" in payload:
        data["periodicita"] = _V.optional_upper(
            payload, "periodicita", function_name=function_name,
        )

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


# Scopo: Restituisce lista listini paginata con filtri e ordinamento validati.
def fn_list_listini(
    *,
    utility_id: int | None = None,
    tipologia_id: int | None = None,
    attivo: bool | None = None,
    in_scadenza: bool | None = None,
    search: str | None = None,
    order_by: str = "codice",
    order_dir: str | None = "asc",
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
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
        in_scadenza=in_scadenza,
    )


# Scopo: Restituisce le tipologie listino ammesse per una utility dalla matrice
#        config.listini_tipologie_utilities. Usato dal drawer per popolare il
#        Select tipologia al cambio utility.
def fn_list_tipologie_per_utility(utility_id: int) -> list[dict[str, Any]]:
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
def fn_get_listino_dettaglio(listino_id: int) -> dict[str, Any]:
    function_name = "vendite.listini_service.fn_get_listino_dettaglio"
    repository = ListiniRepository()
    listino = _get_listino_or_raise(listino_id, function_name=function_name)
    listino["versioni"] = repository.list_versioni(listino_id)
    return listino


# Scopo: Crea il listino e restituisce il dettaglio aggiornato.
def fn_create_listino(payload: dict[str, Any]) -> dict[str, Any]:
    function_name = "vendite.listini_service.fn_create_listino"
    data = _extract_listino_payload(payload, for_update=False, function_name=function_name)
    repository = ListiniRepository()
    try:
        listino_id = repository.create_listino(data)
    except IntegrityError as exc:
        _translate_integrity_error(exc, function_name=function_name, entity="listino")
    return fn_get_listino_dettaglio(listino_id)


# Scopo: Aggiorna il listino sui soli campi presenti nel payload e restituisce il dettaglio.
def fn_update_listino(listino_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    function_name = "vendite.listini_service.fn_update_listino"
    data = _extract_listino_payload(payload, for_update=True, function_name=function_name)
    _V.require_campi_da_aggiornare(
        data,
        message="Payload listino non valido.",
        detail="Nessun campo aggiornabile presente nel payload.",
        context={"allowed_nullable_fields": sorted(_LISTINO_NULLABLE_FIELDS)},
        function_name=function_name,
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
def fn_delete_listino(listino_id: int) -> dict[str, Any]:
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


# Scopo: La pagina delle versioni del listino (lista `vendite.listini_versioni`),
#        con ricerca e ordinamento validato sulla whitelist del repository.
#        404 se il listino non c'e' (o non si vede).
def fn_list_versioni(
    listino_id: int,
    *,
    search: str | None = None,
    order_by: str = "valido_dal",
    order_dir: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    function_name = "vendite.listini_service.fn_list_versioni"
    _get_listino_or_raise(listino_id, function_name=function_name)
    order_by, order_dir = validate_order_params(
        order_by,
        order_dir,
        allowed_columns=_VERSIONI_ORDER_BY_VALIDI,
        error_code="E_VENDITE_VALIDATION",
        nullable=True,
        function_name=function_name,
    )
    repository = ListiniRepository()
    return repository.list_versioni_pagina(
        listino_id,
        search=search,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset,
    )


# Scopo: Restituisce il dettaglio singolo di una versione del listino.
def fn_get_versione(listino_id: int, versione_id: int) -> dict[str, Any]:
    function_name = "vendite.listini_service.fn_get_versione"
    return _get_versione_or_raise(listino_id, versione_id, function_name=function_name)


# Scopo: Crea una nuova versione in stato iniziale BOZZA e restituisce il dettaglio.
def fn_create_versione(listino_id: int, payload: dict[str, Any]) -> dict[str, Any]:
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
def fn_update_versione(listino_id: int, versione_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    function_name = "vendite.listini_service.fn_update_versione"
    _get_versione_or_raise(listino_id, versione_id, function_name=function_name)
    data = _extract_versione_payload(payload, for_update=True, function_name=function_name)
    _V.require_campi_da_aggiornare(
        data,
        message="Payload versione listino non valido.",
        detail="Nessun campo aggiornabile presente nel payload.",
        context={"allowed_nullable_fields": sorted(_VERSIONE_NULLABLE_FIELDS)},
        function_name=function_name,
    )
    # ⛔ Quali campi si cambiano in quale stato lo dice il DB (L-5, giro 12):
    #    `vendite.trgfn_listini_versioni_guard_per_stato`, col codice
    #    E_LISTINO_VERSIONE_CAMPO_NON_MODIFICABILE. Ritirata la copia del service
    #    (`_VERSIONE_PATCH_ALLOWED_BY_STATE`). La fine di una ATTIVA non passa
    #    da qui: E_LISTINO_VERSIONE_FINE_SOLO_DAL_VERBO (C-4 = a), la si cambia
    #    da «Chiudi» (`fn_programma_chiusura_versione`).
    repository = ListiniRepository()
    try:
        updated = repository.update_versione(listino_id, versione_id, data)
    except IntegrityError as exc:
        _translate_integrity_error(exc, function_name=function_name, entity="versione")
    except DatabaseError as exc:
        _rifiuto_del_db_su_versione(
            exc, message="Aggiornamento versione non consentito.",
            context={"listino_id": listino_id, "versione_id": versione_id},
            function_name=function_name,
        )
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
#        La copia e' il verbo `vendite.fn_clona_versione_listino` (§16.14, C-1 = a:
#        da qualunque stato, anche da una BOZZA), che rifiuta col suo codice.
#        ⛔ Ritirato il 2026-10-29 (BE-C1) il controllo D2 del service («la copia
#        non comincia prima della sorgente», `E_VENDITE_VALIDATION`): lo dice il
#        verbo con E_LISTINO_VERSIONE_CLONE_PRIMA_DELLA_SORGENTE sul campo
#        `valido_dal`, dalla stessa `fn_check`.
# Ritorna: il dettaglio della versione nuova, piu' i conteggi della copia
#          (`righe_copiate`, `componenti_copiati`, `componenti_saltati`: i
#          componenti senza giorni in comune fra distinta e versione nuova).
def fn_clone_versione(
    listino_id: int,
    src_versione_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    function_name = "vendite.listini_service.fn_clone_versione"
    # La sorgente di QUESTO listino: la rotta nomina il listino, il verbo no.
    _get_versione_or_raise(listino_id, src_versione_id, function_name=function_name)

    # ⛔ Del payload si prendono solo codice e date: `meta` e `attivo` non si
    #    clonano (la copia nasce attiva e senza meta), e una chiave che il
    #    verbo non riceve e' un 400, non un valore ignorato in silenzio.
    _V.validate_allowed_keys(
        payload, allowed=_VERSIONE_CLONE_ALLOWED_KEYS, function_name=function_name,
    )
    # Riusa la pipeline di validazione per_create della versione: garantisce
    # codice_versione+valido_dal obbligatori, valido_al > valido_dal.
    target_data = _extract_versione_payload(payload, for_update=False, function_name=function_name)

    repository = ListiniRepository()
    try:
        with transaction.atomic():
            copia = repository.clone_versione(
                src_versione_id,
                codice_versione=target_data["codice_versione"],
                valido_dal=target_data["valido_dal"],
                valido_al=target_data.get("valido_al"),
            )
    except IntegrityError as exc:
        _translate_integrity_error(exc, function_name=function_name, entity="versione")
    except DatabaseError as exc:
        _rifiuto_del_db_su_versione(
            exc, message="Clonazione versione non consentita.",
            context={"listino_id": listino_id, "versione_id": src_versione_id},
            function_name=function_name,
        )

    return {
        **fn_get_versione(listino_id, int(copia["versione_id"])),
        "righe_copiate": copia["righe_copiate"],
        "componenti_copiati": copia["componenti_copiati"],
        "componenti_saltati": copia["componenti_saltati"],
    }


# Scopo: Elimina una versione con tutte le sue righe (cascata).
#        Decisione O2 (sviluppo-listini-v2): solo BOZZA e' eliminabile, perche'
#        non e' mai stata visibile al pricing e nessuno snapshot e' propagato.
#        ⛔ La regola e la cascata sono del DB (§16.11): il verbo
#        `vendite.fn_elimina_versione_listino` rifiuta col primo motivo della
#        stessa `fn_check` del pulsante (E_LISTINO_VERSIONE_NON_ELIMINABILE fuori
#        dalla BOZZA, E_LISTINO_VERSIONE_CITATA se un documento la usa), poi
#        cancella componenti, righe e versione. Inesistente o fuori perimetro:
#        E_VENDITE_LISTINO_VERSIONE_NOT_FOUND dal verbo.
# Ritorna: {deleted, id, righe_eliminate, componenti_eliminati}.
def fn_delete_versione(listino_id: int, versione_id: int) -> dict[str, Any]:
    function_name = "vendite.listini_service.fn_delete_versione"
    # La versione di QUESTO listino: la rotta nomina il listino, il verbo no.
    _get_versione_or_raise(listino_id, versione_id, function_name=function_name)
    repository = ListiniRepository()
    try:
        with transaction.atomic():
            esito = repository.delete_versione(versione_id)
    except IntegrityError as exc:
        _translate_integrity_error(exc, function_name=function_name, entity="versione")
    except DatabaseError as exc:
        _rifiuto_del_db_su_versione(
            exc, message="Eliminazione versione non consentita.",
            context={"listino_id": listino_id, "versione_id": versione_id},
            function_name=function_name,
        )
    return {
        "deleted": True,
        "id": versione_id,
        "righe_eliminate": esito["righe_eliminate"],
        "componenti_eliminati": esito["componenti_eliminati"],
    }


# Scopo: «Chiudi» e «Rimuovi chiusura» di una versione ATTIVA: fissa la fine
#        della validita' (la chiusura programmata) o la toglie (`valido_al`
#        null). Decide il verbo `vendite.fn_programma_chiusura_versione_listino`
#        (§16.14, C-2 = a, C-3): non attiva E_LISTINO_VERSIONE_NON_CHIUDIBILE,
#        fine prima di oggi E_LISTINO_VERSIONE_FINE_NEL_PASSATO sul campo
#        `valido_al`. Lo stato non cambia: CHIUSA la scrive il job a scadenza.
#        ⛔ Nessuna regola di stato qui: il PATCH generico della fine di una
#        ATTIVA lo rifiuta il DB (C-4 = a, E_LISTINO_VERSIONE_FINE_SOLO_DAL_VERBO).
# Ritorna: il dettaglio della versione.
def fn_programma_chiusura_versione(
    listino_id: int, versione_id: int, payload: dict[str, Any],
) -> dict[str, Any]:
    function_name = "vendite.listini_service.fn_programma_chiusura_versione"
    # La versione di QUESTO listino: la rotta nomina il listino, il verbo no.
    _get_versione_or_raise(listino_id, versione_id, function_name=function_name)
    message = "Payload chiusura versione non valido."
    _V.validate_allowed_keys(
        payload, allowed=frozenset({"valido_al"}), function_name=function_name,
    )
    # ⚠️ La chiave e' OBBLIGATORIA anche quando il valore e' null (toglie la
    #    chiusura): un corpo vuoto non deve diventare una rimozione muta.
    ErrorManager.require(
        "valido_al" in payload,
        code=E_VENDITE_VALIDATION,
        message=message,
        detail="valido_al obbligatorio (null toglie la chiusura).",
        context={"field": "valido_al"},
        function_name=function_name,
        log_to_db=True,
    )
    valido_al = _extract_payload_date(
        payload, "valido_al", function_name=function_name, nullable=True, message=message,
    )
    assert not isinstance(valido_al, _MissingType)  # la chiave c'e', vedi sopra
    repository = ListiniRepository()
    try:
        with transaction.atomic():
            repository.programma_chiusura(versione_id, valido_al)
    except IntegrityError as exc:
        _translate_integrity_error(exc, function_name=function_name, entity="versione")
    except DatabaseError as exc:
        _rifiuto_del_db_su_versione(
            exc, message="Chiusura versione non consentita.",
            context={"listino_id": listino_id, "versione_id": versione_id},
            function_name=function_name,
        )
    return fn_get_versione(listino_id, versione_id)


# Scopo: Il cambio di stato della versione: l'ATTIVAZIONE (BOZZA -> ATTIVA),
#        l'unico passaggio manuale della matrice (giro 12, L-3 e L-4). Decide il
#        verbo `vendite.fn_attiva_versione_listino`, in una transazione: i motivi
#        che vietano (versione spenta, senza prezzi), la chiusura delle versioni
#        precedenti (decisione D3 di sviluppo-listini-v2) e lo stato attraverso
#        la porta. Il 403 lo da' la catena dei permessi, dalla riga del passaggio
#        (`PassaggioDocumento` della view, azione `attiva_listino`).
#        ATTIVA -> CHIUSA e' di processo: la si programma con la fine («Chiudi»,
#        `fn_programma_chiusura_versione`) e la scrive il job quando la fine passa; qui nessun verbo
#        la scrive, quindi chiederla e' un 400 sul campo.
#
#        Modalita` dry_run: se il payload contiene `dry_run=true` il verbo gira
#        in un savepoint annullato (rifiuta come il gesto, non scrive) e si
#        restituisce l'anteprima delle versioni che verrebbero chiuse, dallo
#        stesso lettore che usa il verbo (`vendite.fn_versioni_listino_da_chiudere`).
# ⛔ Ritirate nel giro 12 (BE-L2) le copie del service: le transizioni
#    (`_validate_versione_state_transition`), la pianificazione e il conteggio
#    delle righe (`_plan_versione_state_change`), la chiusura e l'UPDATE dello
#    stato nel repository.
def fn_change_versione_state(listino_id: int, versione_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    function_name = "vendite.listini_service.fn_change_versione_state"
    # La versione di QUESTO listino: la rotta nomina il listino, il verbo no.
    _get_versione_or_raise(listino_id, versione_id, function_name=function_name)
    message = "Payload stato versione non valido."
    _V.validate_allowed_keys(
        payload, allowed=frozenset({"stato", "dry_run"}), function_name=function_name,
    )
    nuovo_stato = _V.require_string(
        payload, "stato", message=message, function_name=function_name,
    )
    ErrorManager.require(
        nuovo_stato == STATO_VERSIONE_ATTIVA,
        code=E_VENDITE_VALIDATION,
        message=message,
        detail=(
            f"Da qui si chiede solo {STATO_VERSIONE_ATTIVA} (l'attivazione): la "
            "chiusura si programma con «Chiudi» (rotta chiusura/) e la scrive il "
            "job a fine scaduta."
        ),
        context={"field": "stato", "stato": nuovo_stato},
        function_name=function_name,
        log_to_db=True,
    )
    # ⛔ Un flag del corpo e' un booleano JSON (api.md, tre regole del corpo):
    #    `"true"` e' un 400 sul campo, non un `false` muto che eseguiva davvero
    #    il cambio stato a chi chiedeva l'anteprima (brief-be-verifica-
    #    documentazione-api §B4, 2026-10-21). Gemello di `applica_variazione`.
    dry_run = _V.optional_bool(payload, "dry_run") is True

    repository = ListiniRepository()
    da_chiudere: list[dict[str, Any]] = []
    try:
        if dry_run:
            # Il verbo gira in un savepoint annullato: l'anteprima rifiuta con
            # gli stessi codici del gesto, e non scrive.
            da_chiudere = repository.anteprima_attivazione(versione_id)
        else:
            with transaction.atomic():
                repository.attiva_versione(versione_id)
    except IntegrityError as exc:
        _translate_integrity_error(exc, function_name=function_name, entity="versione")
    except DatabaseError as exc:
        _rifiuto_del_db_su_versione(
            exc, message="Attivazione versione non consentita.",
            context={"listino_id": listino_id, "versione_id": versione_id},
            function_name=function_name,
        )
    if dry_run:
        return {
            "dry_run": True,
            "versione_id": versione_id,
            "nuovo_stato": nuovo_stato,
            "auto_close": [
                {
                    "id": int(row["versione_id"]),
                    "codice_versione": row["codice_versione"],
                    "valido_dal": row["valido_dal"],
                    "valido_al_prima": row["valido_al_prima"],
                    "valido_al_dopo": row["valido_al_dopo"],
                }
                for row in da_chiudere
            ],
        }
    return fn_get_versione(listino_id, versione_id)


# Scopo: Restituisce la lista paginata righe prezzo della versione con filtri opzionali.
def fn_list_righe(
    listino_id: int,
    versione_id: int,
    *,
    search: str | None = None,
    attivo: bool | None = True,
    order_by: str = "articolo_descrizione",
    order_dir: str | None = "asc",
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    function_name = "vendite.listini_service.fn_list_righe"
    _get_versione_or_raise(listino_id, versione_id, function_name=function_name)
    order_by, order_dir = _validate_righe_order(order_by, order_dir, function_name)
    repository = ListiniRepository()
    return repository.list_righe(
        listino_id,
        versione_id,
        search=search,
        attivo=attivo,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset,
    )


# Scopo: Crea una nuova riga prezzo dopo validazione articolo/UoM e restituisce il dettaglio.
def fn_create_riga(listino_id: int, versione_id: int, payload: dict[str, Any]) -> dict[str, Any]:
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
def fn_update_riga(listino_id: int, versione_id: int, riga_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    function_name = "vendite.listini_service.fn_update_riga"
    versione = _get_versione_or_raise(listino_id, versione_id, function_name=function_name)
    _assert_versione_bozza_for_riga_op(versione, function_name=function_name)
    current = _get_riga_or_raise(listino_id, versione_id, riga_id, function_name=function_name)
    data = _extract_riga_payload(payload, for_update=True, function_name=function_name)
    _V.require_campi_da_aggiornare(
        data,
        message="Payload riga listino non valido.",
        detail="Nessun campo aggiornabile presente nel payload.",
        context={"allowed_nullable_fields": sorted(_RIGA_NULLABLE_FIELDS)},
        function_name=function_name,
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
def fn_delete_riga(listino_id: int, versione_id: int, riga_id: int) -> dict[str, Any]:
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


# --- N6: Rettifica controllata su riga ATTIVA non propagata ---

# I codici di `vendite.trgfn_listini_righe_guard_stato` che la rettifica N6
# puo' incontrare. Dal campo strutturato il codice arriva comunque: i marker
# servono solo al ripiego sul testo (stesso schema dei prezzi bundle, sotto).
_KNOWN_RETTIFICA_DB_ERROR_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("E_RIGA_LISTINO_PROPAGATA", ("E_RIGA_LISTINO_PROPAGATA",)),
    ("E_RIGA_LISTINO_VERSIONE_CHIUSA", ("E_RIGA_LISTINO_VERSIONE_CHIUSA",)),
)


# Scopo: Consente la modifica del prezzo di una riga in versione ATTIVA solo se
#        nessuna riga di commessa o attivita` fatturabile la cita (riga non
#        «propagata»): lo decide il guard DB sull'UPDATE, sotto lock FOR UPDATE.
#        Motivo obbligatorio. Audit in meta.rettifiche_controllate[].
def fn_rettifica_controllata_riga(
    listino_id: int,
    versione_id: int,
    riga_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
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
    today = oggi_aziendale()
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
    # Le frasi sono quelle del BB: «obbligatorio» se manca, «deve essere un
    # numero» se non lo e' — due casi, due frasi, senza un titolo unico.
    nuovo_prezzo = _V.require_decimal(payload, "prezzo", function_name=function_name)

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

    # --- Lock pessimistico + scrittura; «propagata» la decide il guard DB ---
    # ⛔ Niente controllo di propagazione qui (2026-10-09, ok Tid): la regola e'
    #    di `vendite.trgfn_listini_righe_guard_stato`, che rifiuta l'UPDATE con
    #    `E_RIGA_LISTINO_PROPAGATA` (o `E_RIGA_LISTINO_VERSIONE_CHIUSA`). Fino ad
    #    allora il service ne teneva una copia in Python con un codice suo
    #    (`E_VENDITE_RIGA_GIA_PROPAGATA`): due sedi, due codici per una regola.
    try:
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
            # ⚠️ Prezzo e meta si rileggono SOTTO il lock: letti prima, due
            #    rettifiche concorrenti scrivevano ognuna il proprio `meta`, e
            #    la seconda cancellava la voce di audit della prima (e diceva
            #    un `prezzo_precedente` gia' superato).
            riga = _get_riga_or_raise(
                listino_id, versione_id, riga_id, function_name=function_name
            )
            meta_corrente = _V.optional_meta(
                riga, "meta", function_name=function_name
            ) or {}
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
    except DatabaseError as exc:
        ErrorManager.raise_from_database_error(
            exc,
            known_markers=_KNOWN_RETTIFICA_DB_ERROR_MARKERS,
            fallback_code="E_VENDITE_VALIDATION",
            message="Rettifica della riga di listino non ammessa.",
            context={"riga_id": riga_id, "versione_id": versione_id},
            function_name=function_name,
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
) -> dict[str, Any]:
    function_name = "vendite.listini_service.fn_applica_variazione_percentuale"

    # --- Guard: versione esiste e stato BOZZA ---
    versione = _get_versione_or_raise(listino_id, versione_id, function_name=function_name)
    _assert_versione_bozza_for_riga_op(versione, function_name=function_name)

    # --- Parsing e validazione payload ---
    variazione_pct = _V.require_decimal(
        payload, "variazione_percentuale", function_name=function_name,
    )

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

    # Dal BB: con `bool(...)` la stringa "false" valeva True.
    dry_run = _V.optional_bool(payload, "dry_run") is True

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
        meta_versione = _V.optional_meta(
            versione, "meta", function_name="listini_service.fn_applica_variazione_percentuale"
        ) or {}
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


# ══════════════════════════════════════════════════════════════════════
#  BUNDLE componenti BoM (modello unificato 2026-05-13)
# ══════════════════════════════════════════════════════════════════════
#
# Vedi `manual/modello-componenti-bom.md` §8 e
# `db/changelog/migrations_v2/00_schema/vendite/20260513-18-...yaml`.
# Tabella `vendite.listini_righe_componenti`: prezzi bundle dei figli
# BoM di un articolo composito in contesto versione listino.
# Le righe `listini_righe` su padri compositi sono vietate (trigger
# 20260513-04 `E_LISTINO_RIGA_COMPOSITO_VIETATO`); l'unico modo per
# dare un prezzo al composito e' via questa tabella (somma figli).


# Codici noti dei trigger DB su `listini_righe_componenti` sollevati via
# `script.fn_log_and_raise_error` (P0001). Pattern speculare a
# `_KNOWN_DB_ERROR_MARKERS` in `pricing_service`: ogni voce e' la tupla
# (codice, markers_substring) — TUTTI i marker devono comparire nel MESSAGE
# perche' il codice DB originale venga preservato nel ServiceError.
#
# Trigger noti:
#   - 20260513-20 `trgfn_listini_righe_comp_guard_immutabilita_v5`:
#     blocca INS/UPD/DLT su versioni ATTIVA/CHIUSA → `E_RIGA_LISTINO_VERSIONE_CHIUSA`
#   - guard coerenza BoM (lato team DB): blocca prezzo su componente
#     fuori dalla BoM corrente del padre composito.
#
# Quando aggiungiamo un nuovo trigger DB su `listini_righe_componenti`
# aggiungiamo qui la sua tupla — il codice DB compare in `detail` anche
# senza match (fallback `E_VENDITE_VALIDATION`).
_KNOWN_BUNDLE_DB_ERROR_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "E_RIGA_LISTINO_VERSIONE_CHIUSA",
        ("E_RIGA_LISTINO_VERSIONE_CHIUSA",),
    ),
    (
        "E_LISTINO_RIGA_COMP_BOM_INCOERENTE",
        ("E_LISTINO_RIGA_COMP_BOM_INCOERENTE",),
    ),
    # Guard `vendite.trgfn_listini_kit_guard` (D-2-bis (B)): la periodicita'
    # a parte si scrive solo per un composito. Fuori bozza parla
    # `E_RIGA_LISTINO_VERSIONE_CHIUSA`, la stessa dei componenti.
    (
        "E_LISTINO_KIT_NON_COMPOSITO",
        ("E_LISTINO_KIT_NON_COMPOSITO",),
    ),
)




# Scopo: Preview della BoM di un padre composito in contesto versione
#        listino: 1 riga per ogni `articoli_componenti` valida alla data,
#        LEFT JOIN su `listini_righe_componenti` per i prezzi gia'
#        definiti (NULL se non ancora). Usata dal FE per popolare il
#        Dialog di editing dei prezzi bundle.
#        `data_riferimento`: di default = oggi. L'admin in BOZZA editing
#        vuole vedere la BoM corrente (con cui sta progettando i prezzi),
#        non quella valida al `versione.valido_dal` futuro (che potrebbe
#        non essere ancora configurata in catalogo o avere range diverso).
#        Allinea al pattern preventivi (passa `data_documento`).
#        Override esplicito ammesso per simulazioni admin / audit di
#        versioni ATTIVE/CHIUSE (caller passa `versione.valido_dal`).
def fn_preview_bundle(
    listino_id: int,
    versione_id: int,
    articolo_padre_id: str,
    *,
    data_riferimento: date | None = None,
) -> list[dict[str, Any]]:
    function_name = "vendite.listini_service.fn_preview_bundle"
    _get_listino_or_raise(listino_id, function_name=function_name)
    _get_versione_or_raise(
        listino_id, versione_id, function_name=function_name,
    )
    # Validazione UUID padre: il _v PayloadValidator e' su instance ma qui
    # bastiamo a check positivo (UUID malformato → invalid).
    ErrorManager.require(
        bool(articolo_padre_id),
        code="E_VENDITE_VALIDATION",
        message="articolo_padre_id obbligatorio.",
        function_name=function_name,
    )
    repository = ListiniRepository()
    return repository.list_bundle_preview(
        versione_id=versione_id,
        articolo_padre_id=str(articolo_padre_id),
        data_riferimento=data_riferimento or oggi_aziendale(),
    )


# Scopo: Salva (upsert batch) i prezzi bundle di un padre composito per
#        la versione listino. Strategia "tabula rasa idempotente": il
#        repo soft-disattiva le righe attive correnti per (versione, padre)
#        e inserisce le nuove. Tutto in `transaction.atomic`.
#
#        Guard di stato: solo versione BOZZA modificabile (allinea al
#        pattern righe standalone via `_assert_versione_bozza_for_riga_op`
#        e al trigger DB di immutabilita' v5 `_immutabilita_v5`).
#
#        `rows`: lista di dict `{articolo_componente_id, articolo_figlio_id,
#        prezzo, iva_id?}`. Righe con `prezzo` None/null vengono ignorate
#        ("non gestito a bundle" — il resolver fa fallback STADIO 1
#        standalone). `valido_dal`/`valido_al` default = validita della
#        versione listino.
def fn_save_bundle(
    listino_id: int,
    versione_id: int,
    articolo_padre_id: str,
    rows: Any,  # grezzo dal corpo: la forma la giudica il BB `voci` qui sotto
) -> dict[str, int]:
    function_name = "vendite.listini_service.fn_save_bundle"
    _get_listino_or_raise(listino_id, function_name=function_name)
    versione = _get_versione_or_raise(
        listino_id, versione_id, function_name=function_name,
    )
    _assert_versione_bozza_for_riga_op(versione, function_name=function_name)
    ErrorManager.require(
        bool(articolo_padre_id),
        code="E_VENDITE_VALIDATION",
        message="articolo_padre_id obbligatorio.",
        function_name=function_name,
    )
    # Una lista di voci, ogni voce un oggetto (BB): una voce che non e' un
    # oggetto era un `AttributeError` nel repository (`r.get`), cioe' un 500.
    rows = _V.voci(rows, lambda voce, _indice: dict(voce), campo="rows", function_name=function_name)

    # Validita default = validita versione listino (semplifica UX; la
    # temporal FK PG18 `fk_listrighe_comp_articoli_comp_temporal` blocca
    # comunque se la BoM corrente e' piu' corta del range richiesto —
    # errore parlante al save via `_translate_integrity_error`).
    valido_dal_raw = versione.get("valido_dal")
    valido_al_raw = versione.get("valido_al")
    ErrorManager.require(
        valido_dal_raw is not None,
        code="E_VENDITE_VALIDATION",
        message="Versione listino senza valido_dal.",
        function_name=function_name,
    )

    def _to_date(val: Any) -> date | None:
        if val is None:
            return None
        if isinstance(val, date):
            return val
        # psycopg di solito ritorna date nativi; fallback ISO string
        return date.fromisoformat(str(val))

    valido_dal = _to_date(valido_dal_raw)
    valido_al = _to_date(valido_al_raw)
    assert valido_dal is not None  # require sopra

    err_context = {
        "listino_id": listino_id,
        "versione_id": versione_id,
        "articolo_padre_id": str(articolo_padre_id),
        "n_rows": len(rows),
    }
    repository = ListiniRepository()
    try:
        with transaction.atomic():
            result = repository.upsert_bundle_componenti(
                versione_id=versione_id,
                articolo_padre_id=str(articolo_padre_id),
                rows=rows,
                valido_dal=valido_dal,
                valido_al=valido_al,
            )
    except IntegrityError as exc:
        # IntegrityError e' sottoclasse di DatabaseError: catch prima per
        # mappare i vincoli UNIQUE/FK/CHECK con messaggi parlanti standard.
        _translate_integrity_error(
            exc, function_name=function_name, entity="bundle",
        )
    except DatabaseError as exc:
        # P0001 dai trigger DB su `listini_righe_componenti`
        # (immutabilita' versione ATTIVA/CHIUSA, guard coerenza BoM).
        # Senza questo catch il codice DB strutturato verrebbe perso e
        # il middleware mapperebbe a `E_DATABASE` generico.
        ErrorManager.raise_from_database_error(
            exc,
            known_markers=_KNOWN_BUNDLE_DB_ERROR_MARKERS,
            fallback_code="E_VENDITE_VALIDATION",
            message="Impossibile salvare i prezzi bundle.",
            context=err_context,
            function_name=function_name,
        )

    return result


# Scopo: Elimina TUTTI i prezzi bundle di un composito da una versione
#        listino in BOZZA. Pattern semantico DELETE: tabula rasa idempotente
#        gia' incapsulata da `upsert_bundle_componenti` quando `rows=[]`.
#        Equivalente a `fn_save_bundle(rows=[])` ma esposto come endpoint
#        dedicato per chiarezza REST + audit log.
#
#        Idempotente: 0 disattivati su composito senza prezzi bundle,
#        nessun errore. Guard BOZZA via `_assert_versione_bozza_for_riga_op`
#        ereditata da `fn_save_bundle`.
#        ⭐ Con i prezzi se ne va anche il kit (`vendite.listini_kit`, la sua
#        periodicita'): restando, sarebbe un kit sul listino senza prezzo.
def fn_delete_bundle(
    listino_id: int,
    versione_id: int,
    articolo_padre_id: str,
) -> dict[str, int]:
    with transaction.atomic():
        result = fn_save_bundle(listino_id, versione_id, articolo_padre_id, rows=[])
        _kit_db_errors(
            lambda: ListiniRepository().elimina_kit(
                versione_id=versione_id, articolo_padre_id=str(articolo_padre_id),
            ),
            function_name="vendite.listini_service.fn_delete_bundle",
            context={"versione_id": versione_id, "articolo_padre_id": str(articolo_padre_id)},
        )
    return result


# Scopo: La periodicita' del KIT sulla versione di listino (D-2-bis (B),
#        `vendite.listini_kit`): il kit non ha una riga di listino, e la
#        periodicita' con cui si addebita a canone sta li'. Un codice del
#        vocabolario la scrive, `null` (o vuoto) la toglie. Solo in bozza e
#        solo su un composito: lo dice il guard DB, tradotto qui.
#        ⛔ Che sia obbligatoria su una quota fissa lo dice il controllo
#        all'attivazione della versione (`E_LISTINO_VERSIONE_QUOTA_FISSA_SENZA_
#        PERIODICITA`), non questo verbo: la bozza resta libera.
# Ritorna: {articolo_padre_id, periodicita}.
def fn_save_kit_periodicita(
    listino_id: int,
    versione_id: int,
    articolo_padre_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    function_name = "vendite.listini_service.fn_save_kit_periodicita"
    _get_listino_or_raise(listino_id, function_name=function_name)
    _get_versione_or_raise(listino_id, versione_id, function_name=function_name)
    _V.validate_allowed_keys(payload, allowed=frozenset({"periodicita"}), function_name=function_name)
    ErrorManager.require(
        "periodicita" in payload,
        code="E_VENDITE_VALIDATION",
        message="Campo 'periodicita' obbligatorio: un codice, o null per toglierla.",
        context={"field": "periodicita"},
        function_name=function_name,
    )
    periodicita = _V.optional_upper(payload, "periodicita", function_name=function_name)
    scritta = _kit_db_errors(
        lambda: ListiniRepository().salva_kit_periodicita(
            versione_id=versione_id,
            articolo_padre_id=str(articolo_padre_id),
            periodicita=periodicita,
        ),
        function_name=function_name,
        context={"versione_id": versione_id, "articolo_padre_id": str(articolo_padre_id)},
    )
    return {"articolo_padre_id": str(articolo_padre_id), "periodicita": scritta}


# Scopo: Le scritture di `vendite.listini_kit` con gli errori del DB tradotti:
#        i vincoli col campo (`_translate_integrity_error`), i guard col loro
#        codice (`_KNOWN_BUNDLE_DB_ERROR_MARKERS`, gli stessi del bundle).
def _kit_db_errors(
    scrittura: Callable[[], Any], *, function_name: str, context: dict[str, Any],
) -> Any:
    try:
        with transaction.atomic():
            return scrittura()
    except IntegrityError as exc:
        _translate_integrity_error(exc, function_name=function_name, entity="kit")
    except DatabaseError as exc:
        ErrorManager.raise_from_database_error(
            exc,
            known_markers=_KNOWN_BUNDLE_DB_ERROR_MARKERS,
            fallback_code="E_VENDITE_VALIDATION",
            message="Impossibile salvare il kit sul listino.",
            context=context,
            function_name=function_name,
        )
