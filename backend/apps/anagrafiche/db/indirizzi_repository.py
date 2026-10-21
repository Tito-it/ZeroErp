# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per indirizzi dettaglio, stradario e codici postali.
#        Accesso DB-first via cursor — delega logica a funzioni e view PostgreSQL.
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.db._helpers import (
    RicercaFull,
    add_ricerca_full_condition,
    colonne_identita,
    sql_order_clause,
    fetch_paged_with_total,
    row_to_dict,
    rows_to_list,
)

from apps.core.db.sql_write_helpers import execute_dynamic_update
from django.db import connection


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

# Cosa si PUO' cercare; cosa si cerca lo dice il catalogo (`add_ricerca_full_condition`).
_RICERCA = RicercaFull("anagrafiche.indirizzi", ("indirizzo_normalizzato", "descrizione_comune"))


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
        limit: int = DEFAULT_LIMIT,
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
        conditions: list[str] = ["(%s::integer IS NULL OR vid.comune_id = %s)"]
        params: list[Any] = [comune_id, comune_id]
        add_ricerca_full_condition(conditions, params, search, _RICERCA, alias="vid")

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
             WHERE {" AND ".join(conditions)}
             ORDER BY {ordinamento}
             LIMIT %s OFFSET %s
        """  # noqa: S608
        return fetch_paged_with_total(sql, [*params, limit, offset], offset=offset)

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

    # Scopo: Aggiorna dettagli civico (stradario_id non modificabile).
    # ⚠️ `campi` li legge il service per PRESENZA (`campi_per_presenza`): un
    #    `None` qui svuota il campo. Fino al 2026-10-20 None voleva dire «non
    #    toccare», e svuotare la palazzina dal drawer non scriveva niente.
    def update_indirizzo_dettaglio(self, indirizzo_dettaglio_id: int, campi: Mapping[str, Any]) -> bool:
        return execute_dynamic_update(
            "anagrafiche.indirizzi_dettaglio", indirizzo_dettaglio_id, campi,
            allowed=("civico", "estensione_civico", "palazzina", "scala", "piano",
                     "interno", "attivo"),
        )

    # =================================================================
    # Stradario — supporto creazione via nuova
    # =================================================================

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
