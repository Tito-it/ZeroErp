from __future__ import annotations

from uuid import uuid4

from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

from apps.core.api.retry_policies import get_idempotency_key
from apps.core.services.request_context import clear_request_context, set_request_context

# Middleware contesto richiesta: assegna request_id e idempotency_key a livello globale.


class RequestContextMiddleware(MiddlewareMixin):
    # Scopo: Gestisce `process_request` nel flusso applicativo del modulo.
    def process_request(self, request: HttpRequest) -> None:
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        idempotency_key = get_idempotency_key(request)
        request.request_id = request_id
        request.idempotency_key = idempotency_key
        set_request_context(request_id=request_id, idempotency_key=idempotency_key)

    # Scopo: Gestisce `process_response` nel flusso applicativo del modulo.
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        request_id = getattr(request, "request_id", None)
        if request_id:
            response["X-Request-ID"] = request_id
        idempotency_key = getattr(request, "idempotency_key", None)
        if idempotency_key:
            response["X-Idempotency-Key"] = idempotency_key
        clear_request_context()
        return response

    # Scopo: Gestisce `process_exception` nel flusso applicativo del modulo.
    def process_exception(self, request: HttpRequest, exception: Exception) -> None:
        clear_request_context()
        return None
