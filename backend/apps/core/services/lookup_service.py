# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Facade applicativa per lookup generiche cross-schema (autocompletamento, ricerca).
# ------------------------------------------------------------

# Espone fn_list_lookup_codici come punto unico di accesso per tutte le lookup config.

import math

from django.db import DatabaseError

from apps.core.db.dbops_repository import LOOKUP_ORDER_COLONNE, DbopsRepository
from apps.core.services.error_manager import ErrorManager
from apps.core.services.list_helpers import validate_order_params

# La whitelist di ordinamento e' quella del repository (sede unica).
_ORDER_COL_VALIDI: frozenset[str] = frozenset(LOOKUP_ORDER_COLONNE)

# Mapping P0001 -> codice applicativo per errori sollevati da dbops.fn_get_lookup_codici.
# Pattern speculare a `pricing_service._KNOWN_DB_ERROR_MARKERS`: substring stretti
# multi-match per evitare falsi positivi. Marker "fn_get_lookup_codici" e' il nome
# della funzione DB (non localizzato) e fa da ancora; "Struttura tabella" e' la
# parte italiana del template in config.messaggi_errore id=456.
# Se la lingua dei messaggi cambia (GUC myapp.user_language), il match della
# stringa italiana fallisce e si cade nel fallback E_DATABASE; la soluzione
# strutturale (codice nel DETAIL del RAISE) e' rimandata al refactor DB.
_KNOWN_DB_ERROR_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "E_LOOKUP_STRUTTURA_TABELLA_INVALIDA",
        ("fn_get_lookup_codici", "Struttura tabella"),
    ),
)


# Scopo: Valida i parametri della richiesta e restituisce il risultato paginato della lookup.
# Obiettivo: esporre lista generica codici/descrizioni con filtro ILIKE opzionale.
# Perimetro: sola lettura; valida whitelist relazione, ordinamento e paginazione.
# Risultato: dict con count, page, page_size, total_pages, results (id, codice, descrizione).
def fn_list_lookup_codici(
    *,
    rel: str,
    search: str | None = None,
    order_col: str = "descrizione",
    order_dir: str = "asc",
    attivo_only: bool = True,
    includi_obsoleti: bool = True,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, object]:
    ErrorManager.require(
        page >= 1,
        code="E_CORE_VALIDATION",
        message="Parametri paginazione non validi.",
        detail="page deve essere >= 1",
        context={"page": page},
        function_name="core.lookup_service.fn_list_lookup_codici",
        log_to_db=True,
    )
    ErrorManager.require(
        1 <= page_size <= 200,
        code="E_CORE_VALIDATION",
        message="Parametri paginazione non validi.",
        detail="page_size deve essere compreso tra 1 e 200",
        context={"page_size": page_size},
        function_name="core.lookup_service.fn_list_lookup_codici",
        log_to_db=True,
    )
    # ⛔ Colonna e direzione dal BB `validate_order_params` (2026-09-26): qui
    #    c'era un secondo insieme `{asc, desc}` confrontato case-sensitive, per
    #    cui `DESC` era un 400 sulla lookup e passava sulle liste. La direzione
    #    torna normalizzata (`asc`/`desc`), e l'SQL la vuole maiuscola.
    order_col, order_dir = validate_order_params(
        order_col,
        order_dir,
        allowed_columns=_ORDER_COL_VALIDI,
        error_code="E_CORE_VALIDATION",
        function_name="core.lookup_service.fn_list_lookup_codici",
    )

    offset = (page - 1) * page_size
    repository = DbopsRepository()
    try:
        results, total_count = repository.list_lookup_codici(
            rel=rel,
            search=search,
            order_col=order_col,
            order_dir=order_dir.upper(),
            attivo_only=attivo_only,
            includi_obsoleti=includi_obsoleti,
            limit=page_size,
            offset=offset,
        )
    except DatabaseError as exc:
        # `fallback_code=None`: P0001 ignoti propagano l'eccezione originale
        # al middleware (mapping E_DATABASE).
        ErrorManager.raise_from_database_error(
            exc,
            known_markers=_KNOWN_DB_ERROR_MARKERS,
            fallback_code=None,
            message="Configurazione lookup non valida.",
            context={"rel": rel},
            function_name="core.lookup_service.fn_list_lookup_codici",
        )

    total_pages = math.ceil(total_count / page_size) if page_size > 0 else 0
    return {
        "count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "results": results,
    }


