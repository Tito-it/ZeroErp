# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository core per parametri di sistema (config.parameters)
#        con risoluzione override via script.fn_get_parameter_full.
#        Supporta: risoluzione singola/multipla, lista parametri per
#        utente con livelli override, CRUD override utente.
# ------------------------------------------------------------

from __future__ import annotations

from django.db import connection

# Nuova firma fn_get_parameter_full: p_emittente_fiscale_id (bigint) al posto di p_tenant_id.
# Catena priorita': user -> group -> emittente -> session -> function -> default.
_SQL_RESOLVE = "SELECT script.fn_get_parameter_full(%s, %s, %s, %s, %s, %s)"

# Limite massimo codici per singola richiesta (difesa contro abuse).
MAX_CODES = 20


class ParameterRepository:
    """Accesso DB ai parametri di sistema con risoluzione override."""

    # Scopo: Risolve il valore di un singolo parametro applicando la catena di
    #        override (user -> group -> emittente -> session -> function -> default).
    def get_parameter(
        self,
        code: str,
        django_user_id: int | None = None,
        group_ids: list[int] | None = None,
        emittente_fiscale_id: int | None = None,
        session_key: str | None = None,
        function_name: str | None = None,
    ) -> str | None:
        with connection.cursor() as cursor:
            cursor.execute(_SQL_RESOLVE, [
                code, emittente_fiscale_id, django_user_id,
                group_ids, session_key, function_name,
            ])
            row = cursor.fetchone()
        if not row:
            return None
        return row[0]

    # Scopo: Risolve N parametri in un'unica sessione DB.
    #        Restituisce un dizionario {code: valore_risolto}.
    #        I codici non trovati vengono esclusi dal risultato.
    def get_parameters(
        self,
        codes: list[str],
        django_user_id: int | None = None,
        group_ids: list[int] | None = None,
        emittente_fiscale_id: int | None = None,
    ) -> dict[str, str]:
        if not codes:
            return {}
        safe_codes = codes[:MAX_CODES]
        results: dict[str, str] = {}
        with connection.cursor() as cursor:
            for code in safe_codes:
                cursor.execute(_SQL_RESOLVE, [
                    code, emittente_fiscale_id, django_user_id,
                    group_ids, None, None,
                ])
                row = cursor.fetchone()
                if row and row[0] is not None:
                    results[code] = row[0]
        return results

    # Scopo: Restituisce la lista completa dei parametri con i valori risolti
    #        a ogni livello di scope (emittente, gruppo, utente) e il valore finale.
    #        Delega a script.fn_list_parameters_for_user.
    def list_for_user(
        self,
        django_user_id: int,
        group_ids: list[int] | None = None,
        emittente_fiscale_id: int | None = None,
    ) -> list[dict]:
        sql = "SELECT * FROM script.fn_list_parameters_for_user(%s, %s, %s)"
        with connection.cursor() as cursor:
            cursor.execute(sql, [django_user_id, group_ids, emittente_fiscale_id])
            columns = [col.name for col in cursor.description]
            rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    # Scopo: Crea o aggiorna un override personale dell'utente per un parametro.
    #        Usa UPSERT (INSERT ON CONFLICT UPDATE) sulla combinazione
    #        parameter_id + django_user_id con tutti gli altri scope a NULL.
    def upsert_user_override(
        self,
        parameter_code: str,
        django_user_id: int,
        value: str,
    ) -> int:
        sql = """
            INSERT INTO config.parameter_overrides
                   (parameter_id, django_user_id, overridden_value)
            VALUES (
                (SELECT id FROM config.parameters WHERE code = %s),
                %s, %s
            )
            ON CONFLICT ON CONSTRAINT uq_overrides_full_scope_v2
            DO UPDATE SET overridden_value = EXCLUDED.overridden_value,
                          data_update = now()
            RETURNING id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [parameter_code, django_user_id, value])
            row = cursor.fetchone()
            assert row is not None
            return row[0]

    # Scopo: Rimuove un override personale dell'utente.
    #        Verifica che l'override appartenga all'utente specificato.
    def delete_user_override(
        self,
        override_id: int,
        django_user_id: int,
    ) -> bool:
        sql = """
            DELETE FROM config.parameter_overrides
             WHERE id = %s AND django_user_id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [override_id, django_user_id])
            return cursor.rowcount > 0

    # Scopo: Risolve l'emittente_fiscale_id dell'utente dal bridge HR.
    #        Query leggera: risorse_umane_auth_user -> risorse_umane -> emittente.
    def get_emittente_fiscale_id_for_user(self, auth_user_id: int) -> int | None:
        sql = """
            SELECT ru.emittente_fiscale_id
              FROM anagrafiche.risorse_umane_auth_user rau
              JOIN anagrafiche.risorse_umane ru ON ru.id = rau.risorsa_umana_id
             WHERE rau.auth_user_id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [auth_user_id])
            row = cursor.fetchone()
            return row[0] if row else None
