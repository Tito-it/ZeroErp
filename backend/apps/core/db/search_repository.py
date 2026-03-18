# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository ricerca universale soggetti.
# Chiama le funzioni DB script.fn_search_soggetti_universale
# e script.fn_get_search_detail per la ricerca a due livelli.
# ------------------------------------------------------------

from __future__ import annotations

import json

from apps.core.db._helpers import rows_to_list
from typing import Any

from django.db import connection

# Repository per la ricerca universale soggetti (livello 1 e livello 2).


class SearchRepository:
    """Accesso DB per ricerca universale soggetti e dettaglio per tipo ruolo."""

    # Scopo: Esegue la ricerca universale soggetti (livello 1) tramite
    # script.fn_search_soggetti_universale. Ritorna una riga per soggetto
    # con total_count per paginazione.
    # Perimetro: sola lettura; delega filtri e scope emittente alla funzione DB.
    # Risultato: tuple (list[dict], total_count).
    def search_soggetti(
        self,
        *,
        search_term: str,
        tipo_ruolo_id: int,
        emittente_ids: list[int] | None = None,
        limit: int = 25,
        offset: int = 0,
        order_by: str | None = None,
        order_dir: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        # Converti emittente_ids in array PostgreSQL o None
        pg_emittente_ids = emittente_ids if emittente_ids else None

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT row_to_json(r) AS row_data
                  FROM script.fn_search_soggetti_universale(
                           p_search_term   := %s,
                           p_tipo_ruolo_id := %s,
                           p_emittente_ids := %s,
                           p_limit         := %s,
                           p_offset        := %s,
                           p_order_by      := %s,
                           p_order_dir     := %s
                       ) r
                """,
                [
                    search_term,
                    tipo_ruolo_id,
                    pg_emittente_ids,
                    limit,
                    offset,
                    order_by,
                    order_dir,
                ],
            )
            rows = cursor.fetchall()

        if not rows:
            return [], 0

        results: list[dict[str, Any]] = []
        total_count = 0
        for row in rows:
            data = row[0] if isinstance(row[0], dict) else json.loads(row[0])
            # total_count è presente in ogni riga (COUNT(*) OVER())
            if total_count == 0 and "total_count" in data:
                total_count = data["total_count"]
            # Rimuovi total_count dal risultato esposto
            data.pop("total_count", None)
            results.append(data)

        return results, total_count

    # Scopo: Carica il dettaglio di un soggetto per tipo ruolo (livello 2)
    # tramite script.fn_get_search_detail. Output JSONB con sezioni
    # specifiche per tipo ruolo (righe cliente, fornitore, ecc.).
    # Perimetro: sola lettura; ritorna dict JSONB o None se non trovato.
    def get_search_detail(
        self,
        *,
        soggetto_id: str,
        tipo_ruolo_id: int,
        utility_id: int | None = None,
        emittente_ids: list[int] | None = None,
    ) -> dict[str, Any] | None:
        pg_emittente_ids = emittente_ids if emittente_ids else None

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT script.fn_get_search_detail(
                           p_soggetto_id   := %s::uuid,
                           p_tipo_ruolo_id := %s,
                           p_utility_id    := %s,
                           p_emittente_ids := %s
                       )
                """,
                [soggetto_id, tipo_ruolo_id, utility_id, pg_emittente_ids],
            )
            row = cursor.fetchone()

        if not row or row[0] is None:
            return None

        result = row[0] if isinstance(row[0], dict) else json.loads(row[0])
        return result

    # Scopo: Restituisce i tipi ruolo con ricerca_visibile = true,
    # ordinati per descrizione. Usato dal dropdown della ricerca universale.
    def list_tipi_ruoli_visibili(self) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, codice, descrizione
                  FROM config.tipi_ruoli
                 WHERE ricerca_visibile = true
                 ORDER BY descrizione
                """
            )
            return rows_to_list(cursor)

    # Scopo: Verifica che un tipo_ruolo_id abbia ricerca_visibile = true.
    # Usato dalle view per validare il parametro tipo_ruolo_id.
    def is_tipo_ruolo_visibile(self, tipo_ruolo_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT EXISTS(
                    SELECT 1
                      FROM config.tipi_ruoli
                     WHERE id = %s
                       AND ricerca_visibile = true
                )
                """,
                [tipo_ruolo_id],
            )
            row = cursor.fetchone()
        return bool(row and row[0])
