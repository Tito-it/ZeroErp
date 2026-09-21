# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository CRUD generico per tabelle config whitelisted.
#        Usa metadata da ConfigMetadataRepository per costruire query dinamiche.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import connection

from apps.core.db.config_metadata_repository import ConfigMetadataRepository
from apps.core.db.dbops_repository import REL_CONSENTITE

_metadata = ConfigMetadataRepository()


class ConfigCrudRepository:
    """CRUD generico per tabelle nella whitelist lookup."""

    # Scopo: Dettaglio singolo record con tutti i campi gestibili.
    def get_record(self, schema: str, table: str, record_id: int) -> dict[str, Any] | None:
        cols = _metadata.get_all_column_names(schema, table)
        if not cols:
            return None
        col_list = ", ".join(cols)
        sql = f"SELECT {col_list} FROM {schema}.{table} WHERE id = %s"  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, [record_id])
            row = cursor.fetchone()
            if not row:
                return None
            return dict(zip(cols, row))

    # Scopo: Crea un nuovo record. Accetta solo colonne gestibili (no audit, no id).
    def create_record(self, schema: str, table: str, data: dict[str, Any]) -> dict[str, Any]:
        editable = _metadata.get_editable_column_names(schema, table)
        # Filtra solo i campi forniti che sono colonne reali
        fields = [(k, v) for k, v in data.items() if k in editable]
        if not fields:
            return {}
        col_names = [f[0] for f in fields]
        values = [f[1] for f in fields]
        placeholders = ", ".join(["%s"] * len(fields))
        col_list = ", ".join(col_names)
        all_cols = ", ".join(_metadata.get_all_column_names(schema, table))

        sql = f"""
            INSERT INTO {schema}.{table} ({col_list}) VALUES ({placeholders})
            RETURNING {all_cols}
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, values)
            row = cursor.fetchone()
            assert row is not None
            return_cols = _metadata.get_all_column_names(schema, table)
            return dict(zip(return_cols, row))

    # Scopo: Aggiorna un record. Accetta solo colonne gestibili fornite nel payload.
    def update_record(self, schema: str, table: str, record_id: int,
                      data: dict[str, Any]) -> bool:
        editable = _metadata.get_editable_column_names(schema, table)
        fields = [(k, v) for k, v in data.items() if k in editable]
        if not fields:
            return False
        set_clause = ", ".join([f"{f[0]} = %s" for f in fields])
        values = [f[1] for f in fields]
        values.append(record_id)
        sql = f"UPDATE {schema}.{table} SET {set_clause} WHERE id = %s"  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, values)
            return cursor.rowcount > 0

    # Scopo: Lista tabelle disponibili raggruppate per schema.
    @staticmethod
    def list_available_tables() -> list[dict[str, str]]:
        result = []
        for rel in sorted(REL_CONSENTITE):
            schema, table = rel.split(".", 1)
            result.append({"schema": schema, "table": table, "rel": rel})
        return result
