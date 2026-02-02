from typing import Any

from apps.vendite.db.pipeline_repository import LottoContext, VenditePipelineRepository
from apps.vendite.services.exceptions import (
    PipelineTaskNotAllowedError,
    PipelineTaskNotImplementedError,
    PipelineValidationError,
)


class PipelineStepExecutor:
    """Django counterpart of vendite.fn_execute_pipeline_step."""

    def __init__(self, repository: VenditePipelineRepository | None = None) -> None:
        self.repository = repository or VenditePipelineRepository()

    def execute_step(
        self,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        *,
        rollback: bool = False,
        dry_run: bool = False,
    ) -> None:
        if not lotto_id or not stato_doc_fiscale_id:
            raise PipelineValidationError("lotto_id e stato_doc_fiscale_id sono obbligatori")

        context = self.repository.get_lotto_context(lotto_id)
        if context is None or context.competenza_mese is None:
            raise PipelineValidationError(f"Lotto non trovato: {lotto_id}")

        processi = self.repository.get_step_processes(stato_doc_fiscale_id, rollback=rollback)
        if not processi:
            raise PipelineValidationError(
                f"Pipeline non trovata o processi vuoti per stato_doc_fiscale_id={stato_doc_fiscale_id}"
            )

        for process in processi:
            self._run_task(
                lotto_id=lotto_id,
                stato_doc_fiscale_id=stato_doc_fiscale_id,
                process=process,
                context=context,
                rollback=rollback,
                dry_run=dry_run,
            )

    def _run_task(
        self,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        process: dict[str, Any],
        context: LottoContext,
        rollback: bool,
        dry_run: bool,
    ) -> None:
        task = str(process.get("task", "")).strip()
        fase = process.get("fase") or "Esecuzione step"
        params = process.get("params") or {}
        fn_name = params.get("fn")

        self.repository.log_pipeline_fase(
            lotto_id=lotto_id,
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            fase=fase,
            status="I",
            messaggio=None,
            meta={
                "task": task,
                "params": params,
                "rollback": rollback,
                "dry_run": dry_run,
            },
        )

        if dry_run or task in {"noop", "log_only"}:
            return

        if task == "select_attivita":
            if fn_name and fn_name != self.repository.ALLOWED_TASK_FUNCTIONS["select_attivita"]:
                raise PipelineTaskNotAllowedError(
                    f"Funzione non ammessa per task select_attivita: {fn_name}"
                )
            self.repository.run_select_attivita_task(context=context, params=params)
            return

        raise PipelineTaskNotImplementedError(f"Task pipeline non implementato: {task}")
