# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Helper condivisi per parametri SQL write con cast espliciti.
# ------------------------------------------------------------

from __future__ import annotations

import json
from typing import Any

from django.db import connection


# Scopo: Converte un valore Python nel parametro SQL corretto per il tipo colonna.
def to_write_param(value: Any, column_type: str) -> Any:
    if column_type == "jsonb":
        return None if value is None else json.dumps(value)
    return value


# Scopo: Restituisce placeholder SQL con cast esplicito quando richiesto.
def sql_placeholder(column_type: str) -> str:
    if column_type == "jsonb":
        return "%s::jsonb"
    return "%s"


# Scopo: UPDATE dinamico per-id condiviso (BB estratto 2026-07-13, regola del
#        2 — era copiato in 8+ metodi update_* di ddt/ordini/preventivi/resi/
#        componenti/email): costruisce il SET dai valori (dict/list -> ::jsonb
#        + json.dumps, stringhe strip) e aggiorna la riga per id.
#        `table` DEVE essere un literal del chiamante (mai input utente);
#        `allowed` = whitelist colonne opzionale (chiavi fuori lista scartate
#        in silenzio, defense-in-depth); `extra_set` = clausola SET aggiuntiva
#        literal (es. "data_update = now()"); `skip_none` = True per i CRUD
#        "kwargs espliciti" dove None significa "non toccare" (variante ex
#        `dynamic_update` di _helpers — default False: nei PATCH whitelisted
#        None AZZERA il campo nullable). Ritorna False se non c'e' nulla da
#        aggiornare, altrimenti rowcount > 0.
def execute_dynamic_update(
    table: str,
    row_id: int,
    values: dict[str, Any],
    *,
    allowed: frozenset[str] | None = None,
    extra_set: str | None = None,
    skip_none: bool = False,
) -> bool:
    fields: list[str] = []
    params: list[Any] = []
    for col, val in values.items():
        if allowed is not None and col not in allowed:
            continue  # silenzioso defense-in-depth (whitelist del chiamante)
        if skip_none and val is None:
            continue
        if isinstance(val, (dict, list)):
            fields.append(f"{col} = %s::jsonb")
            params.append(json.dumps(val))
        else:
            if isinstance(val, str):
                val = val.strip()
            fields.append(f"{col} = %s")
            params.append(val)
    if not fields:
        return False
    if extra_set:
        fields.append(extra_set)
    params.append(row_id)
    sql = f"UPDATE {table} SET {', '.join(fields)} WHERE id = %s"  # noqa: S608
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.rowcount > 0
