from django.http import JsonResponse

from apps.core.api.retry_policies import apply_retry_headers
from apps.core.services.request_context import get_idempotency_key, get_request_id
from apps.core.services.error_translator import ErrorTranslator

# Helper condivisi API: envelope errori uniforme per tutti i domini.


def invalid_json_response() -> JsonResponse:
    payload = {"error": "invalid_json"}
    meta = _build_meta()
    if meta:
        payload["meta"] = meta
    return JsonResponse(payload, status=400)


def invalid_payload_response() -> JsonResponse:
    payload = {"error": "invalid_payload"}
    meta = _build_meta()
    if meta:
        payload["meta"] = meta
    return JsonResponse(payload, status=400)


def exception_to_error_response(exc: Exception) -> JsonResponse:
    api_error = ErrorTranslator.to_api_error(exc)
    status_code = ErrorTranslator.get_http_status(api_error)
    payload = {"error": api_error.to_dict()}
    meta = _build_meta()
    if meta:
        payload["meta"] = meta
    response = JsonResponse(payload, status=status_code)
    return apply_retry_headers(response, api_error)


def _build_meta() -> dict[str, str]:
    meta: dict[str, str] = {}
    request_id = get_request_id()
    if request_id:
        meta["request_id"] = request_id
    idempotency_key = get_idempotency_key()
    if idempotency_key:
        meta["idempotency_key"] = idempotency_key
    return meta
