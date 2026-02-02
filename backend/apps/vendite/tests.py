"""
Indice test eseguiti:
1) VenditePipelineApiTests.test_run_lotto_pipeline_ok
2) VenditePipelineApiTests.test_run_lotto_pipeline_invalid_json
3) VenditePipelineApiTests.test_run_lotto_pipeline_pipeline_error
4) VenditePipelineApiTests.test_run_lotto_pipeline_retryable_error
5) LottoPipelineRunnerUnitTests.test_runner_calls_step_executor
"""

import json
from contextlib import nullcontext
from unittest.mock import patch

from django.test import Client, SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.pipeline_runner import LottoPipelineParams, LottoPipelineRunner


class VenditePipelineApiTests(SimpleTestCase):
    def setUp(self) -> None:
        self.client = Client()

    @patch("apps.vendite.api.views.pr_run_lotto_pipeline")
    def test_run_lotto_pipeline_ok(self, mocked_service):
        mocked_service.return_value = 123
        response = self.client.post(
            "/api/vendite/pipeline/run/",
            data=json.dumps({"tipo_lotto": "MASSIVO", "dry_run": True}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["lotto_id"], 123)
        mocked_service.assert_called_once()

    def test_run_lotto_pipeline_invalid_json(self):
        response = self.client.post(
            "/api/vendite/pipeline/run/",
            data="{invalid",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "invalid_json")

    @patch("apps.vendite.api.views.pr_run_lotto_pipeline")
    def test_run_lotto_pipeline_pipeline_error(self, mocked_service):
        mocked_service.side_effect = ServiceError(
            code="E_PIPELINE_LOTTO_NOT_FOUND",
            message="Lotto pipeline non trovato.",
            detail="Lotto non trovato",
        )
        response = self.client.post(
            "/api/vendite/pipeline/run/",
            data=json.dumps({"lotto_id": 999}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_PIPELINE_LOTTO_NOT_FOUND")
        self.assertIn("Lotto non trovato", body["detail"])
        self.assertEqual(body["ui_action"], "show_empty_state")

    @patch("apps.vendite.api.views.pr_run_lotto_pipeline")
    def test_run_lotto_pipeline_retryable_error(self, mocked_service):
        mocked_service.side_effect = ServiceError(
            code="E_DATABASE_RETRYABLE",
            message="Conflitto transazionale, riprovare.",
            retryable=True,
        )
        response = self.client.post(
            "/api/vendite/pipeline/run/",
            data=json.dumps({"lotto_id": 1}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 409)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_DATABASE_RETRYABLE")
        self.assertEqual(body["ui_action"], "show_retry_dialog")


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
