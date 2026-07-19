# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per anagrafiche.categorie_clienti (CRUD admin).
#        Lookup semplice: codice/descrizione + flag partecipa_promo e
#        ordinamento UI. Nessun join con altre tabelle: la matrice
#        categoria -> listino vive in categorie_clienti_listini.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import connection

from apps.core.db._helpers import row_to_dict, rows_to_list, sql_order_direction


# Whitelist colonne ammesse per ORDER BY: protegge da SQL injection sul
# parametro order_by ricevuto dal frontend.
_ORDER_COLS: dict[str, str] = {
    "codice": "cc.codice",
    "descrizione": "cc.descrizione",
    "ordinamento": "cc.ordinamento",
    "partecipa_promo": "cc.partecipa_promo",
    "attivo": "cc.attivo",
    "data_insert": "cc.data_insert",
    "data_update": "cc.data_update",
}


_SELECT_COLS = """
    cc.id,
    cc.codice,
    cc.descrizione,
    cc.partecipa_promo,
    cc.ordinamento,
    cc.meta,
    cc.attivo,
    cc.data_insert,
    cc.user_insert,
    cc.data_update,
    cc.user_update
"""


class CategorieClientiRepository:
    """Accesso DB a anagrafiche.categorie_clienti."""

    # =================================================================
    # Lista e dettaglio
    # =================================================================

    # Scopo: Lista paginata delle categorie cliente con filtri opzionali.
    #        Restituisce (results, total_count) per envelope paginato.
    def list_categorie(
        self,
        *,
        search: str | None = None,
        attivo: bool | None = None,
        partecipa_promo: bool | None = None,
        limit: int = 25,
        offset: int = 0,
        order_by: str = "ordinamento",
        order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        order_column = _ORDER_COLS.get(order_by, _ORDER_COLS["ordinamento"])
        direction = sql_order_direction(order_dir)
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))

        conditions: list[str] = []
        params: list[Any] = []

        if attivo is not None:
            conditions.append("cc.attivo = %s")
            params.append(attivo)
        if partecipa_promo is not None:
            conditions.append("cc.partecipa_promo = %s")
            params.append(partecipa_promo)
        if search:
            conditions.append(
                "(cc.codice ILIKE %s OR cc.descrizione ILIKE %s)"
            )
            like = f"%{search.strip()}%"
            params.extend([like, like])

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        with connection.cursor() as cursor:
            # Count totale per envelope paginato.
            cursor.execute(
                f"""
                SELECT COUNT(*)
                  FROM anagrafiche.categorie_clienti cc
                {where_clause}
                """,  # noqa: S608
                params,
            )
            row = cursor.fetchone()
            assert row is not None
            total_count = int(row[0])

            # Tiebreaker su id per paginazione deterministica (regola progetto).
            cursor.execute(
                f"""
                SELECT {_SELECT_COLS}
                  FROM anagrafiche.categorie_clienti cc
                {where_clause}
                 ORDER BY {order_column} {direction}, cc.id ASC
                 LIMIT %s OFFSET %s
                """,  # noqa: S608
                params + [safe_limit, safe_offset],
            )
            results = rows_to_list(cursor)

        return results, total_count

    # Scopo: Dettaglio singola categoria.
    def get_categoria(self, record_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT {_SELECT_COLS}
                  FROM anagrafiche.categorie_clienti cc
                 WHERE cc.id = %s
                """,  # noqa: S608
                [record_id],
            )
            return row_to_dict(cursor)

    # =================================================================
    # Mutazioni
    # =================================================================

    # Scopo: Inserisce una nuova categoria cliente usando solo colonne whitelisted.
    #        Eventuali violazioni UNIQUE/CHECK vengono propagate al service.
    def create_categoria(self, data: dict[str, Any]) -> int:
        # Colonne DDL ammesse in create. user_* e data_* sono gestite dal DB.
        write_cols = ("codice", "descrizione", "partecipa_promo", "ordinamento", "meta", "attivo")
        cols: list[str] = []
        vals: list[Any] = []
        for col in write_cols:
            if col in data:
                cols.append(col)
                vals.append(data[col])
        # `codice_interno` e' la chiave logica IMMUTABILE (NOT NULL, lockata,
        # nessun default DB): non e' esposta dall'API CRUD e qui il `codice` e'
        # gia' immutabile, quindi i due coincidono. Va valorizzata = codice alla
        # create, altrimenti l'INSERT viola NOT NULL (colonna aggiunta dal DB
        # in 20260629-06, vedi analisi-hardcoded-codice.md §4 #3).
        if "codice" in data:
            cols.append("codice_interno")
            vals.append(data["codice"])
        placeholders = ["%s"] * len(cols)
        sql = f"""
            INSERT INTO anagrafiche.categorie_clienti ({", ".join(cols)})
            VALUES ({", ".join(placeholders)})
            RETURNING id
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: Aggiorna una categoria sui soli campi forniti nel payload.
    #        Il codice e' immutabile a livello service, non a livello repository.
    def update_categoria(self, record_id: int, data: dict[str, Any]) -> bool:
        write_cols = ("descrizione", "partecipa_promo", "ordinamento", "meta", "attivo")
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
            UPDATE anagrafiche.categorie_clienti
               SET {", ".join(set_parts)}
             WHERE id = %s
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            return cursor.rowcount > 0
