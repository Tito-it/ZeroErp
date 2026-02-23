# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Servizio applicativo pipeline attivita fatturabili.
# ------------------------------------------------------------


from datetime import date

from apps.core.services.error_manager import ErrorManager
from apps.vendite.db.attivita_pipeline_repository import AttivitaPipelineRepository
from apps.vendite.services.attivita_pipeline_runner import (
    AttivitaPipelineParams,
    AttivitaPipelineRunner,
)
from apps.vendite.types import AttivitaTaskRunRow  # usato in fn_get_attivita_task_runs

# Facade sottile: firma simile alla SQL, comportamento delegato alle classi OOP.


# Scopo: Facade applicativa: avvia il runner pipeline attivita e restituisce lotto_id eseguito.
def pr_run_attivita_pipeline(
    *,
    lotto_id: int | None = None,
    competenza_mese: date | None = None,
    utility_id: int | None = None,
    billing_account_id: int | None = None,
    sorgente_tipo_id: int | None = None,
    emittente_soggetto_ruolo_id: int | None = None,
    lock_batch_id: str | None = None,
    meta: dict | None = None,
    dry_run: bool = False,
) -> int:
    """Entrypoint servizio Python: avvia pipeline attivita fatturabili."""
    runner = AttivitaPipelineRunner()
    params = AttivitaPipelineParams(
        lotto_id=lotto_id,
        competenza_mese=competenza_mese,
        utility_id=utility_id,
        billing_account_id=billing_account_id,
        sorgente_tipo_id=sorgente_tipo_id,
        emittente_soggetto_ruolo_id=emittente_soggetto_ruolo_id,
        lock_batch_id=lock_batch_id,
        meta=meta,
        dry_run=dry_run,
    )
    return runner.run_pipeline(params)


# Scopo: Restituisce stato lotto attivita con riepilogo task run aggregato per branch.
def fn_get_attivita_pipeline_status(*, lotto_id: int) -> dict:
    """Entrypoint servizio Python: stato pipeline e riepilogo branch per lotto attivita."""
    ErrorManager.require(
        bool(lotto_id and lotto_id > 0),
        code="E_ATTIVITA_VALIDATION",
        message="Parametri non validi.",
        detail="lotto_id obbligatorio e > 0",
        context={"lotto_id": lotto_id},
        function_name="vendite.attivita_pipeline_service.fn_get_attivita_pipeline_status",
        log_to_db=True,
    )
    repo = AttivitaPipelineRepository()
    lotto_stato = repo.get_lotto_attivita_full_stato(lotto_id)
    if lotto_stato is None:
        ErrorManager.raise_error(
            code="E_ATTIVITA_LOTTO_NOT_FOUND",
            message="Lotto attivita non trovato.",
            detail=f"Nessun lotto attivita con id={lotto_id}",
            context={"lotto_id": lotto_id},
            function_name="vendite.attivita_pipeline_service.fn_get_attivita_pipeline_status",
            log_to_db=True,
        )
    branch_summary = repo.get_attivita_branch_summary(lotto_id)
    return {
        "lotto_id": lotto_id,
        "stato_lotto": lotto_stato["stato_lotto"],
        "stato_operativo": lotto_stato["stato_operativo"],
        "branch_summary": branch_summary,
    }


# Scopo: Restituisce i task run runtime del lotto attivita per consultazione operativa.
def fn_get_attivita_task_runs(
    *,
    lotto_id: int,
    limit: int = 100,
    branch_code: str | None = None,
) -> dict:
    """Entrypoint servizio Python: lista task run lotto attivita con filtri opzionali."""
    ErrorManager.require(
        bool(lotto_id and lotto_id > 0),
        code="E_ATTIVITA_VALIDATION",
        message="Parametri non validi.",
        detail="lotto_id obbligatorio e > 0",
        context={"lotto_id": lotto_id},
        function_name="vendite.attivita_pipeline_service.fn_get_attivita_task_runs",
        log_to_db=True,
    )
    ErrorManager.require(
        1 <= int(limit) <= 500,
        code="E_ATTIVITA_VALIDATION",
        message="Parametri non validi.",
        detail="limit deve essere compreso tra 1 e 500",
        context={"lotto_id": lotto_id, "limit": limit},
        function_name="vendite.attivita_pipeline_service.fn_get_attivita_task_runs",
        log_to_db=True,
    )
    repo = AttivitaPipelineRepository()
    runs: list[AttivitaTaskRunRow] = repo.list_attivita_task_runs(
        lotto_id, branch_code=branch_code, limit=limit
    )
    return {
        "lotto_id": lotto_id,
        "count": len(runs),
        "task_runs": runs,
    }


