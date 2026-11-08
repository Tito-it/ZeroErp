# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per la matrice config.utilities_tipi_ruolo.
#        Espone CRUD admin (list/get/create/update_attivo) con join descrittivi
#        verso config.utilities e config.tipi_ruoli, piu' la lookup di utilizzo
#        della singola riga di matrice da parte degli emittenti fiscali.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import connection

from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.db._helpers import (
    limiti_pagina,
    RicercaFull,
    add_ricerca_full_condition,
    fetch_paged_with_total,
    row_to_dict,
    rows_to_list,
    sql_order_clause,
)

# Cosa si PUO' cercare; cosa si cerca lo dice il catalogo (`add_ricerca_full_condition`).
_RICERCA = RicercaFull("config.utilities_tipi_ruolo", {
    "utility_codice": "u.codice",
    "utility_descrizione": "u.descrizione",
    "tipo_ruolo_codice": "tr.codice",
    "tipo_ruolo_descrizione": "tr.descrizione",
})


# Whitelist colonne ammesse per ORDER BY: protegge da SQL injection sul
# parametro order_by ricevuto dal frontend.
_ORDER_COLS: dict[str, str] = {
    "utility_codice": "u.codice",
    "utility_descrizione": "u.descrizione",
    "tipo_ruolo_codice": "tr.codice",
    "tipo_ruolo_descrizione": "tr.descrizione",
    "attivo": "utr.attivo",
    "data_insert": "utr.data_insert",
    "data_update": "utr.data_update",
}


# Lista `config.utilities_tipi_ruolo_usage` (lista 86, tab «Utilizzo»):
# whitelist ORDER BY chiavata sul `campo_sorgente` del catalogo, valore =
# l'espressione che la SELECT proietta con quel nome (brief-db-liste-datatable-
# grezze §4.1 riga 4). Lista `multi_emittente`: ogni riga E' un emittente, e il
# codice e la ragione sociale lo dicono da se'.
USAGE_ORDER_COLS: dict[str, str] = {
    "emittente_codice": "ef.codice",
    "emittente_descrizione": "s_ef.ragione_sociale_completa",
    "emittente_attivo": "ef.attivo",
    "override_attivo": "efu.attivo",
}

# Cosa si PUO' cercare nella lista 86: codice e ragione sociale dell'emittente
# (lista_colonna 962-963, `ricercabile_full = t`).
_RICERCA_USAGE = RicercaFull("config.utilities_tipi_ruolo_usage", {
    "emittente_codice": "ef.codice",
    "emittente_descrizione": "s_ef.ragione_sociale_completa",
})


# Codice interno del tipo_ruolo "Emittente Fiscale", usato per filtrare
# le query di usage. Estratto come costante per evitare hardcoding duplicato
# nelle query SQL.
_RUOLO_EF_CODICE = "EF"


# Frammento SQL FROM+JOIN+WHERE della lista usage emittenti fiscali: lo
# condividono la pagina e il ripiego del conteggio di `fetch_paged_with_total`,
# cosi' i due non possono contare perimetri diversi.
# Il soggetto dell'emittente serve alla ragione sociale a video (e alla ricerca
# e all'ordinamento su di essa): i due JOIN sono 1:1 su PK
# (`emittenti_fiscali.soggetto_ruolo_id` e' NOT NULL + UNIQUE) e non alterano
# la cardinalita' del conteggio.
_USAGE_FROM_WHERE = """
    FROM config.utilities_tipi_ruolo utr
    JOIN config.tipi_ruoli tr
      ON tr.id = utr.tipo_ruolo_id
    JOIN anagrafiche.emittenti_fiscali_utilities efu
      ON efu.utility_id = utr.utility_id
    JOIN anagrafiche.emittenti_fiscali ef
      ON ef.soggetto_ruolo_id = efu.emittente_soggetto_ruolo_id
    JOIN anagrafiche.soggetti_ruoli sr_ef
      ON sr_ef.id = ef.soggetto_ruolo_id
    JOIN anagrafiche.soggetti s_ef
      ON s_ef.id = sr_ef.soggetto_id
   WHERE utr.id = %s
     AND tr.codice_interno = %s
"""


