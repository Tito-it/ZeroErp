# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Pacchetto storage documentale. Espone l'interfaccia
#        astratta DocumentStorage e il selector get_storage()
#        che istanzia il provider attivo da config.parameters.
# ------------------------------------------------------------

from apps.documenti.services.storage.base import DocumentStorage, leggi_da_storage
from apps.documenti.services.storage.selector import get_storage

__all__ = ["DocumentStorage", "get_storage", "leggi_da_storage"]
