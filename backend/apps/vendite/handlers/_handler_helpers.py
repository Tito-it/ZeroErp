# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Helper condivisi tra gli handler di flusso vendite. Estratti per evitare
#        duplicazione (regola del 2): la normalizzazione della competenza era
#        copiata in push_preventivo_handler e accetta_preventivo_handler.
# ------------------------------------------------------------

from datetime import date
from typing import Any


# Scopo: normalizza il valore competenza al primo del mese.
# Accetta 'YYYY-MM-DD', 'YYYY-MM' o un date. None/vuoto/invalido → None.
def parse_competenza_mese(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value.replace(day=1)
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        if len(raw) == 7:  # 'YYYY-MM'
            raw = f"{raw}-01"
        try:
            return date.fromisoformat(raw).replace(day=1)
        except ValueError:
            return None
    return None
