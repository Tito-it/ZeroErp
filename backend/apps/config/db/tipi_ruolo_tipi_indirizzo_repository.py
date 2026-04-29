# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per la matrice config.tipi_ruolo_tipi_indirizzo.
#        Espone CRUD admin (list/get/create/update) con join descrittivi
#        verso config.tipi_ruoli e config.tipi_indirizzi.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import connection

from apps.core.db._helpers import row_to_dict, rows_to_list


# Whitelist colonne ammesse per ORDER BY.
_ORDER_COLS: dict[str, str] = {
    "tipo_ruolo_codice": "tr.codice",
    "tipo_ruolo_descrizione": "tr.descrizione",
    "tipo_indirizzo_codice": "ti.codice",
    "tipo_indirizzo_descrizione": "ti.descrizione",
    "obbligatorio": "trti.obbligatorio",
    "attivo": "trti.attivo",
    "data_insert": "trti.data_insert",
    "data_update": "trti.data_update",
}

# Colonne SELECT comuni a list e get.
_SELECT_COLS = """
    trti.id,
    trti.tipo_ruolo_id,
    COALESCE(tr.codice_interno, tr.codice) AS tipo_ruolo_codice,
    tr.descrizione                         AS tipo_ruolo_descrizione,
    trti.tipo_indirizzo_id,
    COALESCE(ti.codice_interno, ti.codice) AS tipo_indirizzo_codice,
    ti.descrizione                         AS tipo_indirizzo_descrizione,
    trti.obbligatorio,
    trti.fallback_tipo_indirizzo_id,
    COALESCE(ti_fb.codice_interno, ti_fb.codice) AS fallback_codice,
    ti_fb.descrizione                             AS fallback_descrizione,
    trti.attivo,
    trti.data_insert,
    trti.data_update,
    trti.user_insert,
    trti.user_update
"""

# FROM + JOIN comuni a list e get.
_FROM_JOINS = """
    FROM config.tipi_ruolo_tipi_indirizzo trti
    JOIN config.tipi_ruoli    tr    ON tr.id = trti.tipo_ruolo_id
    JOIN config.tipi_indirizzi ti   ON ti.id = trti.tipo_indirizzo_id
    LEFT JOIN config.tipi_indirizzi ti_fb ON ti_fb.id = trti.fallback_tipo_indirizzo_id
"""


class TipiRuoloTipiIndirizzoRepository:
    """Accesso DB alla matrice tipi_ruolo x tipi_indirizzo."""

    # =================================================================
    # Lista e dettaglio
    # =================================================================

    # Scopo: Lista paginata della matrice con join descrittivi e filtri.
    def list_matrice(
        self,
        *,
        search: str | None = None,
        attivo: bool | None = None,
        tipo_ruolo_id: int | None = None,
        tipo_indirizzo_id: int | None = None,
        limit: int = 25,
        offset: int = 0,
        order_by: str = "tipo_ruolo_descrizione",
        order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        order_column = _ORDER_COLS.get(order_by, _ORDER_COLS["tipo_ruolo_descrizione"])
        direction = "DESC" if order_dir and order_dir.lower() == "desc" else "ASC"
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))

        conditions: list[str] = []
        params: list[Any] = []

        if attivo is not None:
            conditions.append("trti.attivo = %s")
            params.append(attivo)
        if tipo_ruolo_id is not None:
            conditions.append("trti.tipo_ruolo_id = %s")
            params.append(tipo_ruolo_id)
        if tipo_indirizzo_id is not None:
            conditions.append("trti.tipo_indirizzo_id = %s")
            params.append(tipo_indirizzo_id)
        if search:
            conditions.append(
                "(tr.codice ILIKE %s OR tr.descrizione ILIKE %s "
                "OR ti.codice ILIKE %s OR ti.descrizione ILIKE %s)"
            )
            like = f"%{search.strip()}%"
            params.extend([like, like, like, like])

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT COUNT(*) {_FROM_JOINS} {where_clause}",  # noqa: S608
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
                ORDER BY {order_column} {direction}, trti.id ASC
                LIMIT %s OFFSET %s
                """,  # noqa: S608
                params + [safe_limit, safe_offset],
            )
            results = rows_to_list(cursor)

        return results, total_count

    # Scopo: Dettaglio singola riga matrice con join descrittivi.
    def get_matrice(self, record_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {_SELECT_COLS} {_FROM_JOINS} WHERE trti.id = %s",  # noqa: S608
                [record_id],
            )
            return row_to_dict(cursor)

    # =================================================================
    # Mutazioni
    # =================================================================

    # Scopo: Inserisce una nuova coppia (tipo_ruolo, tipo_indirizzo).
    def create_matrice(
        self,
        *,
        tipo_ruolo_id: int,
        tipo_indirizzo_id: int,
        obbligatorio: bool | None = None,
        fallback_tipo_indirizzo_id: int | None = None,
        attivo: bool | None = None,
    ) -> int:
        cols = ["tipo_ruolo_id", "tipo_indirizzo_id"]
        vals: list[Any] = [tipo_ruolo_id, tipo_indirizzo_id]
        if obbligatorio is not None:
            cols.append("obbligatorio")
            vals.append(obbligatorio)
        if fallback_tipo_indirizzo_id is not None:
            cols.append("fallback_tipo_indirizzo_id")
            vals.append(fallback_tipo_indirizzo_id)
        if attivo is not None:
            cols.append("attivo")
            vals.append(attivo)
        placeholders = ["%s"] * len(cols)
        sql = f"""
            INSERT INTO config.tipi_ruolo_tipi_indirizzo ({", ".join(cols)})
            VALUES ({", ".join(placeholders)})
            RETURNING id
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: Aggiorna i campi modificabili di una riga matrice.
    #        FK (tipo_ruolo_id, tipo_indirizzo_id) immutabili.
    def update_matrice(self, record_id: int, fields: dict[str, Any]) -> bool:
        if not fields:
            return False
        set_clauses = [f"{k} = %s" for k in fields]
        vals = list(fields.values()) + [record_id]
        sql = f"""
            UPDATE config.tipi_ruolo_tipi_indirizzo
               SET {", ".join(set_clauses)}
             WHERE id = %s
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            return cursor.rowcount > 0

    # Scopo: Sotto-matrice attiva del ruolo per il calcolo `fallback_options`
    #        (Fase 4 — A10). Ritorna tutte le righe attive del ruolo con i
    #        loro fallback, cosi' il service puo' costruire il grafo dei
    #        fallback (DFS) ed escludere candidati in catena con la riga
    #        corrente. Una sola query per detail, niente N+1.
    def list_fallback_chain_for_ruolo(self, tipo_ruolo_id: int) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT trti.tipo_indirizzo_id,
                       COALESCE(ti.codice_interno, ti.codice) AS codice,
                       ti.descrizione,
                       trti.fallback_tipo_indirizzo_id
                  FROM config.tipi_ruolo_tipi_indirizzo trti
                  JOIN config.tipi_indirizzi ti ON ti.id = trti.tipo_indirizzo_id
                 WHERE trti.tipo_ruolo_id = %s
                   AND trti.attivo = true
                 ORDER BY ti.descrizione, trti.tipo_indirizzo_id
                """,
                [tipo_ruolo_id],
            )
            return rows_to_list(cursor)
