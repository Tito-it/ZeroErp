# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository core per funzioni script cross-schema.
#        Profilo utente completo via fn_get_user_profile.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import connection

from apps.core.db._helpers import jsonb_out
from apps.core.services.service_errors import ServiceError


class CoreRepository:
    """Accesso SQL a funzioni dello schema script riusabili dal core."""

    # Scopo: Recupera il profilo completo dell'utente dal DB via script.fn_get_user_profile.
    # Restituisce il JSONB prodotto dalla funzione: blocchi utente, soggetto, emittente.
    def get_user_profile(self, auth_user_id: int) -> dict[str, Any]:
        sql = "SELECT script.fn_get_user_profile(%s)"
        with connection.cursor() as cursor:
            cursor.execute(sql, [auth_user_id])
            row = cursor.fetchone()
            if not row:
                raise ServiceError(
                    code="E_CORE_PROFILE_NOT_FOUND",
                    message="Profilo utente non trovato.",
                    detail=f"fn_get_user_profile non ha restituito dati per auth_user_id={auth_user_id}.",
                )
            assert row is not None
            # Lettura per posizione: il jsonb arriva come testo (`jsonb_out`).
            result = jsonb_out(row[0])
            if result is None:
                raise ServiceError(
                    code="E_CORE_PROFILE_NOT_FOUND",
                    message="Profilo utente non trovato.",
                    detail=f"fn_get_user_profile ha restituito NULL per auth_user_id={auth_user_id}.",
                )
            return result

    # Scopo: Il NOME del fuso dell'azienda (IANA, es. 'Europe/Rome') dalla sede
    #        unica del DB, `script.fn_fuso_operativo()`. Il fail-loud (parametro
    #        assente, vuoto o sconosciuto -> E_CONFIG_MANCANTE) e' della funzione:
    #        qui non si duplica e non si ripiega su niente.
    def get_fuso_operativo(self) -> str:
        with connection.cursor() as cursor:
            cursor.execute("SELECT script.fn_fuso_operativo()")
            row = cursor.fetchone()
        assert row is not None
        return str(row[0])
