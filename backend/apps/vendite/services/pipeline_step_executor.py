from typing import Any

from apps.core.services.error_manager import ErrorManager
from apps.vendite.db.pipeline_repository import LottoContext, VenditePipelineRepository

# Esecutore di singolo step pipeline con mapping task JSON -> azioni applicative.

class PipelineStepExecutor:
    """Controparte Django della funzione SQL vendite.fn_execute_pipeline_step."""

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
        ErrorManager.require(
            bool(lotto_id and stato_doc_fiscale_id),
            code="E_PIPELINE_VALIDATION",
            message="Parametri pipeline non validi.",
            detail="lotto_id e stato_doc_fiscale_id sono obbligatori",
            context={"lotto_id": lotto_id, "stato_doc_fiscale_id": stato_doc_fiscale_id},
            function_name="vendite.pipeline_step_executor.execute_step",
            log_to_db=True,
        )

        context = self.repository.get_lotto_context(lotto_id)
        ErrorManager.require(
            context is not None and context.competenza_mese is not None,
            code="E_PIPELINE_LOTTO_NOT_FOUND",
            message="Lotto pipeline non trovato.",
            detail=f"Lotto non trovato: {lotto_id}",
            context={"lotto_id": lotto_id},
            function_name="vendite.pipeline_step_executor.execute_step",
            log_to_db=True,
        )

        processi = self.repository.get_step_processes(stato_doc_fiscale_id, rollback=rollback)
        ErrorManager.require(
            bool(processi),
            code="E_PIPELINE_NOT_FOUND",
            message="Configurazione pipeline non trovata.",
            detail=(
                "Pipeline non trovata o processi vuoti per "
                f"stato_doc_fiscale_id={stato_doc_fiscale_id}"
            ),
            context={"stato_doc_fiscale_id": stato_doc_fiscale_id, "rollback": rollback},
            function_name="vendite.pipeline_step_executor.execute_step",
            log_to_db=True,
        )

        # Esegue in ordine i task definiti nel JSON processi/rollback.
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
            # Whitelist esplicita per impedire esecuzione arbitraria da parametri JSON.
            if fn_name and fn_name != self.repository.ALLOWED_TASK_FUNCTIONS["select_attivita"]:
                ErrorManager.raise_error(
                    code="E_TASK_NOT_ALLOWED",
                    message="Funzione task non ammessa.",
                    detail=f"Funzione non ammessa per task select_attivita: {fn_name}",
                    context={"task": task, "fn": fn_name},
                    function_name="vendite.pipeline_step_executor._run_task",
                    log_to_db=True,
                )
            self.repository.run_select_attivita_task(context=context, params=params)
            return

        ErrorManager.raise_error(
            code="E_TASK_NOT_IMPLEMENTED",
            message="Task pipeline non implementato.",
            detail=f"Task pipeline non implementato: {task}",
            context={"task": task, "fase": fase},
            function_name="vendite.pipeline_step_executor._run_task",
            log_to_db=True,
        )
