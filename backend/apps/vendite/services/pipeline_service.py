from datetime import date
from typing import Any

from apps.vendite.services.pipeline_runner import LottoPipelineParams, LottoPipelineRunner
from apps.vendite.services.pipeline_step_executor import PipelineStepExecutor


def pr_run_lotto_pipeline(
    *,
    lotto_id: int | None = None,
    competenza_mese: date | None = None,
    tipo_doc_fiscale_id: int | None = None,
    utility_id: int | None = None,
    billing_account_id: int | None = None,
    lock_batch_id: int | None = None,
    meta: dict[str, Any] | None = None,
    dry_run: bool = False,
    tipo_lotto: str = "MASSIVO",
) -> int:
    """Python service entrypoint with the same intent as SQL procedure pr_run_lotto_pipeline."""
    runner = LottoPipelineRunner()
    params = LottoPipelineParams(
        lotto_id=lotto_id,
        competenza_mese=competenza_mese,
        tipo_doc_fiscale_id=tipo_doc_fiscale_id,
        utility_id=utility_id,
        billing_account_id=billing_account_id,
        lock_batch_id=lock_batch_id,
        meta=meta,
        dry_run=dry_run,
        tipo_lotto=tipo_lotto,
    )
    return runner.run(params)


def fn_execute_pipeline_step(
    *,
    lotto_id: int,
    stato_doc_fiscale_id: int,
    rollback: bool = False,
    dry_run: bool = False,
) -> None:
    """Python service entrypoint with the same intent as SQL function fn_execute_pipeline_step."""
    executor = PipelineStepExecutor()
    executor.execute_step(
        lotto_id=lotto_id,
        stato_doc_fiscale_id=stato_doc_fiscale_id,
        rollback=rollback,
        dry_run=dry_run,
    )
