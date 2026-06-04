# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Facade applicativa per il tracciamento processi e job.
#        Espone i tre livelli: audit log, task registry, job run log.
# ------------------------------------------------------------

# Service layer: valida parametri, delega ai repository, restituisce dict paginati.

from apps.core.api.payload_validators import paginated_envelope
from apps.core.db.dbops_repository import DbopsRepository
from apps.core.db.maintenance_repository import MaintenanceRepository
from apps.core.services.error_manager import ErrorManager
from apps.core.services.list_helpers import validate_pagination

_STATUS_VALIDI: frozenset[str] = frozenset({"SUCCESS", "FAILED", "WARNING"})


def _validate_pagination(page: int, page_size: int, fn_name: str) -> int:
    # Scopo: Valida la paginazione page-based e ritorna l'offset. Delega al BB core.
    return validate_pagination(
        page, page_size, error_code="E_CORE_VALIDATION", function_name=fn_name,
    )


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
    date_from: str | None = None,
    date_to: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    fn = "core.tracciamento_service.fn_list_audit_logs"
    offset = _validate_pagination(page, page_size, fn)

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
        limit=page_size,
        offset=offset,
    )
    return paginated_envelope(results, total_count, page, page_size)


# ------------------------------------------------------------------
# Task Registry
# ------------------------------------------------------------------

# Scopo: Restituisce la lista paginata dei domini task.
def fn_list_domini_task(
    *,
    attivo_only: bool = True,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    fn = "core.tracciamento_service.fn_list_domini_task"
    offset = _validate_pagination(page, page_size, fn)
    repo = DbopsRepository()
    results, total_count = repo.list_domini_task(
        attivo_only=attivo_only, search=search, limit=page_size, offset=offset,
    )
    return paginated_envelope(results, total_count, page, page_size)


# Scopo: Restituisce la lista paginata dei task registrati, con filtro dominio opzionale.
def fn_list_task_registry(
    *,
    dominio_codice: str | None = None,
    attivo_only: bool = True,
    search: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> dict:
    fn = "core.tracciamento_service.fn_list_task_registry"
    offset = _validate_pagination(page, page_size, fn)
    repo = DbopsRepository()
    results, total_count = repo.list_task_registry(
        dominio_codice=dominio_codice, attivo_only=attivo_only,
        search=search, limit=page_size, offset=offset,
    )
    return paginated_envelope(results, total_count, page, page_size)


# Scopo: Restituisce le implementazioni dei task con filtro su task_code e dominio.
def fn_list_task_implementations(
    *,
    task_code: str | None = None,
    dominio_codice: str | None = None,
    attivo_only: bool = True,
    page: int = 1,
    page_size: int = 100,
) -> dict:
    fn = "core.tracciamento_service.fn_list_task_implementations"
    offset = _validate_pagination(page, page_size, fn)
    repo = DbopsRepository()
    results, total_count = repo.list_task_implementations(
        task_code=task_code, dominio_codice=dominio_codice,
        attivo_only=attivo_only, limit=page_size, offset=offset,
    )
    return paginated_envelope(results, total_count, page, page_size)


# ------------------------------------------------------------------
# Job Run Log
# ------------------------------------------------------------------

# Scopo: Restituisce la lista paginata delle esecuzioni job pgAgent.
def fn_list_job_runs(
    *,
    jobname: str | None = None,
    ok: bool | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    fn = "core.tracciamento_service.fn_list_job_runs"
    offset = _validate_pagination(page, page_size, fn)
    repo = MaintenanceRepository()
    results, total_count = repo.list_job_runs(
        jobname=jobname, ok=ok, date_from=date_from, date_to=date_to,
        search=search, limit=page_size, offset=offset,
    )
    return paginated_envelope(results, total_count, page, page_size)


# Scopo: Restituisce il riepilogo dei job con conteggi esecuzioni e ultimo esito.
def fn_list_job_summary(
    *,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    fn = "core.tracciamento_service.fn_list_job_summary"
    offset = _validate_pagination(page, page_size, fn)
    repo = MaintenanceRepository()
    results, total_count = repo.list_job_summary(
        limit=page_size, offset=offset,
    )
    return paginated_envelope(results, total_count, page, page_size)
