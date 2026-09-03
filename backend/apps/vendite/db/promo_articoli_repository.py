# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per vendite.promo_articoli (CRUD admin).
#        Overlay promo temporale per (articolo, uom) — STADIO 0 del resolver
#        prezzi v5: batte listini e matrice categoria. E' l'unico livello
#        che ammette tipo_variazione PREZZO_FISSO (prezzo assoluto).
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from typing import Any

from django.db import connection

from apps.core.db._helpers import (
    sql_order_clause,
    call_jsonb_fn,
    row_to_dict,
    rows_to_list,
)


# Whitelist colonne ammesse per ORDER BY (SQL injection safe).
_ORDER_COLS: dict[str, str] = {
    "codice": "p.codice",
    "descrizione": "p.descrizione",
    "articolo_codice": "a.codice",
    "articolo_descrizione": "a.descrizione",
    "uom_codice": "um.codice",
    "valido_dal": "p.valido_dal",
    "valido_al": "p.valido_al",
    "attivo": "p.attivo",
    # `tipo_variazione` NON e' in whitelist: nel catalogo la colonna e'
    # `ordinabile=f` (a video e' una cella composita «TIPO: valore», ordinarla
    # per il solo tipo direbbe poco). Tenerla qui sarebbe una capacita' che
    # nessuna colonna puo' richiedere. Se il seed la ribalta a `t`, e' una riga.
    "data_insert": "p.data_insert",
    "data_update": "p.data_update",
}


_SELECT_COLS = """
    p.id,
    p.codice,
    p.descrizione,
    p.articolo_id,
    a.codice AS articolo_codice,
    a.descrizione AS articolo_descrizione,
    p.uom_id,
    um.codice AS uom_codice,
    um.descrizione AS uom_descrizione,
    p.tipo_variazione,
    p.valore_variazione,
    p.valido_dal,
    p.valido_al,
    p.meta,
    p.attivo,
    p.data_insert,
    p.user_insert,
    p.data_update,
    p.user_update
"""


_FROM_JOINS = """
    FROM vendite.promo_articoli p
    JOIN catalogo.articoli a ON a.id = p.articolo_id
    JOIN catalogo.unita_misura um ON um.id = p.uom_id
"""


class PromoArticoliRepository:
    """Accesso DB a `vendite.promo_articoli`."""

    # =================================================================
    # Lista e dettaglio
    # =================================================================

    # Scopo: Lista paginata delle promo con filtri dimensionali e validita'.
    def list_promo(
        self,
        *,
        search: str | None = None,
        attivo: bool | None = None,
        articolo_id: str | None = None,
        uom_id: int | None = None,
        tipo_variazione: str | None = None,
        valid_at: date | None = None,
        limit: int = 25,
        offset: int = 0,
        order_by: str = "valido_dal",
        order_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_ORDER_COLS,
            default=_ORDER_COLS["valido_dal"],
            tiebreak="p.id",
        )
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))

        conditions: list[str] = []
        params: list[Any] = []

        if attivo is not None:
            conditions.append("p.attivo = %s")
            params.append(attivo)
        if articolo_id is not None:
            conditions.append("p.articolo_id = %s::uuid")
            params.append(str(articolo_id))
        if uom_id is not None:
            conditions.append("p.uom_id = %s")
            params.append(uom_id)
        if tipo_variazione is not None:
            conditions.append("p.tipo_variazione = %s")
            params.append(tipo_variazione)
        if valid_at is not None:
            conditions.append("p.validita @> %s::date")
            params.append(valid_at)
        if search:
            conditions.append(
                "(p.codice ILIKE %s OR p.descrizione ILIKE %s "
                "OR a.codice ILIKE %s OR a.descrizione ILIKE %s)"
            )
            like = f"%{search.strip()}%"
            params.extend([like, like, like, like])

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT COUNT(*)
                  {_FROM_JOINS}
                {where_clause}
                """,  # noqa: S608
                params,
            )
            row = cursor.fetchone()
            assert row is not None
            total_count = int(row[0])

            cursor.execute(
                f"""
                SELECT {_SELECT_COLS}
                  {_FROM_JOINS}
                {where_clause}
                 ORDER BY {ordinamento}
                 LIMIT %s OFFSET %s
                """,  # noqa: S608
                params + [safe_limit, safe_offset],
            )
            results = rows_to_list(cursor)

        return results, total_count

    # Scopo: Dettaglio singola promo con display joinati.
    def get_promo(self, record_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT {_SELECT_COLS}
                  {_FROM_JOINS}
                 WHERE p.id = %s
                """,  # noqa: S608
                [record_id],
            )
            return row_to_dict(cursor)

    # Scopo: Capability promo per il detail API (Fase 1.B3 refactor frontend
    #        vendite). Wrapper su `script.fn_capability_promo_articolo` che
    #        ritorna jsonb con stato_temporale (FUTURA/INIZIATA/SCADUTA),
    #        can_update (+ reason), min_valido_dal/al, non_editable_fields.
    #        Modello data-driven: nessuna available_actions (no transizioni
    #        manuali). Blob opaco lato Python: passato al FE intatto.
    #        Ritorna {} se la fn ritorna NULL (promo inesistente — caller deve
    #        aver gia' verificato l'esistenza).
    def get_capabilities(self, record_id: int) -> dict[str, Any]:
        return call_jsonb_fn("script.fn_capability_promo_articolo", record_id)

    # =================================================================
    # Mutazioni
    # =================================================================

    # Scopo: Inserisce una nuova promo usando colonne whitelisted.
    #        `validita` NON scrivibile: trigger la calcola da valido_dal/al.
    def create_promo(self, data: dict[str, Any]) -> int:
        write_cols = (
            "codice",
            "descrizione",
            "articolo_id",
            "uom_id",
            "tipo_variazione",
            "valore_variazione",
            "valido_dal",
            "valido_al",
            "meta",
            "attivo",
        )
        cols: list[str] = []
        vals: list[Any] = []
        placeholders: list[str] = []
        for col in write_cols:
            if col in data:
                cols.append(col)
                # articolo_id e' uuid, serve cast esplicito.
                placeholders.append("%s::uuid" if col == "articolo_id" else "%s")
                vals.append(data[col])
        sql = f"""
            INSERT INTO vendite.promo_articoli ({", ".join(cols)})
            VALUES ({", ".join(placeholders)})
            RETURNING id
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: Aggiorna una promo sui soli campi forniti. `codice`, `articolo_id`,
    #        `uom_id` sono immutabili lato service. Il repo non impone: consente
    #        al service di scegliere la policy.
    def update_promo(self, record_id: int, data: dict[str, Any]) -> bool:
        write_cols = (
            "descrizione",
            "tipo_variazione",
            "valore_variazione",
            "valido_dal",
            "valido_al",
            "meta",
            "attivo",
        )
        set_parts: list[str] = []
        vals: list[Any] = []
        for col in write_cols:
            if col in data:
                set_parts.append(f"{col} = %s")
                vals.append(data[col])
        if not set_parts:
            return False
        vals.append(record_id)
        sql = f"""
            UPDATE vendite.promo_articoli
               SET {", ".join(set_parts)}
             WHERE id = %s
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            return cursor.rowcount > 0
