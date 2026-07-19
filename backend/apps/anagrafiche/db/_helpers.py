# Helper condivisi per repository anagrafiche.

from __future__ import annotations

from typing import Any

from django.db import connection

from apps.core.services.error_manager import ErrorManager
from apps.anagrafiche.error_codes import E_ANAG_NOT_FOUND


# `extract_paginated` e' stato PROMOSSO a BB core (regola del 2, 2026-07-18):
# vive in `apps.core.db._helpers` insieme a `fetch_paged_with_total` (variante
# con fallback pagina-stantia) e `query_paged_view` (variante clamp). I
# repository anagrafiche lo importano direttamente dal core.


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


def get_or_create_soggetto_ruolo(soggetto_id: str, ruolo_codice: str) -> int:
    """Ottiene o crea il soggetto_ruolo per (soggetto, codice ruolo).

    Delega alla funzione DB script.fn_get_or_create_soggetto_ruolo. Riusato dai
    repository clienti/fornitori/emittenti (regola del 2): il codice ruolo
    ('CL'/'FO'/'EF'/...) e' l'unica variabile, passato come parametro %s.
    """
    sql = "SELECT script.fn_get_or_create_soggetto_ruolo(%s, %s) AS ruolo_id"
    with connection.cursor() as cursor:
        cursor.execute(sql, [soggetto_id, ruolo_codice])
        row = cursor.fetchone()
        assert row is not None
        return row[0]
