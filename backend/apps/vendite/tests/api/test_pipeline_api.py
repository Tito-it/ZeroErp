"""
Indice test eseguiti:
1) VenditePipelineApiTests.test_run_lotto_pipeline_ok
2) VenditePipelineApiTests.test_run_lotto_pipeline_invalid_json
3) VenditePipelineApiTests.test_run_lotto_pipeline_pipeline_error
4) VenditePipelineApiTests.test_run_lotto_pipeline_retryable_error
5) VenditePipelineApiTests.test_run_lotto_pipeline_echoes_idempotency_key
6) VenditePipelineApiTests.test_run_lotto_pipeline_requires_idempotency_key
7) VenditePipelineApiTests.test_run_lotto_pipeline_v1_requires_jwt
8) VenditePipelineApiTests.test_legacy_vendite_path_not_found_when_disabled
9) VenditePipelineApiTests.test_run_lotto_pipeline_hides_technical_detail_for_generic_errors
10) VenditePipelineApiTests.test_run_lotto_pipeline_exposes_technical_message_in_debug_mode
11) VenditePipelineApiTests.test_run_lotto_pipeline_replays_completed_response_when_strong_idempotency_enabled
12) VenditePipelineApiTests.test_run_lotto_pipeline_returns_conflict_when_idempotency_in_progress
13) VenditePipelineApiTests.test_run_lotto_pipeline_accepts_null_lotto_id
14) VenditePipelineApiTests.test_run_lotto_pipeline_converts_zero_optional_ids_to_none
"""

import json
from unittest.mock import patch
from unittest.mock import Mock

from django.test import Client, SimpleTestCase, override_settings

from apps.core.services.idempotency_store import IdempotencyDecision
from apps.core.services.service_errors import ServiceError


