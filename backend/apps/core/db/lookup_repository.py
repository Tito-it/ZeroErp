# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository core per lookup anagrafiche e config.
#        Endpoint: matrice indirizzi, autocomplete comuni,
#        tipi soggetto dettaglio con natura e policy,
#        search stradario per autocomplete vie.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import connection


class LookupRepository:
    """Lookup lettura per tabelle config/anagrafiche cross-dominio."""

    # Scopo: Restituisce i tipi soggetto dettaglio con natura, policy CF/PIVA/dati societari.
    # JOIN config.tipi_soggetto_dettaglio + config.tipi_soggetto per natura_soggetto.
    # Filtro: solo record con stato attivo (stato_id via JOIN config.stati).
    def list_tipi_soggetto_dettaglio(self) -> list[dict[str, Any]]:
        sql = """
            SELECT tsd.id,
                   tsd.codice_interno,
                   tsd.descrizione,
                   ts.id AS natura_soggetto,
                   tsd.cf_obbligatorio,
                   tsd.piva_obbligatoria,
                   tsd.dati_societari_policy
              FROM config.tipi_soggetto_dettaglio tsd
              JOIN config.tipi_soggetto ts ON ts.id = tsd.tipo_soggetto_id
             ORDER BY tsd.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql)
            cols = [c.name for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    # Scopo: Restituisce i tipi ruolo ammessi per una data natura soggetto.
    # Se natura_soggetto e' fornita, filtra via matrice tipi_ruoli_nature_ammesse.
    # Se non fornita, restituisce tutti i ruoli attivi.
    def list_tipi_ruoli_per_natura(
        self, natura_soggetto: str | None = None
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT tr.id, tr.codice, tr.descrizione
              FROM config.tipi_ruoli tr
             WHERE (%s::varchar IS NULL OR NOT EXISTS (
                       SELECT 1 FROM config.tipi_ruoli_nature_ammesse m
                        WHERE m.tipo_ruolo_id = tr.id
                   ) OR EXISTS (
                       SELECT 1 FROM config.tipi_ruoli_nature_ammesse m
                        WHERE m.tipo_ruolo_id = tr.id
                          AND m.tipo_soggetto_id = %s
                          AND m.attivo = true
                          AND (m.valido_dal IS NULL OR m.valido_dal <= CURRENT_DATE)
                          AND (m.valido_al IS NULL OR m.valido_al >= CURRENT_DATE)
                   ))
             ORDER BY tr.descrizione
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [natura_soggetto, natura_soggetto])
            cols = [c.name for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    # Scopo: Restituisce le forme giuridiche con policy REA e capitale sociale.
    # Opzionalmente filtrate per tipo_soggetto_dettaglio_id (via matrice).
    def list_forme_giuridiche(
        self, tipo_soggetto_dettaglio_id: int | None = None
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT fg.id, fg.codice, fg.descrizione,
                   fg.rea_policy, fg.capitale_sociale_policy, fg.attivo
              FROM config.forme_giuridiche fg
             WHERE fg.attivo = true
               AND (%s::bigint IS NULL OR EXISTS (
                   SELECT 1 FROM config.forme_giuridiche_tipi_soggetto_dettaglio fgtsd
                    WHERE fgtsd.forma_giuridica_id = fg.id
                      AND fgtsd.tipo_soggetto_dettaglio_id = %s
                      AND fgtsd.attivo = true
               ))
             ORDER BY fg.descrizione
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [tipo_soggetto_dettaglio_id, tipo_soggetto_dettaglio_id])
            cols = [c.name for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    # Scopo: Restituisce la matrice indirizzi ammessi per un tipo soggetto dettaglio.
    # JOIN config.tipi_soggetto_dettaglio_tipi_indirizzo + config.tipi_indirizzi.
    # Indica per ogni tipo indirizzo se obbligatorio e il fallback.
    def list_matrice_indirizzi(
        self, tipo_soggetto_dettaglio_id: int
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT tsdti.tipo_indirizzo_id,
                   ti.codice_interno AS codice,
                   ti.descrizione,
                   tsdti.obbligatorio,
                   tsdti.fallback_tipo_indirizzo_id,
                   ti_fb.codice_interno AS fallback_codice
              FROM config.tipi_soggetto_dettaglio_tipi_indirizzo tsdti
              JOIN config.tipi_indirizzi ti
                ON ti.id = tsdti.tipo_indirizzo_id
              LEFT JOIN config.tipi_indirizzi ti_fb
                ON ti_fb.id = tsdti.fallback_tipo_indirizzo_id
             WHERE tsdti.tipo_soggetto_dettaglio_id = %s
               AND tsdti.attivo = true
             ORDER BY tsdti.obbligatorio DESC, ti.descrizione
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [tipo_soggetto_dettaglio_id])
            cols = [c.name for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    # Scopo: Ricerca comuni per autocomplete (ILIKE su descrizione).
    # Restituisce id, descrizione, provincia sigla.
    # Risultato: (lista record, conteggio totale).
    def search_comuni(
        self,
        *,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        search_pattern = f"%{search.strip()}%" if search and search.strip() else None

        sql = """
            SELECT c.id,
                   c.descrizione,
                   p.sigla AS provincia_sigla,
                   COUNT(*) OVER () AS total_count
              FROM config.comuni c
              LEFT JOIN config.province p ON p.id = c.provincia_id
             WHERE (%s::text IS NULL OR c.descrizione ILIKE %s)
             ORDER BY c.descrizione, c.id
             LIMIT %s OFFSET %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [search_pattern, search_pattern, limit, offset])
            rows = cursor.fetchall()
            if not rows:
                return [], 0
            cols = [c.name for c in cursor.description]

        # Scopo: estrae total_count dalla window function e mappa i risultati.
        tc_idx = cols.index("total_count")
        total_count = rows[0][tc_idx]
        id_idx = cols.index("id")
        desc_idx = cols.index("descrizione")
        prov_idx = cols.index("provincia_sigla")
        results = [
            {"id": r[id_idx], "descrizione": r[desc_idx], "provincia_sigla": r[prov_idx]}
            for r in rows
        ]
        return results, total_count

    # Scopo: Ricerca vie (stradario) per autocomplete, filtrate per comune.
    # Chiama script.fn_search_stradario(p_comune_id, p_search, p_limit).
    # Restituisce stradario_id, indirizzo_normalizzato, comune, provincia, CAP.
    # Risultato: lista record (la funzione DB gestisce gia' il limit).
    def search_stradario(
        self,
        *,
        comune_id: int | None = None,
        search: str | None = None,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT *
              FROM script.fn_search_stradario(
                       p_comune_id := %s,
                       p_search    := %s,
                       p_limit     := %s
                   )
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [comune_id, search, limit])
            cols = [c.name for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    # Scopo: Ricerca vie su stradario_generale (senza comune/CAP) per autocomplete via nuova.
    # Chiama script.fn_search_stradario_generale(p_search, p_toponomastica_id, p_limit).
    # Restituisce stradario_generale_id, toponomastica_id, toponimo, denominazione, indirizzo_normalizzato.
    def search_stradario_generale(
        self,
        *,
        search: str | None = None,
        toponomastica_id: int | None = None,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT *
              FROM script.fn_search_stradario_generale(
                       p_search           := %s,
                       p_toponomastica_id := %s,
                       p_limit            := %s
                   )
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [search, toponomastica_id, limit])
            cols = [c.name for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
