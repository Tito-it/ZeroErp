from collections.abc import Callable
from typing import Any

from django.http import HttpRequest, JsonResponse
from rest_framework.request import Request

from apps.core.api.error_responses import (
    exception_to_error_response,
    invalid_json_response,
    invalid_payload_response,
)
from apps.core.api.request_parsers import parse_json_body
from apps.core.api.success_responses import success_response
from apps.core.services.service_errors import ServiceError
from apps.core.services.request_context import get_idempotency_key

# Helper condivisi per endpoint dominio: riducono boilerplate parsing/error handling.


def handle_post_json(
    request: HttpRequest | Request,
    *,
    handler: Callable[[dict[str, Any]], dict[str, Any]],
    require_idempotency_key: bool = False,
) -> JsonResponse:
    try:
        payload = parse_json_body(request)
    except ValueError:
        return invalid_json_response()

    try:
        if require_idempotency_key and not get_idempotency_key():
            raise ServiceError(
                code="E_IDEMPOTENCY_KEY_REQUIRED",
                message="Idempotency-Key obbligatoria per questa operazione.",
                detail="Header Idempotency-Key mancante.",
            )
        response_payload = handler(payload)
        return success_response(response_payload)
    except ValueError:
        return invalid_payload_response()
    except Exception as exc:
        return exception_to_error_response(exc)
