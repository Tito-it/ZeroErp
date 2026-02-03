from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET

from apps.core.api.error_responses import exception_to_error_response
from apps.core.services.service_errors import ServiceError

# Endpoint diagnostici core: utili per verificare contratto error envelope API.


@require_GET
def diagnostics_error_envelope(request: HttpRequest) -> JsonResponse:
    kind = request.GET.get("kind", "generic")

    if kind == "retryable":
        exc = ServiceError(
            code="E_DATABASE_RETRYABLE",
            message="Conflitto transazionale, riprovare.",
            retryable=True,
        )
    elif kind == "not_found":
        exc = ServiceError(
            code="E_PIPELINE_LOTTO_NOT_FOUND",
            message="Lotto pipeline non trovato.",
            detail="Lotto non trovato (diagnostica core).",
        )
    else:
        exc = ServiceError(
            code="E_GENERICO",
            message="Errore diagnostico core.",
            detail="Endpoint diagnostico error-envelope.",
        )

    return exception_to_error_response(exc)
