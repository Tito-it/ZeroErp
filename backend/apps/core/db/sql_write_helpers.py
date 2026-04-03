# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Helper condivisi per parametri SQL write con cast espliciti.
# ------------------------------------------------------------

from __future__ import annotations

import json
from typing import Any


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
