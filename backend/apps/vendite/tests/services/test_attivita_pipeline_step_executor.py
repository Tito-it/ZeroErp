# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari step executor pipeline attivita fatturabili.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) AttivitaPipelineStepExecutorUnitTests.test_execute_step_skips_noop_task
2) AttivitaPipelineStepExecutorUnitTests.test_execute_step_completes_on_success_with_policy
3) AttivitaPipelineStepExecutorUnitTests.test_execute_step_fails_task_run_on_handler_error
4) AttivitaPipelineStepExecutorUnitTests.test_execute_step_raises_branch_error_on_handler_failure_branch_scope
5) AttivitaPipelineStepExecutorUnitTests.test_execute_step_raises_global_error_on_handler_failure_global_scope
6) AttivitaPipelineStepExecutorUnitTests.test_task_policy_overrides_sorgente_scope
7) AttivitaPipelineStepExecutorUnitTests.test_handler_not_found_raises_attivita_pipeline_error
8) AttivitaPipelineStepExecutorUnitTests.test_execute_step_skips_task_run_when_dry_run
"""

from datetime import date

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.db.attivita_pipeline_repository import (
    AttivitaPipelineStep,
    AttivitaSorgenteBranchPolicy,
    AttivitaTaskPolicy,
    AttivitaTaskRunResult,
    LottoAttivitaContext,
)
from apps.vendite.services.attivita_pipeline_step_executor import (
    AttivitaPipelineStepExecutor,
    _AttivitaBranchBlockError,
    _AttivitaGlobalBlockError,
)


def _make_sorgente(block_scope: str = "BRANCH", branch_code: str = "DEFAULT") -> AttivitaSorgenteBranchPolicy:
    return AttivitaSorgenteBranchPolicy(
        sorgente_tipo_id=1,
        branch_code=branch_code,
        abilitata=True,
        acquisizione_mode="PULL",
        block_scope=block_scope,
        priorita=1,
        meta={},
    )


def _make_policy(block_scope: str = "BRANCH") -> AttivitaTaskPolicy:
    return AttivitaTaskPolicy(
        annullabile=True,
        resume_mode="RESUME_BRANCH",
        block_scope=block_scope,
        depends_on=[],
        attivo=True,
        meta={},
    )


class AttivitaPipelineStepExecutorUnitTests(SimpleTestCase):
    class _RepoMock:
        def __init__(self):
            self.start_called = False
            self.complete_called = False
            self.fail_called = False
            self.complete_task_run_id = None
            self.fail_task_run_id = None
            self._task_policy_exists = False
            self._policy = None
            self._task_handler_code = "acquisisci_preventivi_default"

        def get_lotto_attivita_context(self, lotto_id):
            return LottoAttivitaContext(
                competenza_mese=date(2026, 1, 1),
                utility_id=1,
                billing_account_id=None,
                sorgente_tipo_id=None,
                emittente_soggetto_ruolo_id=None,
                lock_batch_id=None,
            )

        def get_attivita_step_processes(self, codice_step, *, utility_id, sorgente_tipo_id, rollback):
            return [{"task": "acquisisci_preventivi", "fase": "Acquisizione", "params": {"implementation_key": "default"}}]

        def get_attivita_pipeline_id_for_step(self, codice_step, *, utility_id, sorgente_tipo_id):
            return 1

        def get_task_handler_code(self, *, task_code, implementation_key, dominio_code=None):
            return self._task_handler_code

        def task_policy_exists(self, pipeline_id, task_code, branch_code="DEFAULT"):
            return self._task_policy_exists

        def get_attivita_task_policy(self, pipeline_id, task_code, branch_code="DEFAULT"):
            return self._policy

        def start_attivita_task_run(self, **kwargs):
            self.start_called = True
            return AttivitaTaskRunResult(task_run_id=999, tentativo=1)

        def complete_attivita_task_run(self, task_run_id, meta=None):
            self.complete_called = True
            self.complete_task_run_id = task_run_id

        def fail_attivita_task_run(self, task_run_id, error_code, error_message, meta=None):
            self.fail_called = True
            self.fail_task_run_id = task_run_id

    def _build_executor(self, repo=None) -> tuple:
        if repo is None:
            repo = self._RepoMock()
        error_logger_mock = type("_LoggerMock", (), {"log_error": lambda self, **kw: None})()
        executor = AttivitaPipelineStepExecutor(
            repository=repo,
            error_logger=error_logger_mock,
        )
        return executor, repo

    # Scopo: Verifica che task noop non apra task run e non chiami nessun handler.
    def test_execute_step_skips_noop_task(self):
        repo = self._RepoMock()
        # Sovrascrivi processi con noop
        repo.get_attivita_step_processes = lambda *a, **kw: [{"task": "noop", "params": {}}]
        executor, repo = self._build_executor(repo)

        executor.execute_step(
            lotto_id=10,
            codice_step="STEP_1",
            sorgente=_make_sorgente(),
            dry_run=False,
        )

        self.assertFalse(repo.start_called)
        self.assertFalse(repo.complete_called)

    # Scopo: Verifica che task con policy apra e chiuda task run su handler che riesce.
    def test_execute_step_completes_on_success_with_policy(self):
        repo = self._RepoMock()
        repo._task_policy_exists = True
        repo._policy = _make_policy(block_scope="BRANCH")
        executor, repo = self._build_executor(repo)

        executor.execute_step(
            lotto_id=10,
            codice_step="STEP_1",
            sorgente=_make_sorgente(),
            dry_run=False,
        )

        self.assertTrue(repo.start_called)
        self.assertTrue(repo.complete_called)
        self.assertEqual(repo.complete_task_run_id, 999)

    # Scopo: Verifica che handler che solleva eccezione marchi task run come fallito.
    def test_execute_step_fails_task_run_on_handler_error(self):
        repo = self._RepoMock()
        repo._task_policy_exists = True
        repo._policy = _make_policy()
        executor, repo = self._build_executor(repo)

        # Sostituisce handler con uno che lancia
        executor.handler_registry["acquisisci_preventivi_default"] = lambda **kw: (_ for _ in ()).throw(RuntimeError("boom"))

        with self.assertRaises((_AttivitaBranchBlockError, _AttivitaGlobalBlockError)):
            executor.execute_step(
                lotto_id=10,
                codice_step="STEP_1",
                sorgente=_make_sorgente(),
                dry_run=False,
            )

        self.assertTrue(repo.fail_called)
        self.assertEqual(repo.fail_task_run_id, 999)

    # Scopo: Verifica che handler che fallisce con block_scope=BRANCH sollevi _AttivitaBranchBlockError.
    def test_execute_step_raises_branch_error_on_handler_failure_branch_scope(self):
        repo = self._RepoMock()
        executor, repo = self._build_executor(repo)

        executor.handler_registry["acquisisci_preventivi_default"] = lambda **kw: (_ for _ in ()).throw(RuntimeError("branch fail"))

        with self.assertRaises(_AttivitaBranchBlockError):
            executor.execute_step(
                lotto_id=10,
                codice_step="STEP_1",
                sorgente=_make_sorgente(block_scope="BRANCH"),
                dry_run=False,
            )

    # Scopo: Verifica che handler che fallisce con block_scope=GLOBAL sollevi _AttivitaGlobalBlockError.
    def test_execute_step_raises_global_error_on_handler_failure_global_scope(self):
        repo = self._RepoMock()
        executor, repo = self._build_executor(repo)

        executor.handler_registry["acquisisci_preventivi_default"] = lambda **kw: (_ for _ in ()).throw(RuntimeError("global fail"))

        with self.assertRaises(_AttivitaGlobalBlockError):
            executor.execute_step(
                lotto_id=10,
                codice_step="STEP_1",
                sorgente=_make_sorgente(block_scope="GLOBAL"),
                dry_run=False,
            )

    # Scopo: Verifica che task policy GLOBAL sovrascriva sorgente BRANCH (§5.1).
    def test_task_policy_overrides_sorgente_scope(self):
        repo = self._RepoMock()
        repo._task_policy_exists = True
        repo._policy = _make_policy(block_scope="GLOBAL")  # task policy GLOBAL
        executor, repo = self._build_executor(repo)

        executor.handler_registry["acquisisci_preventivi_default"] = lambda **kw: (_ for _ in ()).throw(RuntimeError("policy override"))

        # Sorgente dice BRANCH ma policy dice GLOBAL → deve sollevare GlobalBlockError
        with self.assertRaises(_AttivitaGlobalBlockError):
            executor.execute_step(
                lotto_id=10,
                codice_step="STEP_1",
                sorgente=_make_sorgente(block_scope="BRANCH"),
                dry_run=False,
            )

    # Scopo: Verifica che handler non registrato sollevi ServiceError E_ATTIVITA_PIPELINE.
    def test_handler_not_found_raises_attivita_pipeline_error(self):
        repo = self._RepoMock()
        repo._task_handler_code = "handler_non_esistente_xyz"
        executor, repo = self._build_executor(repo)

        with self.assertRaises(ServiceError) as exc:
            executor.execute_step(
                lotto_id=10,
                codice_step="STEP_1",
                sorgente=_make_sorgente(),
                dry_run=False,
            )

        self.assertEqual(exc.exception.code, "E_ATTIVITA_PIPELINE")

    # Scopo: Verifica che dry_run=True non chiami handler e non apra task run.
    def test_execute_step_skips_task_run_when_dry_run(self):
        repo = self._RepoMock()
        repo._task_policy_exists = True
        repo._policy = _make_policy()
        executor, repo = self._build_executor(repo)

        handler_called = []
        executor.handler_registry["acquisisci_preventivi_default"] = lambda **kw: handler_called.append(True)

        executor.execute_step(
            lotto_id=10,
            codice_step="STEP_1",
            sorgente=_make_sorgente(),
            dry_run=True,
        )

        self.assertEqual(handler_called, [])
        self.assertFalse(repo.start_called)
