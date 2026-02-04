"""
Indice test eseguiti:
1) VenditePipelineApiTests.test_run_lotto_pipeline_ok
2) VenditePipelineApiTests.test_run_lotto_pipeline_invalid_json
3) VenditePipelineApiTests.test_run_lotto_pipeline_pipeline_error
4) VenditePipelineApiTests.test_run_lotto_pipeline_retryable_error
5) VenditePipelineApiTests.test_run_lotto_pipeline_echoes_idempotency_key
6) VenditePipelineApiTests.test_run_lotto_pipeline_requires_idempotency_key
7) VenditePipelineApiTests.test_run_lotto_pipeline_v1_requires_jwt
"""

import json
from unittest.mock import patch

from django.test import Client, SimpleTestCase

from apps.core.services.service_errors import ServiceError


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
            headers={"Idempotency-Key": "idem-ok-1"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["lotto_id"], 123)
        self.assertIn("request_id", response.json()["meta"])
        self.assertTrue(response["X-Request-ID"])
        self.assertEqual(response["Deprecation"], "true")
        mocked_service.assert_called_once()

    def test_run_lotto_pipeline_invalid_json(self):
        response = self.client.post(
            "/api/vendite/pipeline/run/",
            data="{invalid",
            content_type="application/json",
            headers={"Idempotency-Key": "idem-ok-2"},
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
            headers={"Idempotency-Key": "idem-ok-3"},
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
            headers={"Idempotency-Key": "idem-ok-4"},
        )
        self.assertEqual(response.status_code, 409)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_DATABASE_RETRYABLE")
        self.assertEqual(body["ui_action"], "show_retry_dialog")
        self.assertEqual(response["Retry-After"], "3")

    @patch("apps.vendite.api.views.pr_run_lotto_pipeline")
    def test_run_lotto_pipeline_echoes_idempotency_key(self, mocked_service):
        mocked_service.return_value = 321
        response = self.client.post(
            "/api/vendite/pipeline/run/",
            data=json.dumps({"dry_run": True}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-abc-123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Idempotency-Key"], "idem-abc-123")
        self.assertEqual(response.json()["meta"]["idempotency_key"], "idem-abc-123")

    def test_run_lotto_pipeline_requires_idempotency_key(self):
        response = self.client.post(
            "/api/vendite/pipeline/run/",
            data=json.dumps({"dry_run": True}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_IDEMPOTENCY_KEY_REQUIRED")

    def test_run_lotto_pipeline_v1_requires_jwt(self):
        response = self.client.post(
            "/api/v1/vendite/pipeline/run/",
            data=json.dumps({"tipo_lotto": "MASSIVO"}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-v1-missing-auth"},
        )
        self.assertEqual(response.status_code, 401)
