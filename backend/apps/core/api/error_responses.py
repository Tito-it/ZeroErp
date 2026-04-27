from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.http import JsonResponse
from rest_framework.views import exception_handler as drf_default_handler

from apps.core.api.retry_policies import apply_retry_headers
from apps.core.services.error_policies import ErrorPolicyRegistry
from apps.core.services.error_translator import ErrorTranslator
from apps.core.services.request_context import get_idempotency_key, get_request_id

logger = logging.getLogger("api.exception")

if TYPE_CHECKING:
    from rest_framework.response import Response

# Helper condivisi API: envelope errori uniforme per tutti i domini.


# Scopo: Gestisce `invalid_json_response` nel flusso applicativo del modulo.
def invalid_json_response() -> JsonResponse:
    payload = {"error": "invalid_json"}
    meta = _build_meta()
    if meta:
        payload["meta"] = meta
    return JsonResponse(payload, status=400)


# Scopo: Gestisce `invalid_payload_response` nel flusso applicativo del modulo.
def invalid_payload_response() -> JsonResponse:
    payload = {"error": "invalid_payload"}
    meta = _build_meta()
    if meta:
        payload["meta"] = meta
    return JsonResponse(payload, status=400)


# Scopo: Gestisce `exception_to_error_response` nel flusso applicativo del modulo.
# Prima di mascherare i dettagli tecnici per il client, registra l'eccezione
# sul logger "api.exception" cosi' il dev puo' risalire dal request_id mostrato
# all'utente al problema reale. Differenzia due livelli per non inquinare il log:
# - errori tecnici (E_DATABASE/E_PIPELINE/E_GENERICO) -> exception con stack trace
# - errori business (E_*_NOT_FOUND, E_*_VALIDAZIONE, ...) -> warning senza stack
def exception_to_error_response(exc: Exception) -> JsonResponse:
    api_error = ErrorTranslator.to_api_error(exc)
    status_code = ErrorTranslator.get_http_status(api_error)
    request_id = get_request_id() or "-"
    if ErrorTranslator.is_technical_code(api_error.code):
        logger.exception(
            "api_exception[tech] request_id=%s code=%s http=%s message=%s",
            request_id,
            api_error.code,
            status_code,
            api_error.message,
            exc_info=exc,
        )
    else:
        logger.warning(
            "api_exception[biz] request_id=%s code=%s http=%s message=%s",
            request_id,
            api_error.code,
            status_code,
            api_error.message,
        )
    payload = {"error": api_error.to_dict()}
    meta = _build_meta()
    if meta:
        payload["meta"] = meta
    response = JsonResponse(payload, status=status_code)
    return apply_retry_headers(response, api_error)


# Scopo: Custom DRF exception handler — converte eccezioni auth/permessi
# nell'envelope standard del progetto {"error": {"code": ..., "message": ...}}.
_DRF_ERROR_CODE_MAP: dict[str, str] = {
    "NotAuthenticated": "E_NOT_AUTHENTICATED",
    "AuthenticationFailed": "E_AUTHENTICATION_FAILED",
    "PermissionDenied": "E_PERMISSION_DENIED",
}


def drf_exception_handler(exc: Exception, context: dict) -> Response | None:
    response = drf_default_handler(exc, context)
    if response is None:
        return None

    # Priorita' al default_code applicativo di una subclass (es.
    # VesteNonAttivaError.default_code = "E_VESTE_NON_ATTIVA"). Se assente,
    # fallback alla mappa type-name -> code. Cosi' le subclass custom
    # preservano il proprio codice E_* nell'envelope senza dover essere
    # aggiunte a una mappa globale.
    # NB: questo ordine e' deliberato: aggiungere una subclass a
    # `_DRF_ERROR_CODE_MAP` NON la sovrascrive — default_code vince sempre
    # quando inizia per E_*. Per forzare un code diverso, cambiare default_code.
    exc_default_code = getattr(exc, "default_code", None)
    if isinstance(exc_default_code, str) and exc_default_code.startswith("E_"):
        code = exc_default_code
    else:
        code = _DRF_ERROR_CODE_MAP.get(type(exc).__name__)

    if code:
        # Usa il user_message della policy registrata quando disponibile:
        # garantisce messaggi uniformi per lo stesso codice in qualsiasi
        # punto del backend. Fallback al detail dell'eccezione altrimenti.
        policy = ErrorPolicyRegistry.resolve(code)
        if policy is not None:
            message = policy.user_message
        else:
            detail = getattr(exc, "detail", str(exc))
            message = str(detail) if not isinstance(detail, str) else detail
        payload: dict = {"error": {"code": code, "message": message}}
        meta = _build_meta()
        if meta:
            payload["meta"] = meta
        response.data = payload
    return response


# Scopo: Gestisce `_build_meta` nel flusso applicativo del modulo.
def _build_meta() -> dict[str, str]:
    meta: dict[str, str] = {}
    request_id = get_request_id()
    if request_id:
        meta["request_id"] = request_id
    idempotency_key = get_idempotency_key()
    if idempotency_key:
        meta["idempotency_key"] = idempotency_key
    return meta
