# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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
