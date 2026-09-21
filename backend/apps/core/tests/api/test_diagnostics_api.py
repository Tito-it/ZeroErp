"""
Indice test eseguiti:
1) CoreDiagnosticsApiTests.test_error_envelope_default
2) CoreDiagnosticsApiTests.test_error_envelope_retryable
3) CoreDiagnosticsApiTests.test_error_envelope_not_found
4) CoreDiagnosticsApiTests.test_error_envelope_v1_requires_auth_without_token
5) CoreDiagnosticsApiTests.test_openapi_schema_endpoint
6) CoreDiagnosticsApiTests.test_openapi_swagger_ui_endpoint
7) CoreDiagnosticsApiTests.test_legacy_core_path_not_found_when_disabled
"""

from unittest.mock import Mock, patch

from django.test import Client, override_settings
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest


class CoreDiagnosticsApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    # Scopo: Verifica il caso `test_error_envelope_default`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_error_envelope_default(self, _mock_auth):
        response = self.client.get("/api/v1/core/diagnostics/error-envelope/")
        self.assertEqual(response.status_code, 500)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_GENERICO")
        self.assertEqual(body["ui_action"], "show_error_banner")
        self.assertIn("request_id", response.json()["meta"])
        self.assertTrue(response["X-Request-ID"])

    # Scopo: Verifica il caso `test_error_envelope_retryable`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_error_envelope_retryable(self, _mock_auth):
        response = self.client.get("/api/v1/core/diagnostics/error-envelope/?kind=retryable")
        self.assertEqual(response.status_code, 409)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_DATABASE_RETRYABLE")
        self.assertTrue(body["retryable"])
        self.assertEqual(body["ui_action"], "show_retry_dialog")
        self.assertEqual(response["Retry-After"], "3")

    # Scopo: Verifica il caso `test_error_envelope_not_found`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_error_envelope_not_found(self, _mock_auth):
        response = self.client.get("/api/v1/core/diagnostics/error-envelope/?kind=not_found")
        self.assertEqual(response.status_code, 404)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_PIPELINE_LOTTO_NOT_FOUND")
        self.assertIn("Lotto non trovato", body["detail"])

    # Scopo: Verifica che 401 senza JWT segua l'envelope standard del progetto.
    def test_error_envelope_v1_requires_auth_without_token(self):
        response = self.client.get("/api/v1/core/diagnostics/error-envelope/")
        self.assertEqual(response.status_code, 401)
        body = response.json()
        self.assertEqual(body["error"]["code"], "E_NOT_AUTHENTICATED")

    # Scopo: Verifica il caso `test_openapi_schema_endpoint`.
    @override_settings(API_DOCS_ENABLED=True)
    def test_openapi_schema_endpoint(self):
        # Smoke test: con il flag acceso lo schema OpenAPI deve essere esposto
        # (il flag e' provato in `test_superficie_pubblica`).
        response = self.client.get("/api/schema/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/vnd.oai.openapi", response["Content-Type"])

    # Scopo: Verifica il caso `test_openapi_swagger_ui_endpoint`.
    @override_settings(API_DOCS_ENABLED=True)
    def test_openapi_swagger_ui_endpoint(self):
        # Smoke test: con il flag acceso la UI Swagger deve essere raggiungibile.
        response = self.client.get("/api/docs/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response["Content-Type"])

    # Scopo: Verifica il caso `test_legacy_core_path_not_found_when_disabled`.
    def test_legacy_core_path_not_found_when_disabled(self):
        response = self.client.get("/api/core/diagnostics/error-envelope/")
        self.assertEqual(response.status_code, 404)
