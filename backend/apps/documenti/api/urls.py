# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: URL namespace `/api/v1/documenti/*` — endpoint read-only
#        v1 per template e versioni. CRUD admin (POST/PATCH) +
#        comandi versione (clona/pubblica/cancella-bozza) + endpoint
#        generazione/download atterrano in PR successive sullo
#        stesso namespace.
# ------------------------------------------------------------

from __future__ import annotations

from django.urls import path

from apps.documenti.api.views import (
    ApiAssetDetail,
    ApiAssetFileDownload,
    ApiAssetMiniatura,
    ApiAssetList,
    ApiContextBuilders,
    ApiTemplateDetail,
    ApiTemplateList,
    ApiTemplatePersonalizza,
    ApiTemplateRisoluzione,
    ApiTemplateVersioneClona,
    ApiTemplateVersioneDetail,
    ApiTemplateVersionePubblica,
    ApiTemplateVersioniList,
)

urlpatterns = [
    path(
        "context-builders/",
        ApiContextBuilders.as_view(),
        name="documenti-context-builders",
    ),
    path(
        "templates/",
        ApiTemplateList.as_view(),
        name="documenti-templates-list",
    ),
    # Con che cosa stampa ogni azienda (lettura del DB, K-5).
    path(
        "templates/risoluzione/",
        ApiTemplateRisoluzione.as_view(),
        name="documenti-templates-risoluzione",
    ),
    path(
        "templates/<int:template_id>/",
        ApiTemplateDetail.as_view(),
        name="documenti-templates-detail",
    ),
    # Comando sul modello standard: la copia per un emittente (D-2).
    path(
        "templates/<int:template_id>/personalizza/",
        ApiTemplatePersonalizza.as_view(),
        name="documenti-templates-personalizza",
    ),
    path(
        "templates/<int:template_id>/versioni/",
        ApiTemplateVersioniList.as_view(),
        name="documenti-templates-versioni-list",
    ),
    path(
        "templates/<int:template_id>/versioni/<int:versione_id>/",
        ApiTemplateVersioneDetail.as_view(),
        name="documenti-templates-versioni-detail",
    ),
    # Comandi versione (Tranche F): verbo come ultimo segmento
    # (non-CRUD, applicano guard e regole di transizione di stato).
    path(
        "templates/<int:template_id>/versioni/<int:versione_id>/clona/",
        ApiTemplateVersioneClona.as_view(),
        name="documenti-templates-versioni-clona",
    ),
    path(
        "templates/<int:template_id>/versioni/<int:versione_id>/pubblica/",
        ApiTemplateVersionePubblica.as_view(),
        name="documenti-templates-versioni-pubblica",
    ),
    # Asset documentali (Tranche G).
    path(
        "asset/",
        ApiAssetList.as_view(),
        name="documenti-asset-list",
    ),
    path(
        "asset/<int:asset_id>/",
        ApiAssetDetail.as_view(),
        name="documenti-asset-detail",
    ),
    path(
        "asset/<int:asset_id>/file/",
        ApiAssetFileDownload.as_view(),
        name="documenti-asset-file-download",
    ),
    path(
        "asset/<int:asset_id>/miniatura/",
        ApiAssetMiniatura.as_view(),
        name="documenti-asset-miniatura",
    ),
]
