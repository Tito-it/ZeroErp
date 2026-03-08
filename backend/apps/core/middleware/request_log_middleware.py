# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Middleware per request logging — registra ogni request API
#        autenticata nella tabella dbops.request_log con metodo, path,
#        status, durata e utente.
# ------------------------------------------------------------

from __future__ import annotations

import logging
import time

from django.conf import settings
from django.db import connection
from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

from apps.core.services.request_context import (
    get_client_ip,
    get_idempotency_key,
    get_request_id,
    get_user_agent,
)

logger = logging.getLogger(__name__)

# Path esclusi dal logging (configurabili via settings).
_DEFAULT_EXCLUDE_PATHS = ("/health", "/api/docs/", "/api/schema/", "/static/", "/media/")


class RequestLogMiddleware(MiddlewareMixin):
    """Registra ogni request /api/* nella tabella dbops.request_log.

    Non logga body request/response (sicurezza + volume).
    Logga solo header-level: method, path, status, durata, user.
    """

    # Scopo: Salva il timestamp di inizio request.
    def process_request(self, request: HttpRequest) -> None:
        if not self._should_log(request):
            return
        request._request_log_start = time.monotonic()  # type: ignore[attr-defined]

    # Scopo: Calcola durata e inserisce il record in dbops.request_log.
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        start = getattr(request, "_request_log_start", None)
        if start is None:
            return response

        duration_ms = int((time.monotonic() - start) * 1000)
        self._insert_log(request, response, duration_ms)
        return response

    # Scopo: Determina se la request deve essere loggata.
    @staticmethod
    def _should_log(request: HttpRequest) -> bool:
        if not getattr(settings, "REQUEST_LOG_ENABLED", True):
            return False
        path = request.path
        if not path.startswith("/api/"):
            return False
        exclude = getattr(settings, "REQUEST_LOG_EXCLUDE_PATHS", _DEFAULT_EXCLUDE_PATHS)
        return not any(path.startswith(p) for p in exclude)

    # Scopo: Esegue INSERT nella tabella dbops.request_log.
    # Gestisce errori silenziosamente per non interrompere la response.
    @staticmethod
    def _insert_log(
        request: HttpRequest,
        response: HttpResponse,
        duration_ms: int,
    ) -> None:
        try:
            user = getattr(request, "user", None)
            auth_user_id = None
            username = None
            if user and getattr(user, "is_authenticated", False):
                auth_user_id = user.id
                username = str(user)

            request_id = get_request_id()
            ip_address = get_client_ip(request)
            user_agent = get_user_agent(request)
            idempotency_key = get_idempotency_key()

            # Estrae error_code dalla response JSON se presente
            error_code = None
            if response.status_code >= 400:
                error_code = _extract_error_code(response)

            sql = """
                INSERT INTO dbops.request_log
                    (auth_user_id, username, request_id, method, path,
                     query_string, status_code, duration_ms, ip_address,
                     user_agent, error_code, idempotency_key)
                VALUES
                    (%s, %s, %s::uuid, %s, %s,
                     %s, %s, %s, %s::inet,
                     %s, %s, %s)
            """
            params = [
                auth_user_id,
                username,
                request_id,
                request.method,
                request.path[:500],
                (request.META.get("QUERY_STRING", "") or "")[:1000] or None,
                response.status_code,
                duration_ms,
                ip_address,
                user_agent,
                error_code,
                idempotency_key,
            ]
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
        except Exception:
            logger.exception("request_log.insert_failed path=%s", request.path)


# Scopo: Estrae il codice errore dalla response JSON se presente.
def _extract_error_code(response: HttpResponse) -> str | None:
    try:
        import json
        body = json.loads(response.content)
        error = body.get("error", {})
        if isinstance(error, dict):
            return error.get("code")
    except Exception:
        pass
    return None
