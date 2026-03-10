# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per audit sessioni — INSERT e query su dbops.sessioni_utente.
#        Traccia login, refresh, logout, scadenza, revoca token JWT.
#        Espone query sessioni attive per l'utente (CTE con stato derivato).
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

    # Scopo: Recupera le sessioni attive per un utente.
    # Una sessione e' attiva se l'ultimo evento per quel jti e' LOGIN o REFRESH
    # e il timestamp e' entro il TTL del refresh token (1 giorno).
    def list_sessioni_attive(self, auth_user_id: int) -> list[dict[str, Any]]:
        sql = """
            WITH ranked AS (
                SELECT jti, evento, ip_address, user_agent, data_insert,
                       ROW_NUMBER() OVER (PARTITION BY jti ORDER BY data_insert DESC) AS rn
                  FROM dbops.sessioni_utente
                 WHERE auth_user_id = %s
                   AND jti IS NOT NULL
                   AND jti != ''
            ),
            primo_login AS (
                SELECT jti, MIN(data_insert) AS data_inizio
                  FROM dbops.sessioni_utente
                 WHERE auth_user_id = %s
                   AND jti IS NOT NULL
                   AND jti != ''
                   AND evento = 'LOGIN'
              GROUP BY jti
            )
            SELECT r.jti,
                   r.evento       AS ultimo_evento,
                   r.ip_address::text,
                   r.user_agent,
                   pl.data_inizio,
                   r.data_insert  AS data_ultimo_evento
              FROM ranked r
              LEFT JOIN primo_login pl ON pl.jti = r.jti
             WHERE r.rn = 1
               AND r.evento IN ('LOGIN', 'REFRESH')
               AND r.data_insert > now() - INTERVAL '1 day'
          ORDER BY r.data_insert DESC
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [auth_user_id, auth_user_id])
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
