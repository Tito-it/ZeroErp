# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Esecuzione step pipeline attivita fatturabili.
# ------------------------------------------------------------


from typing import Any

from apps.core.services.error_manager import ErrorManager
from apps.core.services.service_errors import ServiceError
from apps.vendite.db.attivita_pipeline_repository import (
    AttivitaPipelineRepository,
    AttivitaSorgenteBranchPolicy,
)
from apps.vendite.services.attivita_pipeline_error_logger import AttivitaPipelineErrorLogger

# Esecutore di singolo step pipeline con mapping task JSON -> azioni applicative.
# Branch indipendenti: errore BRANCH blocca solo il branch, GLOBAL blocca tutti.


class _AttivitaBranchBlockError(Exception):
    """Errore che blocca solo il branch corrente (block_scope=BRANCH)."""


class _AttivitaGlobalBlockError(Exception):
    """Errore che blocca tutti i branch (block_scope=GLOBAL)."""


class AttivitaPipelineStepExecutor:
    """Esecutore step pipeline attivita fatturabili con supporto branch/global block scope."""

    # Scopo: Inizializza la istanza.
    def __init__(
        self,
        repository: AttivitaPipelineRepository | None = None,
        error_logger: AttivitaPipelineErrorLogger | None = None,
    ) -> None:
        self.repository = repository or AttivitaPipelineRepository()
        self.error_logger = error_logger or AttivitaPipelineErrorLogger(self.repository)
        self.handler_registry = {
            "acquisisci_preventivi_default": self._handle_acquisisci_preventivi,
            "acquisisci_contratti_default": self._handle_acquisisci_contratti,
            "acquisisci_ordini_default": self._handle_acquisisci_ordini,
            "acquisisci_attivita_consumi_default": self._handle_acquisisci_attivita_consumi,
            "normalizza_attivita_default": self._handle_normalizza_attivita,
            "valida_attivita_default": self._handle_valida_attivita,
            "deduplica_attivita_default": self._handle_deduplica_attivita,
        }

    # Scopo: Gestisce uno step pipeline risolvendo processi da configurazione DB e dispatch dei task.
    def execute_step(
        self,
        *,
        lotto_id: int,
        codice_step: str,
        sorgente: AttivitaSorgenteBranchPolicy,
        dry_run: bool = False,
    ) -> None:
        context = self.repository.get_lotto_attivita_context(lotto_id)
        utility_id = context.utility_id if context else None

        processi = self.repository.get_attivita_step_processes(
            codice_step,
            utility_id=utility_id,
            sorgente_tipo_id=sorgente.sorgente_tipo_id,
            rollback=False,
        )

        pipeline_id = self.repository.get_attivita_pipeline_id_for_step(
            codice_step,
            utility_id=utility_id,
            sorgente_tipo_id=sorgente.sorgente_tipo_id,
        )

        for process in processi:
            self._run_task(
                lotto_id=lotto_id,
                process=process,
                sorgente=sorgente,
                pipeline_id=pipeline_id,
                dry_run=dry_run,
            )

    # Scopo: Gestisce il task di step con risoluzione handler via registry e gestione block scope.
    def _run_task(
        self,
        *,
        lotto_id: int,
        process: dict[str, Any],
        sorgente: AttivitaSorgenteBranchPolicy,
        pipeline_id: int | None,
        dry_run: bool,
    ) -> None:
        task = str(process.get("task", "")).strip()
        fase = process.get("fase") or "Esecuzione task"
        params = process.get("params") or {}
        implementation_key = params.get("implementation_key")

        if task in {"noop", "log_only"}:
            return

        handler_code = self.repository.get_task_handler_code(
            task_code=task,
            implementation_key=implementation_key,
        )

        if dry_run:
            return

        task_handler = self.handler_registry.get(handler_code)
        if task_handler is None:
            self.error_logger.log_error(
                scope="ATTIVITA_FATTURABILI",
                severity="C",
                code="E_ATTIVITA_PIPELINE",
                message="Implementazione task pipeline attivita non trovata.",
                detail=f"Implementazione task non trovata: {task} ({handler_code})",
                lotto_id=lotto_id,
                context={
                    "task": task,
                    "fase": fase,
                    "handler_code": handler_code,
                    "branch_code": sorgente.branch_code,
                    "sorgente_tipo_id": sorgente.sorgente_tipo_id,
                },
                function_name="vendite.attivita_pipeline_step_executor._run_task",
            )
            ErrorManager.raise_error(
                code="E_ATTIVITA_PIPELINE",
                message="Implementazione task pipeline attivita non trovata.",
                detail=f"Implementazione task non trovata: {task} ({handler_code})",
                context={
                    "task": task,
                    "handler_code": handler_code,
                    "branch_code": sorgente.branch_code,
                },
                function_name="vendite.attivita_pipeline_step_executor._run_task",
                log_to_db=True,
            )

        # Precedenza block_scope: task policy > sorgente policy (§5.1).
        effective_block_scope = sorgente.block_scope
        task_run_id: int | None = None

        if pipeline_id is not None and self.repository.task_policy_exists(
            pipeline_id, task, sorgente.branch_code
        ):
            policy = self.repository.get_attivita_task_policy(
                pipeline_id, task, sorgente.branch_code
            )
            if policy is not None:
                effective_block_scope = policy.block_scope  # task policy ha precedenza
            task_run_result = self.repository.start_attivita_task_run(
                lotto_id=lotto_id,
                pipeline_id=pipeline_id,
                task_code=task,
                branch_code=sorgente.branch_code,
                sorgente_tipo_id=sorgente.sorgente_tipo_id,
                fase=fase,
                block_scope=effective_block_scope,
                depends_on=policy.depends_on if policy is not None else [],
                meta={"rollback": False},
            )
            task_run_id = task_run_result.task_run_id

        try:
            task_handler(
                task=task,
                lotto_id=lotto_id,
                sorgente=sorgente,
                params=params,
            )
        except Exception as exc:
            self._fail_task_run_safely(task_run_id, exc)
            if effective_block_scope == "GLOBAL":
                raise _AttivitaGlobalBlockError(str(exc)) from exc
            raise _AttivitaBranchBlockError(str(exc)) from exc

        if task_run_id is not None:
            self.repository.complete_attivita_task_run(task_run_id)

    # Scopo: Tenta di marcare il task run in errore senza mascherare l'eccezione originale.
    def _fail_task_run_safely(self, task_run_id: int | None, exc: BaseException) -> None:
        if task_run_id is None:
            return
        try:
            error_code = exc.code if isinstance(exc, ServiceError) else "E_ATTIVITA_TASK"
            self.repository.fail_attivita_task_run(
                task_run_id,
                error_code,
                str(exc),
            )
        except Exception:
            pass  # Mai mascherare l'eccezione originale.

    # --- Handler stub (placeholder per implementazione futura) ---

    # Scopo: Placeholder acquisizione preventivi (implementazione in deliverable successivo).
    def _handle_acquisisci_preventivi(
        self, *, task: str, lotto_id: int, sorgente: AttivitaSorgenteBranchPolicy, params: dict
    ) -> None:
        pass

    # Scopo: Placeholder acquisizione contratti (implementazione in deliverable successivo).
    def _handle_acquisisci_contratti(
        self, *, task: str, lotto_id: int, sorgente: AttivitaSorgenteBranchPolicy, params: dict
    ) -> None:
        pass

    # Scopo: Placeholder acquisizione ordini (implementazione in deliverable successivo).
    def _handle_acquisisci_ordini(
        self, *, task: str, lotto_id: int, sorgente: AttivitaSorgenteBranchPolicy, params: dict
    ) -> None:
        pass

    # Scopo: Placeholder acquisizione attivita consumi (implementazione in deliverable successivo).
    def _handle_acquisisci_attivita_consumi(
        self, *, task: str, lotto_id: int, sorgente: AttivitaSorgenteBranchPolicy, params: dict
    ) -> None:
        pass

    # Scopo: Placeholder normalizzazione attivita (implementazione in deliverable successivo).
    def _handle_normalizza_attivita(
        self, *, task: str, lotto_id: int, sorgente: AttivitaSorgenteBranchPolicy, params: dict
    ) -> None:
        pass

    # Scopo: Placeholder validazione attivita (implementazione in deliverable successivo).
    def _handle_valida_attivita(
        self, *, task: str, lotto_id: int, sorgente: AttivitaSorgenteBranchPolicy, params: dict
    ) -> None:
        pass

    # Scopo: Placeholder deduplicazione attivita (implementazione in deliverable successivo).
    def _handle_deduplica_attivita(
        self, *, task: str, lotto_id: int, sorgente: AttivitaSorgenteBranchPolicy, params: dict
    ) -> None:
        pass
