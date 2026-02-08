"""
Indice test eseguiti:
1) LottoPipelineRunnerUnitTests.test_runner_calls_step_executor
2) LottoPipelineRunnerUnitTests.test_runner_wraps_unexpected_error_with_service_error
3) LottoPipelineRunnerUnitTests.test_runner_preserves_service_error_code
4) LottoPipelineRunnerUnitTests.test_runner_does_not_mask_error_when_mark_fails
5) LottoPipelineRunnerUnitTests.test_runner_rejects_auto_reuse_of_completed_lotto
"""

from contextlib import nullcontext
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.pipeline_runner import LottoPipelineParams, LottoPipelineRunner


class LottoPipelineRunnerUnitTests(SimpleTestCase):
    class _RepoMock:
        def get_or_create_lotto(self, **kwargs):
            return 10

        def get_lotto_tipo(self, lotto_id):
            return "MASSIVO"

        def get_stato_doc_fiscale_id(self, codice):
            return 99

        def get_lotto_job_stato(self, lotto_id):
            return "DRAFT"

        def set_lotto_job_stato(self, lotto_id, stato, messaggio):
            self.last_stato = stato

        def list_pipeline_steps(self, tipo_lotto, utility_id=None, tipo_doc_fiscale_id=None):
            class _Step:
                stato_doc_fiscale_id = 1
                descrizione = "Step 1"
                ordine = 1

            return [_Step()]

        def update_lotto_stato_doc(self, lotto_id, stato_doc_fiscale_id):
            return None

        def close_giornaliero_lotto(self, lotto_id, inviata_id):
            return None

        def log_pipeline_fase(self, **kwargs):
            return None

        def get_lotto_context(self, lotto_id):
            class _Ctx:
                competenza_mese = "2026-01-01"
                tipo_doc_fiscale_id = 1
                utility_id = 1
                billing_account_id = None
                lock_batch_id = None

            return _Ctx()

    class _StepExecutorMock:
        def __init__(self):
            self.called = False
            self.last_kwargs = {}

        def execute_step(self, **kwargs):
            self.called = True
            self.last_kwargs = kwargs

    class _UnexpectedFailingStepExecutorMock:
        def execute_step(self, **kwargs):
            raise RuntimeError("boom")

    class _ServiceFailingStepExecutorMock:
        def execute_step(self, **kwargs):
            raise ServiceError(
                code="E_TASK_NOT_IMPLEMENTED",
                message="Task pipeline non implementato.",
                detail="Task pipeline non implementato: test",
            )

    def test_runner_calls_step_executor(self):
        repo = self._RepoMock()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            result = runner.run_pipeline(LottoPipelineParams(dry_run=True))
        self.assertEqual(result, 10)
        self.assertTrue(step_executor.called)
        self.assertEqual(step_executor.last_kwargs["tipo_lotto"], "MASSIVO")

    def test_runner_wraps_unexpected_error_with_service_error(self):
        repo = self._RepoMock()
        step_executor = self._UnexpectedFailingStepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            with self.assertRaises(ServiceError) as exc:
                runner.run_pipeline(LottoPipelineParams(dry_run=False))
        self.assertEqual(exc.exception.code, "E_PIPELINE")
        self.assertIsInstance(exc.exception.__cause__, RuntimeError)
        self.assertEqual(repo.last_stato, "ERRORE")

    def test_runner_preserves_service_error_code(self):
        repo = self._RepoMock()
        step_executor = self._ServiceFailingStepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            with self.assertRaises(ServiceError) as exc:
                runner.run_pipeline(LottoPipelineParams(dry_run=False))
        self.assertEqual(exc.exception.code, "E_TASK_NOT_IMPLEMENTED")
        self.assertEqual(repo.last_stato, "ERRORE")

    def test_runner_does_not_mask_error_when_mark_fails(self):
        class _FailingMarkRepo(self._RepoMock):
            def set_lotto_job_stato(self, lotto_id, stato, messaggio):
                if stato == "ERRORE":
                    raise RuntimeError("mark-failed")
                self.last_stato = stato

        repo = _FailingMarkRepo()
        step_executor = self._ServiceFailingStepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            with self.assertRaises(ServiceError) as exc:
                runner.run_pipeline(LottoPipelineParams(dry_run=False))
        self.assertEqual(exc.exception.code, "E_TASK_NOT_IMPLEMENTED")

    def test_runner_rejects_auto_reuse_of_completed_lotto(self):
        class _CompletedRepo(self._RepoMock):
            def get_lotto_job_stato(self, lotto_id):
                return "COMPLETATO"

        repo = _CompletedRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            with self.assertRaises(ServiceError) as exc:
                runner.run_pipeline(LottoPipelineParams(lotto_id=0, dry_run=True))
        self.assertEqual(exc.exception.code, "E_PIPELINE_LOTTO_COMPLETATO_REUSE")
        self.assertFalse(step_executor.called)
