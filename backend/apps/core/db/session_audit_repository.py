# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per audit sessioni — INSERT su dbops.sessioni_utente.
#        Traccia login, refresh, logout, scadenza, revoca token JWT.
# ------------------------------------------------------------

from __future__ import annotations

import json
from typing import Any

from django.db import connection


class SessionAuditRepository:
    """Accesso SQL alla tabella dbops.sessioni_utente (insert-only)."""

    # Scopo: Inserisce un evento di sessione nella tabella dbops.sessioni_utente.
    def log_session_event(
        self,
        *,
        auth_user_id: int,
        evento: str,
        jti: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        dettaglio: dict[str, Any] | None = None,
    ) -> None:
        sql = """
            INSERT INTO dbops.sessioni_utente
                (auth_user_id, evento, jti, ip_address, user_agent,
                 request_id, dettaglio)
            VALUES
                (%s, %s, %s, %s::inet, %s, %s::uuid, %s::jsonb)
        """
        params = [
            auth_user_id,
            evento,
            jti,
            ip_address,
            user_agent,
            request_id,
            json.dumps(dettaglio or {}),
        ]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
