# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block repository per soggetti (anagrafiche).
# Chiama anagrafiche.fn_crea_soggetto_pf per creare un soggetto
# Persona Fisica con contatto default.
# Riusabile da qualsiasi dominio che crei soggetti PF
# (operatori, clienti, fornitori).
# ------------------------------------------------------------

from __future__ import annotations

from django.db import connection


class AnagraficheCoreRepository:
    """Building block: operazioni atomiche su soggetti."""

    # Scopo: Crea un soggetto Persona Fisica invocando fn_crea_soggetto_pf.
    # Crea anche il contatto default (guard DEFERRED).
    # Ritorna soggetti.id (UUID come stringa).
    def crea_soggetto_pf(
        self,
        *,
        cognome: str,
        nome: str,
        codice_fiscale: str,
        email: str,
        data_nascita: str | None = None,
        sesso: str = "M",
        stato_iso2: str = "IT",
    ) -> str:
        sql = """
            SELECT anagrafiche.fn_crea_soggetto_pf(
                p_cognome        := %s,
                p_nome           := %s,
                p_codice_fiscale := %s,
                p_email          := %s,
                p_data_nascita   := %s::date,
                p_sesso          := %s,
                p_stato_iso2     := %s
            )
        """
        params = [
            cognome, nome, codice_fiscale, email,
            data_nascita, sesso, stato_iso2,
        ]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
            assert row is not None
            return str(row[0])
