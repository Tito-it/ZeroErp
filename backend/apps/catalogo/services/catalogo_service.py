# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Facade applicativa generica per lo schema catalogo (articoli e lookup).
# ------------------------------------------------------------

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Any, NoReturn
from uuid import UUID

from django.db import DatabaseError, IntegrityError, transaction

from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.core.api.constants import DEFAULT_LIMIT
from apps.catalogo.db.catalogo_bom_repository import (
    COMPONENTE_WRITE_COLUMNS,
    CatalogoBomRepository,
)
from apps.catalogo.db.catalogo_repository import (
    ARTICOLI_CREATE_COLUMNS,
    ARTICOLI_ORDER_COLUMNS,
    ARTICOLI_UPDATE_COLUMNS,
    CONVERSIONI_UPDATE_COLUMNS,
    LOOKUP_ARTICOLI_MAX,
    UNITA_MISURA_UPDATE_COLUMNS,
    UOM_CONVERSIONI_ORDER_COLUMNS,
    UOM_ORDER_COLUMNS,
    UOM_TIPI_ORDER_COLUMNS,
    UOM_TIPI_UPDATE_COLUMNS,
    CatalogoRepository,
)
from apps.catalogo.db.catalogo_uom_repository import (
    ARTICOLO_UOM_ORDER_COLUMNS,
    UOM_OPERATIVA_WRITE_COLUMNS,
    CatalogoUomRepository,
)
from apps.core.db._helpers import resolve_config_id_by_codice_interno
from apps.core.services.db_error_fields import db_error_code
from apps.core.services.error_manager import ErrorManager
from apps.core.services.service_errors import ServiceError
from apps.core.services.list_helpers import collezione_completa, validate_order_params
from apps.core.services.non_editable_fields_helper import compute_non_editable_fields
from apps.core.services.parameter_service import ParameterService
from apps.core.services.testata_guard import o_not_found, pagina_dopo_testata
from apps.core.services.payload_helpers import (
    MISSING as _MISSING,
    MissingType as _MissingType,
    PayloadValidator,
    map_integrity_error,
)

logger = logging.getLogger(__name__)

_ORDER_BY_VALIDI: frozenset[str] = frozenset(ARTICOLI_ORDER_COLUMNS.keys())
_ARTICOLO_FLAG_FIELDS: tuple[str, ...] = (
    "is_composito",
    "is_solo_componente",
    "requires_serial",
    # Lotto 2 di magazzino (brief §4.9): «per lotti», deciso dall'articolo.
    "requires_lotto",
    # NOT NULL DEFAULT false a DB (fail-safe: nessun articolo movimenta giacenza
    # per distrazione). Brief modifiche certe, Blocco B.
    "gestito_a_magazzino",
)
# Scopo: Campi int nullable di articolo (escluso uom_id che e' NOT NULL e immutabile).
# Vedi DDL catalogo.articoli e il suo lock di colonna (`E_CODICE_NON_MODIFICABILE`).
_ARTICOLO_INT_FIELDS: tuple[str, ...] = (
    "tipo_voce_id",
    "gruppo_voce_id",
    "spesa_id",
    "iva_id",
    "conto_contabile_vendita_id",
    "conto_contabile_acquisto_id",
    "listino_tipologia_id",
    # Nullable per scelta di modello: per una prestazione non significa niente,
    # e `0` non e' «non si applica». Il CHECK `>= 0` e' anticipato nel service
    # con messaggio parlante (vedi `_validate_articolo_payload`).
    "lead_time_giorni",
    # La causale dell'articolo-onere (§9.10, D-1 di Tid 2026-11-12): NULL e' la
    # merce, un id fa dell'articolo un onere. Nessun giudizio qui: il doppione,
    # la natura, i flag di struttura e il blocco sull'articolo usato li dice il
    # DB (guard dell'onere, A-10).
    "causale_onere_id",
)
# Scopo: FK NOT NULL a DB con DEFAULT: (chiave, dettaglio dell'errore se
#        arriva null). Il valore si puo' cambiare, mai azzerare — assente nel
#        payload = «lascia decidere il default».
_ARTICOLO_FK_NOT_NULL: tuple[tuple[str, str], ...] = (
    ("natura_vendita_id", "natura_vendita_id non puo' essere null: indica una natura valida."),
    (
        "modo_approvvigionamento_id",
        "modo_approvvigionamento_id non puo' essere null: indica un modo valido.",
    ),
)
_ARTICOLO_NULLABLE_FIELDS: frozenset[str] = frozenset({
    "descrizione_breve",
    *_ARTICOLO_INT_FIELDS,
    "obsoleto_dal",
    "meta",
})
_ARTICOLO_CREATE_ALLOWED_KEYS: frozenset[str] = ARTICOLI_CREATE_COLUMNS
_ARTICOLO_UPDATE_ALLOWED_KEYS: frozenset[str] = ARTICOLI_UPDATE_COLUMNS
_UOM_CREATE_ALLOWED_KEYS: frozenset[str] = UOM_OPERATIVA_WRITE_COLUMNS
_UOM_UPDATE_ALLOWED_KEYS: frozenset[str] = frozenset(key for key in UOM_OPERATIVA_WRITE_COLUMNS if key != "uom_id")
_COMPONENTE_CREATE_ALLOWED_KEYS: frozenset[str] = COMPONENTE_WRITE_COLUMNS

# ⭐ `non_editable_fields` delle tabelle di catalogo: il BB
#    `compute_non_editable_fields`, senza gap. Fino al 2026-11-11 qui c'era
#    `_NON_EDITABLE_DB_GAPS`, le colonne ferme che il DB non dichiarava
#    (unita', fattore e inizio di mappature e conversioni). Dal giro G1-G2 di
#    brief-db-revisione-catalogo (BE21-a) le ferma un lock di colonna
#    (`E_UOM_STORIA_IMMUTABILE`) e `dbops.vw_non_editable_fields` le dichiara:
#    una seconda sede qui sarebbe la stessa regola scritta due volte (cosi'
#    era uscito `catalogo.articoli.codice`, 2026-11-09).


# Scopo: in create, applica il default `valido_dal=today` se il campo manca
# o e' None. Centralizza la regola Fase 4 (BE-only) per i 3 service create
# (componente, uom_operativa, conversione): il DDL DB non ha
# un `DEFAULT` (DB declined), il fallback vive qui — nel giorno dell'azienda.
# Restituisce sempre un `date | _MissingType` coerente per il chiamante.
def _apply_valido_dal_default(valido_dal, *, for_create: bool):
    if for_create and (valido_dal is _MISSING or valido_dal is None):
        return oggi_aziendale()
    return valido_dal


_V = PayloadValidator(validation_code="E_CATALOGO_VALIDATION", log_to_db=True)


# Scopo: Valida il limite dei lookup con messaggio uniforme e massimo configurabile.
def _validate_lookup_limit(limit: int, *, max_limit: int, function_name: str) -> None:
    ErrorManager.require(
        1 <= limit <= max_limit,
        code="E_CATALOGO_VALIDATION",
        message="Parametri lookup non validi.",
        detail=f"limit deve essere compreso tra 1 e {max_limit}",
        context={"limit": limit, "max_limit": max_limit},
        function_name=function_name,
        log_to_db=True,
    )


# Scopo: Normalizza e valida ordinamento lista articoli contro whitelist locale.
def _validate_order(order_by: str, order_dir: str | None, function_name: str) -> tuple[str, str | None]:
    return validate_order_params(
        order_by,
        order_dir,
        allowed_columns=_ORDER_BY_VALIDI,
        error_code="E_CATALOGO_VALIDATION",
        # `nullable`: direzione assente -> `None` e decide il default del
        # repository (`parse_list_params` non inventa piu' "asc", 2026-09-26).
        nullable=True,
        function_name=function_name,
    )


# Scopo: Envelope di un LOOKUP, cioe' di una collezione che un `LIMIT` puo'
#        aver tagliato. Porta `troncato`, che e' l'informazione che `count` da
#        solo non puo' dare.
#
# 🔴 PERCHE' ESISTE, e non e' una raffinatezza (2026-09-10). Fino a oggi lookup e
#    collezioni figlie passavano dallo STESSO helper, che faceva
#    `{"count": len(results)}`. Su una collezione intera e' giusto; su un lookup
#    con `limit=20` significa rispondere `count: 20` su venti righe **quando i
#    risultati erano cento**. ⇒ Il conteggio non rivelava il troncamento: lo
#    CONFERMAVA. E la forma sbagliata era indistinguibile da quella giusta,
#    perche' era la stessa riga di codice.
#    ⚠️ `api.md` lo scrive dal 2026-09-02: *«`len(results)` non e' un conteggio: e'
#    un'eco. Un numero derivato dalle righe non puo' dire niente SULLE righe»*.
#    Il caso vivo era `fn_lookup_articoli`, l'autocomplete piu' usato dell'app.
#
# ⚠️ `count` resta ed e' il numero di righe consegnate — cambia che adesso c'e'
#    accanto la sola cosa che lo rende leggibile. Aggiungere un campo non rompe
#    nessun client; toglierne uno si'.
def _lookup_response(
    results: list[dict[str, Any]], *, troncato: bool
) -> dict[str, Any]:
    return {"count": len(results), "results": results, "troncato": troncato}


# Scopo: Estrae stringa obbligatoria non vuota dal payload.
def _require_string(
    payload: dict[str, Any],
    key: str,
    *,
    function_name: str,
    message: str,
) -> str:
    value = payload.get(key)
    cleaned = value.strip() if isinstance(value, str) else ""
    ErrorManager.require(
        bool(cleaned),
        code="E_CATALOGO_VALIDATION",
        message=message,
        detail=f"{key} obbligatorio e non vuoto.",
        context={"field": key},
        function_name=function_name,
        log_to_db=True,
    )
    return cleaned


# Scopo: Estrae stringa presente nel payload; supporta NULL esplicito se consentito.
def _extract_string(
    payload: dict[str, Any],
    key: str,
    *,
    function_name: str,
    nullable: bool,
    message: str = "Payload articolo non valido.",
) -> str | None | _MissingType:
    return _V.extract_optional_string(
        payload,
        key,
        nullable=nullable,
        message=message,
        function_name=function_name,
        log_to_db=True,
    )


# Scopo: Estrae FK/interi opzionali consentendo NULL esplicito o stringa vuota.
def _extract_nullable_int(
    payload: dict[str, Any],
    key: str,
    *,
    function_name: str,
    message: str = "Payload articolo non valido.",
) -> int | None | _MissingType:
    if key not in payload:
        return _MISSING
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    ErrorManager.require(
        not isinstance(value, (bool, float)),
        code="E_CATALOGO_VALIDATION",
        message=message,
        detail=f"{key} deve essere un intero o null.",
        context={"field": key},
        function_name=function_name,
        log_to_db=True,
    )
    try:
        if isinstance(value, str):
            return int(value.strip())
        raise TypeError(f"{key}_invalid")
    except (TypeError, ValueError) as exc:
        ErrorManager.raise_error(
            code="E_CATALOGO_VALIDATION",
            message=message,
            detail=f"{key} deve essere un intero o null.",
            context={"field": key},
            function_name=function_name,
            log_to_db=True,
            cause=exc,
        )


