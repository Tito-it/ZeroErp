# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block repository per risorse umane.
# Chiama anagrafiche.fn_crea_risorsa_umana per creare una
# risorsa umana con bridge auth_user opzionale.
# Riusabile da qualsiasi dominio che crei risorse umane
# (operatori, admin, dipendenti senza accesso).
# ------------------------------------------------------------

from __future__ import annotations

from django.db import connection


class RisorseUmaneCoreRepository:
    """Building block: operazioni atomiche su risorse umane."""

    # Scopo: Crea una risorsa umana invocando fn_crea_risorsa_umana.
    # Se auth_user_id fornito, crea anche il bridge risorse_umane_auth_user.
    # Ritorna risorse_umane.id.
    def crea_risorsa_umana(
        self,
        *,
        soggetto_id: str,
        qualifica_id: int,
        unita_organizzativa_id: int | None = None,
        valido_dal: str | None = None,
        valido_al: str | None = None,
        auth_user_id: int | None = None,
        ruolo_sistema: str = "OPERATIVO",
    ) -> int:
        sql = """
            SELECT anagrafiche.fn_crea_risorsa_umana(
                p_soggetto_id            := %s::uuid,
                p_qualifica_id           := %s,
                p_unita_organizzativa_id := %s,
                p_valido_dal             := %s::date,
                p_valido_al              := %s::date,
                p_auth_user_id           := %s,
                p_ruolo_sistema          := %s::config.ruolo_sistema
            )
        """
        params = [
            soggetto_id, qualifica_id, unita_organizzativa_id,
            valido_dal, valido_al, auth_user_id, ruolo_sistema,
        ]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
            assert row is not None
            return row[0]
