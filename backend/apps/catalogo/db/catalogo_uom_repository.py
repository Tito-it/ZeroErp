# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB specializzato per UoM operative articoli.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any
from uuid import UUID

from django.db import connection

from apps.core.db._helpers import (
    RicercaFull,
    add_ricerca_full_condition,
    fetch_paged_with_total,
    limiti_pagina,
    row_to_dict,
    rows_to_list,
    sql_order_clause,
)
from apps.core.db.sql_write_helpers import execute_dynamic_insert, sql_set_clause

# Colonne SCRIVIBILI di una UoM operativa: whitelist RIGIDA del BB di
# scrittura (2026-09-26 — prima mappa nome -> tipo per `sql_placeholder`/
# `to_write_param`, ritirati). `meta` (jsonb) arriva dal service come dict o
# None: il BB lo casta da solo. `articolo_id` NON e' qui: viene dal path.
# ⛔ `is_base` non si scrive (2026-11-09, giro 2 di brief-db-revisione-catalogo,
#    D12): la riga base nasce con l'articolo (`trgfn_articoli_seed_uom_base`) e
#    non cambia piu' (`trgfn_articoli_uom_operativa_guard_base`,
#    `E_UOM_RIGA_BASE_IMMUTABILE`). Nessuna scrittura dall'app la puo' creare,
#    spostare o togliere: offrirla vorrebbe dire offrire solo un rifiuto.
# ⛔ `rounding_mode` e `require_lot` sono ritirate dalla tabella (Q4, BE16).
UOM_OPERATIVA_WRITE_COLUMNS: frozenset[str] = frozenset({
    "uom_id",
    "factor_to_base",
    "is_sell_uom",
    "is_purchase_uom",
    "is_logistic_uom",
    "qty_step",
    "max_decimals",
    "forbid_fraction",
    "gtin",
    "valido_dal",
    "valido_al",
    "attivo",
    "meta",
})

# Whitelist ORDER BY della lista `catalogo.articolo_uom` (111): le colonne
# della vista `catalogo.vw_articoli_uom_operativa_dettaglio` (la `vista_sql`
# del catalogo), chiavi = `campo_sorgente`.
ARTICOLO_UOM_ORDER_COLUMNS: dict[str, str] = {
    "uom_codice": "auo.uom_codice",
    "uom_descrizione": "auo.uom_descrizione",
    "is_base": "auo.is_base",
    "factor_to_base": "auo.factor_to_base",
    "is_logistic_uom": "auo.is_logistic_uom",
    "attivo": "auo.attivo",
}
# L'ordine di partenza: la base in cima, poi vendita e logistica, poi il codice.
# Uno solo per la collezione intera (`list_uom_operative`) e per la pagina: il
# dettaglio dell'articolo e la lista mostrano le UoM nello stesso ordine.
_ARTICOLO_UOM_ORDINE_DEFAULT = (
    "auo.is_base DESC, auo.is_sell_uom DESC, auo.is_logistic_uom DESC, auo.uom_codice ASC"
)
# Cosa si PUO' cercare (la soglia della lista e' 1 carattere: codici corti).
_RICERCA_ARTICOLO_UOM = RicercaFull("catalogo.articolo_uom", ("uom_codice", "uom_descrizione"))

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
    "auo.max_decimals",
    "auo.forbid_fraction",
    "auo.gtin",
    "auo.valido_dal",
    "auo.valido_al",
    "auo.attivo",
    "auo.meta",
    "auo.user_insert",
    "auo.user_update",
    "auo.data_insert",
    "auo.data_update",
    # ⭐ Capability di riga: la vista le prende dal BB del DB
    #    `catalogo.fn_uom_conversione_capability` (G1-G2 di
    #    brief-db-revisione-catalogo, 2026-11-11), la stessa regola che il
    #    guard della storia usa per rifiutare. Il backend le TRASPORTA.
    #    `motivo_non_eliminabile`: UOM_BASE_NON_ELIMINABILE, UOM_STORIA_IN_VIGORE
    #    o NULL; `motivo_non_chiudibile`: UOM_BASE, UOM_STORIA_CHIUSA o NULL.
    #    `puo_cambiare_attivo` spegne l'interruttore (la riga base, una
    #    mappatura in vigore); `data_min_chiusura` / `data_default_chiusura`
    #    sono il pavimento e la proposta della data di fine.
    "auo.puo_eliminarsi",
    "auo.motivo_non_eliminabile",
    "auo.puo_cambiare_attivo",
    "auo.puo_chiudersi",
    "auo.data_min_chiusura",
    "auo.data_default_chiusura",
    "auo.motivo_non_chiudibile",
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
                f"""
                SELECT
                    {self._projection()}
                FROM catalogo.vw_articoli_uom_operativa_dettaglio auo
                WHERE auo.articolo_id = %s
                ORDER BY {_ARTICOLO_UOM_ORDINE_DEFAULT}, auo.id ASC
                """,  # noqa: S608 — proiezione e ORDER BY da costanti, valori come parametri
                [articolo_id],
            )
            return rows_to_list(cursor)

    # Scopo: La pagina della lista `catalogo.articolo_uom` (111, dal 2026-10-31):
    #        stessa proiezione di `list_uom_operative`, con ricerca e ordinamento.
    #        `list_uom_operative` resta la collezione intera per il lookup
    #        cross-dominio e il dettaglio dell'articolo.
    def list_uom_operative_pagina(
        self,
        articolo_id: UUID | str,
        *,
        search: str | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit, safe_offset = limiti_pagina(limit, offset)
        conditions = ["auo.articolo_id = %s"]
        params: list[Any] = [str(articolo_id)]
        add_ricerca_full_condition(conditions, params, search, _RICERCA_ARTICOLO_UOM, alias="auo")
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=ARTICOLO_UOM_ORDER_COLUMNS, default_clause=_ARTICOLO_UOM_ORDINE_DEFAULT, tiebreak="auo.id",
        )
        sql = f"""
            SELECT {self._projection()}, COUNT(*) OVER () AS total_count
              FROM catalogo.vw_articoli_uom_operativa_dettaglio auo
             WHERE {" AND ".join(conditions)}
             ORDER BY {ordinamento}
             LIMIT %s OFFSET %s
        """  # noqa: S608 — proiezione da costante, WHERE dal BB add_ricerca_full_condition, ORDER BY da whitelist ARTICOLO_UOM_ORDER_COLUMNS
        return fetch_paged_with_total(sql, [*params, safe_limit, safe_offset])

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