# Scopo: Estrae una FK NOT NULL a DB con DEFAULT (`_ARTICOLO_FK_NOT_NULL`):
#        chiave assente -> _MISSING (il DB applica il default), presente ->
#        int > 0, altrimenti 400 col campo. Un `null` esplicito e' un errore,
#        non un azzeramento: la colonna non ammette «non lo so».
def _extract_fk_not_null(
    payload: dict[str, Any],
    key: str,
    *,
    detail: str,
    function_name: str,
) -> int | _MissingType:
    value = _extract_nullable_int(payload, key, function_name=function_name)
    if value is _MISSING:
        return _MISSING
    ErrorManager.require(
        isinstance(value, int) and value > 0,
        code="E_CATALOGO_VALIDATION",
        message="Payload articolo non valido.",
        detail=detail,
        context={"field": key},
        function_name=function_name,
        log_to_db=True,
    )
    assert isinstance(value, int)
    return value


# Scopo: Estrae booleano solo se esplicitamente presente nel payload.
def _extract_present_bool(
    payload: dict[str, Any],
    key: str,
    *,
    function_name: str,
    message: str = "Payload articolo non valido.",
) -> bool | _MissingType:
    if key not in payload:
        return _MISSING
    value = payload.get(key)
    ErrorManager.require(
        isinstance(value, bool),
        code="E_CATALOGO_VALIDATION",
        message=message,
        detail=f"{key} deve essere booleano.",
        context={"field": key},
        function_name=function_name,
        log_to_db=True,
    )
    assert isinstance(value, bool)
    return value


# Scopo: Estrae meta JSON come dict oppure NULL esplicito.
def _extract_meta(
    payload: dict[str, Any],
    *,
    function_name: str,
    message: str = "Payload articolo non valido.",
) -> dict[str, Any] | None | _MissingType:
    if "meta" not in payload:
        return _MISSING
    value = payload.get("meta")
    if value is None:
        return None
    ErrorManager.require(
        isinstance(value, dict),
        code="E_CATALOGO_VALIDATION",
        message=message,
        detail="meta deve essere un oggetto JSON o null.",
        context={"field": "meta"},
        function_name=function_name,
        log_to_db=True,
    )
    return value


# Scopo: Estrae data ISO opzionale dal payload JSON.
def _extract_payload_date(
    payload: dict[str, Any],
    key: str,
    *,
    function_name: str,
    nullable: bool,
    message: str = "Payload catalogo non valido.",
) -> date | None | _MissingType:
    if key not in payload:
        return _MISSING
    value = payload.get(key)
    if value is None:
        ErrorManager.require(
            nullable,
            code="E_CATALOGO_VALIDATION",
            message=message,
            detail=f"{key} non puo' essere null.",
            context={"field": key},
            function_name=function_name,
            log_to_db=True,
        )
        return None
    ErrorManager.require(
        isinstance(value, str),
        code="E_CATALOGO_VALIDATION",
        message=message,
        detail=f"{key} deve essere una data ISO YYYY-MM-DD.",
        context={"field": key},
        function_name=function_name,
        log_to_db=True,
    )
    cleaned = value.strip()
    ErrorManager.require(
        bool(cleaned) or nullable,
        code="E_CATALOGO_VALIDATION",
        message=message,
        detail=f"{key} non puo' essere vuoto.",
        context={"field": key},
        function_name=function_name,
        log_to_db=True,
    )
    if cleaned == "":
        return None
    try:
        return date.fromisoformat(cleaned)
    except ValueError as exc:
        ErrorManager.raise_error(
            code="E_CATALOGO_VALIDATION",
            message=message,
            detail=f"{key} deve essere una data ISO YYYY-MM-DD.",
            context={"field": key},
            function_name=function_name,
            log_to_db=True,
            cause=exc,
        )


# Scopo: Estrae UUID opzionale dal payload JSON.
def _extract_payload_uuid(
    payload: dict[str, Any],
    key: str,
    *,
    function_name: str,
    nullable: bool,
    message: str = "Payload catalogo non valido.",
) -> UUID | None | _MissingType:
    if key not in payload:
        return _MISSING
    value = payload.get(key)
    if value is None:
        ErrorManager.require(
            nullable,
            code="E_CATALOGO_VALIDATION",
            message=message,
            detail=f"{key} non puo' essere null.",
            context={"field": key},
            function_name=function_name,
            log_to_db=True,
        )
        return None
    try:
        return value if isinstance(value, UUID) else UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        ErrorManager.raise_error(
            code="E_CATALOGO_VALIDATION",
            message=message,
            detail=f"{key} deve essere un UUID valido.",
            context={"field": key},
            function_name=function_name,
            log_to_db=True,
            cause=exc,
        )


# Scopo: Estrae i campi scrivibili di un articolo con una sola regola condivisa.
def _extract_articolo_payload(
    payload: dict[str, Any],
    *,
    for_update: bool,
    function_name: str,
) -> dict[str, Any]:
    data: dict[str, Any] = {}

    if for_update:
        # codice e uom_id sono entrambi immutabili (lock_columns DDL).
        ErrorManager.require(
            "codice" not in payload,
            code="E_CATALOGO_VALIDATION",
            message="Payload articolo non valido.",
            detail="codice e' immutabile e non puo' essere aggiornato.",
            context={"field": "codice"},
            function_name=function_name,
            log_to_db=True,
        )
        ErrorManager.require(
            "uom_id" not in payload,
            code="E_CATALOGO_VALIDATION",
            message="Payload articolo non valido.",
            detail="uom_id e' immutabile e non puo' essere aggiornato dopo la creazione.",
            context={"field": "uom_id"},
            function_name=function_name,
            log_to_db=True,
        )
        # Fase 7: attivo non passa da PATCH, solo dagli endpoint dedicati
        # /disattiva/ e /riattiva/ (azione di dominio, pattern AS/400).
        ErrorManager.require(
            "attivo" not in payload,
            code="E_CATALOGO_VALIDATION",
            message="Payload articolo non valido.",
            detail="attivo non e' modificabile via PATCH: usa gli endpoint /disattiva/ o /riattiva/.",
            context={"field": "attivo"},
            function_name=function_name,
            log_to_db=True,
        )
        _V.validate_allowed_keys(
            payload,
            allowed=_ARTICOLO_UPDATE_ALLOWED_KEYS | {"codice", "uom_id"},
            function_name=function_name,
            message="Payload articolo non valido.",
        )
        descrizione = _extract_string(
            payload,
            "descrizione",
            function_name=function_name,
            nullable=False,
        )
        if descrizione is not _MISSING:
            data["descrizione"] = descrizione
    else:
        _V.validate_allowed_keys(
            payload,
            allowed=_ARTICOLO_CREATE_ALLOWED_KEYS,
            function_name=function_name,
            message="Payload articolo non valido.",
        )
        data["codice"] = _require_string(
            payload,
            "codice",
            function_name=function_name,
            message="codice obbligatorio.",
        )
        data["descrizione"] = _require_string(
            payload,
            "descrizione",
            function_name=function_name,
            message="descrizione obbligatoria.",
        )
        # uom_id e' NOT NULL a livello DDL: obbligatorio e > 0 in create.
        uom_value = _extract_nullable_int(
            payload,
            "uom_id",
            function_name=function_name,
        )
        ErrorManager.require(
            isinstance(uom_value, int) and uom_value > 0,
            code="E_CATALOGO_VALIDATION",
            message="Payload articolo non valido.",
            detail="uom_id obbligatorio.",
            context={"field": "uom_id"},
            function_name=function_name,
            log_to_db=True,
        )
        data["uom_id"] = uom_value

    descrizione_breve = _extract_string(
        payload,
        "descrizione_breve",
        function_name=function_name,
        nullable=True,
    )
    if descrizione_breve is not _MISSING:
        data["descrizione_breve"] = descrizione_breve

    for field_name in _ARTICOLO_INT_FIELDS:
        field_value = _extract_nullable_int(
            payload,
            field_name,
            function_name=function_name,
        )
        if field_value is not _MISSING:
            data[field_name] = field_value

    for field_name in _ARTICOLO_FLAG_FIELDS:
        field_value = _extract_present_bool(
            payload,
            field_name,
            function_name=function_name,
        )
        if field_value is not _MISSING:
            data[field_name] = field_value

    # Le due FK NOT NULL con DEFAULT a DB — natura_vendita_id (MERCE, decide
    # l'instradamento post-accettazione) e modo_approvvigionamento_id (ACQUISTO,
    # Blocco B del brief modifiche certe, deciso 2026-09-02): opzionali nel
    # payload, ma se presenti devono essere un id valido, mai null. Un NULL
    # significherebbe «non lo so», cioe' lo stato che la colonna esiste per
    # abolire (brief §3.3). Stessa regola, una sede sola.
    for fk_key, fk_detail in _ARTICOLO_FK_NOT_NULL:
        fk_value = _extract_fk_not_null(
            payload, fk_key, detail=fk_detail, function_name=function_name,
        )
        if fk_value is not _MISSING:
            data[fk_key] = fk_value

    # lead_time_giorni: anticipa il CHECK `chk_articoli_lead_time_giorni_non_negativo`
    # con un messaggio che nomina il campo. Il NULL e' ammesso (e' un'informazione).
    lead_time = data.get("lead_time_giorni")
    if lead_time is not None:
        ErrorManager.require(
            lead_time >= 0,
            code="E_CATALOGO_VALIDATION",
            message="Payload articolo non valido.",
            detail="lead_time_giorni non puo' essere negativo.",
            context={"field": "lead_time_giorni"},
            function_name=function_name,
            log_to_db=True,
        )

    # Il ritiro: una data, o null per toglierla (l'articolo torna a scegliersi).
    # Passata, di oggi o futura: quando vale lo dice il DB (`e_obsoleto`).
    obsoleto_dal = _extract_payload_date(
        payload, "obsoleto_dal", function_name=function_name, nullable=True,
        message="Payload articolo non valido.",
    )
    if obsoleto_dal is not _MISSING:
        data["obsoleto_dal"] = obsoleto_dal

    meta = _extract_meta(payload, function_name=function_name)
    if meta is not _MISSING:
        data["meta"] = meta

    return data


# I vincoli di `catalogo.articoli` che l'operatore puo' violare, coi nomi
# della doc auto-generata. Il riconoscimento e la traduzione sono del BB
# `map_integrity_error`.
_ARTICOLO_UNIQUE: dict[str, tuple] = {
    "uq_articoli_codice": ("E_CATALOGO_VALIDATION", "Codice articolo gia' esistente.", "codice"),
    # Il legame articolo-causale e' 1:1. Il doppione lo rifiuta prima il guard
    # dell'onere col suo codice; l'indice scatta solo su due scritture
    # concorrenti, e risponde con lo stesso codice (§9.10, C-3).
    "uq_articoli_causale_onere": (
        "E_ARTICOLO_CAUSALE_ONERE_GIA_USATA",
        "La causale onere scelta e' gia' di un altro articolo.",
        "causale_onere_id",
    ),
}
# ⚠️ Il CHECK su composito/solo componente (brief-db-revisione-catalogo, BE10)
#    non ha UN campo: e' la coppia a essere incoerente, e il form spegne
#    l'uno quando l'altro e' acceso.
_ARTICOLO_CHECK: dict[str, tuple] = {
    "chk_articoli_composito_non_solo_componente": (
        "E_CATALOGO_VALIDATION",
        "Un articolo composito non puo' essere solo componente: spegnere uno dei due.",
    ),
}


