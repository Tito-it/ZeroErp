from __future__ import annotations

from uuid import uuid4

from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

from apps.core.api.payload_validators import optional_uuid
from apps.core.api.retry_policies import get_idempotency_key
from apps.core.services.request_context import clear_request_context, set_request_context

# Middleware contesto richiesta: assegna request_id e idempotency_key a livello globale.


# Scopo: L'`X-Request-ID` del client, se e' un UUID; None altrimenti.
# ⛔ E' un dato in ingresso non fidato che finisce in colonne `uuid`
#    (`dbops.request_log`, `dbops.sessioni_utente`): un valore qualunque ne
#    faceva fallire l'INSERT, e l'audit di login e revoche si perdeva col
#    solo log (S-1, 2026-09-27). Non valido = se ne genera uno nuovo, senza
#    rifiutare la richiesta: la correlazione e' un aiuto, non un requisito.
#    In forma canonica, anche nella risposta: niente valori lunghi rimandati.
def _request_id_dal_client(request: HttpRequest) -> str | None:
    try:
        return optional_uuid({"id": request.headers.get("X-Request-ID")}, "id")
    except ValueError:
        return None


class RequestContextMiddleware(MiddlewareMixin):
    # Scopo: Gestisce `process_request` nel flusso applicativo del modulo.
    def process_request(self, request: HttpRequest) -> None:
        request_id = _request_id_dal_client(request) or str(uuid4())
        idempotency_key = get_idempotency_key(request)
        # Attributi DINAMICI sulla request (HttpRequest non li dichiara).
        setattr(request, "request_id", request_id)  # noqa: B010 — attributo dinamico: assegnato col punto, mypy lo rifiuta (il tipo non lo dichiara)
        setattr(request, "idempotency_key", idempotency_key)  # noqa: B010 — attributo dinamico: assegnato col punto, mypy lo rifiuta (il tipo non lo dichiara)
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
