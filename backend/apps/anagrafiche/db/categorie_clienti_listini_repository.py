# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per anagrafiche.categorie_clienti_listini (CRUD admin).
#        Matrice pricing STADIO 2 del resolver v5: categoria x utility x
#        emittente x classe_utenza (opz) -> listino con variazione opzionale.
#        Lista arricchita con codici/descrizioni dalle tabelle riferite per
#        display diretto in UI (no lookup client-side).
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
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
# parametro order_by ricevuto dal frontend. Gli alias mappano a espressioni
# sicure lato DB.
#
# `emittente_ragione_sociale` appartiene al NUCLEO sempre ordinabile (regola di
# Tid: data del contesto, numero, ragione sociale, billing account, id fiscale,
# utility, totale, stato). Mancava, ed era l'unica delle 11 a mancare: la
# colonna era `ordinabile=f` nel seed (riga 371) e il team DB la ribalta a `t`
# ORA che la whitelist esiste — mai prima, o la freccia comparirebbe a video e
# ripiegherebbe in silenzio sul default.
_ORDER_COLS: dict[str, str] = {
    "categoria_codice": "cc.codice",
    "categoria_descrizione": "cc.descrizione",
    "utility_codice": "u.codice",
    "utility_descrizione": "u.descrizione",
    "emittente_ragione_sociale": "s.ragione_sociale_completa",
    "listino_codice": "l.codice",
    "listino_descrizione": "l.descrizione",
    "valido_dal": "m.valido_dal",
    "valido_al": "COALESCE(m.valido_al, 'infinity'::date)",
    "attivo": "m.attivo",
    "data_insert": "m.data_insert",
    "data_update": "m.data_update",
}


# Colonne proiettate in lista/dettaglio. La colonna `validita` daterange e'
# generata da trigger e non viene esposta in API: il contratto espone
# valido_dal/valido_al che sono semanticamente equivalenti per gli admin.
_SELECT_COLS = """
    m.id,
    m.categoria_cliente_id,
    cc.codice AS categoria_codice,
    cc.descrizione AS categoria_descrizione,
    m.utility_id,
    u.codice AS utility_codice,
    u.descrizione AS utility_descrizione,
    m.emittente_soggetto_ruolo_id,
    COALESCE(tr.codice_interno, tr.codice) AS emittente_codice_ruolo,
    -- ⚠️ `ragione_sociale_completa`, NON `ragione_sociale`: la seconda e'
    -- NULL su ogni persona fisica (11 soggetti su 26 alla misura del brief
    -- `brief-emittente-ragione-sociale-dal-soggetto.md`), dove il nome sta in
    -- cognome/nome. La colonna completa e' GENERATED ALWAYS AS
    -- COALESCE(ragione_sociale, cognome || ' ' || nome), quindi copre entrambi
    -- i casi. Il difetto era invisibile solo perche' i due emittenti in
    -- tabella sono societa': si sarebbe visto al primo emittente ditta
    -- individuale. Corretto il 2026-08-02 su segnalazione del team DB.
    s.ragione_sociale_completa AS emittente_ragione_sociale,
    m.classe_utenza_id,
    clu.codice AS classe_utenza_codice,
    clu.descrizione AS classe_utenza_descrizione,
    m.listino_id,
    l.codice AS listino_codice,
    l.descrizione AS listino_descrizione,
    m.tipo_variazione,
    m.valore_variazione,
    m.valido_dal,
    m.valido_al,
    m.meta,
    m.attivo,
    m.data_insert,
    m.user_insert,
    m.data_update,
    m.user_update
"""


# Cosa si PUO' cercare; cosa si cerca lo dice il catalogo (`add_ricerca_full_condition`).
# Mappa `campo_sorgente → espressione`: i nomi del catalogo sono nomi di USCITA
# di `_SELECT_COLS`, e ogni valore e' la stessa espressione che la SELECT
# proietta con quel nome (si cerca su cio' che si mostra).
# ⭐ Le due descrizioni sono colonne del catalogo dal 2026-09-24 (brief DB
#    §3.2-bis): prima la ricerca le cercava senza che il catalogo lo dicesse.
_RICERCA_MATRICE = RicercaFull(
    "anagrafiche.categorie_clienti_listini",
    {
        "categoria_codice": "cc.codice",
        "categoria_descrizione": "cc.descrizione",
        "listino_codice": "l.codice",
        "listino_descrizione": "l.descrizione",
    },
)


_FROM_JOINS = """
    FROM anagrafiche.categorie_clienti_listini m
    JOIN anagrafiche.categorie_clienti cc ON cc.id = m.categoria_cliente_id
    JOIN config.utilities u ON u.id = m.utility_id
    JOIN anagrafiche.soggetti_ruoli sr ON sr.id = m.emittente_soggetto_ruolo_id
    JOIN config.tipi_ruoli tr ON tr.id = sr.tipo_ruolo_id
    JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
    LEFT JOIN config.classi_utenze clu ON clu.id = m.classe_utenza_id
    JOIN vendite.listini l ON l.id = m.listino_id
"""


