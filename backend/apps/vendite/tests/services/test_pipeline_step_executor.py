"""
Indice test eseguiti:
1) PipelineStepExecutorUnitTests.test_execute_step_runs_generate_fatture_righe_task
2) PipelineStepExecutorUnitTests.test_execute_step_rejects_generate_fatture_righe_fn_override
"""

from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.pipeline_step_executor import PipelineStepExecutor


class PipelineStepExecutorUnitTests(SimpleTestCase):
    def _build_executor(self, processi):
        repo = MagicMock()
        repo.get_lotto_context.return_value = MagicMock(
            competenza_mese="2026-01-01",
            utility_id=None,
            tipo_doc_fiscale_id=None,
        )
        repo.get_step_processes.return_value = processi
        repo.log_pipeline_fase.return_value = None
        repo.get_task_handler_code.return_value = "generate_fatture_righe_default"
        repo.ALLOWED_TASK_FUNCTIONS = {
            "select_attivita": "vendite.fn_select_attivita_fatturabili",
            "generate_fatture_righe": "vendite.fn_generate_fatture_righe",
        }
        fatture_righe_service = MagicMock()
        executor = PipelineStepExecutor(
            repository=repo,
            fatture_righe_service=fatture_righe_service,
        )
        return executor, repo, fatture_righe_service

    def test_execute_step_runs_generate_fatture_righe_task(self):
        processi = [{"task": "generate_fatture_righe", "fase": "Genera righe", "params": {}}]
        executor, repo, fatture_righe_service = self._build_executor(processi)
        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )
        repo.get_step_processes.assert_called_once_with(
            2,
            tipo_lotto="MASSIVO",
            utility_id=None,
            tipo_doc_fiscale_id=None,
            rollback=False,
        )
        repo.get_task_handler_code.assert_called_once_with(
            task_code="generate_fatture_righe",
            implementation_key=None,
        )
        fatture_righe_service.generate_fatture_righe.assert_called_once_with(1, dry_run=False)

    def test_execute_step_rejects_generate_fatture_righe_fn_override(self):
        processi = [
            {
                "task": "generate_fatture_righe",
                "fase": "Genera righe",
                "params": {"fn": "vendite.fn_non_permessa"},
            }
        ]
        executor, _, fatture_righe_service = self._build_executor(processi)
        with self.assertRaises(ServiceError) as exc:
            executor.execute_step(
                lotto_id=1,
                stato_doc_fiscale_id=2,
                tipo_lotto="MASSIVO",
                rollback=False,
                dry_run=False,
            )
        self.assertEqual(exc.exception.code, "E_TASK_NOT_ALLOWED")
        self.assertEqual(repo.get_task_handler_code.call_count, 1)
        fatture_righe_service.generate_fatture_righe.assert_not_called()
