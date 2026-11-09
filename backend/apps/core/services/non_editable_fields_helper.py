# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Helper centralizzato per esporre la lista `non_editable_fields`
#        nei detail/list arricchiti delle API admin (Fase 4 — A7/A9/A10).
#
#        Source primaria: `dbops.vw_non_editable_fields` letta via
#        `LockColumnsRepository.list_non_editable`. Dal giro 10a di
#        brief-db-revisione-dbops (D25) la vista legge il lock VIVO: ogni
#        colonna che un trigger di lock montato blocca, `codice_interno`
#        compreso. Il caller passa `gaps=(...)` solo per le colonne
#        immutabili nel dominio che il DB NON blocca ancora con un trigger
#        di lock.
#
#        ⛔ Un gap che ripete una colonna gia' nella vista e' una seconda
#        sede della stessa regola, e si toglie: quando il DB dichiara il
#        lock, il caller passa `gaps=()` e la lista resta DB-driven al
#        100%. I gap dicono sempre cosa manca al DB.
#
#        ⭐ Con `record_id` legge anche i lock CONDIZIONALI valutati sul
#        record (`LockColumnsRepository.list_non_editable_for_record`, cioe'
#        `dbops.fn_non_editable_fields`). Fino al 2026-11-09 questo ramo
#        viveva solo in una copia privata di catalogo
#        (`_compute_non_editable_fields`): ritirata nello stesso giro
#        (regola del 2, ok Tid).
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Iterable

from apps.core.db.lock_columns_repository import LockColumnsRepository


# Scopo: Calcola la lista deduplicata e ordinata `non_editable_fields`
#        per (schema, table). Unisce i lock del DB con i gap dominio.
#        Tipo `gaps` accetta qualsiasi iterabile di stringhe (tupla,
#        lista, frozenset, generator) per ergonomia caller-side.
#        `record_id`: se passato, ai lock statici si aggiungono quelli
#        condizionali valutati su QUEL record (es. `catalogo.articoli` usato
#        o con distinta in vigore); senza, i soli statici (liste, create).
def compute_non_editable_fields(
    schema: str,
    table: str,
    *,
    gaps: Iterable[str] = (),
    record_id: str | int | None = None,
) -> list[str]:
    if record_id is not None:
        db_locked = set(
            LockColumnsRepository.list_non_editable_for_record(schema, table, record_id),
        )
    else:
        db_locked = set(LockColumnsRepository.list_non_editable(schema, table))
    db_locked.update(gaps)
    return sorted(db_locked)
