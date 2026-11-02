# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Helper centralizzato per esporre la lista `non_editable_fields`
#        nei detail/list arricchiti delle API admin (Fase 4 — A7/A9/A10).
#
#        Source primaria: `dbops.vw_non_editable_fields` letta via
#        `LockColumnsRepository.list_non_editable`. Il caller passa
#        `gaps=(...)` per coprire le colonne immutabili nel dominio
#        applicativo non ancora registrate nel registro DB
#        (lock condizionali, trigger custom, FK ereditate, ecc).
#
#        Quando il team DB completa il registro per un dominio, il
#        caller passa `gaps=()` e la lista resta DB-driven al 100%.
#        Drift visibile = self-documenting: i gap dichiarano sempre
#        cosa manca al registro DB.
#
#        Pattern allineato al privato `_compute_non_editable_fields`
#        di catalogo (Fase 5). In una fase futura il privato di
#        catalogo potra' migrare a questo helper centralizzato.
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Iterable

from apps.core.db.lock_columns_repository import LockColumnsRepository


# Scopo: Calcola la lista deduplicata e ordinata `non_editable_fields`
#        per (schema, table). Unisce il registro DB con i gap dominio.
#        Tipo `gaps` accetta qualsiasi iterabile di stringhe (tupla,
#        lista, frozenset, generator) per ergonomia caller-side.
def compute_non_editable_fields(
    schema: str,
    table: str,
    *,
    gaps: Iterable[str] = (),
) -> list[str]:
    db_locked = set(LockColumnsRepository.list_non_editable(schema, table))
    db_locked.update(gaps)
    return sorted(db_locked)
