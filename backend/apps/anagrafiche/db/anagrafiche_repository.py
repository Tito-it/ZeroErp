# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per accesso DB funzioni schema anagrafiche.
# Note: Segue pattern DB-first — delega logica a funzioni PostgreSQL.
# ------------------------------------------------------------

from __future__ import annotations

from django.db import connection


class AnagraficheRepository:
    """Accesso DB per lo schema anagrafiche."""

    # Scopo: Recupera gli auth_user_id delle risorse con finestra temporale
    # scaduta e auth_user ancora attivo. Stessa logica WHERE di
    # anagrafiche.fn_sync_auth_user_expired(), usata per conoscere
    # gli utenti coinvolti *prima* della sync (per invalidazione cache).
    def list_expired_auth_user_ids(self) -> list[int]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT rau.auth_user_id
                  FROM anagrafiche.risorse_umane ru
                  JOIN anagrafiche.risorse_umane_auth_user rau
                    ON rau.risorsa_umana_id = ru.id
                  JOIN django.auth_user au
                    ON au.id = rau.auth_user_id
                 WHERE ru.valido_al IS NOT NULL
                   AND ru.valido_al < CURRENT_DATE
                   AND au.is_active = true
                """
            )
            return [row[0] for row in cursor.fetchall()]

    # Scopo: Chiama la funzione batch anagrafiche.fn_sync_auth_user_expired()
    # che disattiva auth_user per risorse umane con finestra scaduta.
    # Ritorna il numero di utenti effettivamente disattivati.
    def call_sync_auth_user_expired(self) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT anagrafiche.fn_sync_auth_user_expired()"
            )
            row = cursor.fetchone()
            assert row is not None
        return int(row[0])
