from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from django.http import JsonResponse

from apps.core.services.request_context import get_idempotency_key, get_request_id

# Helper condivisi API: envelope successo uniforme con metadati request.


# Scopo: Gestisce `success_response` nel flusso applicativo del modulo.
# ⚠️ `data` puo' essere una LISTA: e' l'envelope delle liste nude dei lookup
#    (api.md §«L'ENVELOPE DI UN LOOKUP»). L'annotazione lo dichiara dal 2026-10-09.
#    E un `Mapping`, non solo un `dict`: un `TypedDict` (le righe tipate dei
#    repository) non e' un `dict[str, Any]` per il type checker.
#    E puo' essere `None` (`{"data": null}`): un dettaglio che non esiste ancora.
def success_response(data: Mapping[str, Any] | list[Any] | None, *, status: int = 200) -> JsonResponse:
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
