# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per metadata tabelle config via information_schema.
#        Introspezione tecnica — non logica business (non viola DB-first).
#        I metadata sono cacheable in memoria (non cambiano a runtime).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import connection

# Colonne di sistema da escludere — audit, transazione, storicizzazione.
_EXCLUDED_COLUMNS = frozenset({
    "data_insert", "user_insert", "data_update", "user_update",
    "tx_id", "storicizza",
})

# Mapping tipo SQL → tipo frontend per il renderer dinamico.
_TYPE_MAP = {
    "integer": "number",
    "bigint": "number",
    "smallint": "number",
    "numeric": "number",
    "boolean": "boolean",
    "jsonb": "json",
    "json": "json",
    "text": "text",
    "character varying": "text",
    "character": "text",
    "varchar": "text",
    "char": "text",
    "date": "date",
    "timestamp with time zone": "datetime",
    "timestamp without time zone": "datetime",
    "uuid": "text",
}

# Cache in memoria — {schema.table: [columns]}
_cache: dict[str, list[dict[str, Any]]] = {}


class ConfigMetadataRepository:
    """Legge metadata colonne da information_schema per il CRUD generico config."""

    # Scopo: Restituisce la lista colonne gestibili di una tabella.
    # Esclude colonne audit/sistema. Cacheable — si legge una volta.
    def get_table_columns(self, schema: str, table: str) -> list[dict[str, Any]]:
        cache_key = f"{schema}.{table}"
        if cache_key in _cache:
            return _cache[cache_key]

        sql = """
            SELECT column_name, data_type, is_nullable, column_default
              FROM information_schema.columns
             WHERE table_schema = %s AND table_name = %s
             ORDER BY ordinal_position
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [schema, table])
            rows = cursor.fetchall()

        columns = []
        for row in rows:
            col_name = row[0]
            if col_name in _EXCLUDED_COLUMNS:
                continue
            columns.append({
                "name": col_name,
                "type": _TYPE_MAP.get(row[1], "text"),
                "db_type": row[1],
                "nullable": row[2] == "YES",
                "has_default": row[3] is not None,
                "is_pk": col_name == "id",
            })

        _cache[cache_key] = columns
        return columns

    # Scopo: Restituisce solo i nomi delle colonne gestibili (per SELECT/INSERT/UPDATE).
    def get_editable_column_names(self, schema: str, table: str) -> list[str]:
        return [c["name"] for c in self.get_table_columns(schema, table) if not c["is_pk"]]

    # Scopo: Restituisce tutti i nomi colonne incluso id (per SELECT).
    def get_all_column_names(self, schema: str, table: str) -> list[str]:
        return [c["name"] for c in self.get_table_columns(schema, table)]

    # Scopo: Invalida la cache (utile in test).
    @staticmethod
    def clear_cache() -> None:
        _cache.clear()
