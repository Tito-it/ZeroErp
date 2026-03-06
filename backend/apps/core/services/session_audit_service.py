# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service per audit sessioni JWT — registra eventi di login,
#        refresh e logout nella tabella dbops.sessioni_utente.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any

from django.http import HttpRequest

from apps.core.db.session_audit_repository import SessionAuditRepository
from apps.core.services.request_context import get_request_id

logger = logging.getLogger(__name__)


# Scopo: Estrae l'IP del client dalla request, gestendo proxy (X-Forwarded-For).
def _get_client_ip(request: HttpRequest) -> str | None:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


# Scopo: Estrae lo User-Agent dalla request.
def _get_user_agent(request: HttpRequest) -> str | None:
    ua = request.META.get("HTTP_USER_AGENT")
    # Tronca a 500 caratteri per evitare inserimenti anomali.
    return ua[:500] if ua else None


# Scopo: Registra un evento LOGIN nella tabella sessioni_utente.
# Chiamato dopo emissione token con successo.
def record_login(
    user_id: int,
    request: HttpRequest,
    *,
    jti: str | None = None,
    dettaglio: dict[str, Any] | None = None,
) -> None:
    _log_event(
        auth_user_id=user_id,
        evento="LOGIN",
        request=request,
        jti=jti,
        dettaglio=dettaglio,
    )


# Scopo: Registra un evento REFRESH nella tabella sessioni_utente.
# Chiamato dopo refresh token con successo.
def record_refresh(
    user_id: int,
    request: HttpRequest,
    *,
    jti: str | None = None,
    dettaglio: dict[str, Any] | None = None,
) -> None:
    _log_event(
        auth_user_id=user_id,
        evento="REFRESH",
        request=request,
        jti=jti,
        dettaglio=dettaglio,
    )


# Scopo: Registra un evento generico nella tabella sessioni_utente.
# Gestisce errori silenziosamente per non interrompere il flusso principale.
def _log_event(
    *,
    auth_user_id: int,
    evento: str,
    request: HttpRequest,
    jti: str | None = None,
    dettaglio: dict[str, Any] | None = None,
) -> None:
    try:
        repo = SessionAuditRepository()
        repo.log_session_event(
            auth_user_id=auth_user_id,
            evento=evento,
            jti=jti,
            ip_address=_get_client_ip(request),
            user_agent=_get_user_agent(request),
            request_id=get_request_id(),
            dettaglio=dettaglio,
        )
    except Exception:
        logger.exception(
            "session_audit.log_event_failed evento=%s user_id=%s",
            evento,
            auth_user_id,
        )
