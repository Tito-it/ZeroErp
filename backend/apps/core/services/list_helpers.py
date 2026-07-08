# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Helper condivisi per la validazione dei parametri lista nei service
#        (ordinamento, ...). BB cross-dominio estratto con la "regola del 2":
#        il pattern "order_by in whitelist + order_dir in {asc,desc}" era
#        duplicato in catalogo_service e listini_service (4 occorrenze).
# ------------------------------------------------------------

from __future__ import annotations

from apps.core.services.error_manager import ErrorManager

_ORDER_DIR_VALIDI = frozenset({"asc", "desc"})


# Scopo: Valida order_by contro una whitelist di colonne e order_dir contro
#        {asc, desc}. Il chiamante passa la propria whitelist (`allowed_columns`)
#        e il proprio `error_code` di dominio. Solleva ServiceError (loggato a DB)
#        sul primo parametro non valido; ritorna la coppia validata.
#
#        NB: DISTINTO da `apps.core.api.search_validators.validate_order_params`,
#        che ha semantica diversa (normalizza maiuscole, ritorna tupla opzionale,
#        nessun error_code di dominio). Questo opera nei service con rigore
#        fail-fast e codice errore parametrico.
def validate_order_params(
    order_by: str,
    order_dir: str,
    *,
    allowed_columns: frozenset[str],
    error_code: str,
    function_name: str,
) -> tuple[str, str]:
    ErrorManager.require(
        order_by in allowed_columns,
        code=error_code,
        message="Parametri ordinamento non validi.",
        detail="order_by deve essere uno tra: " + ", ".join(sorted(allowed_columns)),
        context={"order_by": order_by},
        function_name=function_name,
        log_to_db=True,
    )
    ErrorManager.require(
        order_dir in _ORDER_DIR_VALIDI,
        code=error_code,
        message="Parametri ordinamento non validi.",
        detail="order_dir deve essere 'asc' o 'desc'",
        context={"order_dir": order_dir},
        function_name=function_name,
        log_to_db=True,
    )
    return order_by, order_dir


# Scopo: Valida un parametro enum contro la whitelist del chiamante (aree,
#        stadi, sort key, ...). `None` e' ammesso quando `nullable` (filtro
#        opzionale assente). `allowed` come sequenza ORDINATA: l'ordine entra
#        nel messaggio `detail` (stabile per test e utenti). Estratto
#        2026-07-06 (regola del 2, ok Tid): unifica i blocchi
#        "ErrorManager.require(x in WHITELIST)" duplicati nei service vendite
#        (area fermi, stadio competenza, area backlog, sort_by/sort_dir lotto
#        fatture). Speculare a validate_order_params/validate_pagination.
def validate_enum_param(
    value: str | None,
    *,
    allowed: tuple[str, ...],
    param_name: str,
    error_code: str,
    function_name: str,
    nullable: bool = True,
    log_to_db: bool = False,
) -> str | None:
    ErrorManager.require(
        (value is None and nullable) or value in allowed,
        code=error_code,
        message=f"Parametro {param_name} non valido.",
        detail=f"Valori ammessi: {', '.join(allowed)}",
        context={param_name: value},
        function_name=function_name,
        log_to_db=log_to_db,
    )
    return value


# Scopo: Valida i parametri di paginazione page-based (page >= 1,
#        1 <= page_size <= 200) e ritorna l'offset calcolato `(page-1)*page_size`.
#        `error_code`/`function_name` parametrici. Speculare a `validate_order_params`.
#        NB: convenzione PAGE-based; per le liste offset-based esiste già
#        `parse_list_params` (apps/core/api/payload_validators.py).
def validate_pagination(
    page: int,
    page_size: int,
    *,
    error_code: str,
    function_name: str,
) -> int:
    ErrorManager.require(
        page >= 1,
        code=error_code,
        message="Parametri paginazione non validi.",
        detail="page deve essere >= 1",
        context={"page": page},
        function_name=function_name,
        log_to_db=True,
    )
    ErrorManager.require(
        1 <= page_size <= 200,
        code=error_code,
        message="Parametri paginazione non validi.",
        detail="page_size deve essere compreso tra 1 e 200",
        context={"page_size": page_size},
        function_name=function_name,
        log_to_db=True,
    )
    return (page - 1) * page_size
