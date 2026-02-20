# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Normalizzazione valori di input/output.
# ------------------------------------------------------------


from typing import Any

# Utility condivise cross-domain per normalizzazione input/parametri.


# Scopo: Gestisce `as_bool` nel flusso applicativo del modulo.
def as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y", "on"}


# Scopo: Gestisce `empty_to_none` nel flusso applicativo del modulo.
def empty_to_none(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return value
