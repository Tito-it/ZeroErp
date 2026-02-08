# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Esecuzione step pipeline vendite.
# ------------------------------------------------------------


from typing import Any

from apps.core.services.error_manager import ErrorManager
from apps.vendite.db.pipeline_repository import LottoContext, VenditePipelineRepository
from apps.vendite.services.fatture_righe_service import FattureRigheService

# Esecutore di singolo step pipeline con mapping task JSON -> azioni applicative.

class PipelineStepExecutor:
    """Controparte Django della funzione SQL vendite.fn_execute_pipeline_step."""

    def __init__(
        self,
        repository: VenditePipelineRepository | None = None,
        fatture_righe_service: FattureRigheService | None = None,
    ) -> None:
        self.repository = repository or VenditePipelineRepository()
        self.fatture_righe_service = fatture_righe_service or FattureRigheService(self.repository)
        self.task_registry = {
            "select_attivita": self._handle_select_attivita_task,
            "generate_fatture_righe": self._handle_generate_fatture_righe_task,
        }

    def execute_step(
        self,
        lotto_id: int,
        stato_doc_fiscale_id: int,
        tipo_lotto: str,
        *,
        rollback: bool = False,
        dry_run: bool = False,
    ) -> None:
        ErrorManager.require(
            bool(lotto_id and stato_doc_fiscale_id and tipo_lotto and tipo_lotto.strip()),
            code="E_PIPELINE_VALIDATION",
            message="Parametri pipeline non validi.",
            detail="lotto_id, stato_doc_fiscale_id e tipo_lotto sono obbligatori",
            context={
                "lotto_id": lotto_id,
                "stato_doc_fiscale_id": stato_doc_fiscale_id,
                "tipo_lotto": tipo_lotto,
            },
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
        assert context is not None

        processi = self.repository.get_step_processes(
            stato_doc_fiscale_id,
            tipo_lotto=tipo_lotto,
            utility_id=context.utility_id,
            tipo_doc_fiscale_id=context.tipo_doc_fiscale_id,
            rollback=rollback,
        )
        ErrorManager.require(
            bool(processi),
            code="E_PIPELINE_NOT_FOUND",
            message="Configurazione pipeline non trovata.",
            detail=(
                "Pipeline non trovata o processi vuoti per "
                f"stato_doc_fiscale_id={stato_doc_fiscale_id}, tipo_lotto={tipo_lotto}"
            ),
            context={
                "stato_doc_fiscale_id": stato_doc_fiscale_id,
                "tipo_lotto": tipo_lotto,
                "rollback": rollback,
            },
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

        task_handler = self.task_registry.get(task)
        if task_handler is not None:
            task_handler(
                task=task,
                fn_name=fn_name,
                lotto_id=lotto_id,
                context=context,
                params=params,
                dry_run=dry_run,
            )
            return

        ErrorManager.raise_error(
            code="E_TASK_NOT_IMPLEMENTED",
            message="Task pipeline non implementato.",
            detail=f"Task pipeline non implementato: {task}",
            context={"task": task, "fase": fase},
            function_name="vendite.pipeline_step_executor._run_task",
            log_to_db=True,
        )

    def _validate_task_function_name(self, *, task: str, fn_name: str | None) -> None:
        # `fn` resta un token di compatibilita` SQL nella configurazione processi.
        allowed = self.repository.ALLOWED_TASK_FUNCTIONS[task]
        if fn_name and fn_name != allowed:
            ErrorManager.raise_error(
                code="E_TASK_NOT_ALLOWED",
                message="Funzione task non ammessa.",
                detail=f"Funzione non ammessa per task {task}: {fn_name}",
                context={"task": task, "fn": fn_name},
                function_name="vendite.pipeline_step_executor._validate_task_function_name",
                log_to_db=True,
            )

    def _handle_select_attivita_task(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int,
        context: LottoContext,
        params: dict[str, Any],
        dry_run: bool,
    ) -> None:
        self._validate_task_function_name(task=task, fn_name=fn_name)
        self.repository.run_select_attivita_task(context=context, params=params)

    def _handle_generate_fatture_righe_task(
        self,
        *,
        task: str,
        fn_name: str | None,
        lotto_id: int,
        context: LottoContext,
        params: dict[str, Any],
        dry_run: bool,
    ) -> None:
        self._validate_task_function_name(task=task, fn_name=fn_name)
        self.fatture_righe_service.generate_fatture_righe(lotto_id, dry_run=dry_run)
