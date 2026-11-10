# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per esporre i lock_columns DDL come metadata API.
# ------------------------------------------------------------

# La vista `dbops.vw_non_editable_fields` legge il lock VIVO (dal giro 10a di
# brief-db-revisione-dbops, D25): una riga per ogni colonna che un trigger di
# lock montato blocca davvero, `codice_interno` compreso, col nome del
# trigger (`trigger_name`). Non e' piu' il registro
# `dbops.automation_lock_columns`, che poteva dichiarare lock che nessun
# trigger applicava. Il repository legge la vista e restituisce la lista
# colonna per (schema, tabella) per essere inclusa nei detail come
# `non_editable_fields: list[str]`. Il FE costruisce whitelist PATCH e
# disabled UI dai metadata invece di cablare le regole.
# ⚠️ Una colonna bloccata da DUE trigger compare due volte nella vista: qui si
#    legge `DISTINCT`, perche' il contratto verso il FE e' un elenco di colonne.

from __future__ import annotations

import logging
from functools import lru_cache

from django.db import DatabaseError, connection

logger = logging.getLogger(__name__)


# Scopo: la lettura dei lock statici, in cache per processo: la vista cambia
#        solo con le migrazioni, quindi la cache toglie l'N+1 sui detail senza
#        rischio di stale.
# ⛔ La cache sta QUI, sulla lettura che RIUSCITA, e non sul metodo pubblico
#    col fallback (2026-11-09). Prima l'`lru_cache` avvolgeva anche il ramo
#    `except`: un errore transitorio del DB alla prima lettura metteva in cache
#    la tupla VUOTA per tutta la vita del worker, e il form tornava a lasciar
#    modificare `codice` di articoli ed emittenti — che dal BE2 nessun gap
#    Python ripete piu' — finche' nessuno riavviava il processo. Un'eccezione
#    non entra nella cache di `lru_cache`: la lettura successiva ci riprova.
@lru_cache(maxsize=128)
def _leggi_lock_statici(schema: str, table: str) -> tuple[str, ...]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT DISTINCT column_name
              FROM dbops.vw_non_editable_fields
             WHERE target_schema = %s
               AND target_table = %s
             ORDER BY column_name
            """,
            [schema, table],
        )
        rows = cursor.fetchall()
    return tuple(row[0] for row in rows)


class LockColumnsRepository:
    """Repository riusabile per leggere `dbops.vw_non_editable_fields`."""

    # Scopo: Lista colonne lock per (target_schema, target_table), dalla
    #        cache di `_leggi_lock_statici`. Per invalidarla (test, hot
    #        reload) `LockColumnsRepository.cache_clear()`.
    #        Defensive: se la vista non esiste o il DB non e' raggiungibile
    #        (testbed isolato, pre-migration), ritorna tupla vuota e logga —
    #        SENZA metterla in cache. Il chiamante ha comunque un gap Python
    #        per le colonne immutabili che il DB non blocca ancora con un
    #        trigger di lock.
    @staticmethod
    def cache_clear() -> None:
        _leggi_lock_statici.cache_clear()

    @staticmethod
    def list_non_editable(schema: str, table: str) -> tuple[str, ...]:
        try:
            return _leggi_lock_statici(schema, table)
        except DatabaseError as exc:
            logger.warning(
                "LockColumnsRepository.list_non_editable: query fallita per "
                "%s.%s, fallback a tupla vuota (cause: %s).",
                schema, table, exc,
            )
            return ()

    # Scopo: Lista colonne non editabili per (schema, table, record_id).
    #        Wrapper su `dbops.fn_non_editable_fields(text,text,text)`:
    #        unisce lock statici (vw_non_editable_fields) e lock
    #        condizionali (lock_columns_conditional) valutati sul record.
    #        Migration 20260522-03; seed regole condizionali in 20260522-04.
    #        Per casi senza record_id (lock statici-only) usare il metodo
    #        `list_non_editable` cached. Qui niente cache: il risultato
    #        dipende dallo stato runtime del record (BoM attiva, ecc.).
    #        Defensive: se la fn non esiste o il DB e' irraggiungibile,
    #        fallback al solo lock statico per non rompere il detail.
    @staticmethod
    def list_non_editable_for_record(
        schema: str, table: str, record_id: str | int,
    ) -> tuple[str, ...]:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT dbops.fn_non_editable_fields(%s, %s, %s)",
                    [schema, table, str(record_id)],
                )
                row = cursor.fetchone()
            if not row or row[0] is None:
                return ()
            return tuple(row[0])
        except DatabaseError as exc:
            logger.warning(
                "LockColumnsRepository.list_non_editable_for_record: query "
                "fallita per %s.%s id=%s, fallback ai soli lock statici "
                "(cause: %s).",
                schema, table, record_id, exc,
            )
            return LockColumnsRepository.list_non_editable(schema, table)
