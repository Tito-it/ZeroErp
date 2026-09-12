# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block per gli endpoint di export liste configurabili
#        (DEF-1). Estratto 2026-06-02 (regola del 2): le view export di
#        clienti/soggetti/fornitori/contratti condividevano la stessa coda
#        invariante (validazione formato, guard limite righe, risoluzione
#        colonne dalla config runtime, render + HttpResponse). Qui vive una
#        volta sola; ogni dominio mantiene solo il parsing dei propri filtri
#        e la chiamata al proprio service.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.http import HttpResponse
from rest_framework.request import Request

from apps.core.services.error_manager import ErrorManager
from apps.ui.db.ui_repository import UiRepository
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS, ListaExportService
from apps.ui.services.ui_service import UiService

_FORMATI_AMMESSI = ("csv", "xlsx")


# Scopo: Estrae e valida il query param `?formato=csv|xlsx`. Da chiamare in
#        cima alla view PRIMA di eseguire la query (evita lavoro inutile su
#        formato invalido). Ritorna il formato normalizzato lowercase.
def parse_export_format(request: Request) -> str:
    fmt = (request.query_params.get("formato") or "csv").strip().lower()
    ErrorManager.require(
        fmt in _FORMATI_AMMESSI,
        code="E_UI_EXPORT_FORMAT_INVALID",
        message="Formato export non supportato.",
        detail=f"format='{fmt}', ammessi={list(_FORMATI_AMMESSI)}",
    )
    return fmt


# Scopo: Coda invariante dell'export. Riceve le righe gia' fetchate dal
#        repository del dominio (chiamato con `limit=EXPORT_MAX_ROWS + 1` per
#        intercettare l'overflow) e produce la HttpResponse col file.
#        Passi: guard limite -> colonne coerenti con la DataTable a video
#        (config runtime: preferenza+preset+permessi) -> render -> response
#        con Content-Disposition. NB: `filtri_applicati` viene incluso come
#        metadato nel file (DEF-1 §6).
def build_export_response(
    request: Request,
    *,
    lista_codice: str,
    results: list[dict[str, Any]],
    total: int,
    filtri_applicati: dict[str, Any] | None,
    fmt: str,
) -> HttpResponse:
    ErrorManager.require(
        int(total or 0) <= EXPORT_MAX_ROWS,
        code="E_UI_EXPORT_LIMIT_EXCEEDED",
        message="Export oltre il limite consentito.",
        detail=f"matched={total}, max={EXPORT_MAX_ROWS}. Raffinare i filtri.",
        context={"matched": total, "limit": EXPORT_MAX_ROWS},
    )

    config = UiService().get_lista_config(request.user, lista_codice)
    metadata = UiRepository().list_colonne_by_codice(lista_codice)
    colonne = ListaExportService.select_colonne_visibili_da_config(config, metadata)

    body, content_type, filename = ListaExportService().render(
        lista_codice=lista_codice,
        colonne=colonne,
        righe=results,
        filtri_applicati=filtri_applicati,
        formato=fmt,
    )

    response = HttpResponse(body, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