# Scopo: Converte IntegrityError su articoli in errore applicativo leggibile.
def _translate_articolo_integrity_error(exc: IntegrityError, *, function_name: str) -> NoReturn:
    map_integrity_error(
        exc,
        unique_constraints=_ARTICOLO_UNIQUE,
        check_constraints=_ARTICOLO_CHECK,
        fallback_code="E_CATALOGO_VALIDATION",
        fallback_message="Violazione vincoli articolo.",
        function_name=function_name,
        log_to_db=True,
    )


# Scopo: Estrae il payload scrivibile di una UoM operativa con regole condivise.
def _extract_uom_operativa_payload(
    payload: dict[str, Any],
    *,
    for_update: bool,
    function_name: str,
) -> dict[str, Any]:
    data: dict[str, Any] = {}
    payload_message = "Payload UoM operativa non valido."

    if for_update:
        ErrorManager.require(
            "uom_id" not in payload,
            code="E_CATALOGO_VALIDATION",
            message="Payload UoM operativa non valido.",
            detail="uom_id e' immutabile e non puo' essere aggiornato.",
            context={"field": "uom_id"},
            function_name=function_name,
            log_to_db=True,
        )
        _V.validate_allowed_keys(
            payload,
            allowed=_UOM_UPDATE_ALLOWED_KEYS | {"uom_id"},
            function_name=function_name,
            message=payload_message,
        )
    else:
        _V.validate_allowed_keys(
            payload,
            allowed=_UOM_CREATE_ALLOWED_KEYS,
            function_name=function_name,
            message=payload_message,
        )
        data["uom_id"] = _extract_nullable_int(
            payload,
            "uom_id",
            function_name=function_name,
            message=payload_message,
        )
        ErrorManager.require(
            isinstance(data["uom_id"], int),
            code="E_CATALOGO_VALIDATION",
            message="Payload UoM operativa non valido.",
            detail="uom_id obbligatorio.",
            context={"field": "uom_id"},
            function_name=function_name,
            log_to_db=True,
        )

    for field_name in (
        "is_sell_uom",
        "is_purchase_uom",
        "is_logistic_uom",
        "forbid_fraction",
        "attivo",
    ):
        field_value = _extract_present_bool(
            payload,
            field_name,
            function_name=function_name,
            message=payload_message,
        )
        if field_value is not _MISSING:
            data[field_name] = field_value

    for field_name, min_value in {
        "factor_to_base": Decimal("0.000001"),
        "qty_step": Decimal("0.000001"),
    }.items():
        decimal_value = _V.extract_optional_decimal(
            payload,
            field_name,
            function_name=function_name,
            nullable=True,
            min_value=min_value,
            message=payload_message,
        )
        if decimal_value is not _MISSING:
            data[field_name] = decimal_value

    max_decimals = _extract_nullable_int(
        payload,
        "max_decimals",
        function_name=function_name,
        message=payload_message,
    )
    if not isinstance(max_decimals, _MissingType):
        ErrorManager.require(
            max_decimals is None or 0 <= max_decimals <= 6,
            code="E_CATALOGO_VALIDATION",
            message="Payload UoM operativa non valido.",
            detail="max_decimals deve essere compreso tra 0 e 6.",
            context={"field": "max_decimals", "value": max_decimals},
            function_name=function_name,
            log_to_db=True,
        )
        data["max_decimals"] = max_decimals

    gtin = _extract_string(
        payload,
        "gtin",
        function_name=function_name,
        nullable=True,
        message=payload_message,
    )
    if gtin is not _MISSING:
        data["gtin"] = gtin

    valido_dal = _extract_payload_date(
        payload,
        "valido_dal",
        function_name=function_name,
        nullable=True,
        message=payload_message,
    )
    valido_al = _extract_payload_date(
        payload,
        "valido_al",
        function_name=function_name,
        nullable=True,
        message=payload_message,
    )
    # Fase 4 (BE-only): centralizzato in `_apply_valido_dal_default`.
    valido_dal = _apply_valido_dal_default(valido_dal, for_create=not for_update)
    if valido_dal is not _MISSING:
        data["valido_dal"] = valido_dal
    if valido_al is not _MISSING:
        data["valido_al"] = valido_al
    # L'ordine delle date lo giudica il DB: guard comune
    # `script.trgfn_guard_date_validita`, E_DATA_AL_MINORE_DAL col campo
    # `valido_al`. ⚠️ Fino al 2026-10-09 qui c'era una copia della regola, gia'
    # DIVERGENTE: pretendeva `valido_al > valido_dal` e rifiutava il periodo di
    # un giorno solo, che il DB ammette.

    meta = _extract_meta(payload, function_name=function_name, message=payload_message)
    if meta is not _MISSING:
        data["meta"] = meta

    # La riga base (fattore 1, nessuna data) la tiene il DB:
    # `chk_articoli_uom_operativa_base_fissa`, tradotto in
    # `_UOM_OPERATIVA_CHECK`. ⛔ Fino al 2026-11-09 qui c'era una copia
    # PARZIALE della regola: scattava solo se il payload portava insieme
    # `is_base` e il fattore (D12, BE1 di brief-db-revisione-catalogo).

    forbid_fraction = data.get("forbid_fraction")
    if forbid_fraction is True:
        max_decimals_value = data.get("max_decimals")
        qty_step_value = data.get("qty_step")
        if max_decimals_value is not None:
            ErrorManager.require(
                max_decimals_value == 0,
                code="E_CATALOGO_VALIDATION",
                message="Payload UoM operativa non valido.",
                detail="Con forbid_fraction=true max_decimals deve essere 0.",
                context={"field": "max_decimals"},
                function_name=function_name,
                log_to_db=True,
            )
        if qty_step_value is not None:
            ErrorManager.require(
                qty_step_value == Decimal("1"),
                code="E_CATALOGO_VALIDATION",
                message="Payload UoM operativa non valido.",
                detail="Con forbid_fraction=true qty_step deve essere 1.",
                context={"field": "qty_step"},
                function_name=function_name,
                log_to_db=True,
            )

    return data


# Scopo: Estrae il payload scrivibile di un componente BoM nuovo.
# ⚠️ Solo la CREATE: dal 2026-11-10 un legame non si aggiorna (la PATCH e'
#    ritirata). La sua fine passa dal verbo (`fn_chiudi_componente`).
def _extract_componente_payload(
    payload: dict[str, Any],
    *,
    function_name: str,
) -> dict[str, Any]:
    data: dict[str, Any] = {}
    payload_message = "Payload componente non valido."

    _V.validate_allowed_keys(
        payload,
        allowed=_COMPONENTE_CREATE_ALLOWED_KEYS,
        function_name=function_name,
        message=payload_message,
    )
    componente_id = _extract_payload_uuid(
        payload,
        "componente_id",
        function_name=function_name,
        nullable=False,
        message=payload_message,
    )
    ErrorManager.require(
        isinstance(componente_id, UUID),
        code="E_CATALOGO_VALIDATION",
        message="Payload componente non valido.",
        detail="componente_id obbligatorio.",
        context={"field": "componente_id"},
        function_name=function_name,
        log_to_db=True,
    )
    data["componente_id"] = componente_id

    coeff_qta = _V.extract_optional_decimal(
        payload,
        "coeff_qta",
        function_name=function_name,
        nullable=False,
        min_value=Decimal("0"),
        message=payload_message,
    )
    if coeff_qta is not _MISSING:
        data["coeff_qta"] = coeff_qta
    else:
        ErrorManager.raise_error(
            code="E_CATALOGO_VALIDATION",
            message="Payload componente non valido.",
            detail="coeff_qta obbligatorio.",
            context={"field": "coeff_qta"},
            function_name=function_name,
            log_to_db=True,
        )

    valido_dal = _extract_payload_date(
        payload,
        "valido_dal",
        function_name=function_name,
        nullable=True,
        message=payload_message,
    )
    valido_al = _extract_payload_date(
        payload,
        "valido_al",
        function_name=function_name,
        nullable=True,
        message=payload_message,
    )
    # Fase 4 (BE-only): centralizzato in `_apply_valido_dal_default`.
    valido_dal = _apply_valido_dal_default(valido_dal, for_create=True)
    if valido_dal is not _MISSING:
        data["valido_dal"] = valido_dal
    if valido_al is not _MISSING:
        data["valido_al"] = valido_al
    # L'ordine delle date lo giudica il DB (guard comune
    # `script.trgfn_guard_date_validita`): vedi `_extract_uom_operativa_payload`.

    for field_name in (
        "obbligatorio",
        "attivo",
    ):
        field_value = _extract_present_bool(
            payload,
            field_name,
            function_name=function_name,
            message=payload_message,
        )
        if field_value is not _MISSING:
            data[field_name] = field_value

    # Il modo di esposizione in fattura e' un CODICE di
    # `config.esposizioni_componente`, non un booleano (dal 2026-10-01). Qui si
    # controlla solo che sia una stringa: i valori ammessi li giudica la FK, e
    # una copia del vocabolario in Python divergerebbe al primo modo nuovo.
    # NOT NULL a DB: `null` non e' ammesso, si omette per tenere il default.
    esposizione = _extract_string(
        payload,
        "esposizione_in_fattura",
        function_name=function_name,
        nullable=False,
        message=payload_message,
    )
    if esposizione is not _MISSING:
        data["esposizione_in_fattura"] = esposizione

    meta = _extract_meta(payload, function_name=function_name, message=payload_message)
    if meta is not _MISSING:
        data["meta"] = meta

    return data


