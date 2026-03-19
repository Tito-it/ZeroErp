# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block repository per auth_user (Django).
# Chiama anagrafiche.fn_crea_auth_user per creare un utente
# Django con guard unicita' username/email.
# Gestisce anche il blocco login per tentativi falliti
# (fn_check_blocco_login, fn_registra_tentativo_login).
# Riusabile da qualsiasi dominio che necessiti un utente Django.
# ------------------------------------------------------------

from __future__ import annotations

from django.db import connection


class AuthRepository:
    """Building block: operazioni atomiche su auth_user."""

    # Scopo: Crea un auth_user Django invocando fn_crea_auth_user.
    # Ritorna auth_user.id. Guard unicita' username/email nel DB.
    def crea_auth_user(
        self,
        *,
        username: str,
        email: str,
        password_hash: str,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> int:
        sql = """
            SELECT anagrafiche.fn_crea_auth_user(
                p_username      := %s,
                p_email         := %s,
                p_password_hash := %s,
                p_first_name    := %s,
                p_last_name     := %s
            )
        """
        params = [username, email, password_hash, first_name, last_name]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
            assert row is not None
            return row[0]

    # Scopo: Verifica se l'utente e' bloccato per tentativi falliti.
    # Lancia errore DB (E_UTENTE_BLOCCATO) se blocco attivo.
    # Se blocco scaduto, lo resetta automaticamente.
    def check_blocco_login(self, auth_user_id: int) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT script.fn_check_blocco_login(%s)",
                [auth_user_id],
            )

    # Scopo: Registra esito tentativo login (successo/fallimento).
    # Se fallimento supera soglia, imposta blocco temporaneo.
    # Ritorna { bloccato, minuti_rimanenti, tentativi }.
    def registra_tentativo_login(self, auth_user_id: int, *, successo: bool) -> dict:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT script.fn_registra_tentativo_login(%s, %s)",
                [auth_user_id, successo],
            )
            row = cursor.fetchone()
            if not row or not row[0]:
                return {"bloccato": False, "minuti_rimanenti": 0, "tentativi": 0}
            import json
            return json.loads(row[0]) if isinstance(row[0], str) else row[0]
