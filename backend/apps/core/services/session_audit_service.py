# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service per audit sessioni JWT — registra eventi di login,
#        refresh, logout e revoca nella tabella dbops.sessioni_utente.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any

from django.http import HttpRequest

from apps.core.db.session_audit_repository import SessionAuditRepository
from apps.core.services.request_context import get_client_ip, get_request_id, get_user_agent

logger = logging.getLogger(__name__)


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


# Scopo: Registra un evento LOGOUT nella tabella sessioni_utente.
# Chiamato dall'endpoint di logout dopo blacklist del token.
def record_logout(
    user_id: int,
    request: HttpRequest,
    *,
    jti: str | None = None,
    dettaglio: dict[str, Any] | None = None,
) -> None:
    _log_event(
        auth_user_id=user_id,
        evento="LOGOUT",
        request=request,
        jti=jti,
        dettaglio=dettaglio,
    )


# Scopo: Registra un evento REVOCA nella tabella sessioni_utente.
# Chiamato quando l'utente revoca una sessione remota.
def record_revoca(
    user_id: int,
    request: HttpRequest,
    *,
    jti: str | None = None,
    dettaglio: dict[str, Any] | None = None,
) -> None:
    _log_event(
        auth_user_id=user_id,
        evento="REVOCA",
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
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            request_id=get_request_id(),
            dettaglio=dettaglio,
        )
    except Exception:
        logger.exception(
            "session_audit.log_event_failed evento=%s user_id=%s",
            evento,
            auth_user_id,
        )