# I vincoli di `catalogo.articoli_uom_operativa` e `catalogo.articoli_componenti`
# che l'operatore puo' violare scegliendo, coi nomi della doc auto-generata. Il
# resto (CHECK di forma, FK) lo ferma prima la validazione del payload, e cade
# sul ripiego del BB `map_integrity_error`.
# ⚠️ Il campo solo dove e' vero: l'articolo della UoM e' nella rotta, quindi
#    il doppione e' la UoM scelta; nel legame contano componente E periodo,
#    due scelte dell'operatore, e la tupla resta a due.
# ⭐ La mappatura si versiona (2026-11-09, D13/Q3, BE18): «cambiare» una
#    mappatura e' chiuderla e inserirne una nuova dal giorno dopo. La stessa
#    unita' torna quindi su piu' righe, e il doppione vero e' il PERIODO che si
#    sovrappone (`UNIQUE … WITHOUT OVERLAPS`, 23P01). Unita' e periodo sono due
#    scelte dell'operatore: la tupla resta a due, senza campo.
_UOM_OPERATIVA_UNIQUE: dict[str, tuple] = {
    "uq_articoli_uom_operativa_no_overlap": (
        "E_CATALOGO_VALIDATION",
        "L'unita' ha gia' una mappatura in un periodo che si sovrappone: chiudere quella in vigore "
        "prima di aprirne una nuova.",
    ),
}
# La riga base ha fattore 1 e nessuna data (D12): e' la coppia fattore/date a
# essere incoerente, nessun campo da solo.
_UOM_OPERATIVA_CHECK: dict[str, tuple] = {
    "chk_articoli_uom_operativa_base_fissa": (
        "E_CATALOGO_VALIDATION",
        "La riga dell'unita' base ha sempre fattore 1 e nessuna data di validita'.",
    ),
}
_COMPONENTE_UNIQUE: dict[str, tuple] = {
    "uq_articoli_componenti_no_overlap": (
        "E_CATALOGO_VALIDATION",
        "Il componente e' gia' nella distinta in un periodo che si sovrappone: chiudere il legame in vigore prima di aprirne uno nuovo.",
    ),
}


# Scopo: Converte IntegrityError su UoM operative in errore applicativo leggibile.
def _translate_uom_integrity_error(exc: IntegrityError, *, function_name: str) -> NoReturn:
    map_integrity_error(
        exc,
        unique_constraints=_UOM_OPERATIVA_UNIQUE,
        check_constraints=_UOM_OPERATIVA_CHECK,
        fallback_code="E_CATALOGO_VALIDATION",
        fallback_message="Violazione vincoli UoM operativa.",
        function_name=function_name,
        log_to_db=True,
    )


# Scopo: Converte IntegrityError su componenti BoM in errore applicativo leggibile.
def _translate_componente_integrity_error(exc: IntegrityError, *, function_name: str) -> NoReturn:
    map_integrity_error(
        exc,
        unique_constraints=_COMPONENTE_UNIQUE,
        fallback_code="E_CATALOGO_VALIDATION",
        fallback_message="Violazione vincoli componente.",
        function_name=function_name,
        log_to_db=True,
    )


