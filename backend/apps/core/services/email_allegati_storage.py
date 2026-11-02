# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
from apps.core.services.error_messages_fallback import USER_MESSAGE_FALLBACK

# Il codice degli errori operativi sulle email: lo usano le view
# (`email_views`), che lo importano da qui.
E_EMAIL_OP = "E_EMAIL_OP"
# Il percorso dell'allegato esce dalla radice. ⛔ TECNICO (500), non un dato
# errato: il `file_path` viene dal database, non da una persona — e' un dato
# corrotto o manomesso, un evento da guardare (R-7 di
# brief-db-codici-non-trovato-email-e-permessi).
E_EMAIL_ALLEGATO_PERCORSO_NON_VALIDO = "E_EMAIL_ALLEGATO_PERCORSO_NON_VALIDO"


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
        code=E_EMAIL_ALLEGATO_PERCORSO_NON_VALIDO,
        message=USER_MESSAGE_FALLBACK[E_EMAIL_ALLEGATO_PERCORSO_NON_VALIDO],
        detail=f"file_path={rel_path!r}",
    )
    return abs_path
