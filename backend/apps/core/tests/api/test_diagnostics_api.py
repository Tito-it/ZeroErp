"""
Indice test eseguiti:
1) CoreDiagnosticsApiTests.test_error_envelope_default
2) CoreDiagnosticsApiTests.test_error_envelope_retryable
3) CoreDiagnosticsApiTests.test_error_envelope_not_found
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

    def test_error_envelope_retryable(self):
        response = self.client.get("/api/core/diagnostics/error-envelope/?kind=retryable")
        self.assertEqual(response.status_code, 409)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_DATABASE_RETRYABLE")
        self.assertTrue(body["retryable"])
        self.assertEqual(body["ui_action"], "show_retry_dialog")

    def test_error_envelope_not_found(self):
        response = self.client.get("/api/core/diagnostics/error-envelope/?kind=not_found")
        self.assertEqual(response.status_code, 404)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_PIPELINE_LOTTO_NOT_FOUND")
        self.assertIn("Lotto non trovato", body["detail"])
