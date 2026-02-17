"""
Indice test eseguiti:
1) PipelineStepExecutorUnitTests.test_execute_step_runs_generate_fatture_righe_task
2) PipelineStepExecutorUnitTests.test_execute_step_rejects_generate_fatture_righe_fn_override
3) PipelineStepExecutorUnitTests.test_execute_step_runs_genera_fondi_source_lotto_task
4) PipelineStepExecutorUnitTests.test_execute_step_runs_applica_fondi_lotto_task
5) PipelineStepExecutorUnitTests.test_execute_step_runs_ricalcola_iva_lotto_task
6) PipelineStepExecutorUnitTests.test_execute_step_runs_prepare_sdi_payload_lotto_task
7) PipelineStepExecutorUnitTests.test_execute_step_runs_numera_fatture_task
8) PipelineStepExecutorUnitTests.test_execute_step_runs_close_lotto_task
9) PipelineStepExecutorUnitTests.test_execute_step_runs_reset_lotto_draft_task
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
        repo.list_fatture_by_lotto.return_value = [101, 102]
        repo.get_task_handler_code.return_value = "generate_fatture_righe_default"
        repo.ALLOWED_TASK_FUNCTIONS = {
            "select_attivita": "vendite.fn_select_attivita_fatturabili",
            "generate_fatture_righe": "vendite.fn_generate_fatture_righe",
            "genera_fondi_source_lotto": "vendite.fn_genera_fondi_fattura_source",
            "applica_fondi_lotto": "vendite.fn_applica_fondi_fattura",
            "ricalcola_iva_lotto": "vendite.fn_ricalcola_riepiloghi_iva_lotto",
            "prepare_sdi_payload_lotto": "vendite.fn_prepare_sdi_payload",
            "numera_fatture": "vendite.fn_numera_fattura_opz_emessa",
            "close_lotto": None,
            "reset_lotto_draft": "vendite.fn_reset_lotto_draft",
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

    def test_execute_step_runs_genera_fondi_source_lotto_task(self):
        processi = [{"task": "genera_fondi_source_lotto", "fase": "Genera fondi", "params": {}}]
        executor, repo, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "genera_fondi_source_lotto_default"

        executor.execute_step(
            lotto_id=11,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.run_genera_fondi_source_lotto_task.assert_called_once_with(
            lotto_id=11,
            tipo_fondo_codice_interno="F_F_ADD_ACC",
        )

    def test_execute_step_runs_applica_fondi_lotto_task(self):
        processi = [{"task": "applica_fondi_lotto", "fase": "Applica fondi", "params": {}}]
        executor, repo, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "applica_fondi_lotto_default"

        executor.execute_step(
            lotto_id=11,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.run_applica_fondi_lotto_task.assert_called_once_with(
            lotto_id=11,
            tipo_fondo_codice_interno="F_F_ADD_ACC",
        )

    def test_execute_step_runs_ricalcola_iva_lotto_task(self):
        processi = [{"task": "ricalcola_iva_lotto", "fase": "Ricalcolo IVA", "params": {"batch_size": 500}}]
        executor, repo, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "ricalcola_iva_lotto_default"

        executor.execute_step(
            lotto_id=11,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.run_ricalcola_iva_lotto_task.assert_called_once_with(
            lotto_id=11,
            batch_size=500,
        )

    def test_execute_step_runs_prepare_sdi_payload_lotto_task(self):
        processi = [
            {
                "task": "prepare_sdi_payload_lotto",
                "fase": "Preparazione payload SDI",
                "params": {
                    "stato_sdi_codice_interno": "DA_INVIARE",
                    "force_new_tentativo": False,
                },
            }
        ]
        executor, repo, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "prepare_sdi_payload_lotto_default"

        executor.execute_step(
            lotto_id=11,
            stato_doc_fiscale_id=3,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.run_prepare_sdi_payload_lotto_task.assert_called_once_with(
            lotto_id=11,
            stato_sdi_codice_interno="DA_INVIARE",
            force_new_tentativo=False,
        )

    def test_execute_step_rejects_generate_fatture_righe_fn_override(self):
        processi = [
            {
                "task": "generate_fatture_righe",
                "fase": "Genera righe",
                "params": {"fn": "vendite.fn_non_permessa"},
            }
        ]
        executor, repo, fatture_righe_service = self._build_executor(processi)
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

    def test_execute_step_runs_numera_fatture_task(self):
        processi = [{"task": "numera_fatture", "fase": "Numerazione", "params": {}}]
        executor, repo, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "numera_fatture_default"

        executor.execute_step(
            lotto_id=9,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.list_fatture_by_lotto.assert_called_once_with(9)
        repo.numera_fattura_opz_emessa.assert_any_call(101)
        repo.numera_fattura_opz_emessa.assert_any_call(102)
        repo.sync_lotto_fatture_stato.assert_called_once_with(
            lotto_id=9,
            stato_doc_fiscale_id=2,
        )

    def test_execute_step_runs_close_lotto_task(self):
        processi = [{"task": "close_lotto", "fase": "Chiusura lotto", "params": {}}]
        executor, repo, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "close_lotto_default"

        executor.execute_step(
            lotto_id=5,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.close_lotto_operativo.assert_called_once_with(5)

    def test_execute_step_runs_reset_lotto_draft_task(self):
        processi = [{"task": "reset_lotto_draft", "fase": "Reset lotto", "params": {}}]
        executor, repo, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "reset_lotto_draft_default"

        executor.execute_step(
            lotto_id=12,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=True,
            dry_run=False,
        )

        repo.reset_lotto_draft.assert_called_once_with(12)
