# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Helper condivisi per le view multipart del building block
#        "genera documento + allegati" (offerta, preventivo, contratto, ...).
#        Centralizza l'estrazione degli allegati upload nel formato neutro
#        consumato da `DocumentGenerationService.genera_documento(allegati=...)`,
#        evitando di duplicare la stessa funzione in ogni
#        `<sorgente>_documenti_views.py`.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from rest_framework.request import Request


# Scopo: Estrae gli allegati multipart dal request (campo `allegati` ripetuto)
#        in forma neutra `{file_bytes, mime_type, file_name}`, consumabile dal
#        service senza dipendere dall'oggetto `UploadedFile` di Django. Lista
#        vuota se nessun file: il flusso persiste solo il PDF principale.
def extract_allegati(request: Request) -> list[dict[str, Any]]:
    files = request.FILES.getlist("allegati")
    allegati: list[dict[str, Any]] = []
    for uploaded in files:
        allegati.append({
            "file_bytes": uploaded.read(),
            "mime_type": getattr(uploaded, "content_type", "") or "",
            "file_name": getattr(uploaded, "name", "") or "",
        })
    return allegati