@override_settings(API_STRONG_IDEMPOTENCY_ENABLED=False)
class VenditePipelineApiTests(SimpleTestCase):
    def setUp(self) -> None:
        self.client = Client()

    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.pr_run_lotto_pipeline")
    def test_run_lotto_pipeline_ok(self, mocked_service, _mock_auth):
        mocked_service.return_value = 123
        response = self.client.post(
            "/api/v1/vendite/pipeline/run/",
            data=json.dumps({"tipo_lotto": "MASSIVO", "dry_run": True}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-ok-1"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["lotto_id"], 123)
        self.assertIn("request_id", response.json()["meta"])
        self.assertTrue(response["X-Request-ID"])
        mocked_service.assert_called_once()

    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_run_lotto_pipeline_invalid_json(self, _mock_auth):
        response = self.client.post(
            "/api/v1/vendite/pipeline/run/",
            data="{invalid",
            content_type="application/json",
            headers={"Idempotency-Key": "idem-ok-2"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "invalid_json")

    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.pr_run_lotto_pipeline")
    def test_run_lotto_pipeline_pipeline_error(self, mocked_service, _mock_auth):
        mocked_service.side_effect = ServiceError(
            code="E_PIPELINE_LOTTO_NOT_FOUND",
            message="Lotto pipeline non trovato.",
            detail="Lotto non trovato",
        )
        response = self.client.post(
            "/api/v1/vendite/pipeline/run/",
            data=json.dumps({"lotto_id": 999}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-ok-3"},
        )
        self.assertEqual(response.status_code, 404)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_PIPELINE_LOTTO_NOT_FOUND")
        self.assertIn("Lotto non trovato", body["detail"])
        self.assertEqual(body["ui_action"], "show_empty_state")

    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.pr_run_lotto_pipeline")
    def test_run_lotto_pipeline_retryable_error(self, mocked_service, _mock_auth):
        mocked_service.side_effect = ServiceError(
            code="E_DATABASE_RETRYABLE",
            message="Conflitto transazionale, riprovare.",
            retryable=True,
        )
        response = self.client.post(
            "/api/v1/vendite/pipeline/run/",
            data=json.dumps({"lotto_id": 1}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-ok-4"},
        )
        self.assertEqual(response.status_code, 409)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_DATABASE_RETRYABLE")
        self.assertEqual(body["ui_action"], "show_retry_dialog")
        self.assertEqual(response["Retry-After"], "3")

    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.pr_run_lotto_pipeline")
    def test_run_lotto_pipeline_echoes_idempotency_key(self, mocked_service, _mock_auth):
        mocked_service.return_value = 321
        response = self.client.post(
            "/api/v1/vendite/pipeline/run/",
            data=json.dumps({"dry_run": True}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-abc-123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Idempotency-Key"], "idem-abc-123")
        self.assertEqual(response.json()["meta"]["idempotency_key"], "idem-abc-123")

    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_run_lotto_pipeline_requires_idempotency_key(self, _mock_auth):
        response = self.client.post(
            "/api/v1/vendite/pipeline/run/",
            data=json.dumps({"dry_run": True}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_IDEMPOTENCY_KEY_REQUIRED")

    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.pr_run_lotto_pipeline")
    def test_run_lotto_pipeline_accepts_null_lotto_id(self, mocked_service, _mock_auth):
        mocked_service.return_value = 777
        response = self.client.post(
            "/api/v1/vendite/pipeline/run/",
            data=json.dumps({"lotto_id": None, "dry_run": True}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-null-lotto-1"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["lotto_id"], 777)
        mocked_service.assert_called_once()
        self.assertIsNone(mocked_service.call_args.kwargs["lotto_id"])

    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.pr_run_lotto_pipeline")
    def test_run_lotto_pipeline_converts_zero_optional_ids_to_none(self, mocked_service, _mock_auth):
        mocked_service.return_value = 778
        response = self.client.post(
            "/api/v1/vendite/pipeline/run/",
            data=json.dumps(
                {
                    "lotto_id": 0,
                    "tipo_doc_fiscale_id": 0,
                    "utility_id": 0,
                    "billing_account_id": 0,
                    "dry_run": True,
                }
            ),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-zero-to-null-1"},
        )
        self.assertEqual(response.status_code, 200)
        mocked_service.assert_called_once()
        kwargs = mocked_service.call_args.kwargs
        self.assertIsNone(kwargs["lotto_id"])
        self.assertIsNone(kwargs["tipo_doc_fiscale_id"])
        self.assertIsNone(kwargs["utility_id"])
        self.assertIsNone(kwargs["billing_account_id"])

    def test_run_lotto_pipeline_v1_requires_jwt(self):
        response = self.client.post(
            "/api/v1/vendite/pipeline/run/",
            data=json.dumps({"tipo_lotto": "MASSIVO"}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-v1-missing-auth"},
        )
        self.assertEqual(response.status_code, 401)

    def test_legacy_vendite_path_not_found_when_disabled(self):
        response = self.client.post(
            "/api/vendite/pipeline/run/",
            data=json.dumps({"tipo_lotto": "MASSIVO"}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-legacy-1"},
        )
        self.assertEqual(response.status_code, 404)

    @override_settings(API_EXPOSE_TECHNICAL_DETAILS=False)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.pr_run_lotto_pipeline")
    def test_run_lotto_pipeline_hides_technical_detail_for_generic_errors(self, mocked_service, _mock_auth):
        mocked_service.side_effect = RuntimeError("CONTEXT: SQL interno sensibile")
        response = self.client.post(
            "/api/v1/vendite/pipeline/run/",
            data=json.dumps({"dry_run": True}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-safe-err-1"},
        )
        self.assertEqual(response.status_code, 500)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_GENERICO")
        self.assertEqual(body["message"], "Errore non gestito.")
        self.assertNotIn("SQL interno", body["detail"])
        self.assertIn("request_id", body["detail"])
        self.assertNotIn("technical_message", body)

    @override_settings(API_EXPOSE_TECHNICAL_DETAILS=True)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.pr_run_lotto_pipeline")
    def test_run_lotto_pipeline_exposes_technical_message_in_debug_mode(self, mocked_service, _mock_auth):
        mocked_service.side_effect = RuntimeError("CONTEXT: SQL interno sensibile")
        response = self.client.post(
            "/api/v1/vendite/pipeline/run/",
            data=json.dumps({"dry_run": True}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-safe-err-2"},
        )
        self.assertEqual(response.status_code, 500)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_GENERICO")
        self.assertEqual(body["message"], "Errore non gestito.")
        self.assertEqual(body["technical_message"], "CONTEXT: SQL interno sensibile")

    @override_settings(API_STRONG_IDEMPOTENCY_ENABLED=True)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.core.api.endpoint_helpers.IdempotencyStore.claim_or_replay")
    @patch("apps.vendite.api.views.pr_run_lotto_pipeline")
    def test_run_lotto_pipeline_replays_completed_response_when_strong_idempotency_enabled(
        self,
        mocked_service,
        mocked_claim,
        _mock_auth,
    ):
        mocked_claim.return_value = IdempotencyDecision(
            should_execute=False,
            replay_payload={
                "data": {"lotto_id": 555, "status": "ok"},
                "meta": {"request_id": "00000000-0000-0000-0000-000000000001"},
            },
        )

        response = self.client.post(
            "/api/v1/vendite/pipeline/run/",
            data=json.dumps({"dry_run": True}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-replay-1"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Idempotency-Replayed"], "1")
        self.assertEqual(response.json()["data"]["lotto_id"], 555)
        mocked_service.assert_not_called()

    @override_settings(API_STRONG_IDEMPOTENCY_ENABLED=True)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.core.api.endpoint_helpers.IdempotencyStore.claim_or_replay")
    @patch("apps.vendite.api.views.pr_run_lotto_pipeline")
    def test_run_lotto_pipeline_returns_conflict_when_idempotency_in_progress(
        self,
        mocked_service,
        mocked_claim,
        _mock_auth,
    ):
        mocked_claim.return_value = IdempotencyDecision(
            should_execute=False,
            in_progress=True,
        )

        response = self.client.post(
            "/api/v1/vendite/pipeline/run/",
            data=json.dumps({"dry_run": True}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-progress-1"},
        )

        self.assertEqual(response.status_code, 409)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_IDEMPOTENCY_IN_PROGRESS")
        mocked_service.assert_not_called()
