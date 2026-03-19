# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Costanti centralizzate per il modulo amministrazione software.
# Evita magic numbers e stringhe hardcoded sparsi tra service/repository/views.
# ------------------------------------------------------------

# Ruoli sistema (enum config.ruolo_sistema nel DB)
RUOLO_ADMIN = "ADMIN"
RUOLO_OPERATIVO = "OPERATIVO"
RUOLO_DISABILITATO = "DISABILITATO"
DEFAULT_RUOLO_SISTEMA = RUOLO_OPERATIVO

# Sesso default per creazione soggetto PF
DEFAULT_SESSO = "M"

# Paginazione
DEFAULT_LIMIT = 50
MAX_LIMIT = 200
