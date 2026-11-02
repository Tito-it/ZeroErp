# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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

from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.db._helpers import (
    limiti_pagina,
    RicercaFull,
    add_ricerca_full_condition,
    row_to_dict,
    rows_to_list,
    sql_order_clause,
)
from apps.core.db.sql_write_helpers import execute_dynamic_insert, execute_dynamic_update


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


# Cosa si PUO' cercare; cosa si cerca lo dice il catalogo (`add_ricerca_full_condition`).
_RICERCA = RicercaFull("anagrafiche.categorie_clienti", ("codice", "descrizione"))


# Colonne DDL scrivibili (whitelist RIGIDA dei BB di scrittura, 2026-09-26).
# user_* e data_* sono gestite dal DB; `codice` solo in create (immutabile).
_CREATE_COLS: frozenset[str] = frozenset({
    "codice", "descrizione", "partecipa_promo", "ordinamento", "meta", "attivo",
})
_UPDATE_COLS: frozenset[str] = _CREATE_COLS - {"codice"}


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
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        order_by: str = "ordinamento",
        order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_ORDER_COLS,
            default=_ORDER_COLS["ordinamento"],
            tiebreak="cc.id",
        )
        safe_limit, safe_offset = limiti_pagina(limit, offset)

        conditions: list[str] = []
        params: list[Any] = []

        if attivo is not None:
            conditions.append("cc.attivo = %s")
            params.append(attivo)
        if partecipa_promo is not None:
            conditions.append("cc.partecipa_promo = %s")
            params.append(partecipa_promo)
        # Soglia della ricerca: la dichiara il catalogo della lista
        # (`ricerca_min_caratteri`), non questo modulo.
        add_ricerca_full_condition(conditions, params, search, _RICERCA, alias="cc")

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
                 ORDER BY {ordinamento}
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
    #        BB `execute_dynamic_insert` (2026-09-26): whitelist RIGIDA
    #        `_CREATE_COLS` (prima una chiave fuori lista era scartata in
    #        silenzio; le chiavi le valida il service), `meta` dict -> `::jsonb`.
    #        None scrive NULL (`skip_none` spento): chi vuole il default DB non
    #        manda la chiave, come prima.
    def create_categoria(self, data: dict[str, Any]) -> int:
        valori = dict(data)
        # `codice_interno` e' la chiave logica IMMUTABILE (NOT NULL, lockata,
        # nessun default DB): non e' esposta dall'API CRUD e qui il `codice` e'
        # gia' immutabile, quindi i due coincidono. Va valorizzata = codice alla
        # create, altrimenti l'INSERT viola NOT NULL (colonna aggiunta dal DB
        # in 20260629-06, vedi analisi-hardcoded-codice.md §4 #3).
        if "codice" in valori:
            valori["codice_interno"] = valori["codice"]
        riga = execute_dynamic_insert(
            "anagrafiche.categorie_clienti", valori,
            allowed=_CREATE_COLS | {"codice_interno"},
        )
        return int(riga["id"])

    # Scopo: Aggiorna una categoria sui soli campi forniti nel payload.
    #        Il codice e' immutabile a livello service, non a livello repository.
    #        BB `execute_dynamic_update` (2026-09-26), whitelist RIGIDA `_UPDATE_COLS`.
    def update_categoria(self, record_id: int, data: dict[str, Any]) -> bool:
        return execute_dynamic_update(
            "anagrafiche.categorie_clienti", record_id, data, allowed=_UPDATE_COLS,
        )
