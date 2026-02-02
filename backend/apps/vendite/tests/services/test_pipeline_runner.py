"""
Indice test eseguiti:
1) LottoPipelineRunnerUnitTests.test_runner_calls_step_executor
"""

from contextlib import nullcontext
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.vendite.services.pipeline_runner import LottoPipelineParams, LottoPipelineRunner


class LottoPipelineRunnerUnitTests(SimpleTestCase):
    class _RepoMock:
        def get_or_create_lotto(self, **kwargs):
            return 10

        def get_lotto_tipo(self, lotto_id):
            return "MASSIVO"

        def get_stato_doc_fiscale_id(self, codice):
            return 99

        def set_lotto_job_stato(self, lotto_id, stato, messaggio):
            self.last_stato = stato

        def list_pipeline_steps(self, tipo_lotto):
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

    class _StepExecutorMock:
        def __init__(self):
            self.called = False

        def execute_step(self, **kwargs):
            self.called = True

    def test_runner_calls_step_executor(self):
        repo = self._RepoMock()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic", return_value=nullcontext()):
            result = runner.run(LottoPipelineParams(dry_run=True))
        self.assertEqual(result, 10)
        self.assertTrue(step_executor.called)
