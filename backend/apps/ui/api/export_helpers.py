# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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

from collections.abc import Mapping, Sequence

from typing import Any

from django.http import HttpResponse
from rest_framework.request import Request

# ⚠️ Il MODULO, non il nome: `soglia_ricerca` si legge a ogni chiamata da
#    `_helpers`, cosi' il fake di progetto (`catalogo_ricerca_finto`) la
#    sostituisce anche qui.
from apps.core.db import _helpers as db_helpers
from apps.core.services.error_manager import ErrorManager
from apps.ui.db.ui_repository import UiRepository
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS, ListaExportService
from apps.ui.services.ui_service import UiService

_FORMATI_AMMESSI = ("csv", "xlsx")

# La ricerca libera nel file si dichiara con UNA chiave sola, qui.
_CHIAVE_RICERCA = "Ricerca"
# ⚠️ Le chiavi con cui le view la dichiaravano da se' fino al 2026-09-29:
#    tolte dal dict del caller, o la ricerca comparirebbe due volte. `search`
#    resta nei dict dei filtri di magazzino e dei cruscotti, che sono gli
#    argomenti della QUERY riusati come metadato: li' non si toglie, lo
#    ignora il BB.
_CHIAVI_RICERCA_DEL_CALLER = ("search", _CHIAVE_RICERCA)


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


# Scopo: I filtri che il file dichiara: quelli del caller PIU' la ricerca
#        libera, che si legge dalla richiesta e non dal caller.
# ⭐ PERCHE' QUI (2026-09-29, regola del 2, ok Tid): la dichiaravano le view,
#    ciascuna a modo suo — `"Ricerca"` nei `resolve_filtri_export_label`,
#    `"search"` in magazzino e fatture — e chi se ne dimenticava (righe della
#    distinta, righe di inventario e rettifica) consegnava un file filtrato
#    con `# Filtri applicati: {}`: un sottoinsieme che si presenta come
#    l'insieme, senza nessun errore (rilievo in-app di Tid).
# ⭐ Si dichiara SOLO se ha filtrato davvero: dopo lo `strip`, alla soglia
#    della lista (`soglia_ricerca`, la stessa di `add_ricerca_full_condition`).
#    Un termine di due caratteri non filtra, e scriverlo nel file mentirebbe.
# ⚠️ Invariante su cui poggia (verificato il 2026-09-29 su tutte le view
#    export): una lista con colonne `ricercabile_full` applica `search` anche
#    nell'export; una senza non le mostra la casella, e il frontend non lo
#    manda. Un export che ignorasse una ricerca applicata a video sarebbe un
#    difetto suo — il file non sarebbe la lista che l'operatore vede.
def filtri_export_con_ricerca(
    request: Request,
    *,
    lista_codice: str,
    filtri_applicati: dict[str, Any] | None,
) -> dict[str, Any] | None:
    filtri = {
        k: v for k, v in (filtri_applicati or {}).items()
        if k not in _CHIAVI_RICERCA_DEL_CALLER
    }
    termine = (request.query_params.get("search") or "").strip()
    if termine and len(termine) >= db_helpers.soglia_ricerca(lista_codice):
        filtri = {_CHIAVE_RICERCA: termine, **filtri}
    return filtri or None


# Scopo: Coda invariante dell'export. Riceve le righe gia' fetchate dal
#        repository del dominio (chiamato con `limit=EXPORT_MAX_ROWS + 1` per
#        intercettare l'overflow) e produce la HttpResponse col file.
#        Passi: guard limite -> colonne coerenti con la DataTable a video
#        (config runtime: preferenza+preset+permessi) -> render -> response
#        con Content-Disposition. NB: `filtri_applicati` viene incluso come
#        metadato nel file (DEF-1 §6), con la ricerca libera aggiunta QUI
#        (`filtri_export_con_ricerca`): il caller dichiara solo i suoi filtri.
def build_export_response(
    request: Request,
    *,
    lista_codice: str,
    results: Sequence[Mapping[str, Any]],
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
        filtri_applicati=filtri_export_con_ricerca(
            request, lista_codice=lista_codice, filtri_applicati=filtri_applicati,
        ),
        formato=fmt,
    )

    response = HttpResponse(body, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
