# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB generico per lo schema catalogo (articoli e lookup UoM).
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from django.db import connection

from apps.core.db._helpers import row_to_dict, rows_to_list
from apps.core.db.sql_write_helpers import sql_placeholder, to_write_param

ARTICOLI_ORDER_COLUMNS: dict[str, str] = {
    "codice": "a.codice",
    "descrizione": "a.descrizione",
    "uom_codice": "a.uom_codice",
    "data_insert": "a.data_insert",
    "data_update": "a.data_update",
}

ARTICOLI_CREATE_COLUMNS: dict[str, str] = {
    "codice": "text",
    "descrizione": "text",
    "descrizione_breve": "text",
    "uom_id": "int",
    "tipo_voce_id": "int",
    "gruppo_voce_id": "int",
    "spesa_id": "int",
    "iva_id": "int",
    "conto_contabile_vendita_id": "int",
    "conto_contabile_acquisto_id": "int",
    "is_composito": "bool",
    "is_solo_componente": "bool",
    "requires_serial": "bool",
    "voce_utility": "bool",
    "meta": "jsonb",
}

ARTICOLI_UPDATE_COLUMNS: dict[str, str] = {
    key: value for key, value in ARTICOLI_CREATE_COLUMNS.items() if key != "codice"
} | {"attivo": "bool"}

ARTICOLI_DETAIL_COLUMNS: tuple[str, ...] = (
    "a.id",
    "a.codice",
    "a.descrizione",
    "a.descrizione_breve",
    "a.uom_id",
    "a.tipo_voce_id",
    "a.gruppo_voce_id",
    "a.spesa_id",
    "a.iva_id",
    "a.conto_contabile_vendita_id",
    "a.conto_contabile_acquisto_id",
    "a.is_composito",
    "a.is_solo_componente",
    "a.requires_serial",
    "a.voce_utility",
    "a.meta",
    "a.user_insert",
    "a.user_update",
    "a.data_insert",
    "a.data_update",
    "a.tx_id",
    "a.storicizza",
    "a.attivo",
    "a.note_target_tipo",
    "a.note_id",
    "a.uom_ref_id",
    "a.uom_codice",
    "a.uom_descrizione",
    "a.tipologia_ref_id",
    "a.tipologia_codice",
    "a.tipologia_descrizione",
    "a.gruppo_ref_id",
    "a.gruppo_codice",
    "a.gruppo_descrizione",
    "a.spesa_ref_id",
    "a.spesa_codice",
    "a.spesa_descrizione",
    "a.iva_ref_id",
    "a.iva_codice",
    "a.iva_descrizione",
    "a.iva_aliquota_iva",
)


# Scopo: Aggiunge una condizione di ricerca ILIKE su due colonne testuali.
def _append_ilike_search(
    *,
    conditions: list[str],
    params: list[Any],
    left_column: str,
    right_column: str,
    search: str | None,
) -> None:
    if search is None:
        return
    conditions.append(f"({left_column} ILIKE %s OR {right_column} ILIKE %s)")
    like_value = f"%{search}%"
    params.extend([like_value, like_value])

