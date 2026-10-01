# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Costanti centralizzate per il modulo amministrazione software.
# Evita magic numbers e stringhe hardcoded sparsi tra service/repository/views.
# ------------------------------------------------------------

# Sesso default per creazione soggetto PF
DEFAULT_SESSO = "M"

# Paginazione: la fonte unica e' `apps.core.api.constants` (2026-09-28).
# Si ri-esporta perche' i moduli di questo dominio la leggono da qui.
from apps.core.api.constants import DEFAULT_LIMIT, MAX_LIMIT  # noqa: F401
