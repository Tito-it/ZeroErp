# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Routing API v1 del dominio pagamenti — tutto sotto /api/v1/pagamenti/.
# Note: ⚠️ L'ORDINE conta. Le rotte piu' specifiche stanno PRIMA del pattern
#       generico `<int:contabile_id>/`, che altrimenti le intercetta.
# ------------------------------------------------------------

from django.urls import path

from apps.pagamenti.api.views import (
    ApiDistintaAnteprimaRegistrazione,
    ApiDistintaDetail,
    ApiDistintaRegistra,
    ApiDistintaRighe,
    ApiDistintaStato,
    ApiDistinteList,
    ApiRigaDetail,
    ApiRigaStato,
)

urlpatterns = [
    # --- Distinte contabili ---
    path("distinte/", ApiDistinteList.as_view(), name="pagamenti-distinte-list"),
    # Sotto-risorse e azioni PRIMA del dettaglio generico.
    path(
        "distinte/<int:contabile_id>/righe/",
        ApiDistintaRighe.as_view(),
        name="pagamenti-distinta-righe",
    ),
    path(
        "distinte/<int:contabile_id>/stato/",
        ApiDistintaStato.as_view(),
        name="pagamenti-distinta-stato",
    ),
    path(
        "distinte/<int:contabile_id>/anteprima-registrazione/",
        ApiDistintaAnteprimaRegistrazione.as_view(),
        name="pagamenti-distinta-anteprima-registrazione",
    ),
    path(
        "distinte/<int:contabile_id>/registra/",
        ApiDistintaRegistra.as_view(),
        name="pagamenti-distinta-registra",
    ),
    path(
        "distinte/<int:contabile_id>/",
        ApiDistintaDetail.as_view(),
        name="pagamenti-distinta-detail",
    ),
    # --- Righe contabili (indirizzate per id proprio, non sotto la distinta:
    #     una riga si lavora anche dalla coda del riconciliatore, dove la
    #     distinta di appartenenza non e' il contesto) ---
    path(
        "righe/<int:riga_id>/stato/",
        ApiRigaStato.as_view(),
        name="pagamenti-riga-stato",
    ),
    path("righe/<int:riga_id>/", ApiRigaDetail.as_view(), name="pagamenti-riga-detail"),
]
