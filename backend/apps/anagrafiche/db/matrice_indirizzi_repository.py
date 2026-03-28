# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per gestione matrice indirizzi per ruolo.
#        CRUD config.tipi_ruolo_tipi_indirizzo, lista con JOIN
#        descrizioni ruolo/tipo indirizzo/fallback.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import connection

from apps.anagrafiche.db._helpers import extract_paginated
from apps.core.db._helpers import row_to_dict


_ORDER_COLS = {
    "tipo_ruolo_descrizione", "tipo_indirizzo_descrizione",
    "obbligatorio", "attivo", "valido_dal",
}


class MatriceIndirizziRepository:
    """Accesso DB per config.tipi_ruolo_tipi_indirizzo."""

    # =================================================================
    # Lista
    # =================================================================

    # Scopo: Lista paginata matrice con join descrizioni ruolo, tipo indirizzo e fallback.
    def list_matrice(
        self, *, tipo_ruolo_id: int | None = None,
        search: str | None = None,
        limit: int = 25, offset: int = 0,
        order_by: str = "tipo_ruolo_descrizione", order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        order_col = order_by if order_by in _ORDER_COLS else "tipo_ruolo_descrizione"
        direction = "DESC" if order_dir and order_dir.upper() == "DESC" else "ASC"
        search_pattern = f"%{search.strip()}%" if search and search.strip() else None
        sql = f"""
            SELECT m.id,
                   m.tipo_ruolo_id,
                   tr.descrizione          AS tipo_ruolo_descrizione,
                   tr.codice_interno       AS tipo_ruolo_codice,
                   m.tipo_indirizzo_id,
                   ti.descrizione          AS tipo_indirizzo_descrizione,
                   ti.codice_interno       AS tipo_indirizzo_codice,
                   m.obbligatorio,
                   m.fallback_tipo_indirizzo_id,
                   ti_fb.descrizione       AS fallback_descrizione,
                   ti_fb.codice_interno    AS fallback_codice,
                   m.attivo,
                   m.valido_dal,
                   m.valido_al,
                   m.data_insert,
                   m.data_update,
                   COUNT(*) OVER ()        AS total_count
              FROM config.tipi_ruolo_tipi_indirizzo m
              JOIN config.tipi_ruoli tr         ON tr.id = m.tipo_ruolo_id
              JOIN config.tipi_indirizzi ti     ON ti.id = m.tipo_indirizzo_id
              LEFT JOIN config.tipi_indirizzi ti_fb ON ti_fb.id = m.fallback_tipo_indirizzo_id
             WHERE (%s::integer IS NULL OR m.tipo_ruolo_id = %s)
               AND (%s::text IS NULL OR (
                       tr.descrizione ILIKE %s
                    OR ti.descrizione ILIKE %s
                   ))
             ORDER BY {order_col} {direction}, m.id
             LIMIT %s OFFSET %s
        """  # noqa: S608
        params: list[Any] = [
            tipo_ruolo_id, tipo_ruolo_id,
            search_pattern, search_pattern, search_pattern,
            limit, offset,
        ]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return extract_paginated(cursor)

    # =================================================================
    # Dettaglio
    # =================================================================

    # Scopo: Dettaglio singola regola con join descrizioni.
    def get_regola(self, regola_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT m.id,
                   m.tipo_ruolo_id,
                   tr.descrizione          AS tipo_ruolo_descrizione,
                   tr.codice_interno       AS tipo_ruolo_codice,
                   m.tipo_indirizzo_id,
                   ti.descrizione          AS tipo_indirizzo_descrizione,
                   ti.codice_interno       AS tipo_indirizzo_codice,
                   m.obbligatorio,
                   m.fallback_tipo_indirizzo_id,
                   ti_fb.descrizione       AS fallback_descrizione,
                   ti_fb.codice_interno    AS fallback_codice,
                   m.attivo,
                   m.valido_dal,
                   m.valido_al,
                   m.data_insert,
                   m.data_update
              FROM config.tipi_ruolo_tipi_indirizzo m
              JOIN config.tipi_ruoli tr         ON tr.id = m.tipo_ruolo_id
              JOIN config.tipi_indirizzi ti     ON ti.id = m.tipo_indirizzo_id
              LEFT JOIN config.tipi_indirizzi ti_fb ON ti_fb.id = m.fallback_tipo_indirizzo_id
             WHERE m.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [regola_id])
            return row_to_dict(cursor)

    # =================================================================
    # Creazione
    # =================================================================

    # Scopo: Crea regola matrice con valido_dal = CURRENT_DATE.
    def create_regola(self, **kwargs: Any) -> int:
        sql = """
            INSERT INTO config.tipi_ruolo_tipi_indirizzo
                   (tipo_ruolo_id, tipo_indirizzo_id, obbligatorio,
                    fallback_tipo_indirizzo_id, valido_dal, attivo)
            VALUES (%s, %s, %s, %s, CURRENT_DATE, true)
            RETURNING id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                kwargs["tipo_ruolo_id"],
                kwargs["tipo_indirizzo_id"],
                kwargs.get("obbligatorio", False),
                kwargs.get("fallback_tipo_indirizzo_id"),
            ])
            row = cursor.fetchone()
            assert row is not None
            return row[0]

    # =================================================================
    # Aggiornamento
    # =================================================================

    _UPDATE_ALLOWED = {
        "obbligatorio", "fallback_tipo_indirizzo_id", "attivo",
    }

    # Scopo: Aggiorna regola matrice (delta update).
    #        Logica attivo: se attivo passa a false → valido_al = CURRENT_DATE.
    #        Se attivo passa a true → valido_al = NULL.
    def update_regola(self, regola_id: int, data: dict[str, Any]) -> bool:
        fields = [(k, v) for k, v in data.items() if k in self._UPDATE_ALLOWED]
        if not fields:
            return False

        # Gestione attivo → valido_al (espressioni SQL senza parametri)
        attivo_val = data.get("attivo")
        extra_sets = []
        if attivo_val is not None:
            if attivo_val is False:
                extra_sets.append("valido_al = CURRENT_DATE")
            else:
                extra_sets.append("valido_al = NULL")

        set_parts = [f"{f[0]} = %s" for f in fields]
        values: list[Any] = [f[1] for f in fields]
        set_parts.extend(extra_sets)
        values.append(regola_id)

        sql = f"UPDATE config.tipi_ruolo_tipi_indirizzo SET {', '.join(set_parts)} WHERE id = %s"  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, values)
            return cursor.rowcount > 0