# Scopo: Restituisce elenco articoli paginato con filtri, search e ordinamento.
def fn_list_articoli(
    *,
    attivo: bool | None = None,
    is_composito: bool | None = None,
    tipo_voce_id: int | None = None,
    gruppo_voce_id: int | None = None,
    listino_tipologia_id: int | None = None,
    search: str | None = None,
    data_da: date | None = None,
    data_a: date | None = None,
    order_by: str = "descrizione",
    order_dir: str | None = "asc",
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    function_name = "catalogo.catalogo_service.fn_list_articoli"
    order_by, order_dir = _validate_order(order_by, order_dir, function_name)

    repository = CatalogoRepository()
    return repository.list_articoli(
        attivo=attivo,
        is_composito=is_composito,
        tipo_voce_id=tipo_voce_id,
        gruppo_voce_id=gruppo_voce_id,
        listino_tipologia_id=listino_tipologia_id,
        search=search,
        data_da=data_da,
        data_a=data_a,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset,
    )


# Scopo: Restituisce il dettaglio di un articolo o solleva not found uniforme.
def _get_articolo_base(articolo_id: UUID | str) -> dict[str, Any]:
    repository = CatalogoRepository()
    articolo = repository.get_articolo(articolo_id)
    ErrorManager.require(
        articolo is not None,
        code="E_CATALOGO_ARTICOLO_NOT_FOUND",
        message="Articolo non trovato.",
        detail=f"Nessun articolo con id={articolo_id}.",
        context={"articolo_id": articolo_id},
        function_name="catalogo.catalogo_service.fn_get_articolo",
        log_to_db=False,
    )
    assert articolo is not None
    return articolo


# Scopo: Restituisce il dettaglio completo di un articolo con UoM, componenti
#        e i metadata `non_editable_fields` (Fase 5) per il FE.
def fn_get_articolo(articolo_id: UUID | str) -> dict[str, Any]:
    articolo = _get_articolo_base(articolo_id)
    uom_repository = CatalogoUomRepository()
    bom_repository = CatalogoBomRepository()

    articolo["uom_operative"] = uom_repository.list_uom_operative(articolo_id)
    articolo["componenti"] = (
        bom_repository.list_righe(articolo_id)
        if articolo.get("is_composito") is True
        else []
    )
    # ⛔ Niente `note` nel dettaglio (ritirato il 2026-11-11, decisione di
    #    Tid): era una terza lettura delle note, nessuno la leggeva. Le note
    #    si leggono dalla loro lista (`…/articoli/<id>/note/`, BB delle note).
    # record_id valorizzato: include lock condizionali (es. flag struttura
    # immutabili quando BoM attiva, seed 20260522-04). Senza record_id
    # avremmo solo i lock statici e l'UX non saprebbe del vincolo finche'
    # il trigger DB non rifiuta al save.
    articolo["non_editable_fields"] = compute_non_editable_fields(
        # `str(...)`: lo fa comunque il repository dei lock; qui rende il tipo
        # coerente con la firma (`UUID | str` -> `str`).
        "catalogo", "articoli", record_id=str(articolo_id),
    )
    # Le colonne che la correzione di struttura riapre (R-DB-3): le legge la
    # sede del DB, la stessa del verbo. Il FE non ne tiene una copia.
    articolo["struttura_correggibile"] = CatalogoRepository().colonne_struttura_articolo()
    return articolo


# Scopo: Crea un articolo e restituisce il dettaglio completo appena persistito.
def fn_create_articolo(payload: dict[str, Any]) -> dict[str, Any]:
    function_name = "catalogo.catalogo_service.fn_create_articolo"
    data = _extract_articolo_payload(payload, for_update=False, function_name=function_name)
    repository = CatalogoRepository()
    try:
        articolo_id = repository.create_articolo(data)
    except IntegrityError as exc:
        _translate_articolo_integrity_error(exc, function_name=function_name)
    return fn_get_articolo(articolo_id)


# La chiave del PATCH che porta la CORREZIONE DI STRUTTURA: `{colonna: valore}`
# delle sole colonne strutturali da cambiare (R-BE-1).
CHIAVE_CORREZIONE_STRUTTURA = "correzione_struttura"


# Scopo: Aggiorna un articolo sui soli campi presenti e restituisce il dettaglio aggiornato.
# ⭐ LA CORREZIONE DI STRUTTURA viaggia nello STESSO PATCH (R-BE-1 di
#    brief-db-articoli-ammessi-per-documento, 2026-10-18): `correzione_struttura`
#    porta le colonne strutturali da cambiare di un articolo anche se usato
#    (A-10, per un errore di caricamento). Prima il verbo, poi l'UPDATE, in UNA
#    transazione: un UPDATE rifiutato annulla anche la correzione. Fino ad
#    allora erano due chiamate (`POST …/struttura/`, poi il PATCH) e un PATCH
#    fallito lasciava la struttura gia' corretta.
# ⛔ Il backend non giudica la correzione: il permesso (SUPER_ADMIN), la forma
#    di `campi`, le colonne ammesse (`fn_articolo_colonne_struttura`), le righe
#    dei documenti aperti (A-11) e l'articolo inesistente li giudica il verbo
#    `catalogo.fn_articolo_correggi_struttura`, coi suoi codici. Una copia qui
#    divergerebbe.
def fn_update_articolo(articolo_id: UUID | str, payload: dict[str, Any]) -> dict[str, Any]:
    function_name = "catalogo.catalogo_service.fn_update_articolo"
    payload = dict(payload)
    correzione = payload.pop(CHIAVE_CORREZIONE_STRUTTURA, _MISSING)
    data = _extract_articolo_payload(payload, for_update=True, function_name=function_name)
    if correzione is _MISSING:
        _V.require_campi_da_aggiornare(
            data,
            message="Payload articolo non valido.",
            detail="Nessun campo aggiornabile presente nel payload.",
            context={"allowed_nullable_fields": sorted(_ARTICOLO_NULLABLE_FIELDS)},
            function_name=function_name,
        )
    repository = CatalogoRepository()
    with transaction.atomic():
        if correzione is not _MISSING:
            repository.correggi_struttura_articolo(articolo_id, correzione)
        if data:
            try:
                updated = repository.update_articolo(articolo_id, data)
            except IntegrityError as exc:
                _translate_articolo_integrity_error(exc, function_name=function_name)
            ErrorManager.require(
                updated,
                code="E_CATALOGO_ARTICOLO_NOT_FOUND",
                message="Articolo non trovato.",
                detail=f"Nessun articolo con id={articolo_id}.",
                context={"articolo_id": articolo_id},
                function_name=function_name,
                log_to_db=False,
            )
    return fn_get_articolo(articolo_id)


# Scopo: Disattiva soft un articolo e restituisce il dettaglio aggiornato.
def fn_disattiva_articolo(articolo_id: UUID | str) -> dict[str, Any]:
    articolo = fn_get_articolo(articolo_id)
    if articolo.get("attivo") is False:
        return articolo

    repository = CatalogoRepository()
    updated = repository.deactivate_articolo(articolo_id)
    ErrorManager.require(
        updated,
        code="E_CATALOGO_ARTICOLO_NOT_FOUND",
        message="Articolo non trovato.",
        detail=f"Nessun articolo attivo con id={articolo_id}.",
        context={"articolo_id": articolo_id},
        function_name="catalogo.catalogo_service.fn_disattiva_articolo",
        log_to_db=False,
    )
    return fn_get_articolo(articolo_id)


# Scopo: Riattiva un articolo (Fase 7) — pattern simmetrico a fn_disattiva.
# La fn DB `catalogo.fn_riattiva_articolo` e' idempotente su gia' attivo
# e raise E_ARTICOLO_NOT_FOUND se l'id non esiste. Pre-flight via
# fn_get_articolo (uniforma il NOT_FOUND con il codice catalogo).
# I figli (UoM operative, righe BoM) restano invariati: l'admin li
# riattiva esplicitamente in azioni successive (pattern AS/400).
def fn_riattiva_articolo(articolo_id: UUID | str) -> dict[str, Any]:
    function_name = "catalogo.catalogo_service.fn_riattiva_articolo"
    articolo = fn_get_articolo(articolo_id)
    if articolo.get("attivo") is True:
        return articolo

    repository = CatalogoRepository()
    # Eventuali violazioni di vincoli (es. nuovi UNIQUE su attivo) tradotte
    # in errore applicativo coerente con create/update. I trigger plpgsql
    # P0001 (parent inattivo) viaggiano come DatabaseError e li gestisce
    # il middleware: cattura mirata qui solo per IntegrityError noti.
    try:
        repository.reactivate_articolo(articolo_id)
    except IntegrityError as exc:
        _translate_articolo_integrity_error(exc, function_name=function_name)
    return fn_get_articolo(articolo_id)


# Scopo: Restituisce defaults pre-compilazione form articolo (Fase 8 — A5).
#        Centralizza il consumo dei parametri usati dal FE per il form di
#        creazione articolo (oggi: DEFAULT_IVA). Tipi gia' risolti: il FE non
#        duplica la conversione. Parametri malformati o non risolvibili
#        ritornano None (best-effort, no raise: il form mostra comunque,
#        l'utente seleziona manualmente).
#
# ⛔ IL PARAMETRO PORTA UNA CHIAVE NATURALE, NON UN ID, e la differenza NON e'
#    stilistica: fino al 2026-08-31 si chiamava `DEFAULT_IVA_ID` e stoccava
#    l'id `16`. Ora si chiama `DEFAULT_IVA` e vale `22`, cioe' il
#    `config.iva.codice_interno` dell'aliquota ordinaria
#    (`brief-db-default-iva-chiave-naturale`, `linee-guida-sql §6b`).
#
# ⛔ QUINDI NON SI FA `int()` SU QUEL VALORE, e il motivo e' che non
#    fallirebbe: `22` e' un numero, il cast riuscirebbe, e si otterrebbe l'ID
#    22 — che oggi in `config.iva` non esiste, ma che il modello ammette
#    eccome. Il giorno che esistesse sarebbe un'aliquota SBAGLIATA proposta in
#    silenzio, su un dato che finisce sui documenti fiscali. Si risolve con il
#    lookup sulla colonna lockata, che e' il building block previsto per questo.
def fn_get_articolo_form_defaults(
    *,
    django_user_id: int | None = None,
    group_ids: list[int] | None = None,
    emittente_fiscale_id: int | None = None,
) -> dict[str, Any]:
    service = ParameterService()
    raw = service.get_defaults(
        ["DEFAULT_IVA"],
        django_user_id=django_user_id,
        group_ids=group_ids,
        emittente_fiscale_id=emittente_fiscale_id,
    )
    return {"default_iva_id": _risolvi_default_iva_id(raw.get("DEFAULT_IVA"))}


# Scopo: dal `codice_interno` del parametro all'`id` di `config.iva`.
# Perimetro: best-effort — e' il contratto del form-defaults, che deve mostrare
#        il form anche quando un default non si risolve.
# ⚠️ MA NON MUTO: il ripiego a `None` e' indistinguibile a video da «non c'e'
#    un default configurato», quindi un seed che punta a un'aliquota
#    disattivata sparirebbe senza lasciare traccia. Il warning e' l'unico posto
#    in cui quella differenza resta leggibile.
def _risolvi_default_iva_id(codice_interno: object) -> int | None:
    if codice_interno is None or str(codice_interno).strip() == "":
        return None
    try:
        return resolve_config_id_by_codice_interno(
            "config.iva",
            str(codice_interno).strip(),
            etichetta="Aliquota IVA di default",
            function_name="catalogo.fn_get_articolo_form_defaults",
        )
    except ServiceError:
        # ⛔ `ServiceError` e NON `Exception`. Il ripiego serve per il caso
        #    previsto — `E_CONFIG_MANCANTE`, cioe' il codice non esiste o
        #    l'aliquota e' disattivata. Un `except` largo inghiottirebbe anche
        #    un errore di programmazione (un nome di tabella sbagliato, una
        #    firma cambiata) e lo farebbe uscire come «nessun default»: il
        #    difetto resterebbe vivo e invisibile per mesi.
        logger.warning(
            "DEFAULT_IVA non risolvibile: nessuna aliquota attiva con "
            "codice_interno=%r. Il form articolo non proporra' un'IVA.",
            codice_interno,
        )
        return None


# Scopo: Restituisce lookup articoli limitato per autocomplete cross-dominio.
def fn_lookup_articoli(
    *,
    search: str | None = None,
    attivo: bool | None = True,
    is_composito: bool | None = None,
    # R-5 (brief magazzino 2-bis): `None` = nessun filtro. Lo passa SOLO il
    # picker di riga di inventario e rettifica; altrove la tendina propone tutto.
    gestito_a_magazzino: bool | None = None,
    solo_oneri: bool = False,
    limit: int = 20,
) -> dict[str, Any]:
    _validate_lookup_limit(
        limit,
        max_limit=LOOKUP_ARTICOLI_MAX,
        function_name="catalogo.catalogo_service.fn_lookup_articoli",
    )
    repository = CatalogoRepository()
    results, troncato = repository.lookup_articoli(
        search=search,
        attivo=attivo,
        is_composito=is_composito,
        gestito_a_magazzino=gestito_a_magazzino,
        solo_oneri=solo_oneri,
        limit=limit,
    )
    return _lookup_response(results, troncato=troncato)


# Scopo: Il lookup articoli di una RIGA di documento (preventivo, ordine, bolla,
#        eccezioni di offerta e contratto, versione di listino, distinta, promo):
#        gli articoli trovati col `motivo` per cui il documento non li ammette
#        (None = ammesso), prima gli ammessi. Stesso envelope di
#        `fn_lookup_articoli` (`results` + `troncato`).
# ⭐ La regola e' del DB (`catalogo.fn_articoli_ammessi`, la check dei guard):
#    il service valida solo cio' che al cast diventerebbe un 500 e passa il resto.
#    Documento sconosciuto, id mancante, tipo d'eccezione o padre mancanti li
#    rifiuta la funzione, coi suoi codici.
def fn_lookup_articoli_ammessi(
    *,
    documento: str,
    documento_id: int | None = None,
    search: str | None = None,
    tipo_eccezione: str | None = None,
    articolo_padre_id: UUID | str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    function_name = "catalogo.catalogo_service.fn_lookup_articoli_ammessi"
    _validate_lookup_limit(limit, max_limit=LOOKUP_ARTICOLI_MAX, function_name=function_name)
    repository = CatalogoRepository()
    if tipo_eccezione is not None:
        ErrorManager.require(
            repository.tipo_eccezione_valido(tipo_eccezione),
            code="E_CATALOGO_VALIDATION",
            message="Parametri lookup non validi.",
            detail="tipo_eccezione non e' un valore di vendite.tipo_eccezione_contratto.",
            context={"tipo_eccezione": tipo_eccezione},
            function_name=function_name,
            log_to_db=True,
        )
    results, troncato = repository.lookup_articoli_ammessi(
        documento=documento,
        documento_id=documento_id,
        search=search,
        tipo_eccezione=tipo_eccezione,
        articolo_padre_id=articolo_padre_id,
        limit=limit,
    )
    return _lookup_response(results, troncato=troncato)


# Scopo: La PAGINA delle UoM operative dell'articolo (lista
#        `catalogo.articolo_uom`), previa verifica esistenza articolo: righe,
#        totale e `non_editable_fields` (il FE costruisce il form di edit da
#        una riga della lista, e i campi immutabili sono della collezione).
def fn_list_uom_operative_pagina(
    articolo_id: UUID | str,
    *,
    search: str | None = None,
    order_by: str | None = None,
    order_dir: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int, list[str]]:
    # La pagina della lista `catalogo.articolo_uom` (dal 2026-10-31), coi
    # campi non modificabili del form di riga (come la collezione intera).
    _get_articolo_base(articolo_id)
    if order_by:
        order_by, order_dir = validate_order_params(
            order_by, order_dir,
            allowed_columns=frozenset(ARTICOLO_UOM_ORDER_COLUMNS),
            error_code="E_VALIDATION_INPUT",
            nullable=True,
            function_name="catalogo.catalogo_service.fn_list_uom_operative_pagina",
        )
    results, total = CatalogoUomRepository().list_uom_operative_pagina(
        articolo_id, search=search, order_by=order_by, order_dir=order_dir, limit=limit, offset=offset,
    )
    return results, total, compute_non_editable_fields("catalogo", "articoli_uom_operativa")


# Scopo: Tutte le UoM operative dell'articolo, coi campi non modificabili:
#        per il lookup cross-dominio (`uom/lookup/`), che le vuole intere.
def fn_list_uom_operative(articolo_id: UUID | str) -> dict[str, Any]:
    _get_articolo_base(articolo_id)
    repository = CatalogoUomRepository()
    response = collezione_completa(repository.list_uom_operative(articolo_id))
    response["non_editable_fields"] = compute_non_editable_fields(
        "catalogo", "articoli_uom_operativa",
    )
    return response


# Scopo: Crea una UoM operativa per l'articolo e restituisce la riga arricchita.
def fn_create_uom_operativa(articolo_id: UUID | str, payload: dict[str, Any]) -> dict[str, Any]:
    function_name = "catalogo.catalogo_service.fn_create_uom_operativa"
    _get_articolo_base(articolo_id)
    # Fase 4 (BE-only): il fallback `valido_dal=today` se omesso e' applicato
    # internamente da `_extract_uom_operativa_payload` per garantire la
    # validazione coerente con valido_al.
    data = _extract_uom_operativa_payload(payload, for_update=False, function_name=function_name)
    repository = CatalogoUomRepository()
    try:
        uom_operativa_id = repository.create_uom_operativa(articolo_id, data)
    except IntegrityError as exc:
        _translate_uom_integrity_error(exc, function_name=function_name)
    result = repository.get_uom_operativa(articolo_id, uom_operativa_id)
    assert result is not None
    result["non_editable_fields"] = compute_non_editable_fields(
        "catalogo", "articoli_uom_operativa",
    )
    return result


# Scopo: Aggiorna una UoM operativa per l'articolo e restituisce la riga aggiornata.
def fn_update_uom_operativa(
    articolo_id: UUID | str,
    uom_operativa_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    function_name = "catalogo.catalogo_service.fn_update_uom_operativa"
    _get_articolo_base(articolo_id)
    data = _extract_uom_operativa_payload(payload, for_update=True, function_name=function_name)
    _V.require_campi_da_aggiornare(
        data,
        message="Payload UoM operativa non valido.",
        detail="Nessun campo aggiornabile presente nel payload.",
        function_name=function_name,
    )
    repository = CatalogoUomRepository()
    try:
        updated = repository.update_uom_operativa(articolo_id, uom_operativa_id, data)
    except IntegrityError as exc:
        _translate_uom_integrity_error(exc, function_name=function_name)
    ErrorManager.require(
        updated,
        code="E_CATALOGO_UOM_NOT_FOUND",
        message="UoM operativa non trovata.",
        detail=f"Nessuna UoM operativa id={uom_operativa_id} per articolo id={articolo_id}.",
        context={"articolo_id": articolo_id, "uom_operativa_id": uom_operativa_id},
        function_name=function_name,
        log_to_db=False,
    )
    result = repository.get_uom_operativa(articolo_id, uom_operativa_id)
    assert result is not None
    result["non_editable_fields"] = compute_non_editable_fields(
        "catalogo", "articoli_uom_operativa",
    )
    return result


# Scopo: Elimina una UoM operativa per l'articolo con ownership check.
def fn_delete_uom_operativa(articolo_id: UUID | str, uom_operativa_id: int) -> dict[str, Any]:
    function_name = "catalogo.catalogo_service.fn_delete_uom_operativa"
    _get_articolo_base(articolo_id)
    repository = CatalogoUomRepository()
    try:
        deleted = repository.delete_uom_operativa(articolo_id, uom_operativa_id)
    except IntegrityError as exc:
        _translate_uom_integrity_error(exc, function_name=function_name)
    ErrorManager.require(
        deleted,
        code="E_CATALOGO_UOM_NOT_FOUND",
        message="UoM operativa non trovata.",
        detail=f"Nessuna UoM operativa id={uom_operativa_id} per articolo id={articolo_id}.",
        context={"articolo_id": articolo_id, "uom_operativa_id": uom_operativa_id},
        function_name=function_name,
        log_to_db=False,
    )
    return {"deleted": True}


# Scopo: Lista componenti BoM dell'articolo, previa verifica esistenza articolo.
def fn_list_componenti(articolo_id: UUID | str) -> dict[str, Any]:
    _get_articolo_base(articolo_id)
    repository = CatalogoBomRepository()
    return collezione_completa(repository.list_righe(articolo_id))


# Scopo: UNA PAGINA della distinta dell'articolo, per la lista configurabile
#        `catalogo.articolo_componenti` (brief-db-liste-righe-documento,
#        lotto C). «Leggi prima la testata» (BB core `pagina_dopo_testata`):
#        un articolo inesistente e' un 404, non una lista vuota. Fra le
#        opzioni, `valido_al` = il filtro «in vigore al» (None: tutte le
#        versioni); il resto e' il contratto della lista.
def fn_list_componenti_pagina(
    articolo_id: UUID | str, **opzioni: Any,
) -> tuple[list[dict[str, Any]], int]:
    return pagina_dopo_testata(
        lambda: _get_articolo_base(articolo_id),
        CatalogoBomRepository().list_righe_pagina, articolo_id, **opzioni,
    )


# Scopo: Crea un componente BoM per l'articolo e restituisce la riga arricchita.
def fn_create_componente(articolo_id: UUID | str, payload: dict[str, Any]) -> dict[str, Any]:
    function_name = "catalogo.catalogo_service.fn_create_componente"
    articolo = _get_articolo_base(articolo_id)
    data = _extract_componente_payload(payload, function_name=function_name)
    ErrorManager.require(
        str(data["componente_id"]) != str(articolo["id"]),
        code="E_CATALOGO_VALIDATION",
        message="Payload componente non valido.",
        detail="Un articolo non puo' essere componente di se stesso.",
        context={"articolo_id": str(articolo["id"]), "componente_id": str(data["componente_id"])},
        function_name=function_name,
        log_to_db=True,
    )
    # Fase 4 (BE-only): fallback `valido_dal=today` applicato internamente da
    # `_extract_componente_payload` (single source of truth, validato).
    repository = CatalogoBomRepository()
    try:
        componente_row_id = repository.create_componente(articolo_id, data)
    except IntegrityError as exc:
        _translate_componente_integrity_error(exc, function_name=function_name)
    result = repository.get_componente(articolo_id, componente_row_id)
    assert result is not None
    return result


# Scopo: ⛔ Il componente dell'URL esiste ED e' dell'articolo dell'URL, o 404.
#        Prima l'articolo (`_get_articolo_base`, 404 suo), poi il componente
#        letto CON l'articolo (`get_componente` ha l'ownership nel WHERE).
#        Fino al 2026-10-21 le note di un componente ignoravano `articolo_id`
#        del path: un componente di un altro articolo si leggeva e si annotava
#        dall'URL di questo (brief-be-verifica-documentazione-api §B8; stessa
#        regola delle righe di vendita, `riga_del_padre_o_not_found`).
def _componente_dell_articolo(
    articolo_id: UUID | str, componente_id: UUID | str, *, function_name: str,
) -> dict[str, Any]:
    _get_articolo_base(articolo_id)
    return o_not_found(
        CatalogoBomRepository().get_componente(articolo_id, componente_id),
        code="E_CATALOGO_COMPONENTE_NOT_FOUND",
        message="Componente non trovato.",
        detail=f"Nessun componente id={componente_id} per articolo id={articolo_id}.",
        function_name=function_name,
    )


# Scopo: Il cancello del padre delle note di un legame di distinta (BB
#        `make_note_views`, `cancello_padre`): il legame dell'URL e'
#        dell'articolo dell'URL, o 404. Stessa regola di
#        `_componente_dell_articolo`, che resta la sede.
def fn_verifica_componente_dell_articolo(articolo_id: UUID | str, componente_id: UUID | str) -> None:
    _componente_dell_articolo(
        articolo_id, componente_id,
        function_name="catalogo.catalogo_service.fn_verifica_componente_dell_articolo",
    )


# ⭐ LA CHIUSURA DI UN LEGAME COI PREZZI BUNDLE (BE19 di
#    brief-db-revisione-catalogo, giro 3, 2026-11-10). Un legame che ha prezzi
#    bundle oltre la nuova fine non si chiude in silenzio: il verbo del DB
#    `catalogo.fn_chiudi_legame_distinta` rifiuta il primo tentativo con
#    `E_BOM_CHIUSURA_CON_PREZZI` (`confirm_and_retry`), la finestra elenca i
#    prezzi (`fn_get_chiusura_componente`) e la conferma DICHIARA quanti ne ha
#    visti (`prezzi_confermati`). E' lo stampo dell'annullo con legami
#    (`_annullo_con_legami.py`); un legame senza prezzi si chiude al primo colpo.
_CAMPO_PREZZI_CONFERMATI = "prezzi_confermati"


# Scopo: I prezzi bundle che la chiusura del legame alla data `valido_al`
#        tocca, per la finestra di conferma: le righe del lettore del DB e il
#        loro numero (`prezzi`), che e' cio' che la conferma dichiara.
# ⚠️ `prezzi` conta TUTTE le righe, come `legami` dell'annullo. Il verbo conta
#    le sole CHIUDE e TOGLIE, ma una riga BLOCCA o fuori perimetro gli fa
#    rifiutare la chiusura PRIMA del confronto: quando la conferma serve, i due
#    numeri coincidono. Scegliere qui quali esiti contare sarebbe una copia
#    della regola del verbo.
def fn_get_chiusura_componente(
    articolo_id: UUID | str, componente_id: UUID | str, params: dict[str, Any],
) -> dict[str, Any]:
    function_name = "catalogo.catalogo_service.fn_get_chiusura_componente"
    _componente_dell_articolo(articolo_id, componente_id, function_name=function_name)
    valido_al = _V.require_date(params, "valido_al", function_name=function_name)
    righe = CatalogoBomRepository().prezzi_legame_oltre_la_fine(componente_id, valido_al)
    return {"valido_al": valido_al, "prezzi": len(righe), "righe": righe}


# Scopo: Chiude il legame della distinta alla data `valido_al`, coi suoi
#        prezzi bundle, dal verbo del DB. Ritorna il legame come la lista lo
#        mostra e quanti prezzi il verbo ha chiuso e tolto.
# ⛔ Al primo tentativo `prezzi_confermati` NON c'e': dichiarare un numero mai
#    letto svuoterebbe la conferma. Un valore non intero e' un 400 col campo.
def fn_chiudi_componente(
    articolo_id: UUID | str, componente_id: UUID | str, payload: dict[str, Any],
) -> dict[str, Any]:
    function_name = "catalogo.catalogo_service.fn_chiudi_componente"
    _V.validate_allowed_keys(
        payload,
        allowed=frozenset({"valido_al", _CAMPO_PREZZI_CONFERMATI}),
        function_name=function_name,
        message="Payload chiusura componente non valido.",
    )
    _componente_dell_articolo(articolo_id, componente_id, function_name=function_name)
    valido_al = _V.require_date(payload, "valido_al", function_name=function_name)
    confermati = _V.optional_positive_int(
        payload, _CAMPO_PREZZI_CONFERMATI, function_name=function_name,
    )
    repository = CatalogoBomRepository()
    esito = repository.chiudi_legame(componente_id, valido_al, confermati)
    componente = repository.get_componente(articolo_id, componente_id)
    assert componente is not None
    return {
        "componente": componente,
        "prezzi_chiusi": esito["prezzi_chiusi"],
        "prezzi_tolti": esito["prezzi_tolti"],
    }


# ============================================================
# Sezione CRUD uom_tipi / unita_misura
# ============================================================

# Whitelist order_by derivate dalle costanti del repository, unica fonte di
# verita' — stesso schema di `_ORDER_BY_CONTRATTI`/`_ORDER_BY_OFFERTE`. Erano
# copie a mano: su offerte la stessa copia aveva gia' divergito.
_UOM_TIPO_ORDER_BY_VALIDI: frozenset[str] = frozenset(UOM_TIPI_ORDER_COLUMNS)
_UOM_TIPO_CREATE_ALLOWED_KEYS: frozenset[str] = frozenset({"codice", "codice_interno", "descrizione"})
# ⭐ Le whitelist UPDATE vengono dal repository (2026-09-26): la sua e' RIGIDA
#    (`execute_dynamic_update` -> RuntimeError), quindi il 400 qui deve
#    coprire esattamente le stesse chiavi — due copie a mano divergerebbero.
_UOM_TIPO_UPDATE_ALLOWED_KEYS: frozenset[str] = UOM_TIPI_UPDATE_COLUMNS
_UOM_ORDER_BY_VALIDI: frozenset[str] = frozenset(UOM_ORDER_COLUMNS)
_UOM_ALLOWED_KEYS: frozenset[str] = frozenset({"codice", "descrizione", "descrizione_fattura", "tipo_uom_id"})


# Scopo: Valida ordinamento UoM/tipi UoM contro whitelist locale.
def _validate_uom_order(
    order_by: str,
    order_dir: str | None,
    *,
    allowed: frozenset[str],
    function_name: str,
) -> tuple[str, str | None]:
    return validate_order_params(
        order_by,
        order_dir,
        allowed_columns=allowed,
        error_code="E_CATALOGO_VALIDATION",
        # `nullable`: direzione assente -> `None` e decide il default del
        # repository (`parse_list_params` non inventa piu' "asc", 2026-09-26).
        nullable=True,
        function_name=function_name,
    )


# Scopo: Traduce errori DB attesi nella scrittura UoM in ServiceError leggibili.
def _raise_uom_write_error(
    exc: DatabaseError,
    *,
    function_name: str,
    context: dict[str, Any],
) -> NoReturn:
    msg = str(exc).lower()
    if "fk_unita_misura_tipo_uom" in msg:
        ErrorManager.raise_error(
            code="E_CATALOGO_VALIDATION",
            message="Tipo UoM non valido.",
            detail="tipo_uom_id non esiste in catalogo.uom_tipi.",
            context=context,
            function_name=function_name,
            log_to_db=True,
            cause=exc,
        )
    if "cambio tipo uom non ammesso" in msg:
        ErrorManager.raise_error(
            code="E_CATALOGO_VALIDATION",
            message="Cambio tipo UoM non ammesso.",
            detail="La UoM partecipa a conversioni globali.",
            context=context,
            function_name=function_name,
            log_to_db=True,
            cause=exc,
        )
    raise exc


# Scopo: Lista paginata tipologie UoM con filtri e ordinamento.
def fn_list_uom_tipi(
    *,
    attivo: bool | None = None,
    search: str | None = None,
    order_by: str = "descrizione",
    order_dir: str | None = "asc",
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    function_name = "catalogo.catalogo_service.fn_list_uom_tipi"
    order_by, order_dir = _validate_uom_order(
        order_by,
        order_dir,
        allowed=_UOM_TIPO_ORDER_BY_VALIDI,
        function_name=function_name,
    )
    repository = CatalogoRepository()
    return repository.list_uom_tipi(
        attivo=attivo,
        search=search,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset,
    )


# Scopo: Dettaglio singola tipologia UoM.
def fn_get_uom_tipo(tipo_id: int) -> dict[str, Any]:
    function_name = "catalogo.catalogo_service.fn_get_uom_tipo"
    repository = CatalogoRepository()
    result = repository.get_uom_tipo(tipo_id)
    ErrorManager.require(
        result is not None,
        code="E_CATALOGO_UOM_TIPO_NOT_FOUND",
        message="Tipologia UoM non trovata.",
        detail=f"Nessuna tipologia UoM con id={tipo_id}.",
        context={"tipo_id": tipo_id},
        function_name=function_name,
        log_to_db=False,
    )
    assert result is not None
    return result


# Scopo: Crea una nuova tipologia UoM.
def fn_create_uom_tipo(payload: dict[str, Any]) -> dict[str, Any]:
    function_name = "catalogo.catalogo_service.fn_create_uom_tipo"
    _V.validate_allowed_keys(
        payload,
        allowed=_UOM_TIPO_CREATE_ALLOWED_KEYS,
        function_name=function_name,
        message="Payload tipologia UoM non valido.",
    )
    codice = _require_string(payload, "codice", function_name=function_name, message="Codice obbligatorio.")
    codice_interno = _require_string(
        payload,
        "codice_interno",
        function_name=function_name,
        message="Codice interno obbligatorio.",
    )
    descrizione = _require_string(payload, "descrizione", function_name=function_name, message="Descrizione obbligatoria.")

    # `codice` in maiuscolo lo mette il DB (CODICE_MAIUSCOLO); `codice_interno`
    # e' fuori da quella regola e resta normalizzato qui.
    data: dict[str, Any] = {
        "codice": codice,
        "codice_interno": codice_interno.upper(),
        "descrizione": descrizione,
    }

    repository = CatalogoRepository()
    try:
        new_id = repository.create_uom_tipo(data)
    except IntegrityError as exc:
        msg = str(exc).lower()
        if "uq_uom_tipi_codice" in msg or "uq_uom_tipi_codice_interno" in msg or "unique" in msg:
            ErrorManager.raise_error(
                code="E_CATALOGO_VALIDATION",
                message="Codice tipologia UoM gia' esistente.",
                detail=f"codice={codice}, codice_interno={codice_interno}.",
                context={"codice": codice, "codice_interno": codice_interno},
                function_name=function_name,
                log_to_db=True,
                cause=exc,
            )
        raise
    return fn_get_uom_tipo(new_id)


# Scopo: Aggiorna una tipologia UoM.
def fn_update_uom_tipo(tipo_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    function_name = "catalogo.catalogo_service.fn_update_uom_tipo"
    _V.validate_allowed_keys(
        payload,
        allowed=_UOM_TIPO_UPDATE_ALLOWED_KEYS,
        function_name=function_name,
        message="Payload tipologia UoM non valido.",
    )
    data: dict[str, Any] = {}
    descrizione = _extract_string(payload, "descrizione", function_name=function_name, nullable=False)
    if descrizione is not _MISSING:
        data["descrizione"] = descrizione
    attivo = _extract_present_bool(payload, "attivo", function_name=function_name, message="Payload tipologia UoM non valido.")
    if attivo is not _MISSING:
        data["attivo"] = attivo

    # ⛔ Un PATCH senza campi e' un 400, non un 200 che non scrive (Tid,
    #    2026-10-20, brief-be-verifica-documentazione-api §A2).
    _V.require_campi_da_aggiornare(
        data,
        message="Payload tipologia UoM non valido.",
        detail="Nessun campo aggiornabile presente nel payload.",
        function_name=function_name,
    )
    repository = CatalogoRepository()
    updated = repository.update_uom_tipo(tipo_id, data)
    ErrorManager.require(
        updated,
        code="E_CATALOGO_UOM_TIPO_NOT_FOUND",
        message="Tipologia UoM non trovata.",
        detail=f"Nessuna tipologia UoM con id={tipo_id}.",
        context={"tipo_id": tipo_id},
        function_name=function_name,
        log_to_db=False,
    )
    return fn_get_uom_tipo(tipo_id)


# Scopo: Lista paginata unita' di misura con filtri e ordinamento.
def fn_list_unita_misura(
    *,
    attivo: bool | None = None,
    search: str | None = None,
    order_by: str = "codice",
    order_dir: str | None = "asc",
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    function_name = "catalogo.catalogo_service.fn_list_unita_misura"
    order_by, order_dir = _validate_uom_order(
        order_by,
        order_dir,
        allowed=_UOM_ORDER_BY_VALIDI,
        function_name=function_name,
    )
    repository = CatalogoRepository()
    return repository.list_unita_misura(
        attivo=attivo,
        search=search,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset,
    )


# Scopo: Dettaglio singola unita' di misura.
def fn_get_unita_misura(uom_id: int) -> dict[str, Any]:
    function_name = "catalogo.catalogo_service.fn_get_unita_misura"
    repository = CatalogoRepository()
    result = repository.get_unita_misura(uom_id)
    ErrorManager.require(
        result is not None,
        code="E_CATALOGO_UOM_NOT_FOUND",
        message="Unita' di misura non trovata.",
        detail=f"Nessuna unita' di misura con id={uom_id}.",
        context={"uom_id": uom_id},
        function_name=function_name,
        log_to_db=False,
    )
    assert result is not None
    return result


# Scopo: Crea una nuova unita' di misura.
def fn_create_unita_misura(payload: dict[str, Any]) -> dict[str, Any]:
    function_name = "catalogo.catalogo_service.fn_create_unita_misura"
    _V.validate_allowed_keys(payload, allowed=_UOM_ALLOWED_KEYS, function_name=function_name, message="Payload UoM non valido.")
    codice = _require_string(payload, "codice", function_name=function_name, message="Codice obbligatorio.")
    descrizione = _require_string(payload, "descrizione", function_name=function_name, message="Descrizione obbligatoria.")
    descrizione_fattura = _extract_string(payload, "descrizione_fattura", function_name=function_name, nullable=True)
    tipo_uom_id = _extract_nullable_int(payload, "tipo_uom_id", function_name=function_name, message="Tipo UoM obbligatorio.")
    ErrorManager.require(
        isinstance(tipo_uom_id, int) and tipo_uom_id > 0,
        code="E_CATALOGO_VALIDATION",
        message="Tipo UoM obbligatorio.",
        detail="tipo_uom_id deve essere un intero positivo.",
        context={"tipo_uom_id": None if tipo_uom_id is _MISSING else tipo_uom_id},
        function_name=function_name,
        log_to_db=True,
    )

    # Il maiuscolo del codice lo mette il DB (CODICE_MAIUSCOLO): non si ricopia.
    data: dict[str, Any] = {"codice": codice, "descrizione": descrizione, "tipo_uom_id": tipo_uom_id}
    if descrizione_fattura is not _MISSING:
        data["descrizione_fattura"] = descrizione_fattura

    repository = CatalogoRepository()
    try:
        new_id = repository.create_unita_misura(data)
    except DatabaseError as exc:
        msg = str(exc).lower()
        if "uq_unita_misura_codice" in msg or "unique" in msg:
            ErrorManager.raise_error(
                code="E_CATALOGO_VALIDATION",
                message="Codice UoM gia' esistente.",
                detail=f"codice={codice} gia' presente.",
                context={"codice": codice},
                function_name=function_name,
                log_to_db=True,
                cause=exc,
            )
        _raise_uom_write_error(
            exc,
            function_name=function_name,
            context={"codice": codice, "tipo_uom_id": tipo_uom_id},
        )
    return fn_get_unita_misura(new_id)


# Scopo: Aggiorna una unita' di misura.
def fn_update_unita_misura(uom_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    function_name = "catalogo.catalogo_service.fn_update_unita_misura"
    # Il payload per presenza (BB): chiave fuori contratto e PATCH senza campi
    # sono un 400 (Tid, 2026-10-20, brief-be-verifica-documentazione-api §A2).
    data = _V.campi_per_presenza(
        payload, ammesse=UNITA_MISURA_UPDATE_COLUMNS,
        testi={"descrizione": (False, None), "descrizione_fattura": (True, None)},
        interi={"tipo_uom_id": False},
        flag=frozenset({"attivo"}),
        message="Payload UoM non valido.",
        message_vuoto="Payload UoM non valido.",
        detail_vuoto="Nessun campo aggiornabile presente nel payload.",
        function_name=function_name,
    )
    repository = CatalogoRepository()
    try:
        updated = repository.update_unita_misura(uom_id, data)
    except DatabaseError as exc:
        _raise_uom_write_error(
            exc,
            function_name=function_name,
            context={"uom_id": uom_id, "tipo_uom_id": data.get("tipo_uom_id")},
        )
    ErrorManager.require(
        updated,
        code="E_CATALOGO_UOM_NOT_FOUND",
        message="Unita' di misura non trovata.",
        detail=f"Nessuna unita' di misura con id={uom_id}.",
        context={"uom_id": uom_id},
        function_name=function_name,
        log_to_db=False,
    )
    return fn_get_unita_misura(uom_id)


# Scopo: Disattiva una unita' di misura (soft-delete con guard DB).
def fn_disattiva_unita_misura(uom_id: int) -> dict[str, Any]:
    function_name = "catalogo.catalogo_service.fn_disattiva_unita_misura"
    repository = CatalogoRepository()
    try:
        deactivated = repository.deactivate_unita_misura(uom_id)
    except IntegrityError as exc:
        ErrorManager.raise_error(
            code="E_CATALOGO_VALIDATION",
            message="Impossibile disattivare: esistono entita' collegate attive.",
            detail=str(exc),
            context={"uom_id": uom_id},
            function_name=function_name,
            log_to_db=True,
            cause=exc,
        )
    ErrorManager.require(
        deactivated,
        code="E_CATALOGO_UOM_NOT_FOUND",
        message="Unita' di misura non trovata o gia' disattivata.",
        detail=f"Nessuna unita' di misura attiva con id={uom_id}.",
        context={"uom_id": uom_id},
        function_name=function_name,
        log_to_db=False,
    )
    return fn_get_unita_misura(uom_id)


# =================================================================
# Conversioni UoM (catalogo.unita_misura_conversioni)
# =================================================================

_CONV_CREATE_KEYS: frozenset[str] = frozenset({
    "uom_from_id", "uom_to_id", "fattore", "valido_dal", "valido_al",
})
_CONV_UPDATE_KEYS: frozenset[str] = CONVERSIONI_UPDATE_COLUMNS
_CONV_ORDER_BY_VALIDI: frozenset[str] = frozenset(UOM_CONVERSIONI_ORDER_COLUMNS)


# Scopo: Lista paginata conversioni UoM, con join UoM per display.
#        Filtro opzionale `uom_id` (conversioni da/verso una UoM), usato dal
#        sotto-drawer conversioni.
#
# Paginata e ordinabile dal 2026-08-01 (seed lista 'catalogo.conversioni_uom',
# terzo lotto). Prima ignorava `order_by` e leggeva 9999 righe in un colpo:
# il repository sapeva gia' ordinare e paginare, era questo strato a
# schiacciarlo — e col catalogo che dichiara 4 colonne ordinabili sarebbero
# state 4 frecce che non ordinano.
def fn_list_conversioni(
    *,
    attivo: bool | None = None,
    uom_id: int | None = None,
    search: str | None = None,
    order_by: str = "uom_from_codice",
    order_dir: str | None = "asc",
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    function_name = "catalogo.catalogo_service.fn_list_conversioni"
    order_by, order_dir = _validate_uom_order(
        order_by,
        order_dir,
        allowed=_CONV_ORDER_BY_VALIDI,
        function_name=function_name,
    )
    repository = CatalogoRepository()
    return repository.list_conversioni(
        attivo=attivo,
        uom_id=uom_id,
        search=search,
        limit=limit, offset=offset,
        order_by=order_by, order_dir=order_dir,
    )


# Scopo: Dettaglio singola conversione UoM.
def fn_get_conversione(conv_id: int) -> dict[str, Any]:
    function_name = "catalogo.catalogo_service.fn_get_conversione"
    repository = CatalogoRepository()
    result = repository.get_conversione(conv_id)
    ErrorManager.require(
        result is not None,
        code="E_CATALOGO_CONV_NOT_FOUND",
        message="Conversione UoM non trovata.",
        detail=f"Nessuna conversione con id={conv_id}.",
        context={"conv_id": conv_id},
        function_name=function_name,
        log_to_db=False,
    )
    assert result is not None
    # Fase 5: arricchisce il detail coi campi non editabili (uom_from_id,
    # uom_to_id immutabili dopo create per coerenza con exclude daterange).
    result["non_editable_fields"] = compute_non_editable_fields(
        "catalogo", "unita_misura_conversioni",
    )
    return result


# Scopo: Crea una nuova conversione UoM (uom_from -> uom_to con fattore).
def fn_create_conversione(payload: dict[str, Any]) -> dict[str, Any]:
    function_name = "catalogo.catalogo_service.fn_create_conversione"
    _V.validate_allowed_keys(payload, allowed=_CONV_CREATE_KEYS, function_name=function_name, message="Payload conversione non valido.")

    uom_from_id = _extract_nullable_int(payload, "uom_from_id", function_name=function_name, message="Payload conversione non valido.")
    ErrorManager.require(
        uom_from_id is not _MISSING and uom_from_id is not None,
        code="E_CATALOGO_VALIDATION",
        message="UoM Da obbligatorio.",
        function_name=function_name,
        log_to_db=True,
    )
    uom_to_id = _extract_nullable_int(payload, "uom_to_id", function_name=function_name, message="Payload conversione non valido.")
    ErrorManager.require(
        uom_to_id is not _MISSING and uom_to_id is not None,
        code="E_CATALOGO_VALIDATION",
        message="UoM A obbligatorio.",
        function_name=function_name,
        log_to_db=True,
    )
    ErrorManager.require(
        uom_from_id != uom_to_id,
        code="E_CATALOGO_VALIDATION",
        message="UoM Da e UoM A devono essere diverse.",
        detail=f"uom_from_id={uom_from_id}, uom_to_id={uom_to_id}",
        function_name=function_name,
        log_to_db=True,
    )
    fattore = _V.extract_optional_decimal(payload, "fattore", function_name=function_name, nullable=False, min_value=Decimal("0.000001"), message="Payload conversione non valido.")
    ErrorManager.require(
        fattore is not _MISSING,
        code="E_CATALOGO_VALIDATION",
        message="Fattore obbligatorio.",
        function_name=function_name,
        log_to_db=True,
    )
    valido_dal = _extract_payload_date(payload, "valido_dal", function_name=function_name, nullable=True, message="Payload conversione non valido.")
    valido_al = _extract_payload_date(payload, "valido_al", function_name=function_name, nullable=True, message="Payload conversione non valido.")
    # Fase 4 (BE-only): centralizzato in `_apply_valido_dal_default`.
    valido_dal = _apply_valido_dal_default(valido_dal, for_create=True)
    # L'ordine delle date lo giudica il DB (guard comune
    # `script.trgfn_guard_date_validita`): vedi `_extract_uom_operativa_payload`.

    data: dict[str, Any] = {
        "uom_from_id": uom_from_id,
        "uom_to_id": uom_to_id,
        "fattore": fattore,
        "valido_dal": valido_dal,
    }
    if valido_al is not _MISSING:
        data["valido_al"] = valido_al

    repository = CatalogoRepository()
    try:
        new_id = repository.create_conversione(data)
    except DatabaseError as exc:
        _translate_conversione_integrity_error(exc, function_name=function_name)
        raise
    return fn_get_conversione(new_id)


# Scopo: Aggiorna una conversione UoM (fattore, date validita', attivo).
#        uom_from_id e uom_to_id sono immutabili dopo la creazione.
def fn_update_conversione(conv_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    function_name = "catalogo.catalogo_service.fn_update_conversione"
    _V.validate_allowed_keys(payload, allowed=_CONV_UPDATE_KEYS, function_name=function_name, message="Payload conversione non valido.")

    data: dict[str, Any] = {}
    fattore = _V.extract_optional_decimal(payload, "fattore", function_name=function_name, nullable=False, min_value=Decimal("0.000001"), message="Payload conversione non valido.")
    if fattore is not _MISSING:
        data["fattore"] = fattore
    valido_dal = _extract_payload_date(payload, "valido_dal", function_name=function_name, nullable=True, message="Payload conversione non valido.")
    if valido_dal is not _MISSING:
        data["valido_dal"] = valido_dal
    valido_al = _extract_payload_date(payload, "valido_al", function_name=function_name, nullable=True, message="Payload conversione non valido.")
    if valido_al is not _MISSING:
        data["valido_al"] = valido_al
    # L'ordine delle date lo giudica il DB (guard comune
    # `script.trgfn_guard_date_validita`): vedi `_extract_uom_operativa_payload`.
    attivo = _extract_present_bool(payload, "attivo", function_name=function_name, message="Payload conversione non valido.")
    if attivo is not _MISSING:
        data["attivo"] = attivo

    # ⛔ Un PATCH senza campi e' un 400, non un 200 che non scrive (Tid,
    #    2026-10-20, brief-be-verifica-documentazione-api §A2).
    _V.require_campi_da_aggiornare(
        data,
        message="Payload conversione non valido.",
        detail="Nessun campo aggiornabile presente nel payload.",
        function_name=function_name,
    )
    repository = CatalogoRepository()
    try:
        updated = repository.update_conversione(conv_id, data)
    except DatabaseError as exc:
        _translate_conversione_integrity_error(exc, function_name=function_name)
        raise
    ErrorManager.require(
        updated,
        code="E_CATALOGO_CONV_NOT_FOUND",
        message="Conversione UoM non trovata.",
        detail=f"Nessuna conversione con id={conv_id}.",
        context={"conv_id": conv_id},
        function_name=function_name,
        log_to_db=False,
    )
    return fn_get_conversione(conv_id)


# I vincoli di `catalogo.unita_misura_conversioni` che l'operatore puo'
# violare, coi nomi del catalogo (riconosciuti dal BB `map_integrity_error`).
# ⭐ Una conversione per coppia NON orientata e periodo (2026-11-09, D14, BE18):
#    kg→g e g→kg nello stesso periodo sono la stessa conversione detta due
#    volte, e l'EXCLUDE la rifiuta (23P01). Coppia e periodo sono scelte
#    dell'operatore: niente campo.
_CONVERSIONE_EXCLUDE: dict[str, tuple] = {
    "ex_unita_misura_conversioni_coppia_no_overlap": (
        "E_CATALOGO_VALIDATION",
        "Esiste gia' una conversione fra queste due unita' (in uno dei due versi) in un periodo che "
        "si sovrappone: chiudere quella in vigore prima di aprirne una nuova.",
    ),
}
# La frase di ripiego, una volta: la usano il BB (vincolo senza nome in mappa)
# e il ramo dei DatabaseError che non sono violazioni d'integrita'.
_CONVERSIONE_MSG_GENERICO = "Dati conversione non validi."
_CONVERSIONE_CHECK: dict[str, tuple] = {
    "chk_uom_conv_no_self": ("E_CATALOGO_VALIDATION", "UoM Da e UoM A devono essere diverse."),
}
_CONVERSIONE_FK: dict[str, tuple] = {
    "fk_uom_conv_from": ("E_CATALOGO_VALIDATION", "Unita' di misura non trovata.", "uom_from_id"),
    "fk_uom_conv_to": ("E_CATALOGO_VALIDATION", "Unita' di misura non trovata.", "uom_to_id"),
}


# Scopo: Traduce gli errori DB delle conversioni in messaggi utente.
def _translate_conversione_integrity_error(exc: DatabaseError, *, function_name: str) -> None:
    # ⭐ Un rifiuto del DB col suo codice di catalogo PASSA INTATTO: il
    #    chiamante rilancia l'eccezione (`raise`), e il traduttore del middleware
    #    la rende con codice, frase e campo del catalogo. 🔴 Fino al 2026-10-09
    #    il ripiego qui sotto ingoiava anche quelli: il guard comune delle date
    #    (`E_DATA_AL_MINORE_DAL`, campo `valido_al`) arrivava al client come
    #    «Dati conversione non validi.» senza campo da evidenziare — trovato
    #    togliendo la copia della regola dal service
    #    (`test_date_validita_guard_comune_db` 7).
    #    Dal 2026-11-09 il guard delle tipologie solleva il suo codice
    #    (`E_UOM_CONVERSIONE_TIPO_DIVERSO`, D6): il ramo che riconosceva la sua
    #    frase dentro `E_GENERICO` e' uscito, e con lui il riconoscimento dei
    #    vincoli dal testo («overlap», «foreign»): ora per nome, dal BB.
    if db_error_code(exc) is not None:
        return
    if isinstance(exc, IntegrityError):
        map_integrity_error(
            exc,
            unique_constraints=_CONVERSIONE_EXCLUDE,
            fk_constraints=_CONVERSIONE_FK,
            check_constraints=_CONVERSIONE_CHECK,
            fallback_code="E_CATALOGO_VALIDATION",
            fallback_message=_CONVERSIONE_MSG_GENERICO,
            function_name=function_name,
            log_to_db=True,
        )
    ErrorManager.raise_error(
        code="E_CATALOGO_VALIDATION",
        message=_CONVERSIONE_MSG_GENERICO,
        detail=str(exc),
        function_name=function_name,
        log_to_db=True,
        cause=exc,
    )
