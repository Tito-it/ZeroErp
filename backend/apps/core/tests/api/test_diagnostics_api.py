"""
Indice test eseguiti:
1) CoreDiagnosticsApiTests.test_error_envelope_default
2) CoreDiagnosticsApiTests.test_error_envelope_retryable
3) CoreDiagnosticsApiTests.test_error_envelope_not_found
4) CoreDiagnosticsApiTests.test_error_envelope_default_v1_path_requires_auth
5) CoreDiagnosticsApiTests.test_openapi_schema_endpoint
6) CoreDiagnosticsApiTests.test_openapi_swagger_ui_endpoint
7) CoreDiagnosticsApiTests.test_legacy_core_path_has_deprecation_headers
"""

from django.test import Client, SimpleTestCase


class CoreDiagnosticsApiTests(SimpleTestCase):
    def setUp(self) -> None:
        self.client = Client()

    def test_error_envelope_default(self):
        response = self.client.get("/api/core/diagnostics/error-envelope/")
        self.assertEqual(response.status_code, 500)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_GENERICO")
        self.assertEqual(body["ui_action"], "show_error_banner")
        self.assertIn("request_id", response.json()["meta"])
        self.assertTrue(response["X-Request-ID"])

    def test_error_envelope_retryable(self):
        response = self.client.get("/api/core/diagnostics/error-envelope/?kind=retryable")
        self.assertEqual(response.status_code, 409)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_DATABASE_RETRYABLE")
        self.assertTrue(body["retryable"])
        self.assertEqual(body["ui_action"], "show_retry_dialog")
        self.assertEqual(response["Retry-After"], "3")

    def test_error_envelope_not_found(self):
        response = self.client.get("/api/core/diagnostics/error-envelope/?kind=not_found")
        self.assertEqual(response.status_code, 404)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_PIPELINE_LOTTO_NOT_FOUND")
        self.assertIn("Lotto non trovato", body["detail"])

    def test_error_envelope_default_v1_path_requires_auth(self):
        response = self.client.get("/api/v1/core/diagnostics/error-envelope/")
        self.assertEqual(response.status_code, 401)

    def test_openapi_schema_endpoint(self):
        response = self.client.get("/api/schema/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/vnd.oai.openapi", response["Content-Type"])

    def test_openapi_swagger_ui_endpoint(self):
        response = self.client.get("/api/docs/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response["Content-Type"])

    def test_legacy_core_path_has_deprecation_headers(self):
        response = self.client.get("/api/core/diagnostics/error-envelope/")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response["Deprecation"], "true")
        self.assertIn("successor-version", response["Link"])
        self.assertTrue(response["Sunset"])