class CatalogoRepository:
    """Repository generico per query articoli e lookup UoM."""

    # Scopo: Restituisce la proiezione SQL esplicita per la vista articoli dettaglio.
    @staticmethod
    def _articoli_detail_projection() -> str:
        return ",\n                    ".join(ARTICOLI_DETAIL_COLUMNS)

    # Scopo: Restituisce elenco articoli da vista dettaglio con filtri opzionali.
    def list_articoli(
        self,
        *,
        attivo: bool | None,
        is_composito: bool | None,
        voce_utility: bool | None,
        tipo_voce_id: int | None,
        gruppo_voce_id: int | None,
        search: str | None,
        data_da: date | None,
        data_a: date | None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))
        order_column = ARTICOLI_ORDER_COLUMNS[order_by]
        safe_order_dir = "DESC" if order_dir.lower() == "desc" else "ASC"

        conditions: list[str] = []
        params: list[Any] = []

        # Scopo: Applica solo i filtri realmente valorizzati mantenendo SQL parametrico.
        if attivo is not None:
            conditions.append("a.attivo = %s")
            params.append(attivo)
        if is_composito is not None:
            conditions.append("a.is_composito = %s")
            params.append(is_composito)
        if voce_utility is not None:
            conditions.append("a.voce_utility = %s")
            params.append(voce_utility)
        if tipo_voce_id is not None:
            conditions.append("a.tipo_voce_id = %s")
            params.append(tipo_voce_id)
        if gruppo_voce_id is not None:
            conditions.append("a.gruppo_voce_id = %s")
            params.append(gruppo_voce_id)
        _append_ilike_search(
            conditions=conditions,
            params=params,
            left_column="a.codice",
            right_column="a.descrizione",
            search=search,
        )
        if data_da is not None:
            conditions.append("a.data_insert::date >= %s")
            params.append(data_da)
        if data_a is not None:
            conditions.append("a.data_insert::date <= %s")
            params.append(data_a)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        count_sql = f"""
            SELECT COUNT(*)
            FROM catalogo.vw_articoli_dettaglio a
            {where_clause}
        """
        data_sql = f"""
            SELECT
                {self._articoli_detail_projection()}
            FROM catalogo.vw_articoli_dettaglio a
            {where_clause}
            ORDER BY {order_column} {safe_order_dir}, a.id ASC
            LIMIT %s OFFSET %s
        """

        with connection.cursor() as cursor:
            cursor.execute(count_sql, params)
            row = cursor.fetchone()
            assert row is not None
            total_count = int(row[0])

            cursor.execute(data_sql, params + [safe_limit, safe_offset])
            results = rows_to_list(cursor)

        return results, total_count

    # Scopo: Restituisce singolo articolo arricchito dalla vista dettaglio.
    def get_articolo(self, articolo_id: UUID | str) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    {projection}
                FROM catalogo.vw_articoli_dettaglio a
                WHERE a.id = %s
                """.format(projection=self._articoli_detail_projection()),
                [articolo_id],
            )
            return row_to_dict(cursor)

    # Scopo: Inserisce un articolo usando solo colonne esplicitamente ammesse.
    def create_articolo(self, data: dict[str, Any]) -> UUID:
        fields = [(key, value) for key, value in data.items() if key in ARTICOLI_CREATE_COLUMNS]
        if not fields:
            raise ValueError("create_articolo_empty_payload")

        column_names = [field_name for field_name, _ in fields]
        placeholders = ", ".join(
            sql_placeholder(ARTICOLI_CREATE_COLUMNS[field_name])
            for field_name, _ in fields
        )
        params = [
            to_write_param(field_value, ARTICOLI_CREATE_COLUMNS[field_name])
            for field_name, field_value in fields
        ]

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO catalogo.articoli ({", ".join(column_names)})
                VALUES ({placeholders})
                RETURNING id
                """,
                params,
            )
            row = cursor.fetchone()

        assert row is not None
        return row[0]

    # Scopo: Aggiorna i soli campi presenti nel payload, supportando anche NULL espliciti.
    def update_articolo(self, articolo_id: UUID | str, data: dict[str, Any]) -> bool:
        fields = [(key, value) for key, value in data.items() if key in ARTICOLI_UPDATE_COLUMNS]
        if not fields:
            return False

        set_clause = ", ".join(
            f"{field_name} = {sql_placeholder(ARTICOLI_UPDATE_COLUMNS[field_name])}"
            for field_name, _ in fields
        )
        params = [
            to_write_param(field_value, ARTICOLI_UPDATE_COLUMNS[field_name])
            for field_name, field_value in fields
        ]
        params.append(articolo_id)

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE catalogo.articoli
                SET {set_clause}
                WHERE id = %s
                """,
                params,
            )
            return cursor.rowcount > 0

    # Scopo: Disattiva un articolo mantenendo la semantica soft-delete prevista dal dominio.
    def deactivate_articolo(self, articolo_id: UUID | str) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE catalogo.articoli
                SET attivo = FALSE
                WHERE id = %s
                  AND attivo IS DISTINCT FROM FALSE
                """,
                [articolo_id],
            )
            return cursor.rowcount > 0

    # Scopo: Restituisce lookup articoli per autocomplete cross-dominio.
    def lookup_articoli(
        self,
        *,
        search: str | None,
        voce_utility: bool | None,
        attivo: bool | None,
        is_composito: bool | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 50))
        conditions: list[str] = []
        params: list[Any] = []

        _append_ilike_search(
            conditions=conditions,
            params=params,
            left_column="a.codice",
            right_column="a.descrizione",
            search=search,
        )
        if voce_utility is not None:
            conditions.append("a.voce_utility = %s")
            params.append(voce_utility)
        if attivo is not None:
            conditions.append("a.attivo = %s")
            params.append(attivo)
        if is_composito is not None:
            conditions.append("a.is_composito = %s")
            params.append(is_composito)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    a.id,
                    a.codice,
                    a.descrizione,
                    a.uom_codice,
                    a.uom_descrizione,
                    a.is_composito,
                    a.voce_utility,
                    a.attivo
                FROM catalogo.vw_articoli_dettaglio a
                {where_clause}
                ORDER BY a.codice ASC
                LIMIT %s
                """,
                params + [safe_limit],
            )
            return rows_to_list(cursor)

    # --- Sezione CRUD unita_misura ---

    # Scopo: Restituisce elenco paginato unita' di misura con filtri opzionali.
    def list_unita_misura(
        self,
        *,
        attivo: bool | None,
        search: str | None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))
        order_map = {"codice": "u.codice", "descrizione": "u.descrizione", "data_insert": "u.data_insert", "data_update": "u.data_update"}
        order_column = order_map.get(order_by, "u.codice")
        safe_order_dir = "DESC" if order_dir.lower() == "desc" else "ASC"

        conditions: list[str] = []
        params: list[Any] = []

        if attivo is not None:
            conditions.append("u.attivo = %s")
            params.append(attivo)
        _append_ilike_search(
            conditions=conditions,
            params=params,
            left_column="u.codice",
            right_column="u.descrizione",
            search=search,
        )

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT COUNT(*) FROM catalogo.unita_misura u {where_clause}",
                params,
            )
            row = cursor.fetchone()
            assert row is not None
            total_count = int(row[0])

            cursor.execute(
                f"""
                SELECT u.id, u.codice, u.descrizione, u.descrizione_fattura, u.attivo,
                       u.user_insert, u.user_update, u.data_insert, u.data_update
                FROM catalogo.unita_misura u
                {where_clause}
                ORDER BY {order_column} {safe_order_dir}, u.id ASC
                LIMIT %s OFFSET %s
                """,
                params + [safe_limit, safe_offset],
            )
            results = rows_to_list(cursor)

        return results, total_count

    # Scopo: Restituisce singola unita' di misura per id.
    def get_unita_misura(self, uom_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT u.id, u.codice, u.descrizione, u.descrizione_fattura, u.attivo,
                       u.user_insert, u.user_update, u.data_insert, u.data_update
                FROM catalogo.unita_misura u
                WHERE u.id = %s
                """,
                [uom_id],
            )
            return row_to_dict(cursor)

    # Scopo: Inserisce una nuova unita' di misura.
    def create_unita_misura(self, data: dict[str, Any]) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO catalogo.unita_misura (codice, descrizione, descrizione_fattura)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                [data["codice"], data["descrizione"], data.get("descrizione_fattura")],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    # Scopo: Aggiorna una unita' di misura esistente.
    def update_unita_misura(self, uom_id: int, data: dict[str, Any]) -> bool:
        sets: list[str] = []
        params: list[Any] = []
        for key in ("descrizione", "descrizione_fattura"):
            if key in data:
                sets.append(f"{key} = %s")
                params.append(data[key])
        if not sets:
            return False
        params.append(uom_id)
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE catalogo.unita_misura SET {', '.join(sets)} WHERE id = %s",
                params,
            )
            return cursor.rowcount > 0

    # Scopo: Disattiva una unita' di misura (soft delete).
    def deactivate_unita_misura(self, uom_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE catalogo.unita_misura SET attivo = FALSE
                WHERE id = %s AND attivo IS DISTINCT FROM FALSE
                """,
                [uom_id],
            )
            return cursor.rowcount > 0

    # Scopo: Restituisce lookup UoM attive per autocomplete e select.
    def lookup_unita_misura(
        self,
        *,
        search: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 200))
        conditions = ["u.attivo = TRUE"]
        params: list[Any] = []

        _append_ilike_search(
            conditions=conditions,
            params=params,
            left_column="u.codice",
            right_column="u.descrizione",
            search=search,
        )

        where_clause = "WHERE " + " AND ".join(conditions)

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    u.id,
                    u.codice,
                    u.descrizione
                FROM catalogo.unita_misura u
                {where_clause}
                ORDER BY u.codice ASC
                LIMIT %s
                """,
                params + [safe_limit],
            )
            return rows_to_list(cursor)
