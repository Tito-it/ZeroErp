# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Dove stanno su disco i file degli allegati email: la radice e la
#        risoluzione di un `file_path` relativo, col guard contro il path
#        traversal.
# Note: ⭐ Sede unica per i due lettori del file — il download
#       (`EmailAllegatoDownloadView`) e l'invio SMTP (`EmailDispatchService`),
#       che fino al 2026-09-25 non allegava i file affatto. Sta in un modulo
#       suo perche' `email_outbox_service` importa `email_service`: la
#       risoluzione non poteva stare in nessuno dei due senza un import
#       circolare.
# ------------------------------------------------------------

from __future__ import annotations

import os

from django.conf import settings

from apps.core.services.error_manager import ErrorManager

# Il codice degli errori operativi sulle email: lo usano questo modulo e le view
# (`email_views`), che lo importano da qui.
E_EMAIL_OP = "E_EMAIL_OP"


# Scopo: La radice degli allegati, letta da settings a runtime (i test la
#        cambiano).
def radice_allegati() -> str:
    return getattr(settings, "EMAIL_ATTACHMENTS_ROOT", os.path.join(settings.BASE_DIR, "email_attachments"))


# Scopo: Il percorso assoluto di un allegato dal suo `file_path` relativo.
#        ⛔ Il percorso risolto deve restare DENTRO la radice: il `file_path`
#        viene dal database, e un valore come `../../etc/passwd` non deve
#        diventare un file letto (download) o spedito (SMTP).
def percorso_allegato(rel_path: str) -> str:
    root = os.path.normpath(radice_allegati())
    abs_path = os.path.normpath(os.path.join(root, rel_path))
    ErrorManager.require(
        abs_path.startswith(root + os.sep),
        code=E_EMAIL_OP, message="Path allegato non valido.",
    )
    return abs_path
