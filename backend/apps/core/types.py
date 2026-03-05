# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Tipi condivisi core per tracciamento processi, task registry, audit e job.
# ------------------------------------------------------------

from typing import Any, TypedDict


# --- Audit Log (dbops.audit_log) ---

class AuditLogRow(TypedDict):
    id: int
    function_name: str
    executed_by: str
    executed_at: str
    status: str
    message: str | None
    duration_ms: int | None
    tx_id: str | None
    exec_mode: str | None
    rule_type: str | None
    dry_run: bool | None
    rows_affected: int | None
    params: dict[str, Any] | None
    result: dict[str, Any] | None


# --- Task Registry (dbops.domini_task / pipeline_task_registry / pipeline_task_registry_impl) ---

class DominioTaskRow(TypedDict):
    id: int
    codice: str
    descrizione: str | None
    attivo: bool


class TaskRegistryRow(TypedDict):
    id: int
    dominio_id: int
    dominio_codice: str
    task_code: str
    descrizione: str | None
    attivo: bool


class TaskRegistryImplRow(TypedDict):
    id: int
    task_registry_id: int
    task_code: str
    implementation_key: str
    handler_code: str
    is_default: bool
    attivo: bool


# --- Job Run Log (maintenance.job_run_log) ---

class JobRunLogRow(TypedDict):
    id: int
    jobname: str
    stepname: str | None
    started_at: str
    ended_at: str | None
    ok: bool | None
    rows_affected: int | None
    message: str | None
    error_code: str | None
    error_detail: str | None
    agent_host: str | None
    run_uuid: str
