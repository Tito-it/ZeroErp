from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import Http404, HttpRequest, HttpResponse
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

from apps.core.api.error_responses import exception_to_error_response

# Middleware globale: converte eccezioni non gestite in envelope JSON uniforme
# solo per endpoint API, senza alterare il comportamento Django su pagine non API.


class ApiExceptionMiddleware(MiddlewareMixin):
    # Scopo: Gestisce `process_exception` nel flusso applicativo del modulo.
    def process_exception(self, request: HttpRequest, exc: Exception) -> HttpResponse | None:
        if not getattr(settings, "API_EXCEPTION_MIDDLEWARE_ENABLED", True):
            return None
        if not self._should_handle(request, exc):
            return None
        return exception_to_error_response(exc)

    # Scopo: Gestisce `_should_handle` nel flusso applicativo del modulo.
    @staticmethod
    def _should_handle(request: HttpRequest, exc: Exception) -> bool:
        if not request.path.startswith("/api/"):
            return False
        # Mantiene il comportamento standard Django per 404/403/sicurezza.
        if isinstance(exc, (Http404, PermissionDenied, SuspiciousOperation)):
            return False
        return True
