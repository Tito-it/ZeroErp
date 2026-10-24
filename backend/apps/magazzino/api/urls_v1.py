# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Routing API v1 del dominio magazzino — tutto sotto /api/v1/magazzino/:
#        il documento interno, le anagrafiche (magazzini, ubicazioni, lotti), i
#        lookup di riga, la consultazione.
# Note: ⚠️ L'ORDINE conta. Le rotte piu' specifiche stanno PRIMA del pattern
#       generico `<int:doc_id>/`, che altrimenti le intercetta.
#
#       ⭐ Le rotte del documento interno nascono UNA volta per famiglia da
#       `_rotte_documento_interno`: inventari e rettifiche hanno la stessa
#       forma, e due elenchi scritti a mano divergono al primo verbo nuovo.
# ------------------------------------------------------------

from django.urls import path

from apps.magazzino.api.views_anagrafiche import (
    ApiLottiExport,
    ApiLottiList,
    ApiLottoDetail,
    ApiMagazziniExport,
    ApiMagazziniList,
    ApiMagazzinoDetail,
    ApiUbicazioneDetail,
    ApiUbicazioniExport,
    ApiUbicazioniList,
)
from apps.magazzino.api.views import (
    VISTE_INVENTARI,
    VISTE_RETTIFICHE,
    ApiAssetsLookup,
    ApiDisponibilita,
    ApiDisponibilitaArticoli,
    ApiDisponibilitaArticoliExport,
    ApiDisponibilitaBlocchi,
    ApiDisponibilitaBloccoLibera,
    ApiDisponibilitaExport,
    ApiLottiLookup,
    ApiMagazzinoUbicazioniLookup,
    ApiMovimenti,
    ApiMovimentiExport,
    ApiRigheMotivi,
)


# Scopo: le rotte di UNA famiglia di documento interno, sotto `<famiglia>/`.
def _rotte_documento_interno(famiglia: str, viste: dict) -> list:
    base = f"{famiglia}/"
    nome = f"magazzino-{famiglia}"
    rotte = [
        path(base, viste["lista"].as_view(), name=f"{nome}-list"),
        # ⭐ `export/` e' una rotta SORELLA della lista: sotto `<famiglia>/`
        #    c'e' il pattern `<int:doc_id>/`, che `export` (non intero) non
        #    matcha — ma la forma resta quella della famiglia.
        path(f"{base}export/", viste["lista_export"].as_view(), name=f"{nome}-export"),
        # Sotto-risorse e azioni PRIMA del dettaglio generico.
        path(f"{base}<int:doc_id>/righe/", viste["righe"].as_view(), name=f"{nome}-righe"),
        path(f"{base}<int:doc_id>/righe/export/", viste["righe_export"].as_view(), name=f"{nome}-righe-export"),
        path(f"{base}<int:doc_id>/righe/<int:riga_id>/", viste["riga"].as_view(), name=f"{nome}-riga-detail"),
        path(f"{base}<int:doc_id>/stato/", viste["stato"].as_view(), name=f"{nome}-stato"),
        path(f"{base}<int:doc_id>/registra/", viste["registra"].as_view(), name=f"{nome}-registra"),
    ]
    if "piano" in viste:
        rotte += [
            path(f"{base}<int:doc_id>/piano/", viste["piano"].as_view(), name=f"{nome}-piano"),
            path(f"{base}<int:doc_id>/piano/export/", viste["piano_export"].as_view(), name=f"{nome}-piano-export"),
        ]
    rotte.append(path(f"{base}<int:doc_id>/", viste["dettaglio"].as_view(), name=f"{nome}-detail"))
    return rotte


urlpatterns = [
    # --- Il documento interno: inventari e rettifiche, stessa forma ---
    *_rotte_documento_interno("inventari", VISTE_INVENTARI),
    *_rotte_documento_interno("rettifiche", VISTE_RETTIFICHE),
    # --- L'anteprima dei motivi di una riga (la stessa check del piano) ---
    path("righe/motivi/", ApiRigheMotivi.as_view(), name="magazzino-righe-motivi"),
    # --- Le anagrafiche: magazzini, ubicazioni (figlie), lotti (dell'articolo) ---
    # ⚠️ `export/` e `lookup/` PRIMA dei pattern `<int:…>/` che li intercetterebbero.
    path("magazzini/", ApiMagazziniList.as_view(), name="magazzino-magazzini-list"),
    path("magazzini/export/", ApiMagazziniExport.as_view(), name="magazzino-magazzini-export"),
    path(
        "magazzini/<int:magazzino_id>/ubicazioni/",
        ApiUbicazioniList.as_view(),
        name="magazzino-ubicazioni-list",
    ),
    path(
        "magazzini/<int:magazzino_id>/ubicazioni/export/",
        ApiUbicazioniExport.as_view(),
        name="magazzino-ubicazioni-export",
    ),
    path(
        "magazzini/<int:magazzino_id>/ubicazioni/lookup/",
        ApiMagazzinoUbicazioniLookup.as_view(),
        name="magazzino-ubicazioni-lookup",
    ),
    path(
        "magazzini/<int:magazzino_id>/ubicazioni/<int:ubicazione_id>/",
        ApiUbicazioneDetail.as_view(),
        name="magazzino-ubicazioni-detail",
    ),
    path("magazzini/<int:magazzino_id>/", ApiMagazzinoDetail.as_view(), name="magazzino-magazzini-detail"),
    path("lotti/", ApiLottiList.as_view(), name="magazzino-lotti-list"),
    path("lotti/export/", ApiLottiExport.as_view(), name="magazzino-lotti-export"),
    path("lotti/lookup/", ApiLottiLookup.as_view(), name="magazzino-lotti-lookup"),
    path("lotti/<int:lotto_id>/", ApiLottoDetail.as_view(), name="magazzino-lotti-detail"),
    # --- Il lookup dei seriali ---
    path("assets/lookup/", ApiAssetsLookup.as_view(), name="magazzino-assets-lookup"),
    # --- Consultazione: la disponibilita' e il registro ---
    path("disponibilita/", ApiDisponibilita.as_view(), name="magazzino-disponibilita-list"),
    path("disponibilita/export/", ApiDisponibilitaExport.as_view(), name="magazzino-disponibilita-export"),
    path("disponibilita/articoli/", ApiDisponibilitaArticoli.as_view(), name="magazzino-disponibilita-articoli-list"),
    path(
        "disponibilita/articoli/export/",
        ApiDisponibilitaArticoliExport.as_view(),
        name="magazzino-disponibilita-articoli-export",
    ),
    path("disponibilita/blocchi/", ApiDisponibilitaBlocchi.as_view(), name="magazzino-disponibilita-blocchi"),
    path(
        "disponibilita/blocchi/<int:blocco_id>/libera/",
        ApiDisponibilitaBloccoLibera.as_view(),
        name="magazzino-disponibilita-blocco-libera",
    ),
    path("movimenti/", ApiMovimenti.as_view(), name="magazzino-movimenti-list"),
    path("movimenti/export/", ApiMovimentiExport.as_view(), name="magazzino-movimenti-export"),
]
