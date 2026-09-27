from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.http import JsonResponse
from rest_framework import exceptions as drf_exceptions
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
# - errori tecnici (E_DATABASE/E_PIPELINE/E_GENERICO) -> ERROR con stack trace
# - errori business (E_*_NOT_FOUND, E_*_VALIDAZIONE, ...) -> warning senza stack
# ⚠️ `logger.error(..., exc_info=exc)` e non `logger.exception(...)`: sono la
#    stessa riga di log, ma `.exception()` e' pensato per stare DENTRO un
#    `except`, dove l'eccezione la prende dal contesto. Qui arriva come
#    parametro, quindi il traceback lo passa `exc_info` — e la forma esplicita
#    dice a chi legge da dove viene (regola `LOG004`).
#
# ⭐ IL `request_id` NON SI SCRIVE PIU' QUI (consegna BE-8): lo mette il
#    formatter su OGNI riga, come `req=...`. Questo era l'unico punto del
#    progetto che se lo ricordava — cioe' la prova che scriverlo a mano copre
#    solo dove qualcuno ci ha pensato. Lasciarlo avrebbe stampato la stessa
#    informazione due volte sulla stessa riga.
def exception_to_error_response(exc: Exception) -> JsonResponse:
    api_error = ErrorTranslator.to_api_error(exc)
    status_code = ErrorTranslator.get_http_status(api_error)
    if ErrorTranslator.is_technical_code(api_error.code):
        logger.error(
            "api_exception[tech] code=%s http=%s message=%s",
            api_error.code,
            status_code,
            api_error.message,
            exc_info=exc,
        )
    else:
        logger.warning(
            "api_exception[biz] code=%s http=%s message=%s",
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
# ⛔ Per CLASSE (`isinstance`), non per nome: fino al 2026-09-27 la chiave era
#    `type(exc).__name__`, e una sottoclasse restava fuori. `InvalidToken` di
#    SimpleJWT (token scaduto o illeggibile) e' un `AuthenticationFailed`, ma
#    col suo nome usciva nel formato grezzo di DRF, fuori envelope (E-3).
_DRF_ERROR_CODE_MAP: tuple[tuple[type[Exception], str], ...] = (
    (drf_exceptions.NotAuthenticated, "E_NOT_AUTHENTICATED"),
    (drf_exceptions.AuthenticationFailed, "E_AUTHENTICATION_FAILED"),
    (drf_exceptions.PermissionDenied, "E_PERMISSION_DENIED"),
)


# Scopo: Il codice E_* di un'eccezione DRF standard, dalla sua classe o da
#        una delle classi madri. None = nessuna mappatura (resta il formato DRF).
def _codice_drf(exc: Exception) -> str | None:
    return next((code for cls, code in _DRF_ERROR_CODE_MAP if isinstance(exc, cls)), None)


def drf_exception_handler(exc: Exception, context: dict) -> Response | None:
    response = drf_default_handler(exc, context)
    if response is None:
        return None

    # Priorita' al default_code applicativo di una subclass (es.
    # VesteNonAttivaError.default_code = "E_VESTE_NON_ATTIVA"). Se assente,
    # fallback alla mappa classe -> code. Cosi' le subclass custom
    # preservano il proprio codice E_* nell'envelope senza dover essere
    # aggiunte a una mappa globale.
    # NB: questo ordine e' deliberato: aggiungere una subclass a
    # `_DRF_ERROR_CODE_MAP` NON la sovrascrive — default_code vince sempre
    # quando inizia per E_*. Per forzare un code diverso, cambiare default_code.
    exc_default_code = getattr(exc, "default_code", None)
    if isinstance(exc_default_code, str) and exc_default_code.startswith("E_"):
        code = exc_default_code
    else:
        code = _codice_drf(exc)

    if code:
        # Usa il user_message della policy: garantisce messaggi uniformi per lo
        # stesso codice in qualsiasi punto del backend.
        # ⚠️ Qui c'era un `if policy is not None` con un ramo di ripiego sul
        # `detail` dell'eccezione: `resolve` non ha mai restituito None — per un
        # codice non registrato ripiega, dal 2026-08-07 per una classe senza
        # status solleva — quindi quel ramo non e' mai stato eseguito.
        policy = ErrorPolicyRegistry.resolve(code)
        # ⚠️ `ui_action` va nell'envelope anche QUI. Fino al 2026-08-07 questo
        # percorso la calcolava e la buttava via, mentre l'altro
        # (`exception_to_error_response` -> `ApiError.to_dict`) la spediva: lo
        # stesso codice usciva con due forme diverse a seconda di CHI aveva
        # sollevato. Oggi non se ne accorge nessuno perche' il frontend non la
        # legge ancora; il giorno in cui la leggera', un contratto che vale su
        # un percorso e non sull'altro si manifesta come «a volte funziona»,
        # che e' il modo peggiore in cui puo' presentarsi.
        payload: dict = {
            "error": {"code": code, "message": policy.user_message, "ui_action": policy.ui_action}
        }
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
