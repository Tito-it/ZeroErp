# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per config.token_monouso — token monouso generico
#        riutilizzabile per inviti, reset password, conferme.
#        Il token in chiaro NON viene mai salvato: solo hash SHA-256.
# ------------------------------------------------------------

from __future__ import annotations

import json
from typing import Any

from django.db import connection, transaction

from apps.core.db._helpers import row_to_dict


class TokenRepository:
    """Accesso DB per config.token_monouso."""

    # Scopo: Inserisce un token monouso (hash SHA-256). Invalida token precedenti
    #        dello stesso tipo per lo stesso utente.
    def create(
        self,
        *,
        token_hash: str,
        tipo: str,
        auth_user_id: int,
        scadenza_iso: str,
        meta: dict[str, Any] | None = None,
    ) -> int:
        with transaction.atomic(), connection.cursor() as cursor:
            # Invalida token precedenti dello stesso tipo/utente (atomico)
            self.invalidate_all(tipo, auth_user_id)
            # Inserisci nuovo token
            cursor.execute(
                """INSERT INTO config.token_monouso
                       (token_hash, tipo, auth_user_id, scadenza, meta)
                   VALUES (%s, %s, %s, %s::timestamptz, %s::jsonb)
                   RETURNING id""",
                [token_hash, tipo, auth_user_id, scadenza_iso, json.dumps(meta or {})],
            )
            row = cursor.fetchone()
            assert row is not None
            return row[0]

    # Scopo: Cerca un token valido (non utilizzato, non scaduto) per hash e tipo.
    #        Ritorna il record o None.
    def find_valid(self, token_hash: str, tipo: str) -> dict[str, Any] | None:
        sql = """
            SELECT id, token_hash, tipo, auth_user_id, scadenza,
                   utilizzato, meta, data_insert
              FROM config.token_monouso
             WHERE token_hash = %s
               AND tipo = %s
               AND utilizzato = false
               AND scadenza > now()
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [token_hash, tipo])
            return row_to_dict(cursor)

    # Scopo: Segna un token come utilizzato (consumato). Salva IP e timestamp.
    def consume(self, token_id: int, ip: str | None = None) -> bool:
        sql = """
            UPDATE config.token_monouso
               SET utilizzato = true,
                   utilizzato_at = now(),
                   ip_utilizzo = %s::inet
             WHERE id = %s AND utilizzato = false
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [ip, token_id])
            return cursor.rowcount > 0

    # Scopo: Invalida tutti i token di un tipo per un utente (senza consumarli).
    def invalidate_all(self, tipo: str, auth_user_id: int) -> int:
        sql = """
            UPDATE config.token_monouso
               SET utilizzato = true, utilizzato_at = now()
             WHERE tipo = %s AND auth_user_id = %s AND utilizzato = false
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [tipo, auth_user_id])
            return cursor.rowcount
