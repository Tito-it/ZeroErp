from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest, JsonResponse

from apps.core.services.error_translator import ApiError

# Policy centralizzate retry/idempotenza per endpoint API.


def get_idempotency_key(request: HttpRequest) -> str | None:
    key = request.headers.get("Idempotency-Key") or request.headers.get("X-Idempotency-Key")
    if key is None:
        return None
    normalized = key.strip()
    if not normalized:
        return None
    if len(normalized) > 128:
        return None
    return normalized


def apply_retry_headers(response: JsonResponse, api_error: ApiError) -> JsonResponse:
    if not api_error.retryable:
        return response
    retry_after = getattr(settings, "API_RETRY_AFTER_SECONDS", 3)
    response["Retry-After"] = str(retry_after)
    return response
