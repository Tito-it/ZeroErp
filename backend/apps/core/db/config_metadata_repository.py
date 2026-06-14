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


# Scopo: Normalizza il `column_default` di information_schema nel valore tipizzato
# da usare come default del form di creazione. Restituisce None quando il default
# non e' un literal riconoscibile (es. sequenze nextval(...), espressioni now(),
# cast complessi): in quel caso il FE applica il proprio fallback.
def _parse_column_default(raw_default: str | None, fe_type: str) -> Any:
    if raw_default is None:
        return None
    # Strip cast esplicito (es. "'false'::boolean", "0::integer", "''::text").
    val = raw_default.split("::", 1)[0].strip()
    if fe_type == "boolean":
        # Postgres puo' rappresentare il default come `false` o `'false'`.
        unquoted = val[1:-1] if len(val) >= 2 and val[0] == "'" and val[-1] == "'" else val
        if unquoted in ("true", "false"):
            return unquoted == "true"
        return None
    if fe_type == "number":
        try:
            return int(val)
        except ValueError:
            try:
                return float(val)
            except ValueError:
                return None
    # text/date/json: prefill solo se literal stringa quotata, altrimenti None
    # (evita di propagare espressioni SQL come now() nel form).
    if len(val) >= 2 and val[0] == "'" and val[-1] == "'":
        return val[1:-1]
    return None


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
            fe_type = _TYPE_MAP.get(row[1], "text")
            columns.append({
                "name": col_name,
                "type": fe_type,
                "db_type": row[1],
                "nullable": row[2] == "YES",
                "has_default": row[3] is not None,
                # Default DB normalizzato (literal) per inizializzare il form di
                # creazione; None se non e' un literal riconoscibile.
                "default": _parse_column_default(row[3], fe_type),
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
