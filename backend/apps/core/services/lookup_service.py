# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Facade applicativa per lookup generiche cross-schema (autocompletamento, ricerca).
# ------------------------------------------------------------

# Espone fn_list_lookup_codici come punto unico di accesso per tutte le lookup config.

import math

from apps.core.db.dbops_repository import DbopsRepository
from apps.core.services.error_manager import ErrorManager

_ORDER_COL_VALIDI: frozenset[str] = frozenset({"codice", "descrizione"})
_ORDER_DIR_VALIDI: frozenset[str] = frozenset({"asc", "desc"})


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
    ErrorManager.require(
        order_col in _ORDER_COL_VALIDI,
        code="E_CORE_VALIDATION",
        message="Parametro order_col non valido.",
        detail="Valori ammessi: codice, descrizione",
        context={"order_col": order_col},
        function_name="core.lookup_service.fn_list_lookup_codici",
        log_to_db=True,
    )
    ErrorManager.require(
        order_dir in _ORDER_DIR_VALIDI,
        code="E_CORE_VALIDATION",
        message="Parametro order_dir non valido.",
        detail="Valori ammessi: asc, desc",
        context={"order_dir": order_dir},
        function_name="core.lookup_service.fn_list_lookup_codici",
        log_to_db=True,
    )

    offset = (page - 1) * page_size
    repository = DbopsRepository()
    results, total_count = repository.list_lookup_codici(
        rel=rel,
        search=search,
        order_col=order_col,
        order_dir=order_dir.upper(),
        attivo_only=attivo_only,
        limit=page_size,
        offset=offset,
    )

    total_pages = math.ceil(total_count / page_size) if page_size > 0 else 0
    return {
        "count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "results": results,
    }
