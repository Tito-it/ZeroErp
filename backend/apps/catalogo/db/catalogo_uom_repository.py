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
from apps.core.db.sql_write_helpers import execute_dynamic_insert, sql_set_clause

# Colonne SCRIVIBILI di una UoM operativa: whitelist RIGIDA del BB di
# scrittura (2026-09-26 — prima mappa nome -> tipo per `sql_placeholder`/
# `to_write_param`, ritirati). `meta` (jsonb) arriva dal service come dict o
# None: il BB lo casta da solo. `articolo_id` NON e' qui: viene dal path.
UOM_OPERATIVA_WRITE_COLUMNS: frozenset[str] = frozenset({
    "uom_id",
    "is_base",
    "factor_to_base",
    "is_sell_uom",
    "is_purchase_uom",
    "is_logistic_uom",
    "qty_step",
    "rounding_mode",
    "max_decimals",
    "forbid_fraction",
    "require_lot",
    "gtin",
    "valido_dal",
    "valido_al",
    "attivo",
    "meta",
})

UOM_OPERATIVA_DETAIL_COLUMNS: tuple[str, ...] = (
    "auo.id",
    "auo.articolo_id",
    "auo.uom_id",
    "auo.uom_codice",
    "auo.uom_descrizione",
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
    # Capability di riga (Fase 6): only is_base blocca eliminazione.
    # motivo_non_eliminabile: 'UOM_BASE_NON_ELIMINABILE' | NULL.
    "auo.puo_eliminarsi",
    "auo.motivo_non_eliminabile",
)


class CatalogoUomRepository:
    """Repository specializzato per UoM operative articolo."""

    # Scopo: Restituisce la proiezione SQL esplicita per il dettaglio UoM operativa.
    @staticmethod
    def _projection() -> str:
        return ",\n                    ".join(UOM_OPERATIVA_DETAIL_COLUMNS)

    # Scopo: Lista le UoM operative dell'articolo ordinate con la base in cima.
    # Legge da vw_articoli_uom_operativa_dettaglio: include denormalizzazioni
    # uom_codice/uom_descrizione e capability puo_eliminarsi/motivo_non_eliminabile
    # (Fase 6 — single source of truth, vista DB).
    def list_uom_operative(self, articolo_id: UUID | str) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    {projection}
                FROM catalogo.vw_articoli_uom_operativa_dettaglio auo
                WHERE auo.articolo_id = %s
                ORDER BY auo.is_base DESC, auo.is_sell_uom DESC, auo.is_logistic_uom DESC, auo.uom_codice ASC, auo.id ASC
                """.format(projection=self._projection()),
                [articolo_id],
            )
            return rows_to_list(cursor)

    # Scopo: Restituisce una singola UoM operativa verificando l'ownership sull'articolo.
    # Stessa proiezione della lista (Fase 6 — capability incluse).
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
                FROM catalogo.vw_articoli_uom_operativa_dettaglio auo
                WHERE auo.articolo_id = %s
                  AND auo.id = %s
                """.format(projection=self._projection()),
                [articolo_id, uom_operativa_id],
            )
            return row_to_dict(cursor)

    # Scopo: Inserisce una nuova UoM operativa per l'articolo.
    # ⛔ Whitelist RIGIDA dal 2026-09-26 (BB `execute_dynamic_insert`): il 400
    #    lo da' il service (`_extract_uom_operativa_payload`). L'articolo viene
    #    dal path, scritto PER ULTIMO: vince sul payload.
    def create_uom_operativa(self, articolo_id: UUID | str, data: dict[str, Any]) -> int:
        riga = execute_dynamic_insert(
            "catalogo.articoli_uom_operativa",
            {**data, "articolo_id": articolo_id},
            allowed=UOM_OPERATIVA_WRITE_COLUMNS | {"articolo_id"},
        )
        return int(riga["id"])

    # Scopo: Aggiorna la UoM operativa solo se appartiene all'articolo indicato.
    #        SET dal BB `sql_set_clause` (whitelist RIGIDA), WHERE del metodo.
    def update_uom_operativa(
        self,
        articolo_id: UUID | str,
        uom_operativa_id: int,
        data: dict[str, Any],
    ) -> bool:
        if not data:
            return False
        set_clause, params = sql_set_clause(data, allowed=UOM_OPERATIVA_WRITE_COLUMNS)
        params.extend([articolo_id, uom_operativa_id])

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE catalogo.articoli_uom_operativa
                SET {set_clause}
                WHERE articolo_id = %s
                  AND id = %s
                """,  # noqa: S608 — SET da sql_set_clause (colonne verificate sulla whitelist UOM_OPERATIVA_WRITE_COLUMNS), valori come parametri
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