# Colonne scrivibili (whitelist RIGIDA dei BB di scrittura, 2026-09-26).
# In update mancano le 4 dimensioni della riga: sono immutabili.
_UPDATE_COLS: frozenset[str] = frozenset({
    "listino_id", "tipo_variazione", "valore_variazione",
    "valido_dal", "valido_al", "meta", "attivo",
})
_CREATE_COLS: frozenset[str] = _UPDATE_COLS | {
    "categoria_cliente_id", "utility_id", "emittente_soggetto_ruolo_id", "classe_utenza_id",
}


class CategorieClientiListiniRepository:
    """Accesso DB alla matrice `anagrafiche.categorie_clienti_listini`."""

    # =================================================================
    # Lista e dettaglio
    # =================================================================

    # Scopo: Lista paginata della matrice con filtri opzionali sulle
    #        dimensioni (categoria, utility, emittente, listino) e stato.
    #        Restituisce (results, total_count) per envelope paginato.
    def list_matrice(
        self,
        *,
        search: str | None = None,
        attivo: bool | None = None,
        categoria_cliente_id: int | None = None,
        utility_id: int | None = None,
        emittente_soggetto_ruolo_id: int | None = None,
        listino_id: int | None = None,
        valid_at: date | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        order_by: str = "valido_dal",
        order_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_ORDER_COLS,
            default=_ORDER_COLS["valido_dal"],
            tiebreak="m.id",
            # Il default e' una DATA: parte dalla piu' recente (regola di Tid
            # 2026-09-02). Fino al 2026-10-20 mancava, e la lista partiva ASC.
            default_desc=True,
        )
        safe_limit, safe_offset = limiti_pagina(limit, offset)

        conditions: list[str] = []
        params: list[Any] = []

        if attivo is not None:
            conditions.append("m.attivo = %s")
            params.append(attivo)
        if categoria_cliente_id is not None:
            conditions.append("m.categoria_cliente_id = %s")
            params.append(categoria_cliente_id)
        if utility_id is not None:
            conditions.append("m.utility_id = %s")
            params.append(utility_id)
        if emittente_soggetto_ruolo_id is not None:
            conditions.append("m.emittente_soggetto_ruolo_id = %s")
            params.append(emittente_soggetto_ruolo_id)
        if listino_id is not None:
            conditions.append("m.listino_id = %s")
            params.append(listino_id)
        if valid_at is not None:
            # La colonna validita e' daterange calcolata da trigger.
            conditions.append("m.validita @> %s::date")
            params.append(valid_at)
        # ⭐ Una condizione sola per pagina e conteggio (`where_clause` qui
        #    sotto): i due insiemi non possono divergere.
        # ⭐ Matrice di configurazione, gemella di `tipi_ruolo_tipi_indirizzo`
        #    e `categorie_clienti` (Tid, 2026-09-24): la soglia la dichiara il
        #    catalogo (`ricerca_min_caratteri`). Fino ad allora la ricerca
        #    scritta a mano non escapava `%`/`_` (e un termine di soli spazi
        #    diventava `%%`).
        add_ricerca_full_condition(conditions, params, search, _RICERCA_MATRICE)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT COUNT(*)
                  {_FROM_JOINS}
                {where_clause}
                """,
                params,
            )
            row = cursor.fetchone()
            assert row is not None
            total_count = int(row[0])

            # Tiebreaker su id per paginazione deterministica.
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

    # Scopo: Dettaglio singola riga matrice con tutti i display joinati.
    def get_matrice(self, record_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT {_SELECT_COLS}
                  {_FROM_JOINS}
                 WHERE m.id = %s
                """,
                [record_id],
            )
            return row_to_dict(cursor)

    # =================================================================
    # Mutazioni
    # =================================================================

    # Scopo: Inserisce una nuova riga di matrice usando solo colonne
    #        whitelisted. `validita` NON e' scrivibile: e' STORED generated
    #        column (PG 18) calcolata automaticamente da valido_dal/valido_al.
    #        BB `execute_dynamic_insert` (2026-09-26): whitelist RIGIDA
    #        `_CREATE_COLS`, `meta` dict -> `::jsonb`, None scrive NULL.
    def create_matrice(self, data: dict[str, Any]) -> int:
        riga = execute_dynamic_insert(
            "anagrafiche.categorie_clienti_listini", data, allowed=_CREATE_COLS,
        )
        return int(riga["id"])

    # Scopo: Aggiorna una riga matrice sui soli campi forniti. Le 4+1 FK
    #        dimensionali (categoria, utility, emittente, classe_utenza)
    #        sono immutabili lato service (non arrivano nel payload di
    #        update) e FUORI da `_UPDATE_COLS`: se arrivassero qui sarebbe
    #        `RuntimeError` (BB `execute_dynamic_update`, 2026-09-26).
    def update_matrice(self, record_id: int, data: dict[str, Any]) -> bool:
        return execute_dynamic_update(
            "anagrafiche.categorie_clienti_listini", record_id, data,
            allowed=_UPDATE_COLS,
        )