class UtilitiesTipiRuoloRepository:
    """Accesso DB alla matrice utilities x tipi_ruolo."""

    # =================================================================
    # Lista e dettaglio
    # =================================================================

    # Scopo: Lista paginata della matrice utility/tipo_ruolo con join
    #        descrittivi e filtri opzionali. Restituisce (results, total_count).
    def list_matrice(
        self,
        *,
        search: str | None = None,
        attivo: bool | None = None,
        utility_id: int | None = None,
        tipo_ruolo_id: int | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        order_by: str = "utility_descrizione",
        order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_ORDER_COLS,
            default=_ORDER_COLS["utility_descrizione"],
            tiebreak="utr.id",
        )
        safe_limit, safe_offset = limiti_pagina(limit, offset)

        conditions: list[str] = []
        params: list[Any] = []

        if attivo is not None:
            conditions.append("utr.attivo = %s")
            params.append(attivo)
        if utility_id is not None:
            conditions.append("utr.utility_id = %s")
            params.append(utility_id)
        if tipo_ruolo_id is not None:
            conditions.append("utr.tipo_ruolo_id = %s")
            params.append(tipo_ruolo_id)
        # Soglia della ricerca: la dichiara il catalogo della lista
        # (`ricerca_min_caratteri`), non questo modulo.
        add_ricerca_full_condition(conditions, params, search, _RICERCA)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        select_cols = """
            utr.id,
            utr.utility_id,
            u.codice       AS utility_codice,
            u.descrizione  AS utility_descrizione,
            utr.tipo_ruolo_id,
            tr.codice      AS tipo_ruolo_codice,
            tr.descrizione AS tipo_ruolo_descrizione,
            utr.attivo,
            utr.data_insert,
            utr.data_update,
            utr.user_insert,
            utr.user_update
        """

        with connection.cursor() as cursor:
            # Conteggio totale per envelope paginato
            cursor.execute(
                f"""
                SELECT COUNT(*)
                  FROM config.utilities_tipi_ruolo utr
                  JOIN config.utilities  u  ON u.id  = utr.utility_id
                  JOIN config.tipi_ruoli tr ON tr.id = utr.tipo_ruolo_id
                {where_clause}
                """,  # noqa: S608
                params,
            )
            row = cursor.fetchone()
            assert row is not None
            total_count = int(row[0])

            cursor.execute(
                f"""
                SELECT {select_cols}
                  FROM config.utilities_tipi_ruolo utr
                  JOIN config.utilities  u  ON u.id  = utr.utility_id
                  JOIN config.tipi_ruoli tr ON tr.id = utr.tipo_ruolo_id
                {where_clause}
                ORDER BY {ordinamento}
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
                """
                SELECT utr.id,
                       utr.utility_id,
                       u.codice       AS utility_codice,
                       u.descrizione  AS utility_descrizione,
                       utr.tipo_ruolo_id,
                       tr.codice      AS tipo_ruolo_codice,
                       tr.descrizione AS tipo_ruolo_descrizione,
                       utr.attivo,
                       utr.data_insert,
                       utr.data_update,
                       utr.user_insert,
                       utr.user_update
                  FROM config.utilities_tipi_ruolo utr
                  JOIN config.utilities  u  ON u.id  = utr.utility_id
                  JOIN config.tipi_ruoli tr ON tr.id = utr.tipo_ruolo_id
                 WHERE utr.id = %s
                """,
                [record_id],
            )
            return row_to_dict(cursor)

    # =================================================================
    # Mutazioni
    # =================================================================

    # Scopo: Inserisce una nuova coppia (utility, tipo_ruolo) in matrice.
    #        Eventuale UNIQUE violation viene propagata come IntegrityError
    #        e gestita dal service.
    def create_matrice(
        self,
        *,
        utility_id: int,
        tipo_ruolo_id: int,
        attivo: bool | None,
    ) -> int:
        cols = ["utility_id", "tipo_ruolo_id"]
        vals: list[Any] = [utility_id, tipo_ruolo_id]
        if attivo is not None:
            cols.append("attivo")
            vals.append(attivo)
        placeholders = ["%s"] * len(cols)
        sql = f"""
            INSERT INTO config.utilities_tipi_ruolo ({", ".join(cols)})
            VALUES ({", ".join(placeholders)})
            RETURNING id
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: Aggiorna il flag attivo di una riga matrice.
    #        Le FK (utility_id, tipo_ruolo_id) sono immutabili per scelta di
    #        progetto: se cambia la coppia bisogna creare una nuova riga e
    #        disattivare la precedente.
    def update_matrice_attivo(self, record_id: int, attivo: bool) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE config.utilities_tipi_ruolo
                   SET attivo = %s
                 WHERE id = %s
                """,
                [attivo, record_id],
            )
            return cursor.rowcount > 0

    # =================================================================
    # Utilizzo: emittenti fiscali con override per la stessa coppia
    # =================================================================

    # Scopo: la lista `config.utilities_tipi_ruolo_usage` (lista 86, tab
    #        «Utilizzo» del drawer della matrice): gli emittenti fiscali che
    #        hanno gia' configurato un override
    #        (anagrafiche.emittenti_fiscali_utilities) per la stessa utility
    #        della riga matrice indicata. Significativa solo se la riga e' del
    #        ruolo EF (codice_interno o codice del tipo_ruolo); per altri ruoli
    #        la lista e' vuota. Restituisce (results, total_count).
    #        Riferimento: feedback_slot_override_matrix.md (pattern slot/override).
    #
    # ⭐ Pagina e conteggio in UNA valutazione (`fetch_paged_with_total`,
    #    `COUNT(*) OVER ()`): fino al 2026-09-27 erano due query
    #    (`count_emittenti_usage` + la pagina) sul frammento condiviso — il
    #    frammento resta, e ora serve la pagina e il ripiego del conteggio.
    # ⭐ `emittente_descrizione` porta la ragione sociale del SOGGETTO
    #    dell'emittente, non `emittenti_fiscali.descrizione` (etichetta interna
    #    divergente, in via di eliminazione — brief
    #    `brief-emittente-ragione-sociale-dal-soggetto.md`).
    # ⚠️ Ordine di partenza = quello storico del tab (ragione sociale, poi
    #    codice): lo porta `default_clause`, perche' e' a DUE criteri e non
    #    una colonna sola.
    def list_emittenti_usage(
        self,
        record_id: int,
        *,
        search: str | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit, safe_offset = limiti_pagina(limit, offset)
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=USAGE_ORDER_COLS,
            default_clause="s_ef.ragione_sociale_completa ASC, ef.codice ASC",
            tiebreak="ef.id",
        )
        conditions: list[str] = []
        params: list[Any] = [record_id, _RUOLO_EF_CODICE]
        add_ricerca_full_condition(conditions, params, search, _RICERCA_USAGE)
        # ⚠️ Il frammento finisce col suo WHERE: la ricerca si ACCODA in AND.
        from_where = _USAGE_FROM_WHERE + "".join(f" AND {c}" for c in conditions)
        return fetch_paged_with_total(
            f"""
            SELECT ef.id                         AS emittente_id,
                   ef.codice                     AS emittente_codice,
                   s_ef.ragione_sociale_completa AS emittente_descrizione,
                   ef.attivo                     AS emittente_attivo,
                   efu.id                        AS override_id,
                   efu.attivo                    AS override_attivo,
                   COUNT(*) OVER ()              AS total_count
            {from_where}
             ORDER BY {ordinamento}
             LIMIT %s OFFSET %s
            """,  # ORDER BY da sql_order_clause su whitelist USAGE_ORDER_COLS, WHERE da frammento costante + add_ricerca_full_condition, valori come parametri
            params + [safe_limit, safe_offset],
            fallback_count_sql=f"SELECT COUNT(*) {from_where}",  # stesso FROM/WHERE della pagina
            fallback_params=params,
            offset=safe_offset,
        )
