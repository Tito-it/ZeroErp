from collections.abc import Callable
from typing import Any

from django.http import HttpRequest, JsonResponse

from apps.core.api.error_responses import (
    exception_to_error_response,
    invalid_json_response,
    invalid_payload_response,
)
from apps.core.api.request_parsers import parse_json_body

# Helper condivisi per endpoint dominio: riducono boilerplate parsing/error handling.


def handle_post_json(
    request: HttpRequest,
    *,
    handler: Callable[[dict[str, Any]], dict[str, Any]],
) -> JsonResponse:
    try:
        payload = parse_json_body(request)
    except ValueError:
        return invalid_json_response()

    try:
        response_payload = handler(payload)
        return JsonResponse(response_payload)
    except ValueError:
        return invalid_payload_response()
    except Exception as exc:
        return exception_to_error_response(exc)
