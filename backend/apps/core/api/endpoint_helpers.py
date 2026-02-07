from collections.abc import Callable
import json
import logging
from typing import Any

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from rest_framework.request import Request

from apps.core.api.error_responses import (
    exception_to_error_response,
    invalid_json_response,
    invalid_payload_response,
)
from apps.core.api.request_parsers import parse_json_body
from apps.core.api.success_responses import success_response
from apps.core.services.idempotency_store import IdempotencyStore
from apps.core.services.request_context import get_request_id
from apps.core.services.service_errors import ServiceError
from apps.core.services.request_context import get_idempotency_key

# Helper condivisi per endpoint dominio: riducono boilerplate parsing/error handling.

logger = logging.getLogger(__name__)


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
        idempotency_key = get_idempotency_key()
        request_id = get_request_id()
        idempotency_claimed = False
        if require_idempotency_key and not idempotency_key:
            raise ServiceError(
                code="E_IDEMPOTENCY_KEY_REQUIRED",
                message="Idempotency-Key obbligatoria per questa operazione.",
                detail="Header Idempotency-Key mancante.",
            )

        strong_idempotency_enabled = (
            require_idempotency_key
            and bool(idempotency_key)
            and getattr(settings, "API_STRONG_IDEMPOTENCY_ENABLED", False)
        )
        if strong_idempotency_enabled:
            assert idempotency_key is not None
            decision = IdempotencyStore.claim_or_replay(
                idempotency_key=idempotency_key,
                request_id=request_id,
            )
            if decision.replay_payload is not None:
                logger.info(
                    "idempotency_replay key=%s request_id=%s",
                    idempotency_key,
                    request_id,
                )
                response = JsonResponse(decision.replay_payload, status=200)
                response["X-Idempotency-Replayed"] = "1"
                return response
            if decision.in_progress:
                logger.info(
                    "idempotency_in_progress key=%s request_id=%s",
                    idempotency_key,
                    request_id,
                )
                raise ServiceError(
                    code="E_IDEMPOTENCY_IN_PROGRESS",
                    message="Operazione gia` in elaborazione.",
                    detail="La stessa Idempotency-Key e` gia` in corso.",
                    retryable=True,
                )
            idempotency_claimed = True
            logger.info(
                "idempotency_first_execution key=%s request_id=%s",
                idempotency_key,
                request_id,
            )

        response_payload = handler(payload)
        response = success_response(response_payload)
        if strong_idempotency_enabled and idempotency_claimed:
            assert idempotency_key is not None
            IdempotencyStore.mark_completed(
                idempotency_key=idempotency_key,
                response_payload=_extract_json_payload(response),
                request_id=request_id,
            )
            logger.info(
                "idempotency_completed key=%s request_id=%s",
                idempotency_key,
                request_id,
            )
        return response
    except ValueError:
        if idempotency_claimed and idempotency_key and getattr(
            settings,
            "API_STRONG_IDEMPOTENCY_ENABLED",
            False,
        ):
            IdempotencyStore.mark_failed(idempotency_key=idempotency_key, request_id=request_id)
            logger.warning(
                "idempotency_failed_invalid_payload key=%s request_id=%s",
                idempotency_key,
                request_id,
            )
        return invalid_payload_response()
    except Exception as exc:
        if idempotency_claimed and idempotency_key and getattr(
            settings,
            "API_STRONG_IDEMPOTENCY_ENABLED",
            False,
        ):
            IdempotencyStore.mark_failed(idempotency_key=idempotency_key, request_id=request_id)
            logger.warning(
                "idempotency_failed_exception key=%s request_id=%s error=%s",
                idempotency_key,
                request_id,
                type(exc).__name__,
            )
        return exception_to_error_response(exc)


def _extract_json_payload(response: JsonResponse) -> dict[str, Any]:
    return json.loads(response.content.decode("utf-8"))
