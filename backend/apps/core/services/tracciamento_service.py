# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Facade applicativa per il tracciamento processi e job.
#        Espone i tre livelli: audit log, task registry, job run log.
# ------------------------------------------------------------

# Service layer: valida parametri, delega ai repository, restituisce dict paginati.

from datetime import date

from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.api.payload_validators import envelope_da_offset
from apps.core.db.dbops_repository import ERROR_LOG_SORT_COLUMNS, DbopsRepository
from apps.core.db.maintenance_repository import MaintenanceRepository
from apps.core.services.error_manager import ErrorManager
from apps.core.services.list_helpers import validate_order_params

_STATUS_VALIDI: frozenset[str] = frozenset({"SUCCESS", "FAILED", "WARNING"})


# ------------------------------------------------------------------
# Audit Log
# ------------------------------------------------------------------

# Scopo: Restituisce la lista paginata dell'audit log con filtri opzionali.
# Obiettivo: esporre dbops.audit_log via API con validazione parametri.
# Perimetro: sola lettura.
def fn_list_audit_logs(
    *,
    status: str | None = None,
    function_name: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> dict:
    fn = "core.tracciamento_service.fn_list_audit_logs"

    if status is not None:
        ErrorManager.require(
            status in _STATUS_VALIDI,
            code="E_CORE_VALIDATION",
            message="Parametro status non valido.",
            detail=f"Valori ammessi: {sorted(_STATUS_VALIDI)}",
            context={"status": status},
            function_name=fn,
            log_to_db=True,
        )

    repo = DbopsRepository()
    results, total_count = repo.list_audit_logs(
        status=status,
        function_name=function_name,
        date_from=date_from,
        date_to=date_to,
        search=search,
        limit=limit,
        offset=offset,
    )
    return envelope_da_offset(results, total_count, limit=limit, offset=offset)


# ------------------------------------------------------------------
# Error Log — la consultazione dei tecnici (pezzo E, 2026-09-19)
# ------------------------------------------------------------------

# Scopo: la lista paginata di `dbops.error_log` col catalogo dei messaggi,
#        nella forma dell'audit log qui sopra. I filtri arrivano gia'
#        normalizzati dalla view (date ISO, `tx_id` uuid, testi strip):
#        qui si valida la pagina e si delega.
# ⚠️ `limit`/`offset` e non `page`/`page_size`: e' la lingua con cui gli
#    store-lista del frontend chiedono una pagina (`useListaStoreCore`),
#    la stessa del log email della stessa schermata. L'envelope resta quello
#    paginato standard, con la pagina derivata.
def fn_list_error_logs(
    *,
    area: str | None = None,
    function_name: str | None = None,
    codice: str | None = None,
    tx_id: str | None = None,
    data_da: str | None = None,
    data_a: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    order_by: str | None = None,
    order_dir: str | None = None,
) -> dict:
    fn = "core.tracciamento_service.fn_list_error_logs"
    ErrorManager.require(
        int(limit) > 0 and int(offset) >= 0,
        code="E_CORE_VALIDATION",
        message="Parametri di paginazione non validi.",
        detail=f"limit={limit}, offset={offset}",
        function_name=fn,
    )
    # ⛔ Un `order_by` fuori whitelist e' un 400, non un ripiego muto: il
    #    repository ripiegherebbe sulla data senza dirlo, e una lista ordinata
    #    diversamente da come e' stata chiesta non solleva niente. `nullable`:
    #    senza parametro l'ordine lo decide il default dichiarato a catalogo.
    validate_order_params(
        order_by,
        order_dir,
        allowed_columns=ERROR_LOG_SORT_COLUMNS,
        error_code="E_CORE_VALIDATION",
        function_name=fn,
        nullable=True,
    )
    results, total_count = DbopsRepository().list_error_logs(
        area=area,
        function_name=function_name,
        codice=codice,
        tx_id=tx_id,
        data_da=data_da,
        data_a=data_a,
        limit=limit,
        offset=offset,
        order_by=order_by,
        order_dir=order_dir,
    )
    return envelope_da_offset(results, total_count, limit=int(limit), offset=int(offset))


# ------------------------------------------------------------------
# Task Registry
# ------------------------------------------------------------------

# Scopo: Restituisce la lista paginata dei domini task.
def fn_list_domini_task(
    *,
    attivo_only: bool = True,
    search: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> dict:
    repo = DbopsRepository()
    results, total_count = repo.list_domini_task(
        attivo_only=attivo_only, search=search, limit=limit, offset=offset,
    )
    return envelope_da_offset(results, total_count, limit=limit, offset=offset)


# Scopo: Restituisce la lista paginata dei task registrati, con filtro dominio opzionale.
def fn_list_task_registry(
    *,
    dominio_codice: str | None = None,
    attivo_only: bool = True,
    search: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> dict:
    repo = DbopsRepository()
    results, total_count = repo.list_task_registry(
        dominio_codice=dominio_codice, attivo_only=attivo_only,
        search=search, limit=limit, offset=offset,
    )
    return envelope_da_offset(results, total_count, limit=limit, offset=offset)


# Scopo: Restituisce le implementazioni dei task con filtro su task_code e dominio.
def fn_list_task_implementations(
    *,
    task_code: str | None = None,
    dominio_codice: str | None = None,
    attivo_only: bool = True,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> dict:
    repo = DbopsRepository()
    results, total_count = repo.list_task_implementations(
        task_code=task_code, dominio_codice=dominio_codice,
        attivo_only=attivo_only, limit=limit, offset=offset,
    )
    return envelope_da_offset(results, total_count, limit=limit, offset=offset)


# ------------------------------------------------------------------
# Job Run Log
# ------------------------------------------------------------------

# Scopo: Restituisce la lista paginata delle esecuzioni job pgAgent.
def fn_list_job_runs(
    *,
    jobname: str | None = None,
    ok: bool | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> dict:
    repo = MaintenanceRepository()
    results, total_count = repo.list_job_runs(
        jobname=jobname, ok=ok, date_from=date_from, date_to=date_to,
        search=search, limit=limit, offset=offset,
    )
    return envelope_da_offset(results, total_count, limit=limit, offset=offset)


# Scopo: Restituisce il riepilogo dei job con conteggi esecuzioni e ultimo esito.
def fn_list_job_summary(
    *,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> dict:
    repo = MaintenanceRepository()
    results, total_count = repo.list_job_summary(
        limit=limit, offset=offset,
    )
    return envelope_da_offset(results, total_count, limit=limit, offset=offset)
