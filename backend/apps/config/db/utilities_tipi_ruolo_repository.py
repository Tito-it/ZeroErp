# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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

from apps.core.db._helpers import (
    RicercaFull,
    add_ricerca_full_condition,
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


# Codice interno del tipo_ruolo "Emittente Fiscale", usato per filtrare
# le query di usage. Estratto come costante per evitare hardcoding duplicato
# nelle query SQL.
_RUOLO_EF_CODICE = "EF"


# Frammento SQL FROM+JOIN+WHERE comune alle query usage emittenti fiscali.
# Estratto per garantire allineamento tra count e list (evita drift in caso
# di refactor di una sola delle due).
# Il soggetto dell'emittente serve solo alla list (ragione sociale a video), ma
# sta qui perche' il frammento e' condiviso: i due JOIN sono 1:1 su PK
# (`emittenti_fiscali.soggetto_ruolo_id` e' NOT NULL + UNIQUE) e non alterano
# la cardinalita' della count.
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
     AND COALESCE(tr.codice_interno, tr.codice) = %s
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
        limit: int = 25,
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
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))

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
        # Tabella di configurazione: la ricerca parte da un carattere (Tid, 2026-09-23).
        add_ricerca_full_condition(conditions, params, search, _RICERCA, min_caratteri=1)

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

    # Scopo: Conta gli emittenti fiscali che hanno gia' configurato un
    #        override (anagrafiche.emittenti_fiscali_utilities) per la stessa
    #        utility della riga matrice indicata. La query e' significativa
    #        solo se la matrice e' per il ruolo EF (codice_interno o codice
    #        del tipo_ruolo); per altri ruoli ritorna sempre 0.
    #        Riferimento: feedback_slot_override_matrix.md (pattern slot/override).
    def count_emittenti_usage(self, record_id: int) -> int:
        sql = f"SELECT COUNT(*) {_USAGE_FROM_WHERE}"  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, [record_id, _RUOLO_EF_CODICE])
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: Lista paginata degli emittenti fiscali che usano la matrice
    #        indicata (override esistente). Filtra sul ruolo EF. Restituisce
    #        (results, total_count).
    def list_emittenti_usage(
        self,
        record_id: int,
        *,
        limit: int = 25,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))
        total_count = self.count_emittenti_usage(record_id)
        # `emittente_descrizione` porta la ragione sociale del SOGGETTO
        # dell'emittente, non `emittenti_fiscali.descrizione` (etichetta interna
        # divergente, in via di eliminazione — brief
        # `brief-emittente-ragione-sociale-dal-soggetto.md`). L'alias resta
        # invariato: il FE non si accorge del cambio di sorgente.
        sql = f"""
            SELECT ef.id                         AS emittente_id,
                   ef.codice                     AS emittente_codice,
                   s_ef.ragione_sociale_completa AS emittente_descrizione,
                   ef.attivo                     AS emittente_attivo,
                   efu.id                        AS override_id,
                   efu.attivo                    AS override_attivo
            {_USAGE_FROM_WHERE}
             ORDER BY s_ef.ragione_sociale_completa ASC, ef.codice ASC
             LIMIT %s OFFSET %s
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(
                sql,
                [record_id, _RUOLO_EF_CODICE, safe_limit, safe_offset],
            )
            results = rows_to_list(cursor)
        return results, total_count
