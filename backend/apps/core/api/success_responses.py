from __future__ import annotations

from typing import Any

from django.http import JsonResponse

from apps.core.services.request_context import get_idempotency_key, get_request_id

# Helper condivisi API: envelope successo uniforme con metadati request.


# Scopo: Gestisce `success_response` nel flusso applicativo del modulo.
def success_response(data: dict[str, Any], *, status: int = 200) -> JsonResponse:
    meta: dict[str, Any] = {}
    request_id = get_request_id()
    if request_id:
        meta["request_id"] = request_id
    idempotency_key = get_idempotency_key()
    if idempotency_key:
        meta["idempotency_key"] = idempotency_key

    payload: dict[str, Any] = {"data": data}
    if meta:
        payload["meta"] = meta
    return JsonResponse(payload, status=status)
