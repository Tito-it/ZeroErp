# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: rendere JSON-safe i valori che i resolver DB restituiscono.
#        `Decimal` come STRINGA (mai float: su un importo o un'aliquota la
#        conversione a binario perde cifre) e `date` in ISO.
#
# ⭐ Estratto il 2026-08-31 alla SECONDA occorrenza (regola del 2): la stessa
#    funzione stava in `views_pricing` e in `views_iva`, identica. Due copie di
#    una conversione di trasporto sono due posti in cui un tipo nuovo viene
#    gestito in uno solo — e il difetto si vede in un endpoint e non nell'altro.
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

__all__ = ["serialize_value"]


# Scopo: converte un valore in forma JSON stabile; lo lascia com'e' se non ha
#        bisogno di conversione.
def serialize_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    return value
