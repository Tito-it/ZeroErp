# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per la matrice config.tipi_ruolo_tipi_indirizzo.
#        Espone CRUD admin (list/get/create/update) con join descrittivi
#        verso config.tipi_ruoli e config.tipi_indirizzi.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import connection

from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.db._helpers import (
    limiti_pagina,
    RicercaFull,
    add_ricerca_full_condition,
    row_to_dict,
    rows_to_list,
    sql_order_clause,
)
from apps.core.db.sql_write_helpers import (
    execute_dynamic_insert,
    execute_dynamic_update,
)


# Whitelist colonne ammesse per ORDER BY.
_ORDER_COLS: dict[str, str] = {
    "tipo_ruolo_codice": "tr.codice",
    "tipo_ruolo_descrizione": "tr.descrizione",
    "tipo_indirizzo_codice": "ti.codice",
    "tipo_indirizzo_descrizione": "ti.descrizione",
    "obbligatorio": "trti.obbligatorio",
    "attivo": "trti.attivo",
    "valido_dal": "COALESCE(trti.valido_dal, '-infinity'::date)",
    "valido_al": "COALESCE(trti.valido_al, 'infinity'::date)",
    "data_insert": "trti.data_insert",
    "data_update": "trti.data_update",
}

# Colonne SELECT comuni a list e get.
# ⛔ `*_codice` e' il `codice` (mutabile, dell'operatore), MAI il
#    `codice_interno`: fino al 2026-09-23 era `COALESCE(x.codice_interno,
#    x.codice)`, cioe' un codice interno sotto un nome che dice il contrario
#    (linee-guida-sql §6c) — e la ricerca, che cerca su cio' che si mostra,
#    sarebbe finita sul `codice_interno`, che non si usa per cercare (Tid).
_SELECT_COLS = """
    trti.id,
    trti.tipo_ruolo_id,
    tr.codice                              AS tipo_ruolo_codice,
    tr.descrizione                         AS tipo_ruolo_descrizione,
    trti.tipo_indirizzo_id,
    ti.codice                              AS tipo_indirizzo_codice,
    ti.descrizione                         AS tipo_indirizzo_descrizione,
    trti.obbligatorio,
    trti.fallback_tipo_indirizzo_id,
    ti_fb.codice                           AS fallback_codice,
    ti_fb.descrizione                      AS fallback_descrizione,
    trti.attivo,
    trti.valido_dal,
    trti.valido_al,
    trti.data_insert,
    trti.data_update,
    trti.user_insert,
    trti.user_update
"""

# Cosa si PUO' cercare; cosa si cerca lo dice il catalogo (`add_ricerca_full_condition`).
# ⭐ Le stesse espressioni che la `SELECT` proietta con quei nomi.
_RICERCA = RicercaFull("config.tipi_ruolo_tipi_indirizzo", {
    "tipo_ruolo_codice": "tr.codice",
    "tipo_ruolo_descrizione": "tr.descrizione",
    "tipo_indirizzo_codice": "ti.codice",
    "tipo_indirizzo_descrizione": "ti.descrizione",
})

# FROM + JOIN comuni a list e get.
_FROM_JOINS = """
    FROM config.tipi_ruolo_tipi_indirizzo trti
    JOIN config.tipi_ruoli    tr    ON tr.id = trti.tipo_ruolo_id
    JOIN config.tipi_indirizzi ti   ON ti.id = trti.tipo_indirizzo_id
    LEFT JOIN config.tipi_indirizzi ti_fb ON ti_fb.id = trti.fallback_tipo_indirizzo_id
"""


# Colonne modificabili in update (whitelist RIGIDA del BB, 2026-09-26).
_UPDATE_COLS: frozenset[str] = frozenset({
    "attivo", "obbligatorio", "fallback_tipo_indirizzo_id",
})


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
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        order_by: str = "tipo_ruolo_descrizione",
        order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_ORDER_COLS,
            default=_ORDER_COLS["tipo_ruolo_descrizione"],
            tiebreak="trti.id",
        )
        safe_limit, safe_offset = limiti_pagina(limit, offset)

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
        # Soglia della ricerca: la dichiara il catalogo della lista
        # (`ricerca_min_caratteri`), non questo modulo.
        add_ricerca_full_condition(conditions, params, search, _RICERCA)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT COUNT(*) {_FROM_JOINS} {where_clause}",
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
                """,
                params + [safe_limit, safe_offset],
            )
            results = rows_to_list(cursor)

        return results, total_count

    # Scopo: Dettaglio singola riga matrice con join descrittivi.
    def get_matrice(self, record_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {_SELECT_COLS} {_FROM_JOINS} WHERE trti.id = %s",
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
        # ⭐ BB core `execute_dynamic_insert` (2026-09-26). `allowed=None`
        #    perche' le chiavi sono i kwargs LETTERALI di questo metodo;
        #    `skip_none=True` omette gli opzionali None (DEFAULT del DB, come
        #    prima); `valido_dal` e' l'espressione letterale dell'oggi aziendale (`fn_data_operativa()`).
        riga = execute_dynamic_insert(
            "config.tipi_ruolo_tipi_indirizzo",
            {
                "tipo_ruolo_id": tipo_ruolo_id,
                "tipo_indirizzo_id": tipo_indirizzo_id,
                "obbligatorio": obbligatorio,
                "fallback_tipo_indirizzo_id": fallback_tipo_indirizzo_id,
                "attivo": attivo,
            },
            allowed=None,
            skip_none=True,
            espressioni={"valido_dal": "(SELECT script.fn_data_operativa())"},
        )
        return int(riga["id"])

    # Scopo: Aggiorna i campi modificabili di una riga matrice.
    #        FK (tipo_ruolo_id, tipo_indirizzo_id) immutabili: fuori da
    #        `_UPDATE_COLS`, quindi `RuntimeError` se arrivassero (BB
    #        `execute_dynamic_update`, whitelist RIGIDA dal 2026-09-26).
    #        `attivo` trascina `valido_al`: riattivare azzera la fine
    #        validita', disattivare la chiude a oggi.
    # ⭐ La clausola su `valido_al` e' un LITERAL scelto qui dal valore Python
    #    (`extra_set`), non un `CASE WHEN %s`: il BB appende `extra_set` dopo i
    #    SET composti e non ne conosce i parametri. Il valore di `attivo` e' un
    #    bool validato dal service; `bool()` fissa la stessa verita' del `CASE`.
    def update_matrice(self, record_id: int, fields: dict[str, Any]) -> bool:
        extra_set = None
        if "attivo" in fields:
            extra_set = (
                "valido_al = NULL" if bool(fields["attivo"])
                else "valido_al = (SELECT script.fn_data_operativa())"
            )
        return execute_dynamic_update(
            "config.tipi_ruolo_tipi_indirizzo", record_id, fields,
            allowed=_UPDATE_COLS, extra_set=extra_set,
        )

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
                       ti.codice AS codice,
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
