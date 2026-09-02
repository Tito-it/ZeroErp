# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per indirizzi dettaglio, stradario e codici postali.
#        Accesso DB-first via cursor — delega logica a funzioni e view PostgreSQL.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.core.db._helpers import (
    colonne_identita,
    dynamic_update,
    sql_order_clause,
    extract_paginated,
    row_to_dict,
    rows_to_list,
)

from django.db import connection, transaction


# ⚠️ Dizionario e non insieme, e le due meta' sono UGUALI apposta: su questa
#    vista il nome logico della colonna E' la sua espressione SQL. Scriverlo
#    come mappa non e' cerimonia — e' la forma che `sql_order_clause` chiede a
#    tutte le liste, e dirlo esplicitamente evita che il prossimo lettore creda
#    che qui manchi una traduzione.
# ⭐ `set(_ORDER_COLS)` continua a funzionare (le chiavi), quindi
#    `_whitelist_indirizzi` del presidio seed non cambia.
_ORDER_COLS = colonne_identita(
    "indirizzo_normalizzato", "civico", "descrizione_comune", "cap",
    "provincia", "attivo", "data_insert",
)


class IndirizziRepository:
    """Accesso DB per indirizzi dettaglio, stradario e codici postali."""

    # =================================================================
    # Indirizzi Dettaglio
    # =================================================================

    # Scopo: Lista paginata indirizzi_dettaglio con info stradario/comune.
    def list_indirizzi_dettaglio(
        self,
        *,
        search: str | None = None,
        comune_id: int | None = None,
        limit: int = 25,
        offset: int = 0,
        order_by: str = "indirizzo_normalizzato",
        order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_ORDER_COLS,
            default="indirizzo_normalizzato",
            tiebreak="vid.indirizzo_dettaglio_id",
        )
        search_pattern = f"%{search.strip()}%" if search and search.strip() else None

        sql = f"""
            SELECT vid.indirizzo_dettaglio_id,
                   vid.stradario_id,
                   vid.indirizzo_normalizzato,
                   vid.civico,
                   vid.estensione_civico,
                   vid.descrizione_comune,
                   vid.cap,
                   vid.provincia,
                   vid.attivo,
                   vid.data_insert,
                   COUNT(*) OVER () AS total_count
              FROM anagrafiche.vw_indirizzi_dettaglio vid
             WHERE (%s::text IS NULL OR vid.indirizzo_normalizzato ILIKE %s
                    OR vid.descrizione_comune ILIKE %s)
               AND (%s::integer IS NULL OR vid.comune_id = %s)
             ORDER BY {ordinamento}
             LIMIT %s OFFSET %s
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                search_pattern, search_pattern, search_pattern,
                comune_id, comune_id,
                limit, offset,
            ])
            return extract_paginated(cursor)

    # Scopo: Dettaglio singolo indirizzo per form edit.
    def get_indirizzo_dettaglio(self, indirizzo_dettaglio_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT vid.indirizzo_dettaglio_id,
                   vid.stradario_id,
                   vid.indirizzo_normalizzato,
                   vid.civico,
                   vid.estensione_civico,
                   vid.descrizione_comune,
                   vid.cap,
                   vid.provincia,
                   vid.attivo,
                   idd.palazzina,
                   idd.scala,
                   idd.piano,
                   idd.interno
              FROM anagrafiche.vw_indirizzi_dettaglio vid
              JOIN anagrafiche.indirizzi_dettaglio idd
                ON idd.id = vid.indirizzo_dettaglio_id
             WHERE vid.indirizzo_dettaglio_id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [indirizzo_dettaglio_id])
            return row_to_dict(cursor)

    # Scopo: Cerca indirizzo duplicato via fn_check_indirizzo_duplicato (DB).
    #        La funzione DB costruisce la stringa normalizzata, cerca match prefix
    #        e ritorna exact_match boolean. Python e' passante.
    #        Supporta due flussi: stradario_id diretto, oppure
    #        stradario_generale_id + comune_id per risoluzione indiretta.
    def find_duplicato(
        self, *, stradario_id: int | None = None, civico: int | None = None,
        estensione_civico: str | None = None,
        palazzina: str | None = None,
        scala: str | None = None,
        piano: str | None = None,
        interno: str | None = None,
        stradario_generale_id: int | None = None,
        comune_id: int | None = None,
        codice_postale_id: int | None = None,
    ) -> dict[str, Any] | None:
        sql = """
            SELECT indirizzo_dettaglio_id,
                   indirizzo_normalizzato,
                   descrizione_comune,
                   exact_match
              FROM script.fn_check_indirizzo_duplicato(
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
              )
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                stradario_id, civico, estensione_civico,
                palazzina, scala, piano, interno,
                stradario_generale_id, comune_id, codice_postale_id,
            ])
            return row_to_dict(cursor)

    # Scopo: Crea indirizzo dettaglio tramite building block DB.
    def create_indirizzo_dettaglio(
        self,
        *,
        stradario_id: int,
        civico: int | None = None,
        estensione_civico: str | None = None,
        palazzina: str | None = None,
        scala: str | None = None,
        piano: str | None = None,
        interno: str | None = None,
    ) -> int:
        sql = """
            SELECT anagrafiche.fn_get_or_create_indirizzo_dettaglio(
                %s, %s, %s, %s, %s, %s, %s
            )
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                stradario_id, civico, estensione_civico,
                palazzina, scala, piano, interno,
            ])
            row = cursor.fetchone()
            if not row:
                raise RuntimeError("fn_get_or_create_indirizzo_dettaglio returned NULL")
            assert row is not None
        return int(row[0])

    # Scopo: Aggiorna dettagli civico (stradario_id non modificabile).
    def update_indirizzo_dettaglio(
        self,
        indirizzo_dettaglio_id: int,
        *,
        civico: int | None = None,
        estensione_civico: str | None = None,
        palazzina: str | None = None,
        scala: str | None = None,
        piano: str | None = None,
        interno: str | None = None,
        attivo: bool | None = None,
    ) -> bool:
        return dynamic_update("anagrafiche.indirizzi_dettaglio", indirizzo_dettaglio_id,
                              civico=civico, estensione_civico=estensione_civico,
                              palazzina=palazzina, scala=scala, piano=piano,
                              interno=interno, attivo=attivo)

    # =================================================================
    # Stradario — supporto creazione via nuova
    # =================================================================

    # Scopo: Cerca o crea stradario locale (toponomastica + via + comune + CAP).
    def get_or_create_stradario(
        self,
        *,
        toponomastica_id: int,
        descrizione_via: str,
        comune_id: int,
        codice_postale_id: int,
    ) -> int:
        descrizione_via = descrizione_via.strip()

        # Guardrail atomicità (review 2026-07-08): 2 upsert sequenziali (stradario_generale
        # + stradario) resi self-atomici. Prima protetti solo dal caller; nested=savepoint.
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO config.stradario_generale (toponomastica_id, descrizione, descrizione_breve)
                VALUES (%s, %s, %s)
                ON CONFLICT (toponomastica_id, descrizione) DO UPDATE
                   SET descrizione = EXCLUDED.descrizione
                RETURNING id
            """, [toponomastica_id, descrizione_via, descrizione_via])
            row = cursor.fetchone()
            assert row is not None
            stradario_generale_id = row[0]

            cursor.execute("""
                INSERT INTO config.stradario (stradario_generale_id, comune_id, codice_postale_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (comune_id, stradario_generale_id, codice_postale_id) DO UPDATE
                   SET comune_id = EXCLUDED.comune_id
                RETURNING id
            """, [stradario_generale_id, comune_id, codice_postale_id])
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: Creazione atomica dell'indirizzo via funzione madre DB.
    #        Obiettivo: fondere in UNA sola statement (anagrafiche.fn_create_indirizzo)
    #        l'upsert dello stradario (generale + locale, solo per "via nuova" con
    #        p_stradario_id NULL) e il get_or_create del dettaglio civico.
    #        Perimetro: o tutto o rollback totale — niente piu' righe stradario di
    #        registro orfane se il dettaglio fallisce (fix analisi-fix-transazioni
    #        Classe D, finding #13; prima get_or_create_stradario +
    #        create_indirizzo_dettaglio erano due scritture autocommit separate).
    #        La fn e' SECURITY INVOKER. Ritorna l'id del dettaglio indirizzo.
    #        Se p_stradario_id e' valorizzato la fn salta l'upsert e usa quello.
    def create_indirizzo_atomico(
        self, *,
        stradario_id: int | None = None,
        toponomastica_id: int | None = None,
        descrizione_via: str | None = None,
        comune_id: int | None = None,
        codice_postale_id: int | None = None,
        civico: int | None = None,
        estensione_civico: str | None = None,
        palazzina: str | None = None,
        scala: str | None = None,
        piano: str | None = None,
        interno: str | None = None,
    ) -> int:
        sql = """
            SELECT anagrafiche.fn_create_indirizzo(
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                stradario_id, toponomastica_id, descrizione_via,
                comune_id, codice_postale_id, civico, estensione_civico,
                palazzina, scala, piano, interno,
            ])
            row = cursor.fetchone()
            assert row is not None and row[0] is not None
        return int(row[0])

    # =================================================================
    # Codici postali
    # =================================================================

    # Scopo: Lista CAP per un comune.
    def list_codici_postali_by_comune(self, comune_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT id, codice
              FROM config.codici_postali
             WHERE comune_id = %s
             ORDER BY codice
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [comune_id])
            return rows_to_list(cursor)
