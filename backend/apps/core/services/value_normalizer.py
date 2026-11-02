# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Normalizzazione valori di input/output.
# ------------------------------------------------------------


from typing import Any

# Utility condivise cross-domain per normalizzazione input/parametri.


# Scopo: Gestisce `empty_to_none` nel flusso applicativo del modulo.
def empty_to_none(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return value
