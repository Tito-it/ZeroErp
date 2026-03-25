# Helper condivisi per repository anagrafiche.

from __future__ import annotations

from typing import Any

from apps.core.services.error_manager import ErrorManager
from apps.anagrafiche.error_codes import E_ANAG_NOT_FOUND


def extract_paginated(cursor) -> tuple[list[dict[str, Any]], int]:
    """Estrae risultati paginati da query con COUNT(*) OVER() AS total_count.

    Restituisce (lista dict senza total_count, conteggio totale).
    Pre-computa mappa indici per evitare O(n*m) su cols.index().
    """
    rows = cursor.fetchall()
    if not rows:
        return [], 0
    cols = [c.name for c in cursor.description]
    tc_idx = cols.index("total_count")
    total_count = rows[0][tc_idx]
    col_idx = {c: i for i, c in enumerate(cols) if c != "total_count"}
    results = [
        {c: row[i] for c, i in col_idx.items()}
        for row in rows
    ]
    return results, total_count


def resolve_soggetto_id(cursor, soggetto_ruolo_id: int) -> str:
    """Risolve soggetto_id dal ruolo. Solleva E_ANAG_NOT_FOUND se non trovato.

    Usato da views contatti_ruolo e indirizzi_ruolo per evitare duplicazione.
    """
    cursor.execute(
        "SELECT soggetto_id FROM anagrafiche.soggetti_ruoli WHERE id = %s",
        [soggetto_ruolo_id],
    )
    row = cursor.fetchone()
    ErrorManager.require(
        row is not None, code=E_ANAG_NOT_FOUND,
        message="Ruolo non trovato.",
    )
    assert row is not None
    return str(row[0])
