# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: URL routing per CRUD contratti v5 (F2-BE-06).
# ------------------------------------------------------------

from django.urls import path

from apps.vendite.api.views_contratti import (
    ApiContrattiList,
    ApiContrattoCambiaStato,
    ApiContrattoDetail,
    ApiContrattoRigaDetail,
    ApiContrattoRigheList,
    ApiContrattoRighePreview,
    ApiContrattoUtility,
)
from apps.vendite.api.views_form_defaults import ApiContrattoFormDefaults

urlpatterns = [
    # Form-defaults BA-aware (Fase 2.B3 refactor frontend vendite).
    # Risolve categoria_cliente_id_snapshot/utility/istanza dal BA + default
    # data/valido_dal da parameter (lead_gg).
    path(
        "form-defaults/",
        ApiContrattoFormDefaults.as_view(),
        name="vendite-contratto-form-defaults",
    ),
    path("", ApiContrattiList.as_view(), name="vendite-contratti-list"),
    path("<int:contratto_id>/", ApiContrattoDetail.as_view(), name="vendite-contratto-detail"),
    path(
        "<int:contratto_id>/cambia-stato/",
        ApiContrattoCambiaStato.as_view(),
        name="vendite-contratto-cambia-stato",
    ),
    path(
        "<int:contratto_id>/righe/",
        ApiContrattoRigheList.as_view(),
        name="vendite-contratto-righe-list",
    ),
    path(
        "<int:contratto_id>/righe-preview/",
        ApiContrattoRighePreview.as_view(),
        name="vendite-contratto-righe-preview",
    ),
    path(
        "<int:contratto_id>/righe/<int:riga_id>/",
        ApiContrattoRigaDetail.as_view(),
        name="vendite-contratto-riga-detail",
    ),
    path(
        "<int:contratto_id>/utility/",
        ApiContrattoUtility.as_view(),
        name="vendite-contratto-utility",
    ),
]
