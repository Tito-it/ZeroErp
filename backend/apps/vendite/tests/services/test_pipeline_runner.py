"""
Indice test eseguiti:
1) LottoPipelineRunnerUnitTests.test_runner_calls_step_executor
2) LottoPipelineRunnerUnitTests.test_runner_wraps_unexpected_error_with_service_error
3) LottoPipelineRunnerUnitTests.test_runner_preserves_service_error_code
4) LottoPipelineRunnerUnitTests.test_runner_does_not_mask_error_when_mark_fails
5) LottoPipelineRunnerUnitTests.test_runner_completed_lotto_reexecutes_pipeline_steps
6) LottoPipelineRunnerUnitTests.test_runner_massivo_error_rerun_resumes_from_current_step
7) LottoPipelineRunnerUnitTests.test_runner_massivo_error_rerun_executes_step_rollback_when_enabled
8) LottoPipelineRunnerUnitTests.test_runner_massivo_error_rerun_skips_destructive_reset_lotto_rollback
9) LottoPipelineRunnerUnitTests.test_runner_blocks_when_lotto_in_esecuzione
10) LottoPipelineRunnerUnitTests.test_runner_closes_lotto_when_stato_has_chiude_lotto_flag
11) LottoPipelineRunnerUnitTests.test_runner_does_not_close_lotto_when_stato_has_no_chiude_lotto_flag
12) LottoPipelineRunnerUnitTests.test_runner_does_not_block_new_lotto_when_initial_state_is_in_esecuzione
13) LottoPipelineRunnerUnitTests.test_runner_blocks_when_lotto_has_critical_signals
14) LottoPipelineRunnerUnitTests.test_runner_blocks_when_fatture_hanno_stato_esecuzione_errore
15) LottoPipelineRunnerUnitTests.test_runner_non_blocca_se_solo_warning_senza_critical_e_senza_stato_errore
16) LottoPipelineRunnerUnitTests.test_runner_emits_pipeline_started_event
17) LottoPipelineRunnerUnitTests.test_runner_emits_pipeline_completed_event
18) LottoPipelineRunnerUnitTests.test_runner_emits_step_completed_event
19) LottoPipelineRunnerUnitTests.test_runner_emits_pipeline_error_event
20) LottoPipelineRunnerUnitTests.test_runner_syncs_fatture_to_step_stato_on_forward
21) LottoPipelineRunnerUnitTests.test_runner_does_not_sync_fatture_in_dry_run
"""

from contextlib import nullcontext
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.pipeline_runner import LottoPipelineParams, LottoPipelineRunner


