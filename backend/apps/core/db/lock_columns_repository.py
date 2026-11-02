# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per esporre i lock_columns DDL come metadata API.
# ------------------------------------------------------------

# La vista `dbops.vw_non_editable_fields` (alias semantico su
# `dbops.automation_lock_columns` filtrato `enabled=true`) elenca i campi
# resi immutabili da trigger lock_columns AUTO. Il repository legge la
# vista e restituisce la lista colonna per (schema, tabella) per essere
# inclusa nei detail come `non_editable_fields: list[str]`. Il FE costruisce
# whitelist PATCH e disabled UI dai metadata invece di cablare le regole.

from __future__ import annotations

import logging
from functools import lru_cache

from django.db import DatabaseError, connection

logger = logging.getLogger(__name__)


class LockColumnsRepository:
    """Repository riusabile per leggere `dbops.vw_non_editable_fields`."""

    # Scopo: Lista colonne lock per (target_schema, target_table). Cache
    #        modulo-level: la vista cambia solo con migrazioni Liquibase
    #        (no mutazioni runtime), quindi una cache statica per processo
    #        riduce N+1 sui detail-arricchiti senza rischio di stale.
    #        Per invalidazione manuale (test, hot reload) usare `cache_clear`.
    #        Defensive: se la vista non esiste o il DB non e' raggiungibile
    #        (testbed isolato, pre-migration), ritorna tupla vuota e logga.
    #        Il chiamante (`_compute_non_editable_fields`) ha comunque un
    #        gap Python che copre i lock condizionali non registrati.
    @staticmethod
    @lru_cache(maxsize=128)
    def list_non_editable(schema: str, table: str) -> tuple[str, ...]:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT column_name
                      FROM dbops.vw_non_editable_fields
                     WHERE target_schema = %s
                       AND target_table = %s
                     ORDER BY column_name
                    """,
                    [schema, table],
                )
                rows = cursor.fetchall()
            return tuple(row[0] for row in rows)
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
