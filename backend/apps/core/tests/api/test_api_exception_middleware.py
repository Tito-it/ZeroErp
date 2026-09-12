"""
Indice test eseguiti:
1) ApiExceptionMiddlewareTests.test_api_runtime_error_returns_error_envelope
2) ApiExceptionMiddlewareTests.test_api_service_error_uses_policy_status
3) ApiExceptionMiddlewareTests.test_api_http404_keeps_default_django_handling
4) ApiExceptionMiddlewareTests.test_non_api_runtime_error_is_not_intercepted
5) ApiExceptionMiddlewareTests.test_middleware_can_be_disabled_by_setting
6) ApiExceptionMiddlewareTests.test_api_value_error_returns_400
"""

from django.http import Http404
from django.test import Client, override_settings
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest
from django.urls import path

from apps.core.services.service_errors import ServiceError


# Scopo: Gestisce `_api_runtime_error_view` nel flusso applicativo del modulo.
def _api_runtime_error_view(request):
    raise RuntimeError("boom")


# Scopo: Gestisce `_api_service_error_view` nel flusso applicativo del modulo.
def _api_service_error_view(request):
    raise ServiceError(
        code="E_PIPELINE_LOTTO_NOT_FOUND",
        message="Lotto pipeline non trovato.",
        detail="Lotto non trovato: middleware test",
    )


# Scopo: Gestisce `_api_not_found_view` nel flusso applicativo del modulo.
def _api_not_found_view(request):
    raise Http404("not found")


# Scopo: Gestisce `_web_runtime_error_view` nel flusso applicativo del modulo.
def _web_runtime_error_view(request):
    raise RuntimeError("boom-web")


# Scopo: Simula un ValueError da query param malformato (es. page=abc).
def _api_value_error_view(request):
    raise ValueError("page_invalid")


urlpatterns = [
    path("api/test/runtime-error/", _api_runtime_error_view),
    path("api/test/service-error/", _api_service_error_view),
    path("api/test/not-found/", _api_not_found_view),
    path("api/test/value-error/", _api_value_error_view),
    path("web/test/runtime-error/", _web_runtime_error_view),
]


@override_settings(ROOT_URLCONF=__name__, REQUEST_LOG_ENABLED=False)
class ApiExceptionMiddlewareTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        self.client = Client(raise_request_exception=False)

    # Scopo: Verifica il caso `test_api_runtime_error_returns_error_envelope`.
    def test_api_runtime_error_returns_error_envelope(self):
        response = self.client.get("/api/test/runtime-error/")
        self.assertEqual(response.status_code, 500)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_GENERICO")
        self.assertEqual(body["ui_action"], "show_error_banner")
        self.assertTrue(response["X-Request-ID"])

    # Scopo: Verifica il caso `test_api_service_error_uses_policy_status`.
    def test_api_service_error_uses_policy_status(self):
        response = self.client.get("/api/test/service-error/")
        self.assertEqual(response.status_code, 404)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_PIPELINE_LOTTO_NOT_FOUND")
        self.assertEqual(body["ui_action"], "show_empty_state")

    # Scopo: Verifica il caso `test_api_http404_keeps_default_django_handling`.
    def test_api_http404_keeps_default_django_handling(self):
        response = self.client.get("/api/test/not-found/")
        self.assertEqual(response.status_code, 404)
        self.assertIn("text/html", response["Content-Type"])

    # Scopo: Verifica il caso `test_non_api_runtime_error_is_not_intercepted`.
    def test_non_api_runtime_error_is_not_intercepted(self):
        response = self.client.get("/web/test/runtime-error/")
        self.assertEqual(response.status_code, 500)
        self.assertIn("text/html", response["Content-Type"])

    # Scopo: Verifica che ValueError da input malformato restituisca 400 (non 500).
    def test_api_value_error_returns_400(self):
        response = self.client.get("/api/test/value-error/")
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_VALIDATION_INPUT")
        self.assertEqual(body["ui_action"], "highlight_form_fields")

    # Scopo: Verifica il caso `test_middleware_can_be_disabled_by_setting`.
    @override_settings(API_EXCEPTION_MIDDLEWARE_ENABLED=False)
    def test_middleware_can_be_disabled_by_setting(self):
        response = self.client.get("/api/test/runtime-error/")
        self.assertEqual(response.status_code, 500)
        self.assertIn("text/html", response["Content-Type"])