class LottoPipelineRunnerUnitTests(SimpleTestCase):
    class _RepoMock:
        # Scopo: Recupera `or_create_lotto` dal contesto applicativo o dal database.
        def get_or_create_lotto(self, **kwargs):
            return 10

        # Scopo: Recupera `lotto_tipo` dal contesto applicativo o dal database.
        def get_lotto_tipo(self, lotto_id):
            return "MASSIVO"

        # Scopo: Recupera `stato_doc_fiscale_id` dal contesto applicativo o dal database.
        def get_stato_doc_fiscale_id(self, codice):
            mapping = {
                "DRAFT": 1,
                "EMESSA": 2,
                "INVIATA": 3,
            }
            return mapping.get(codice, 99)

        # Scopo: Recupera `lotto_job_stato` dal contesto applicativo o dal database.
        def get_lotto_job_stato(self, lotto_id):
            return "DRAFT"

        # Scopo: Determina se il lotto e` in errore usando lo stato job persistito.
        def is_lotto_in_errore(self, lotto_id):
            return self.get_lotto_job_stato(lotto_id) == "ERRORE"

        # Scopo: Recupera `lotto_stato_doc_fiscale_id` dal contesto applicativo o dal database.
        def get_lotto_stato_doc_fiscale_id(self, lotto_id):
            return 1

        # Scopo: Restituisce riepilogo segnalazioni lotto per severita`.
        def get_lotto_segnalazioni_summary(self, lotto_id):
            return {
                "fatture_critical_count": 0,
                "fatture_warning_count": 0,
                "lotto_critical_count": 0,
                "lotto_warning_count": 0,
                "lotto_info_count": 0,
                "fatture_stato_esecuzione_errore_count": 0,
            }

        # Scopo: Aggiorna `lotto_job_stato` con i valori richiesti dal flusso corrente.
        def set_lotto_job_stato(self, lotto_id, stato, messaggio):
            self.last_stato = stato

        # Scopo: Restituisce elenco `pipeline_steps` in base ai filtri disponibili.
        def list_pipeline_steps(self, tipo_lotto, utility_id=None, tipo_doc_fiscale_id=None):
            class _Step:
                # Scopo: Inizializza la istanza.
                def __init__(self, stato_doc_fiscale_id, descrizione, ordine):
                    self.stato_doc_fiscale_id = stato_doc_fiscale_id
                    self.descrizione = descrizione
                    self.ordine = ordine

            return [
                _Step(1, "Step DRAFT", 1),
                _Step(2, "Step EMESSA", 2),
                _Step(8, "Step DEFINITIVA", 3),
            ]

        # Scopo: Gestisce `update_lotto_stato_doc` nel flusso applicativo del modulo.
        def update_lotto_stato_doc(self, lotto_id, stato_doc_fiscale_id):
            return None

        # Scopo: Gestisce `close_giornaliero_lotto` nel flusso applicativo del modulo.
        def close_giornaliero_lotto(self, lotto_id, inviata_id):
            return None

        # Scopo: Recupera `stato_doc_chiude_lotto` dal contesto applicativo o dal database.
        def is_stato_doc_chiude_lotto(self, stato_doc_fiscale_id):
            return False

        # Scopo: Gestisce `close_lotto_operativo` nel flusso applicativo del modulo.
        def close_lotto_operativo(self, lotto_id):
            self.close_lotto_operativo_called = lotto_id
            return None

        # Scopo: Gestisce `log_pipeline_fase` nel flusso applicativo del modulo.
        def log_pipeline_fase(self, **kwargs):
            return None

        # Scopo: Gestisce `log_lotto_esito_fatture` nel flusso applicativo del modulo.
        def log_lotto_esito_fatture(self, lotto_id):
            return None

        # Scopo: Stub `sync_lotto_fatture_stato` con tracking delle chiamate (lotto, stato).
        def sync_lotto_fatture_stato(self, *, lotto_id, stato_doc_fiscale_id=None):
            if not hasattr(self, "sync_calls"):
                self.sync_calls = []
            self.sync_calls.append((lotto_id, stato_doc_fiscale_id))
            return None

        # Scopo: Gestisce `log_fatture_lotto` nel flusso applicativo del modulo.
        def log_fatture_lotto(self, **kwargs):
            return None

        # Scopo: Recupera `step_processes` dal contesto applicativo o dal database.
        def get_step_processes(
            self,
            stato_doc_fiscale_id,
            *,
            tipo_lotto,
            utility_id,
            tipo_doc_fiscale_id,
            rollback,
        ):
            if rollback and stato_doc_fiscale_id == 2:
                return [{"task": "reset_lotto_draft", "params": {}}]
            return []

        # Scopo: Gestisce `has_step_processes` nel flusso applicativo del modulo.
        def has_step_processes(
            self,
            *,
            stato_doc_fiscale_id,
            tipo_lotto,
            utility_id,
            tipo_doc_fiscale_id,
            rollback,
        ):
            return rollback and stato_doc_fiscale_id == 2

        # Scopo: Recupera `lotto_context` dal contesto applicativo o dal database.
        def get_lotto_context(self, lotto_id):
            class _Ctx:
                competenza_mese = "2026-01-01"
                tipo_doc_fiscale_id = 1
                utility_id = 1
                billing_account_id = None
                lock_batch_id = None
                emittente_soggetto_ruolo_id = None

            return _Ctx()

        # Scopo: Stub per log_event su event_log.
        def log_event(self, **kwargs):
            return 1

    class _StepExecutorMock:
        # Scopo: Inizializza la istanza.
        def __init__(self):
            self.called = False
            self.last_kwargs = {}
            self.calls = []

        # Scopo: Gestisce `execute_step` nel flusso applicativo del modulo.
        def execute_step(self, **kwargs):
            self.called = True
            self.last_kwargs = kwargs
            self.calls.append(kwargs)

    class _UnexpectedFailingStepExecutorMock:
        # Scopo: Gestisce `execute_step` nel flusso applicativo del modulo.
        def execute_step(self, **kwargs):
            raise RuntimeError("boom")

    class _ServiceFailingStepExecutorMock:
        # Scopo: Gestisce `execute_step` nel flusso applicativo del modulo.
        def execute_step(self, **kwargs):
            raise ServiceError(
                code="E_TASK_NOT_IMPLEMENTED",
                message="Task pipeline non implementato.",
                detail="Task pipeline non implementato: test",
            )

    # Scopo: Verifica il caso `test_runner_calls_step_executor`.
    def test_runner_calls_step_executor(self):
        repo = self._RepoMock()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            result = runner.run_pipeline(LottoPipelineParams(dry_run=True))
        self.assertEqual(result, 10)
        self.assertTrue(step_executor.called)
        self.assertEqual(step_executor.last_kwargs["tipo_lotto"], "MASSIVO")

    # Scopo: Verifica il caso `test_runner_wraps_unexpected_error_with_service_error`.
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

    # Scopo: Verifica il caso `test_runner_preserves_service_error_code`.
    def test_runner_preserves_service_error_code(self):
        repo = self._RepoMock()
        step_executor = self._ServiceFailingStepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            with self.assertRaises(ServiceError) as exc:
                runner.run_pipeline(LottoPipelineParams(dry_run=False))
        self.assertEqual(exc.exception.code, "E_TASK_NOT_IMPLEMENTED")
        self.assertEqual(repo.last_stato, "ERRORE")

    # Scopo: Verifica il caso `test_runner_does_not_mask_error_when_mark_fails`.
    def test_runner_does_not_mask_error_when_mark_fails(self):
        class _FailingMarkRepo(self._RepoMock):
            # Scopo: Aggiorna `lotto_job_stato` con i valori richiesti dal flusso corrente.
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

    # Scopo: Verifica il caso `test_runner_completed_lotto_reexecutes_pipeline_steps`.
    def test_runner_completed_lotto_reexecutes_pipeline_steps(self):
        class _CompletedRepo(self._RepoMock):
            # Scopo: Recupera `lotto_job_stato` dal contesto applicativo o dal database.
            def get_lotto_job_stato(self, lotto_id):
                return "COMPLETATO"

        repo = _CompletedRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            result = runner.run_pipeline(LottoPipelineParams(lotto_id=0, dry_run=True))
        self.assertEqual(result, 10)
        self.assertEqual(len(step_executor.calls), 1)
        self.assertEqual(step_executor.calls[0]["stato_doc_fiscale_id"], 1)

    # Scopo: Verifica il caso `test_runner_massivo_error_rerun_resumes_from_current_step`.
    def test_runner_massivo_error_rerun_resumes_from_current_step(self):
        class _ErroredRepo(self._RepoMock):
            # Scopo: Recupera `lotto_job_stato` dal contesto applicativo o dal database.
            def get_lotto_job_stato(self, lotto_id):
                return "ERRORE"

            # Scopo: Recupera `lotto_stato_doc_fiscale_id` dal contesto applicativo o dal database.
            def get_lotto_stato_doc_fiscale_id(self, lotto_id):
                return 8

        repo = _ErroredRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            result = runner.run_pipeline(LottoPipelineParams(dry_run=True, tipo_lotto="MASSIVO"))
        self.assertEqual(result, 10)
        self.assertEqual(len(step_executor.calls), 1)
        self.assertEqual(step_executor.calls[0]["stato_doc_fiscale_id"], 8)
        self.assertFalse(step_executor.calls[0]["rollback"])

    # Scopo: Verifica il caso `test_runner_massivo_error_rerun_executes_step_rollback_when_enabled`.
    def test_runner_massivo_error_rerun_executes_step_rollback_when_enabled(self):
        class _ErroredRepo(self._RepoMock):
            # Scopo: Recupera `lotto_job_stato` dal contesto applicativo o dal database.
            def get_lotto_job_stato(self, lotto_id):
                return "ERRORE"

            # Scopo: Recupera `lotto_stato_doc_fiscale_id` dal contesto applicativo o dal database.
            def get_lotto_stato_doc_fiscale_id(self, lotto_id):
                return 2

            # Scopo: Recupera `step_processes` dal contesto applicativo o dal database.
            def get_step_processes(
                self,
                stato_doc_fiscale_id,
                *,
                tipo_lotto,
                utility_id,
                tipo_doc_fiscale_id,
                rollback,
            ):
                if rollback and stato_doc_fiscale_id == 2:
                    return [{"task": "noop", "params": {}}]
                return []

        repo = _ErroredRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            result = runner.run_pipeline(
                LottoPipelineParams(
                    dry_run=True,
                    tipo_lotto="MASSIVO",
                    meta={"auto_step_rollback": True},
                )
            )
        self.assertEqual(result, 10)
        self.assertEqual(len(step_executor.calls), 2)
        self.assertEqual(step_executor.calls[0]["stato_doc_fiscale_id"], 2)
        self.assertTrue(step_executor.calls[0]["rollback"])
        self.assertEqual(step_executor.calls[1]["stato_doc_fiscale_id"], 2)
        self.assertFalse(step_executor.calls[1]["rollback"])

    # Scopo: Verifica il caso `test_runner_massivo_error_rerun_skips_destructive_reset_lotto_rollback`.
    def test_runner_massivo_error_rerun_skips_destructive_reset_lotto_rollback(self):
        class _ErroredRepo(self._RepoMock):
            # Scopo: Recupera `lotto_job_stato` dal contesto applicativo o dal database.
            def get_lotto_job_stato(self, lotto_id):
                return "ERRORE"

            # Scopo: Recupera `lotto_stato_doc_fiscale_id` dal contesto applicativo o dal database.
            def get_lotto_stato_doc_fiscale_id(self, lotto_id):
                return 2

        repo = _ErroredRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            result = runner.run_pipeline(
                LottoPipelineParams(
                    dry_run=True,
                    tipo_lotto="MASSIVO",
                    meta={"auto_step_rollback": True},
                )
            )
        self.assertEqual(result, 10)
        self.assertEqual(len(step_executor.calls), 1)
        self.assertEqual(step_executor.calls[0]["stato_doc_fiscale_id"], 2)
        self.assertFalse(step_executor.calls[0]["rollback"])

    # Scopo: Verifica il caso `test_runner_blocks_when_lotto_in_esecuzione`.
    def test_runner_blocks_when_lotto_in_esecuzione(self):
        class _RunningRepo(self._RepoMock):
            # Scopo: Recupera `lotto_job_stato` dal contesto applicativo o dal database.
            def get_lotto_job_stato(self, lotto_id):
                return "IN_ESECUZIONE"

        repo = _RunningRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            with self.assertRaises(ServiceError) as exc:
                runner.run_pipeline(LottoPipelineParams(lotto_id=10, dry_run=True))
        self.assertEqual(exc.exception.code, "E_PIPELINE_LOTTO_IN_ESECUZIONE")
        self.assertFalse(step_executor.called)

    # Scopo: Verifica il caso `test_runner_closes_lotto_when_stato_has_chiude_lotto_flag`.
    def test_runner_closes_lotto_when_stato_has_chiude_lotto_flag(self):
        class _CloseByFlagRepo(self._RepoMock):
            # Scopo: Recupera `stato_doc_chiude_lotto` dal contesto applicativo o dal database.
            def is_stato_doc_chiude_lotto(self, stato_doc_fiscale_id):
                return stato_doc_fiscale_id == 8

            # Scopo: Restituisce elenco `pipeline_steps` in base ai filtri disponibili.
            def list_pipeline_steps(self, tipo_lotto, utility_id=None, tipo_doc_fiscale_id=None):
                class _Step:
                    # Scopo: Inizializza la istanza.
                    def __init__(self, stato_doc_fiscale_id, descrizione, ordine):
                        self.stato_doc_fiscale_id = stato_doc_fiscale_id
                        self.descrizione = descrizione
                        self.ordine = ordine

                return [_Step(8, "Step DEFINITIVA", 1)]

        repo = _CloseByFlagRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            result = runner.run_pipeline(LottoPipelineParams(dry_run=False))
        self.assertEqual(result, 10)
        self.assertEqual(getattr(repo, "close_lotto_operativo_called", None), 10)

    # Scopo: Verifica il caso `test_runner_does_not_close_lotto_when_stato_has_no_chiude_lotto_flag`.
    def test_runner_does_not_close_lotto_when_stato_has_no_chiude_lotto_flag(self):
        class _NoCloseByFlagRepo(self._RepoMock):
            # Scopo: Recupera `stato_doc_chiude_lotto` dal contesto applicativo o dal database.
            def is_stato_doc_chiude_lotto(self, stato_doc_fiscale_id):
                return False

            # Scopo: Restituisce elenco `pipeline_steps` in base ai filtri disponibili.
            def list_pipeline_steps(self, tipo_lotto, utility_id=None, tipo_doc_fiscale_id=None):
                class _Step:
                    # Scopo: Inizializza la istanza.
                    def __init__(self, stato_doc_fiscale_id, descrizione, ordine):
                        self.stato_doc_fiscale_id = stato_doc_fiscale_id
                        self.descrizione = descrizione
                        self.ordine = ordine

                return [_Step(1, "Step DRAFT", 1)]

        repo = _NoCloseByFlagRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            result = runner.run_pipeline(LottoPipelineParams(dry_run=False))
        self.assertEqual(result, 10)
        self.assertIsNone(getattr(repo, "close_lotto_operativo_called", None))

    # Scopo: Verifica che dopo lo step (forward, non dry-run) le fatture vengano
    # sincronizzate allo stato_doc_fiscale_id dello step (es. EMESSA/2), così la
    # fattura segue il lotto e non salta a DEFINITIVA/8 violando la matrice.
    def test_runner_syncs_fatture_to_step_stato_on_forward(self):
        class _SingleEmessaStepRepo(self._RepoMock):
            # Scopo: Forza il resolve a tenere lo step EMESSA come unico step da eseguire.
            def get_lotto_stato_doc_fiscale_id(self, lotto_id):
                return None

            # Scopo: Restituisce un solo step EMESSA(2).
            def list_pipeline_steps(self, tipo_lotto, utility_id=None, tipo_doc_fiscale_id=None):
                class _Step:
                    # Scopo: Inizializza la istanza.
                    def __init__(self, stato_doc_fiscale_id, descrizione, ordine):
                        self.stato_doc_fiscale_id = stato_doc_fiscale_id
                        self.descrizione = descrizione
                        self.ordine = ordine

                return [_Step(2, "Step EMESSA", 1)]

        repo = _SingleEmessaStepRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            result = runner.run_pipeline(LottoPipelineParams(dry_run=False))
        self.assertEqual(result, 10)
        # La fattura viene allineata allo stato dello step (lotto 10, stato 2).
        self.assertEqual(getattr(repo, "sync_calls", []), [(10, 2)])

    # Scopo: Verifica che in dry-run NON venga sincronizzato lo stato delle fatture.
    def test_runner_does_not_sync_fatture_in_dry_run(self):
        repo = self._RepoMock()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            result = runner.run_pipeline(LottoPipelineParams(dry_run=True))
        self.assertEqual(result, 10)
        self.assertEqual(getattr(repo, "sync_calls", []), [])

    # Scopo: Verifica il caso `test_runner_does_not_block_new_lotto_when_initial_state_is_in_esecuzione`.
    def test_runner_does_not_block_new_lotto_when_initial_state_is_in_esecuzione(self):
        class _NewLottoInEsecuzioneRepo(self._RepoMock):
            # Scopo: Recupera `lotto_job_stato` dal contesto applicativo o dal database.
            def get_lotto_job_stato(self, lotto_id):
                return "IN_ESECUZIONE"

        repo = _NewLottoInEsecuzioneRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            result = runner.run_pipeline(LottoPipelineParams(lotto_id=0, dry_run=True))
        self.assertEqual(result, 10)
        self.assertTrue(step_executor.called)

    # Scopo: Verifica il caso `test_runner_blocks_when_lotto_has_critical_signals`.
    def test_runner_blocks_when_lotto_has_critical_signals(self):
        class _CriticalSignalsRepo(self._RepoMock):
            # Scopo: Restituisce riepilogo segnalazioni lotto per severita`.
            def get_lotto_segnalazioni_summary(self, lotto_id):
                return {
                    "fatture_critical_count": 1,
                    "fatture_warning_count": 0,
                    "lotto_critical_count": 0,
                    "lotto_warning_count": 0,
                    "lotto_info_count": 0,
                    "fatture_stato_esecuzione_errore_count": 0,
                }

        repo = _CriticalSignalsRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            with self.assertRaises(ServiceError) as exc:
                runner.run_pipeline(LottoPipelineParams(dry_run=False))
        self.assertEqual(exc.exception.code, "E_PIPELINE_LOTTO_CRITICAL")
        self.assertFalse(step_executor.called)

    # Scopo: Verifica che il runner blocchi quando la tabella ponte ha fatture con stato_esecuzione=ERRORE,
    # anche in assenza di segnalazioni critical nei log (guard unificata PRE-1).
    def test_runner_blocks_when_fatture_hanno_stato_esecuzione_errore(self):
        class _StatoEsecuzioneErroreRepo(self._RepoMock):
            # Scopo: Restituisce riepilogo con fatture in stato errore per test blocco.
            def get_lotto_segnalazioni_summary(self, lotto_id):
                return {
                    "fatture_critical_count": 0,
                    "fatture_warning_count": 0,
                    "lotto_critical_count": 0,
                    "lotto_warning_count": 0,
                    "lotto_info_count": 0,
                    "fatture_stato_esecuzione_errore_count": 2,
                }

        repo = _StatoEsecuzioneErroreRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            with self.assertRaises(ServiceError) as exc:
                runner.run_pipeline(LottoPipelineParams(dry_run=False))
        self.assertEqual(exc.exception.code, "E_PIPELINE_LOTTO_CRITICAL")
        self.assertFalse(step_executor.called)

    # Scopo: Verifica che la sola presenza di warning (senza critical e senza stato_esecuzione=ERRORE)
    # non blocchi il runner (partial failure non bloccante).
    def test_runner_non_blocca_se_solo_warning_senza_critical_e_senza_stato_errore(self):
        class _OnlyWarningsRepo(self._RepoMock):
            # Scopo: Restituisce riepilogo segnalazioni lotto per severita`.
            def get_lotto_segnalazioni_summary(self, lotto_id):
                return {
                    "fatture_critical_count": 0,
                    "fatture_warning_count": 3,
                    "lotto_critical_count": 0,
                    "lotto_warning_count": 1,
                    "lotto_info_count": 0,
                    "fatture_stato_esecuzione_errore_count": 0,
                }

        repo = _OnlyWarningsRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            result = runner.run_pipeline(LottoPipelineParams(dry_run=True))
        self.assertEqual(result, 10)
        self.assertTrue(step_executor.called)

    # Scopo: Verifica che run_pipeline emetta PIPELINE_STARTED su event_log.
    def test_runner_emits_pipeline_started_event(self):
        repo = MagicMock(wraps=self._RepoMock())
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            runner.run_pipeline(LottoPipelineParams(dry_run=True))
        started_calls = [
            c for c in repo.log_event.call_args_list
            if c.kwargs.get("event_code") == "PIPELINE_STARTED"
        ]
        self.assertEqual(len(started_calls), 1)
        self.assertEqual(started_calls[0].kwargs["domain"], "PIPELINE")
        self.assertEqual(started_calls[0].kwargs["entity_type"], "LOTTO")
        self.assertEqual(started_calls[0].kwargs["entity_id"], 10)

    # Scopo: Verifica che run_pipeline emetta PIPELINE_COMPLETED su event_log.
    def test_runner_emits_pipeline_completed_event(self):
        repo = MagicMock(wraps=self._RepoMock())
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            runner.run_pipeline(LottoPipelineParams(dry_run=True))
        completed_calls = [
            c for c in repo.log_event.call_args_list
            if c.kwargs.get("event_code") == "PIPELINE_COMPLETED"
        ]
        self.assertEqual(len(completed_calls), 1)
        self.assertEqual(completed_calls[0].kwargs["domain"], "PIPELINE")
        self.assertEqual(completed_calls[0].kwargs["payload"]["tipo_lotto"], "MASSIVO")

    # Scopo: Verifica che _execute_pipeline_step emetta STEP_COMPLETED su event_log.
    def test_runner_emits_step_completed_event(self):
        repo = MagicMock(wraps=self._RepoMock())
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            runner.run_pipeline(LottoPipelineParams(dry_run=True))
        step_calls = [
            c for c in repo.log_event.call_args_list
            if c.kwargs.get("event_code") == "STEP_COMPLETED"
        ]
        self.assertEqual(len(step_calls), 1)
        self.assertEqual(step_calls[0].kwargs["payload"]["stato_doc_fiscale_id"], 1)

    # Scopo: Verifica che un errore pipeline emetta PIPELINE_ERROR su event_log.
    def test_runner_emits_pipeline_error_event(self):
        repo = MagicMock(wraps=self._RepoMock())
        step_executor = self._UnexpectedFailingStepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            with self.assertRaises(ServiceError):
                runner.run_pipeline(LottoPipelineParams(dry_run=False))
        error_calls = [
            c for c in repo.log_event.call_args_list
            if c.kwargs.get("event_code") == "PIPELINE_ERROR"
        ]
        self.assertEqual(len(error_calls), 1)
        self.assertEqual(error_calls[0].kwargs["severity"], "ERROR")
        self.assertEqual(error_calls[0].kwargs["domain"], "PIPELINE")

    # Scopo: F1 — su lotto ESISTENTE in successo, il runner AVANZA allo step
    # successivo a quello corrente (non ri-esegue il primo). Catalogo [1,2,8],
    # stato corrente 1 → esegue lo step 2.
    def test_runner_existing_lotto_success_advances_to_next_step(self):
        repo = self._RepoMock()  # job_stato "DRAFT" (non ERRORE), stato_doc corrente 1
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            result = runner.run_pipeline(LottoPipelineParams(lotto_id=10, dry_run=True))
        self.assertEqual(result, 10)
        self.assertEqual(len(step_executor.calls), 1)
        # Avanzamento: NON il primo step (1) ma il successivo (2).
        self.assertEqual(step_executor.calls[0]["stato_doc_fiscale_id"], 2)

    # Scopo: F1 — su lotto ESISTENTE in successo gia` all'ultimo step del catalogo,
    # non resta nulla da eseguire: nessuno step e il lotto risulta COMPLETATO.
    def test_runner_existing_lotto_success_at_last_step_is_noop(self):
        class _AtLastStepRepo(self._RepoMock):
            # Scopo: stato corrente = ultimo step del catalogo (8).
            def get_lotto_stato_doc_fiscale_id(self, lotto_id):
                return 8

        repo = _AtLastStepRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            result = runner.run_pipeline(LottoPipelineParams(lotto_id=10, dry_run=True))
        self.assertEqual(result, 10)
        self.assertEqual(len(step_executor.calls), 0)
        self.assertEqual(repo.last_stato, "COMPLETATO")

    # --- F2: driver run_lotto_until_done ---

    # Repo stateful: lo stato_doc avanza man mano che update_lotto_stato_doc viene
    # chiamato, così il loop del driver progredisce realmente tra le iterazioni.
    class _StatefulRepo(_RepoMock):
        # Scopo: stato corrente del lotto, mutato dal runner ad ogni step.
        def __init__(self, chiude_su=8):
            self.current = None
            self.last_stato = None
            self._chiude_su = chiude_su

        def get_lotto_stato_doc_fiscale_id(self, lotto_id):
            return self.current

        def update_lotto_stato_doc(self, lotto_id, stato_doc_fiscale_id):
            self.current = stato_doc_fiscale_id

        def is_stato_doc_chiude_lotto(self, stato_doc_fiscale_id):
            return self._chiude_su is not None and stato_doc_fiscale_id == self._chiude_su

    # Scopo: F2 — il driver concatena gli step del catalogo [1,2,8] e si ferma allo
    # step di chiusura (chiude_lotto su 8): 3 step eseguiti, esito COMPLETATO.
    def test_until_done_advances_and_stops_at_chiude_lotto(self):
        repo = self._StatefulRepo(chiude_su=8)
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            esito = runner.run_lotto_until_done(LottoPipelineParams(dry_run=True))
        self.assertEqual(esito["lotto_id"], 10)
        self.assertEqual(esito["step_eseguiti"], 3)
        self.assertEqual(esito["motivo_stop"], "COMPLETATO")
        self.assertEqual(esito["stato_doc_fiscale_id"], 8)
        self.assertEqual([c["stato_doc_fiscale_id"] for c in step_executor.calls], [1, 2, 8])

    # Scopo: F2 — senza flag chiude_lotto, il driver si ferma per "nessun avanzamento"
    # una volta esaurito il catalogo (3 step eseguiti), esito COMPLETATO.
    def test_until_done_stops_on_no_progress_without_chiude_flag(self):
        repo = self._StatefulRepo(chiude_su=None)
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            esito = runner.run_lotto_until_done(LottoPipelineParams(dry_run=True))
        self.assertEqual(esito["step_eseguiti"], 3)
        self.assertEqual(esito["motivo_stop"], "COMPLETATO")
        self.assertEqual([c["stato_doc_fiscale_id"] for c in step_executor.calls], [1, 2, 8])

    # Scopo: F2 (regressione bug step fantasma) — su lotto ESISTENTE già all'ultimo
    # step, il driver NON conta step inesistenti: 0 step, esito COMPLETATO.
    def test_until_done_existing_lotto_already_at_last_step_no_phantom_step(self):
        repo = self._StatefulRepo(chiude_su=8)
        repo.current = 8  # già all'ultimo step del catalogo [1,2,8]
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            esito = runner.run_lotto_until_done(LottoPipelineParams(lotto_id=10, dry_run=True))
        self.assertEqual(esito["lotto_id"], 10)
        self.assertEqual(esito["step_eseguiti"], 0)
        self.assertEqual(esito["motivo_stop"], "COMPLETATO")
        self.assertEqual(len(step_executor.calls), 0)

    # Scopo: F2 — su lotto ESISTENTE con segnalazioni critical il driver non esegue
    # step e ritorna un esito BLOCCATO_CRITICITA (no eccezione propagata).
    def test_until_done_blocked_by_critical_returns_outcome(self):
        class _CriticalRepo(self._StatefulRepo):
            # Scopo: riepilogo con criticità attive → blocks_next_step.
            def get_lotto_segnalazioni_summary(self, lotto_id):
                return {
                    "fatture_critical_count": 1,
                    "fatture_warning_count": 0,
                    "lotto_critical_count": 0,
                    "lotto_warning_count": 0,
                    "lotto_info_count": 0,
                    "fatture_stato_esecuzione_errore_count": 0,
                }

        repo = _CriticalRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            esito = runner.run_lotto_until_done(LottoPipelineParams(lotto_id=10, dry_run=False))
        self.assertEqual(esito["lotto_id"], 10)
        self.assertEqual(esito["step_eseguiti"], 0)
        self.assertEqual(esito["motivo_stop"], "BLOCCATO_CRITICITA")
        self.assertEqual(len(step_executor.calls), 0)
