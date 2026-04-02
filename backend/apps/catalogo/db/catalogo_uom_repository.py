# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB specializzato per UoM operative articoli.
# ------------------------------------------------------------

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from django.db import connection

from apps.core.db._helpers import row_to_dict, rows_to_list
from apps.core.db.sql_write_helpers import sql_placeholder, to_write_param

UOM_OPERATIVA_WRITE_COLUMNS: dict[str, str] = {
    "uom_id": "int",
    "is_base": "bool",
    "factor_to_base": "numeric",
    "is_sell_uom": "bool",
    "is_purchase_uom": "bool",
    "is_logistic_uom": "bool",
    "qty_step": "numeric",
    "rounding_mode": "text",
    "max_decimals": "int",
    "forbid_fraction": "bool",
    "require_lot": "bool",
    "gtin": "text",
    "valido_dal": "date",
    "valido_al": "date",
    "attivo": "bool",
    "meta": "jsonb",
}

UOM_OPERATIVA_DETAIL_COLUMNS: tuple[str, ...] = (
    "auo.id",
    "auo.articolo_id",
    "auo.uom_id",
    "u.codice AS uom_codice",
    "u.descrizione AS uom_descrizione",
    "auo.is_base",
    "auo.factor_to_base",
    "auo.is_sell_uom",
    "auo.is_purchase_uom",
    "auo.is_logistic_uom",
    "auo.qty_step",
    "auo.rounding_mode",
    "auo.max_decimals",
    "auo.forbid_fraction",
    "auo.require_lot",
    "auo.gtin",
    "auo.valido_dal",
    "auo.valido_al",
    "auo.attivo",
    "auo.meta",
    "auo.user_insert",
    "auo.user_update",
    "auo.data_insert",
    "auo.data_update",
)


class CatalogoUomRepository:
    """Repository specializzato per UoM operative articolo."""

    # Scopo: Restituisce la proiezione SQL esplicita per il dettaglio UoM operativa.
    @staticmethod
    def _projection() -> str:
        return ",\n                    ".join(UOM_OPERATIVA_DETAIL_COLUMNS)

    # Scopo: Lista le UoM operative dell'articolo ordinate con la base in cima.
    def list_uom_operative(self, articolo_id: UUID | str) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    {projection}
                FROM catalogo.articoli_uom_operativa auo
                JOIN catalogo.unita_misura u
                  ON u.id = auo.uom_id
                WHERE auo.articolo_id = %s
                ORDER BY auo.is_base DESC, auo.is_sell_uom DESC, auo.is_logistic_uom DESC, u.codice ASC, auo.id ASC
                """.format(projection=self._projection()),
                [articolo_id],
            )
            return rows_to_list(cursor)

    # Scopo: Restituisce una singola UoM operativa verificando l'ownership sull'articolo.
    def get_uom_operativa(
        self,
        articolo_id: UUID | str,
        uom_operativa_id: int,
    ) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    {projection}
                FROM catalogo.articoli_uom_operativa auo
                JOIN catalogo.unita_misura u
                  ON u.id = auo.uom_id
                WHERE auo.articolo_id = %s
                  AND auo.id = %s
                """.format(projection=self._projection()),
                [articolo_id, uom_operativa_id],
            )
            return row_to_dict(cursor)

    # Scopo: Inserisce una nuova UoM operativa per l'articolo.
    def create_uom_operativa(self, articolo_id: UUID | str, data: dict[str, Any]) -> int:
        fields = [("articolo_id", articolo_id), *[(key, value) for key, value in data.items() if key in UOM_OPERATIVA_WRITE_COLUMNS]]

        column_names = [field_name for field_name, _ in fields]
        placeholders = ", ".join(
            "%s" if field_name == "articolo_id" else sql_placeholder(UOM_OPERATIVA_WRITE_COLUMNS[field_name])
            for field_name, _ in fields
        )
        params = [
            field_value if field_name == "articolo_id" else to_write_param(field_value, UOM_OPERATIVA_WRITE_COLUMNS[field_name])
            for field_name, field_value in fields
        ]

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO catalogo.articoli_uom_operativa ({", ".join(column_names)})
                VALUES ({placeholders})
                RETURNING id
                """,
                params,
            )
            row = cursor.fetchone()

        assert row is not None
        return int(row[0])

    # Scopo: Aggiorna la UoM operativa solo se appartiene all'articolo indicato.
    def update_uom_operativa(
        self,
        articolo_id: UUID | str,
        uom_operativa_id: int,
        data: dict[str, Any],
    ) -> bool:
        fields = [(key, value) for key, value in data.items() if key in UOM_OPERATIVA_WRITE_COLUMNS]
        if not fields:
            return False

        set_clause = ", ".join(
            f"{field_name} = {sql_placeholder(UOM_OPERATIVA_WRITE_COLUMNS[field_name])}"
            for field_name, _ in fields
        )
        params = [
            to_write_param(field_value, UOM_OPERATIVA_WRITE_COLUMNS[field_name])
            for field_name, field_value in fields
        ]
        params.extend([articolo_id, uom_operativa_id])

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE catalogo.articoli_uom_operativa
                SET {set_clause}
                WHERE articolo_id = %s
                  AND id = %s
                """,
                params,
            )
            return cursor.rowcount > 0

    # Scopo: Elimina una UoM operativa dell'articolo con ownership check.
    def delete_uom_operativa(self, articolo_id: UUID | str, uom_operativa_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM catalogo.articoli_uom_operativa
                WHERE articolo_id = %s
                  AND id = %s
                """,
                [articolo_id, uom_operativa_id],
            )
            return cursor.rowcount > 0

    # Scopo: Wrappa la funzione DB per la UoM base dell'articolo.
    def get_uom_base(self, articolo_id: UUID | str) -> int | None:
        with connection.cursor() as cursor:
            cursor.execute("SELECT catalogo.fn_get_uom_base(%s)", [articolo_id])
            row = cursor.fetchone()
        return None if row is None or row[0] is None else int(row[0])

    # Scopo: Wrappa la funzione DB per il fattore di conversione alla base.
    def get_uom_factor(self, articolo_id: UUID | str, uom_id: int) -> Decimal | None:
        with connection.cursor() as cursor:
            cursor.execute("SELECT catalogo.fn_get_uom_factor(%s, %s)", [articolo_id, uom_id])
            row = cursor.fetchone()
        return None if row is None else row[0]
