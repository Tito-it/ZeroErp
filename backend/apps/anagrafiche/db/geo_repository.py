# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per entita' geografiche config:
#        toponomastica, comuni, province, regioni, stati.
#        Accesso DB-first via cursor.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import connection

from apps.anagrafiche.db._helpers import extract_paginated

_TOPONOMASTICA_ORDER_COLS = {"descrizione", "attivo"}
_COMUNI_ORDER_COLS = {"descrizione", "provincia_sigla", "regione_descrizione"}
_PROVINCE_ORDER_COLS = {"descrizione", "sigla", "regione_descrizione"}
_REGIONI_ORDER_COLS = {"descrizione", "stato_descrizione"}
_STATI_ORDER_COLS = {"descrizione", "codice_iso2", "continente"}
_CODICI_POSTALI_ORDER_COLS = {"codice", "comune_descrizione"}


class GeoRepository:
    """Accesso DB per toponomastica, comuni, province, regioni, stati."""

    # =================================================================
    # Toponomastica
    # =================================================================

    # Scopo: Lista paginata toponomastica.
    def list_toponomastica(
        self, *, search: str | None = None, limit: int = 25, offset: int = 0,
        order_by: str = "descrizione", order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        order_col = order_by if order_by in _TOPONOMASTICA_ORDER_COLS else "descrizione"
        direction = "DESC" if order_dir and order_dir.upper() == "DESC" else "ASC"
        search_pattern = f"%{search.strip()}%" if search and search.strip() else None
        sql = f"""
            SELECT id, descrizione, attivo, COUNT(*) OVER () AS total_count
              FROM config.toponomastica
             WHERE (%s::text IS NULL OR descrizione ILIKE %s)
             ORDER BY {order_col} {direction}, id
             LIMIT %s OFFSET %s
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, [search_pattern, search_pattern, limit, offset])
            return extract_paginated(cursor)

    # Scopo: Dettaglio singolo toponomastica.
    def get_toponomastica(self, pk: int) -> dict[str, Any] | None:
        return self._get_by_id("config.toponomastica", pk, "id, descrizione, attivo")

    # Scopo: Crea tipo strada.
    def create_toponomastica(self, *, descrizione: str) -> dict[str, Any]:
        sql = """
            INSERT INTO config.toponomastica (descrizione) VALUES (%s)
            RETURNING id, descrizione, attivo
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [descrizione.strip()])
            row = cursor.fetchone()
            assert row is not None
            cols = [c.name for c in cursor.description]
            return dict(zip(cols, row))

    # Scopo: Aggiorna tipo strada.
    def update_toponomastica(self, toponomastica_id: int, *, descrizione: str | None = None,
                             attivo: bool | None = None) -> bool:
        return self._dynamic_update("config.toponomastica", toponomastica_id,
                                    descrizione=descrizione, attivo=attivo)

    # =================================================================
    # Comuni
    # =================================================================

    # Scopo: Lista paginata comuni con provincia e regione.
    def list_comuni(
        self, *, search: str | None = None, limit: int = 25, offset: int = 0,
        order_by: str = "descrizione", order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        order_col = order_by if order_by in _COMUNI_ORDER_COLS else "descrizione"
        direction = "DESC" if order_dir and order_dir.upper() == "DESC" else "ASC"
        search_pattern = f"%{search.strip()}%" if search and search.strip() else None
        sql = f"""
            SELECT c.id, c.descrizione,
                   p.sigla AS provincia_sigla,
                   p.descrizione AS provincia_descrizione,
                   r.descrizione AS regione_descrizione,
                   COUNT(*) OVER () AS total_count
              FROM config.comuni c
              LEFT JOIN config.province p ON p.id = c.provincia_id
              LEFT JOIN config.regioni r ON r.id = p.regione_id
             WHERE (%s::text IS NULL OR c.descrizione ILIKE %s)
             ORDER BY {order_col} {direction}, c.id
             LIMIT %s OFFSET %s
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, [search_pattern, search_pattern, limit, offset])
            return extract_paginated(cursor)

    # Scopo: Dettaglio singolo provincia.
    def get_provincia(self, pk: int) -> dict[str, Any] | None:
        sql = """
            SELECT p.id, TRIM(p.descrizione) AS descrizione, TRIM(p.sigla) AS sigla,
                   p.regione_id, r.descrizione AS regione_descrizione
              FROM config.province p
              LEFT JOIN config.regioni r ON r.id = p.regione_id
             WHERE p.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [pk])
            row = cursor.fetchone()
            if not row:
                return None
            cols = [c.name for c in cursor.description]
            return dict(zip(cols, row))

    # Scopo: Dettaglio singolo regione.
    def get_regione(self, pk: int) -> dict[str, Any] | None:
        sql = """
            SELECT r.id, r.descrizione, r.stato_id, s.descrizione AS stato_descrizione
              FROM config.regioni r
              LEFT JOIN config.stati s ON s.id = r.stato_id
             WHERE r.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [pk])
            row = cursor.fetchone()
            if not row:
                return None
            cols = [c.name for c in cursor.description]
            return dict(zip(cols, row))

    # Scopo: Dettaglio singolo stato.
    def get_stato(self, pk: int) -> dict[str, Any] | None:
        return self._get_by_id("config.stati", pk,
            "id, descrizione, sigla_stato, codice_iso2, codice_iso3, codice_telefonico, continente")

    # Scopo: Crea comune.
    def create_comune(self, *, descrizione: str, provincia_id: int | None = None) -> dict[str, Any]:
        sql = """
            INSERT INTO config.comuni (descrizione, provincia_id) VALUES (%s, %s)
            RETURNING id, descrizione, provincia_id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [descrizione.strip(), provincia_id])
            row = cursor.fetchone()
            assert row is not None
            cols = [c.name for c in cursor.description]
            return dict(zip(cols, row))

    # =================================================================
    # Codici Postali (CAP)
    # =================================================================

    # Scopo: Lista paginata codici postali con comune.
    def list_codici_postali(
        self, *, search: str | None = None, comune_id: int | None = None,
        limit: int = 25, offset: int = 0,
        order_by: str = "codice", order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        order_col = order_by if order_by in _CODICI_POSTALI_ORDER_COLS else "codice"
        direction = "DESC" if order_dir and order_dir.upper() == "DESC" else "ASC"
        search_pattern = f"%{search.strip()}%" if search and search.strip() else None
        sql = f"""
            SELECT cp.id, cp.codice, cp.comune_id,
                   c.descrizione AS comune_descrizione,
                   COUNT(*) OVER () AS total_count
              FROM config.codici_postali cp
              JOIN config.comuni c ON c.id = cp.comune_id
             WHERE (%s::text IS NULL OR cp.codice ILIKE %s OR c.descrizione ILIKE %s)
               AND (%s::integer IS NULL OR cp.comune_id = %s)
             ORDER BY {order_col} {direction}, cp.id
             LIMIT %s OFFSET %s
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                search_pattern, search_pattern, search_pattern,
                comune_id, comune_id, limit, offset,
            ])
            return extract_paginated(cursor)

    # Scopo: Dettaglio singolo codice postale.
    def get_codice_postale(self, pk: int) -> dict[str, Any] | None:
        sql = """
            SELECT cp.id, cp.codice, cp.comune_id, c.descrizione AS comune_descrizione
              FROM config.codici_postali cp
              JOIN config.comuni c ON c.id = cp.comune_id
             WHERE cp.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [pk])
            row = cursor.fetchone()
            if not row:
                return None
            cols = [c.name for c in cursor.description]
            return dict(zip(cols, row))

    # Scopo: Crea codice postale.
    def create_codice_postale(self, *, codice: str, comune_id: int) -> dict[str, Any]:
        sql = """
            INSERT INTO config.codici_postali (codice, comune_id) VALUES (%s, %s)
            RETURNING id, codice, comune_id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [codice.strip(), comune_id])
            row = cursor.fetchone()
            assert row is not None
            cols = [c.name for c in cursor.description]
            return dict(zip(cols, row))

    # Scopo: Aggiorna codice postale.
    def update_codice_postale(self, pk: int, *, codice: str | None = None,
                              comune_id: int | None = None) -> bool:
        return self._dynamic_update("config.codici_postali", pk,
                                    codice=codice, comune_id=comune_id)

    # =================================================================
    # Province
    # =================================================================

    # Scopo: Lista paginata province.
    def list_province_paginated(
        self, *, search: str | None = None, regione_id: int | None = None,
        limit: int = 25, offset: int = 0,
        order_by: str = "descrizione", order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        order_col = order_by if order_by in _PROVINCE_ORDER_COLS else "descrizione"
        direction = "DESC" if order_dir and order_dir.upper() == "DESC" else "ASC"
        search_pattern = f"%{search.strip()}%" if search and search.strip() else None
        sql = f"""
            SELECT p.id, TRIM(p.descrizione) AS descrizione, TRIM(p.sigla) AS sigla,
                   p.regione_id, r.descrizione AS regione_descrizione,
                   COUNT(*) OVER () AS total_count
              FROM config.province p
              LEFT JOIN config.regioni r ON r.id = p.regione_id
             WHERE (%s::text IS NULL OR p.descrizione ILIKE %s OR p.sigla ILIKE %s)
               AND (%s::integer IS NULL OR p.regione_id = %s)
             ORDER BY {order_col} {direction}, p.id
             LIMIT %s OFFSET %s
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                search_pattern, search_pattern, search_pattern,
                regione_id, regione_id, limit, offset,
            ])
            return extract_paginated(cursor)

    # Scopo: Lista province per dropdown.
    def list_province(self) -> list[dict[str, Any]]:
        sql = """
            SELECT p.id, p.sigla, p.descrizione, r.descrizione AS regione_descrizione
              FROM config.province p
              LEFT JOIN config.regioni r ON r.id = p.regione_id
             ORDER BY p.descrizione
        """
        with connection.cursor() as cursor:
            cursor.execute(sql)
            cols = [c.name for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    # Scopo: Crea provincia.
    def create_provincia(self, *, descrizione: str, sigla: str,
                         regione_id: int | None = None) -> dict[str, Any]:
        sql = """
            INSERT INTO config.province (descrizione, sigla, regione_id) VALUES (%s, %s, %s)
            RETURNING id, TRIM(descrizione) AS descrizione, TRIM(sigla) AS sigla, regione_id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [descrizione.strip(), sigla.strip().upper(), regione_id])
            row = cursor.fetchone()
            assert row is not None
            cols = [c.name for c in cursor.description]
            return dict(zip(cols, row))

    # Scopo: Aggiorna provincia.
    def update_provincia(self, provincia_id: int, *, descrizione: str | None = None,
                         sigla: str | None = None, regione_id: int | None = None) -> bool:
        fields: list[str] = []
        params: list[Any] = []
        if descrizione is not None:
            fields.append("descrizione = %s")
            params.append(descrizione.strip())
        if sigla is not None:
            fields.append("sigla = %s")
            params.append(sigla.strip().upper())
        if regione_id is not None:
            fields.append("regione_id = %s")
            params.append(regione_id)
        return self._execute_update("config.province", provincia_id, fields, params)

    # =================================================================
    # Regioni
    # =================================================================

    # Scopo: Lista paginata regioni.
    def list_regioni(
        self, *, search: str | None = None, stato_id: int | None = None,
        limit: int = 25, offset: int = 0,
        order_by: str = "descrizione", order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        order_col = order_by if order_by in _REGIONI_ORDER_COLS else "descrizione"
        direction = "DESC" if order_dir and order_dir.upper() == "DESC" else "ASC"
        search_pattern = f"%{search.strip()}%" if search and search.strip() else None
        sql = f"""
            SELECT r.id, r.descrizione, r.stato_id, s.descrizione AS stato_descrizione,
                   COUNT(*) OVER () AS total_count
              FROM config.regioni r
              LEFT JOIN config.stati s ON s.id = r.stato_id
             WHERE (%s::text IS NULL OR r.descrizione ILIKE %s)
               AND (%s::integer IS NULL OR r.stato_id = %s)
             ORDER BY {order_col} {direction}, r.id
             LIMIT %s OFFSET %s
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                search_pattern, search_pattern,
                stato_id, stato_id, limit, offset,
            ])
            return extract_paginated(cursor)

    # Scopo: Lista regioni per dropdown.
    def list_regioni_lookup(self, stato_id: int | None = None) -> list[dict[str, Any]]:
        sql = """
            SELECT id, descrizione, stato_id FROM config.regioni
             WHERE (%s::integer IS NULL OR stato_id = %s)
             ORDER BY descrizione
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [stato_id, stato_id])
            cols = [c.name for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    # Scopo: Crea regione.
    def create_regione(self, *, descrizione: str, stato_id: int | None = None) -> dict[str, Any]:
        sql = """
            INSERT INTO config.regioni (descrizione, stato_id) VALUES (%s, %s)
            RETURNING id, descrizione, stato_id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [descrizione.strip(), stato_id])
            row = cursor.fetchone()
            assert row is not None
            cols = [c.name for c in cursor.description]
            return dict(zip(cols, row))

    # Scopo: Aggiorna regione.
    def update_regione(self, regione_id: int, *, descrizione: str | None = None,
                       stato_id: int | None = None) -> bool:
        return self._dynamic_update("config.regioni", regione_id,
                                    descrizione=descrizione, stato_id=stato_id)

    # =================================================================
    # Stati
    # =================================================================

    # Scopo: Lista paginata stati.
    def list_stati(
        self, *, search: str | None = None, limit: int = 25, offset: int = 0,
        order_by: str = "descrizione", order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        order_col = order_by if order_by in _STATI_ORDER_COLS else "descrizione"
        direction = "DESC" if order_dir and order_dir.upper() == "DESC" else "ASC"
        search_pattern = f"%{search.strip()}%" if search and search.strip() else None
        sql = f"""
            SELECT id, descrizione, sigla_stato, codice_iso2, codice_iso3,
                   codice_telefonico, continente,
                   COUNT(*) OVER () AS total_count
              FROM config.stati
             WHERE (%s::text IS NULL OR descrizione ILIKE %s
                    OR codice_iso2 ILIKE %s OR codice_iso3 ILIKE %s)
             ORDER BY {order_col} {direction}, id
             LIMIT %s OFFSET %s
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                search_pattern, search_pattern, search_pattern, search_pattern,
                limit, offset,
            ])
            return extract_paginated(cursor)

    # Scopo: Lista stati per dropdown.
    def list_stati_lookup(self) -> list[dict[str, Any]]:
        sql = "SELECT id, descrizione, codice_iso2 FROM config.stati ORDER BY descrizione"
        with connection.cursor() as cursor:
            cursor.execute(sql)
            cols = [c.name for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    # Scopo: Crea stato.
    def create_stato(self, *, descrizione: str, codice_iso2: str | None = None,
                     codice_iso3: str | None = None, sigla_stato: str | None = None,
                     codice_telefonico: str | None = None, continente: str | None = None) -> dict[str, Any]:
        sql = """
            INSERT INTO config.stati (descrizione, codice_iso2, codice_iso3,
                                      sigla_stato, codice_telefonico, continente)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, descrizione, codice_iso2, codice_iso3, sigla_stato,
                      codice_telefonico, continente
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                descrizione.strip(),
                codice_iso2.strip().upper() if codice_iso2 else None,
                codice_iso3.strip().upper() if codice_iso3 else None,
                sigla_stato.strip().upper() if sigla_stato else None,
                codice_telefonico.strip() if codice_telefonico else None,
                continente.strip() if continente else None,
            ])
            row = cursor.fetchone()
            assert row is not None
            cols = [c.name for c in cursor.description]
            return dict(zip(cols, row))

    # Scopo: Aggiorna stato.
    def update_stato(self, stato_id: int, *, descrizione: str | None = None,
                     codice_iso2: str | None = None, codice_iso3: str | None = None,
                     sigla_stato: str | None = None, codice_telefonico: str | None = None,
                     continente: str | None = None) -> bool:
        fields: list[str] = []
        params: list[Any] = []
        if descrizione is not None:
            fields.append("descrizione = %s")
            params.append(descrizione.strip())
        if codice_iso2 is not None:
            fields.append("codice_iso2 = %s")
            params.append(codice_iso2.strip().upper())
        if codice_iso3 is not None:
            fields.append("codice_iso3 = %s")
            params.append(codice_iso3.strip().upper())
        if sigla_stato is not None:
            fields.append("sigla_stato = %s")
            params.append(sigla_stato.strip().upper())
        if codice_telefonico is not None:
            fields.append("codice_telefonico = %s")
            params.append(codice_telefonico.strip())
        if continente is not None:
            fields.append("continente = %s")
            params.append(continente.strip())
        return self._execute_update("config.stati", stato_id, fields, params)

    # =================================================================
    # Helper interni
    # =================================================================

    # Scopo: GET singolo record per id (helper generico per entita' semplici).
    def _get_by_id(self, table: str, pk: int, columns: str) -> dict[str, Any] | None:
        sql = f"SELECT {columns} FROM {table} WHERE id = %s"  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, [pk])
            row = cursor.fetchone()
            if not row:
                return None
            cols = [c.name for c in cursor.description]
            return dict(zip(cols, row))

    # Scopo: UPDATE dinamico generico per entita' semplici (descrizione, attivo, ecc.).
    def _dynamic_update(self, table: str, pk: int, **kwargs) -> bool:
        fields: list[str] = []
        params: list[Any] = []
        for col, val in kwargs.items():
            if val is not None:
                if isinstance(val, str):
                    val = val.strip()
                fields.append(f"{col} = %s")
                params.append(val)
        return self._execute_update(table, pk, fields, params)

    # Scopo: Esegue UPDATE con fields/params pre-costruiti.
    def _execute_update(self, table: str, pk: int, fields: list[str], params: list[Any]) -> bool:
        if not fields:
            return False
        params.append(pk)
        sql = f"UPDATE {table} SET {', '.join(fields)} WHERE id = %s"  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount > 0
