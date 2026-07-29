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
10) PipelineStepExecutorUnitTests.test_execute_step_numera_logs_fattura_error_on_single_failure
11) PipelineStepExecutorUnitTests.test_execute_step_logs_lotto_error_on_not_allowed_function
12) PipelineStepExecutorUnitTests.test_execute_step_logs_lotto_error_on_missing_handler
13) PipelineStepExecutorUnitTests.test_execute_step_skips_close_lotto_task_when_flag_is_false
14) PipelineStepExecutorUnitTests.test_execute_step_skips_task_when_execution_mode_is_skip
15) PipelineStepExecutorUnitTests.test_execute_step_raises_when_execution_mode_is_reset_required
16) PipelineStepExecutorUnitTests.test_execute_step_traces_task_run_on_success
17) PipelineStepExecutorUnitTests.test_execute_step_traces_fail_on_handler_error
18) PipelineStepExecutorUnitTests.test_execute_step_no_tracing_when_no_pipeline_id
19) PipelineStepExecutorUnitTests.test_execute_step_no_tracing_when_no_policy
20) PipelineStepExecutorUnitTests.test_execute_step_select_attivita_uses_emittente_from_context
21) PipelineStepExecutorUnitTests.test_execute_step_runs_pull_attivita_da_commessa_task
22) PipelineStepExecutorUnitTests.test_pull_attivita_da_commessa_dry_run_skips_emit
23) PipelineStepExecutorUnitTests.test_pull_attivita_da_commessa_empty_list_no_emit
24) PipelineStepExecutorUnitTests.test_execute_step_runs_stampa_documenti_lotto_task (C-2c)
25) PipelineStepExecutorUnitTests.test_execute_step_stampa_documenti_lotto_dry_run_skips (C-2c)
"""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.pipeline_step_executor import PipelineStepExecutor


class PipelineStepExecutorUnitTests(SimpleTestCase):
    # Scopo: Gestisce `_build_executor` nel flusso applicativo del modulo.
    def _build_executor(self, processi):
        repo = MagicMock()
        repo.get_lotto_context.return_value = MagicMock(
            competenza_mese="2026-01-01",
            utility_id=None,
            tipo_doc_fiscale_id=None,
            emittente_soggetto_ruolo_id=None,
        )
        repo.get_step_processes.return_value = processi
        repo.log_pipeline_fase.return_value = None
        repo.list_fatture_by_lotto.return_value = [101, 102]
        repo.get_task_handler_code.return_value = "generate_fatture_righe_default"
        repo.is_stato_doc_chiude_lotto.return_value = True
        repo.ALLOWED_TASK_FUNCTIONS = {
            "select_attivita": "vendite.fn_select_attivita_fatturabili",
            # Speculare alla mappa reale: None = task Python-only
            # (`FattureRigheService`), la fn SQL e' stata rimossa (20260728-21).
            "generate_fatture_righe": None,
            "genera_fondi_source_lotto": "vendite.fn_genera_fondi_fattura_source",
            "applica_fondi_lotto": "vendite.fn_applica_fondi_fattura",
            "ricalcola_iva_lotto": "vendite.fn_ricalcola_riepiloghi_iva_lotto",
            "prepare_sdi_payload_lotto": "vendite.fn_prepare_sdi_payload",
            "numera_fatture": "vendite.fn_numera_fattura_opz_emessa",
            "close_lotto": None,
            "reset_lotto_draft": "vendite.fn_reset_lotto_draft",
        }
        # Tracing: default nessuna policy → nessun tracing (test esistenti non cambiano).
        repo.get_pipeline_id_for_step.return_value = 100
        repo.task_policy_exists.return_value = False
        exec_mode_mock = MagicMock()
        exec_mode_mock.execution_mode = "RUN"
        exec_mode_mock.last_task_stato = None
        exec_mode_mock.last_tentativo = None
        repo.resolve_lotto_task_execution_mode.return_value = exec_mode_mock
        task_run_mock = MagicMock()
        task_run_mock.task_run_id = 999
        task_run_mock.tentativo = 1
        repo.start_lotto_task_run.return_value = task_run_mock
        repo.complete_lotto_task_run.return_value = None
        repo.fail_lotto_task_run.return_value = None
        fatture_righe_service = MagicMock()
        error_logger = MagicMock()
        executor = PipelineStepExecutor(
            repository=repo,
            fatture_righe_service=fatture_righe_service,
            error_logger=error_logger,
        )
        return executor, repo, fatture_righe_service, error_logger

    # Scopo: Verifica il caso `test_execute_step_runs_generate_fatture_righe_task`.
    def test_execute_step_runs_generate_fatture_righe_task(self):
        processi = [{"task": "generate_fatture_righe", "fase": "Genera righe", "params": {}}]
        executor, repo, fatture_righe_service, _ = self._build_executor(processi)
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

    # Scopo: Verifica il caso `test_execute_step_runs_genera_fondi_source_lotto_task`.
    def test_execute_step_runs_genera_fondi_source_lotto_task(self):
        processi = [{"task": "genera_fondi_source_lotto", "fase": "Genera fondi", "params": {}}]
        executor, repo, _, _ = self._build_executor(processi)
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

    # Scopo: Verifica il caso `test_execute_step_runs_applica_fondi_lotto_task`.
    def test_execute_step_runs_applica_fondi_lotto_task(self):
        processi = [{"task": "applica_fondi_lotto", "fase": "Applica fondi", "params": {}}]
        executor, repo, _, _ = self._build_executor(processi)
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

    # Scopo: Verifica il caso `test_execute_step_runs_ricalcola_iva_lotto_task`.
    def test_execute_step_runs_ricalcola_iva_lotto_task(self):
        processi = [{"task": "ricalcola_iva_lotto", "fase": "Ricalcolo IVA", "params": {"batch_size": 500}}]
        executor, repo, _, _ = self._build_executor(processi)
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

    # Scopo: Verifica il caso `test_execute_step_runs_prepare_sdi_payload_lotto_task`.
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
        executor, repo, _, _ = self._build_executor(processi)
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

    # Scopo: Verifica il caso `test_execute_step_rejects_generate_fatture_righe_fn_override`.
    def test_execute_step_rejects_generate_fatture_righe_fn_override(self):
        processi = [
            {
                "task": "generate_fatture_righe",
                "fase": "Genera righe",
                "params": {"fn": "vendite.fn_non_permessa"},
            }
        ]
        executor, repo, fatture_righe_service, error_logger = self._build_executor(processi)
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
        error_logger.log_error.assert_called_once()
        kwargs = error_logger.log_error.call_args.kwargs
        self.assertEqual(kwargs["scope"], "LOTTO")
        self.assertEqual(kwargs["lotto_id"], 1)

    # Scopo: Verifica il caso `test_execute_step_runs_numera_fatture_task`.
    def test_execute_step_runs_numera_fatture_task(self):
        processi = [{"task": "numera_fatture", "fase": "Numerazione", "params": {}}]
        executor, repo, _, _ = self._build_executor(processi)
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
        # Il task numera NON sincronizza piu' lo stato documentale: l'allineamento allo
        # stato dello step (→ DEFINITIVA/8) e' centralizzato nel runner (_execute_pipeline_step).
        repo.sync_lotto_fatture_stato.assert_not_called()

    # Scopo: C-2c (outbox stampa) — il task stampa_documenti_lotto ACCODA via
    #        fn_accoda_stampe_lotto e non tocca altro (nessun render qui).
    def test_execute_step_runs_stampa_documenti_lotto_task(self):
        processi = [{"task": "stampa_documenti_lotto", "fase": "Stampa documenti lotto", "params": {"implementation_key": "default"}}]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "stampa_documenti_lotto_default"
        repo.accoda_stampe_lotto.return_value = 3

        executor.execute_step(
            lotto_id=9,
            stato_doc_fiscale_id=8,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.accoda_stampe_lotto.assert_called_once_with(9)
        # Adattatore stupido: niente render, niente numerazione qui.
        repo.numera_fattura_opz_emessa.assert_not_called()

    # Scopo: C-2c — in dry-run l'accodamento NON viene eseguito.
    def test_execute_step_stampa_documenti_lotto_dry_run_skips(self):
        processi = [{"task": "stampa_documenti_lotto", "fase": "Stampa documenti lotto", "params": {}}]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "stampa_documenti_lotto_default"

        executor.execute_step(
            lotto_id=9,
            stato_doc_fiscale_id=8,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=True,
        )

        repo.accoda_stampe_lotto.assert_not_called()

    # Scopo: Verifica il caso `test_execute_step_runs_close_lotto_task`.
    def test_execute_step_runs_close_lotto_task(self):
        processi = [{"task": "close_lotto", "fase": "Chiusura lotto", "params": {}}]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "close_lotto_default"

        executor.execute_step(
            lotto_id=5,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.close_lotto_operativo.assert_called_once_with(5)

    # Scopo: Verifica il caso `test_execute_step_skips_close_lotto_task_when_flag_is_false`.
    def test_execute_step_skips_close_lotto_task_when_flag_is_false(self):
        processi = [{"task": "close_lotto", "fase": "Chiusura lotto", "params": {}}]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "close_lotto_default"
        repo.is_stato_doc_chiude_lotto.return_value = False

        executor.execute_step(
            lotto_id=5,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.close_lotto_operativo.assert_not_called()

    # Scopo: Verifica il caso `test_execute_step_runs_reset_lotto_draft_task`.
    def test_execute_step_runs_reset_lotto_draft_task(self):
        processi = [{"task": "reset_lotto_draft", "fase": "Reset lotto", "params": {}}]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "reset_lotto_draft_default"

        executor.execute_step(
            lotto_id=12,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=True,
            dry_run=False,
        )

        repo.reset_lotto_draft.assert_called_once_with(12)

    # Scopo: Verifica il caso `test_execute_step_numera_logs_fattura_error_on_single_failure`.
    def test_execute_step_numera_logs_fattura_error_on_single_failure(self):
        processi = [{"task": "numera_fatture", "fase": "Numerazione", "params": {}}]
        executor, repo, _, error_logger = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "numera_fatture_default"
        repo.list_fatture_by_lotto.return_value = [101, 102]
        repo.numera_fattura_opz_emessa.side_effect = [None, RuntimeError("boom-numera")]

        with self.assertRaises(ServiceError) as exc:
            executor.execute_step(
                lotto_id=9,
                stato_doc_fiscale_id=2,
                tipo_lotto="MASSIVO",
                rollback=False,
                dry_run=False,
            )

        self.assertEqual(exc.exception.code, "E_TASK_FATTURA")
        error_logger.log_error.assert_called_once()
        kwargs = error_logger.log_error.call_args.kwargs
        self.assertEqual(kwargs["scope"], "FATTURA")
        self.assertEqual(kwargs["fattura_id"], 102)
        self.assertEqual(kwargs["lotto_id"], 9)

    # Scopo: Verifica il caso `test_execute_step_logs_lotto_error_on_not_allowed_function`.
    def test_execute_step_logs_lotto_error_on_not_allowed_function(self):
        processi = [
            {
                "task": "select_attivita",
                "fase": "Caricamento",
                "params": {"fn": "vendite.fn_non_permessa"},
            }
        ]
        executor, _, _, error_logger = self._build_executor(processi)
        with self.assertRaises(ServiceError) as exc:
            executor.execute_step(
                lotto_id=21,
                stato_doc_fiscale_id=1,
                tipo_lotto="MASSIVO",
                rollback=False,
                dry_run=False,
            )
        self.assertEqual(exc.exception.code, "E_TASK_NOT_ALLOWED")
        error_logger.log_error.assert_called_once()
        kwargs = error_logger.log_error.call_args.kwargs
        self.assertEqual(kwargs["scope"], "LOTTO")
        self.assertEqual(kwargs["lotto_id"], 21)

    # Scopo: Verifica il caso `test_execute_step_logs_lotto_error_on_missing_handler`.
    def test_execute_step_logs_lotto_error_on_missing_handler(self):
        processi = [{"task": "generate_fatture_righe", "fase": "Genera righe", "params": {}}]
        executor, repo, _, error_logger = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "handler_non_esistente"

        with self.assertRaises(ServiceError) as exc:
            executor.execute_step(
                lotto_id=22,
                stato_doc_fiscale_id=2,
                tipo_lotto="MASSIVO",
                rollback=False,
                dry_run=False,
            )

        self.assertEqual(exc.exception.code, "E_TASK_IMPLEMENTATION_NOT_FOUND")
        error_logger.log_error.assert_called_once()
        kwargs = error_logger.log_error.call_args.kwargs
        self.assertEqual(kwargs["scope"], "LOTTO")
        self.assertEqual(kwargs["lotto_id"], 22)

    # Scopo: Verifica che il task venga saltato quando la modalità di esecuzione è SKIP.
    def test_execute_step_skips_task_when_execution_mode_is_skip(self):
        processi = [{"task": "generate_fatture_righe", "fase": "Genera righe", "params": {}}]
        executor, repo, fatture_righe_service, _ = self._build_executor(processi)
        repo.task_policy_exists.return_value = True
        skip_mode = MagicMock()
        skip_mode.execution_mode = "SKIP"
        repo.resolve_lotto_task_execution_mode.return_value = skip_mode

        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.start_lotto_task_run.assert_not_called()
        fatture_righe_service.generate_fatture_righe.assert_not_called()

    # Scopo: Verifica che venga sollevato ServiceError quando la modalità è RESET_REQUIRED.
    def test_execute_step_raises_when_execution_mode_is_reset_required(self):
        processi = [{"task": "generate_fatture_righe", "fase": "Genera righe", "params": {}}]
        executor, repo, fatture_righe_service, error_logger = self._build_executor(processi)
        repo.task_policy_exists.return_value = True
        reset_mode = MagicMock()
        reset_mode.execution_mode = "RESET_REQUIRED"
        reset_mode.last_task_stato = "IN_ESECUZIONE"
        reset_mode.last_tentativo = 1
        repo.resolve_lotto_task_execution_mode.return_value = reset_mode

        with self.assertRaises(ServiceError) as exc:
            executor.execute_step(
                lotto_id=1,
                stato_doc_fiscale_id=2,
                tipo_lotto="MASSIVO",
                rollback=False,
                dry_run=False,
            )

        self.assertEqual(exc.exception.code, "E_TASK_RESET_REQUIRED")
        repo.start_lotto_task_run.assert_not_called()
        fatture_righe_service.generate_fatture_righe.assert_not_called()
        error_logger.log_error.assert_called_once()
        kwargs = error_logger.log_error.call_args.kwargs
        self.assertEqual(kwargs["scope"], "LOTTO")
        self.assertEqual(kwargs["lotto_id"], 1)

    # Scopo: Verifica che start e complete task run vengano chiamati su esecuzione riuscita.
    def test_execute_step_traces_task_run_on_success(self):
        processi = [{"task": "generate_fatture_righe", "fase": "Genera righe", "params": {}}]
        executor, repo, _, _ = self._build_executor(processi)
        repo.task_policy_exists.return_value = True
        run_mode = MagicMock()
        run_mode.execution_mode = "RUN"
        repo.resolve_lotto_task_execution_mode.return_value = run_mode
        task_run = MagicMock()
        task_run.task_run_id = 888
        repo.start_lotto_task_run.return_value = task_run

        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.start_lotto_task_run.assert_called_once()
        call_kwargs = repo.start_lotto_task_run.call_args.kwargs
        self.assertEqual(call_kwargs["lotto_id"], 1)
        self.assertEqual(call_kwargs["pipeline_id"], 100)
        self.assertEqual(call_kwargs["task_code"], "generate_fatture_righe")
        repo.complete_lotto_task_run.assert_called_once_with(888)
        repo.fail_lotto_task_run.assert_not_called()

    # Scopo: Verifica che fail task run venga chiamato e l'eccezione propagata quando l'handler fallisce.
    def test_execute_step_traces_fail_on_handler_error(self):
        processi = [{"task": "generate_fatture_righe", "fase": "Genera righe", "params": {}}]
        executor, repo, fatture_righe_service, _ = self._build_executor(processi)
        repo.task_policy_exists.return_value = True
        run_mode = MagicMock()
        run_mode.execution_mode = "RUN"
        repo.resolve_lotto_task_execution_mode.return_value = run_mode
        task_run = MagicMock()
        task_run.task_run_id = 777
        repo.start_lotto_task_run.return_value = task_run
        fatture_righe_service.generate_fatture_righe.side_effect = RuntimeError("boom-task")

        with self.assertRaises(RuntimeError):
            executor.execute_step(
                lotto_id=1,
                stato_doc_fiscale_id=2,
                tipo_lotto="MASSIVO",
                rollback=False,
                dry_run=False,
            )

        repo.start_lotto_task_run.assert_called_once()
        repo.fail_lotto_task_run.assert_called_once()
        fail_args = repo.fail_lotto_task_run.call_args.args
        self.assertEqual(fail_args[0], 777)
        repo.complete_lotto_task_run.assert_not_called()

    # Scopo: Verifica che il tracing venga saltato quando pipeline_id è None.
    def test_execute_step_no_tracing_when_no_pipeline_id(self):
        processi = [{"task": "generate_fatture_righe", "fase": "Genera righe", "params": {}}]
        executor, repo, fatture_righe_service, _ = self._build_executor(processi)
        repo.get_pipeline_id_for_step.return_value = None

        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.task_policy_exists.assert_not_called()
        repo.start_lotto_task_run.assert_not_called()
        repo.complete_lotto_task_run.assert_not_called()
        fatture_righe_service.generate_fatture_righe.assert_called_once()

    # Scopo: Verifica che il tracing venga saltato quando non esiste policy per il task.
    def test_execute_step_no_tracing_when_no_policy(self):
        processi = [{"task": "generate_fatture_righe", "fase": "Genera righe", "params": {}}]
        executor, repo, fatture_righe_service, _ = self._build_executor(processi)
        repo.task_policy_exists.return_value = False

        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.task_policy_exists.assert_called_once_with(100, "generate_fatture_righe")
        repo.start_lotto_task_run.assert_not_called()
        repo.complete_lotto_task_run.assert_not_called()
        fatture_righe_service.generate_fatture_righe.assert_called_once()

    # Scopo: Verifica che select_attivita usi emittente_soggetto_ruolo_id dal context (lotto), non dai params.
    def test_execute_step_select_attivita_uses_emittente_from_context(self):
        processi = [
            {
                "task": "select_attivita",
                "fase": "Selezione attivita",
                "params": {"emittente_soggetto_ruolo_id": 99},
            }
        ]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "select_attivita_default"
        repo.get_lotto_context.return_value = MagicMock(
            competenza_mese="2026-01-01",
            utility_id=None,
            tipo_doc_fiscale_id=None,
            emittente_soggetto_ruolo_id=42,
        )

        executor.execute_step(
            lotto_id=7,
            stato_doc_fiscale_id=1,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.run_select_attivita_task.assert_called_once()
        call_kwargs = repo.run_select_attivita_task.call_args.kwargs
        self.assertEqual(call_kwargs["context"].emittente_soggetto_ruolo_id, 42)

    # --- Pull attivita da commessa (step 0) ---

    # Scopo: Verifica il caso `test_execute_step_runs_pull_attivita_da_commessa_task`.
    @patch("apps.vendite.services.pipeline_step_executor.transaction")
    def test_execute_step_runs_pull_attivita_da_commessa_task(self, _mock_txn):
        processi = [{"task": "pull_attivita_da_commessa", "fase": "Pull commesse", "params": {}}]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "pull_attivita_da_commessa_default"
        repo.ALLOWED_TASK_FUNCTIONS["pull_attivita_da_commessa"] = (
            "vendite.fn_emit_attivita_fatturabili_da_commessa"
        )
        commesse_repo = MagicMock()
        commesse_repo.list_commesse_emittibili.return_value = [10, 20]
        executor.commesse_repository = commesse_repo

        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        commesse_repo.list_commesse_emittibili.assert_called_once()
        self.assertEqual(commesse_repo.emit_attivita_fatturabili.call_count, 2)
        call_args_list = commesse_repo.emit_attivita_fatturabili.call_args_list
        self.assertEqual(call_args_list[0][0][0], 10)
        self.assertEqual(call_args_list[1][0][0], 20)

    # Scopo: Verifica il caso `test_pull_attivita_da_commessa_dry_run_skips_emit`.
    def test_pull_attivita_da_commessa_dry_run_skips_emit(self):
        processi = [{"task": "pull_attivita_da_commessa", "fase": "Pull commesse", "params": {}}]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "pull_attivita_da_commessa_default"
        repo.ALLOWED_TASK_FUNCTIONS["pull_attivita_da_commessa"] = (
            "vendite.fn_emit_attivita_fatturabili_da_commessa"
        )
        commesse_repo = MagicMock()
        commesse_repo.list_commesse_emittibili.return_value = [10, 20]
        executor.commesse_repository = commesse_repo

        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=True,
        )

        commesse_repo.emit_attivita_fatturabili.assert_not_called()

    # Scopo: Verifica il caso `test_pull_attivita_da_commessa_empty_list_no_emit`.
    def test_pull_attivita_da_commessa_empty_list_no_emit(self):
        processi = [{"task": "pull_attivita_da_commessa", "fase": "Pull commesse", "params": {}}]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "pull_attivita_da_commessa_default"
        repo.ALLOWED_TASK_FUNCTIONS["pull_attivita_da_commessa"] = (
            "vendite.fn_emit_attivita_fatturabili_da_commessa"
        )
        commesse_repo = MagicMock()
        commesse_repo.list_commesse_emittibili.return_value = []
        executor.commesse_repository = commesse_repo

        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        commesse_repo.list_commesse_emittibili.assert_called_once()
        commesse_repo.emit_attivita_fatturabili.assert_not_called()
