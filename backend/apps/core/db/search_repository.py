# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository ricerca universale soggetti.
# Chiama le funzioni DB script.fn_search_soggetti_universale
# e script.fn_get_search_detail per la ricerca a due livelli.
# ------------------------------------------------------------

from __future__ import annotations


from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.db._helpers import RicercaFull, colonne_ricerca_attive, jsonb_out, rows_to_list
from typing import Any

from django.db import connection

# Dove la ricerca universale SA cercare: i campi della whitelist di
# `fn_search_soggetti_universale` (`p_campi_ricerca`, D-4 di
# brief-db-liste-datatable-grezze-secondo-giro, 2026-10-31). Dove CERCA lo dice
# il catalogo della lista 113, letto a ogni ricerca: spegnere una colonna dal
# pannello admin la toglie subito, e una colonna BLOCCATA per l'utente non si
# sonda cercandola. `soggetto_codice` copre anche il codice dell'entita' del
# ruolo: e' la funzione a saperlo.
RICERCA_SOGGETTI = RicercaFull(
    "anagrafiche.ricerca_soggetti",
    ("soggetto_codice", "ragione_sociale_completa", "id_fiscale_univoco"),
)

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
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        order_by: str | None = None,
        order_dir: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        # ⭐ Il perimetro lo fa la RLS di `anagrafiche.clienti` (dal 2026-10-08,
        #    brief-db-codici-non-trovato-email-e-permessi R-4): il backend non
        #    passa piu' `p_emittente_ids`, superato e non letto dalla funzione.
        # ⭐ `r.*` e non `row_to_json(r)` (2026-10-31): la riga arriva per
        #    colonne, e il presidio della proiezione della lista
        #    (`test_lista_proiezione_campo_sorgente`) le legge dal cursore.
        # ⭐ I campi si leggono UNA volta, prima della pagina: la rilettura per
        #    il totale cerca dove ha cercato la pagina. ⛔ Elenco vuoto: la
        #    funzione non restituisce righe (nessuna colonna accesa non trova
        #    niente, come il `FALSE` di `add_ricerca_full_condition`). Mai
        #    `None`: per la funzione vorrebbe dire «i tre campi», e
        #    riaccenderebbe le colonne spente.
        campi = colonne_ricerca_attive(RICERCA_SOGGETTI)

        def _pagina(lim: int, off: int) -> list[dict[str, Any]]:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT r.*
                      FROM script.fn_search_soggetti_universale(
                               p_search_term   := %s,
                               p_tipo_ruolo_id := %s,
                               p_limit         := %s,
                               p_offset        := %s,
                               p_order_by      := %s,
                               p_order_dir     := %s,
                               p_campi_ricerca := %s::text[]
                           ) r
                    """,
                    [search_term, tipo_ruolo_id, lim, off, order_by, order_dir, campi],
                )
                return rows_to_list(cursor)

        rows = _pagina(limit, offset)
        if not rows:
            # ⚠️ Pagina oltre l'ultima: il totale lo porta ogni riga
            #    (`COUNT(*) OVER()` nella funzione), e qui non ce n'e' nessuna.
            #    Si rilegge la PRIMA riga per il totale vero (stessa regola di
            #    `fetch_paged_with_total`, che qui non si puo' usare: la
            #    paginazione la fa la funzione a DB).
            if offset > 0:
                prima = _pagina(1, 0)
                if prima:
                    return [], int(prima[0].get("total_count") or 0)
            return [], 0

        # total_count e' in ogni riga (COUNT(*) OVER()): si legge e si toglie.
        total_count = int(rows[0].get("total_count") or 0)
        for row in rows:
            row.pop("total_count", None)
        return rows, total_count

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
    ) -> dict[str, Any] | None:
        # Perimetro dalla RLS, come in `search_soggetti` sopra.
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT script.fn_get_search_detail(
                           p_soggetto_id   := %s::uuid,
                           p_tipo_ruolo_id := %s,
                           p_utility_id    := %s
                       )
                """,
                [soggetto_id, tipo_ruolo_id, utility_id],
            )
            row = cursor.fetchone()

        if not row or row[0] is None:
            return None

        return jsonb_out(row[0])

    # Scopo: Restituisce i tipi ruolo con ricerca_visibile = true,
    # ordinati per descrizione. Usato dal dropdown della ricerca universale.
    def list_tipi_ruoli_visibili(self) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, COALESCE(codice_interno, codice) AS codice, descrizione
                  FROM config.tipi_ruoli
                 WHERE ricerca_visibile = true
                 ORDER BY descrizione
                """
            )
            return rows_to_list(cursor)

    # ⛔ `is_tipo_ruolo_visibile` RITIRATA (2026-10-10, Q-2 di
    #    brief-db-codici-non-trovato-email-e-permessi): «il ruolo e'
    #    ricercabile» lo dicono le due funzioni DB, col BB
    #    `script.fn_predicato_soggetto_ruolo_visibile`. Il menu a tendina
    #    continua a leggere la colonna (`list_tipi_ruoli_visibili`, sopra).
