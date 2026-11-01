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

from apps.core.services.percorsi_tecnici import e_percorso_tecnico
from apps.core.services.request_context import (
    get_client_ip,
    get_idempotency_key,
    get_request_id,
    get_user_agent,
)

logger = logging.getLogger(__name__)

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
        # I percorsi tecnici dal BB `core/services/percorsi_tecnici`. Fino al
        # 2026-11-01 erano una tupla di questo modulo, sovrascrivibile da un
        # `REQUEST_LOG_EXCLUDE_PATHS` che nessun settings impostava.
        return not e_percorso_tecnico(path)

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

            # ⭐ `emittente_attivo_id` SI COLLEGA, e non si passa dal Python
            #    (consegna BE-8). Era una delle due colonne MORTE di questa
            #    tabella: 0 righe valorizzate su 354.595. Il valore c'e' gia'
            #    nella sessione — la GUC `app.current_emittente_id`, che
            #    `jwt_audit_authentication` scrive a ogni richiesta autenticata
            #    ed e' la STESSA che le policy RLS leggono per decidere cosa
            #    l'utente vede.
            #
            # ⚠️ Si legge di la' e non dal JWT apposta: l'autenticazione ha gia'
            #    verificato che quell'emittente esista e sia attivo prima di
            #    metterlo nella GUC. Ripartire dal token vorrebbe dire rifare la
            #    verifica — o, peggio, non rifarla e scrivere nel log un
            #    emittente che il resto della richiesta non ha usato.
            #
            # ⭐ E la GUC e' ancora leggibile QUI, che e' la ragione per cui
            #    questo funziona: `set_config(..., false)` la mette a livello di
            #    SESSIONE, non di transazione, e questa INSERT avviene dopo la
            #    risposta ma sulla stessa connessione. Con `true` sarebbe gia'
            #    sparita.
            #
            # ⛔ `tx_id` NON C'E' PIU', ed e' il finale della stessa storia:
            #    era l'altra colonna morta di questa tabella, e non si poteva
            #    collegare da qui — la riga si scrive quando la transazione di
            #    lavoro ha gia' chiuso, quindi il suo `tx_id` non esiste piu' e
            #    un valore coniato adesso avrebbe legato la riga a se stessa.
            #    Richiesta al team DB e **tolta il 2026-08-24** (0 valorizzate
            #    su 355.702). ⚠️ Se un giorno servisse davvero, non si riapre
            #    qui: la riga andrebbe scritta DENTRO la transazione di lavoro,
            #    cioe' da un'altra parte e con un altro disegno.
            sql = """
                INSERT INTO dbops.request_log
                    (auth_user_id, username, request_id, method, path,
                     query_string, status_code, duration_ms, ip_address,
                     user_agent, error_code, idempotency_key,
                     emittente_attivo_id)
                VALUES
                    (%s, %s, %s::uuid, %s, %s,
                     %s, %s, %s, %s::inet,
                     %s, %s, %s,
                     NULLIF(current_setting('app.current_emittente_id', true), '')::bigint)
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
    # Corpo non JSON (ValueError, anche per UnicodeDecodeError), JSON che non
    # e' un oggetto o response in streaming senza `.content` (AttributeError):
    # la risposta non porta un codice errore, e non e' un guasto.
    except (ValueError, AttributeError):
        pass
    return None
