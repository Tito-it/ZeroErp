# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: URL patterns per preventivi vendita (/api/v1/vendite/preventivi/).
# ------------------------------------------------------------

from django.urls import path

from apps.vendite.api.preventivi_views import (
    ApiPreventiviList,
    ApiPreventivoDetail,
    ApiPreventivoGeneraPratica,
    ApiPreventivoIndirizzi,
    ApiPreventivoPratiche,
    ApiPreventivoPushCommessa,
    ApiPreventivoRevisione,
    ApiPreventivoRigaDetail,
    ApiPreventivoRigaSuggerisciPrezzo,
    ApiPreventivoRigheList,
    ApiPreventivoStato,
    ApiPreventivoStatoFatturazione,
)

urlpatterns = [
    # Testata: lista + creazione
    path("", ApiPreventiviList.as_view(), name="vendite-preventivi-list"),
    # Testata: dettaglio + aggiornamento
    path(
        "<int:preventivo_id>/",
        ApiPreventivoDetail.as_view(),
        name="vendite-preventivi-detail",
    ),
    # Cambio stato
    path(
        "<int:preventivo_id>/stato/",
        ApiPreventivoStato.as_view(),
        name="vendite-preventivi-stato",
    ),
    # Revisione
    path(
        "<int:preventivo_id>/revisione/",
        ApiPreventivoRevisione.as_view(),
        name="vendite-preventivi-revisione",
    ),
    # Righe: lista + creazione
    path(
        "<int:preventivo_id>/righe/",
        ApiPreventivoRigheList.as_view(),
        name="vendite-preventivi-righe-list",
    ),
    # Righe: aggiornamento + eliminazione
    path(
        "<int:preventivo_id>/righe/<int:riga_id>/",
        ApiPreventivoRigaDetail.as_view(),
        name="vendite-preventivi-righe-detail",
    ),
    # Righe: suggerimento prezzo via pricing resolver v5
    path(
        "<int:preventivo_id>/righe/suggerisci-prezzo/",
        ApiPreventivoRigaSuggerisciPrezzo.as_view(),
        name="vendite-preventivi-righe-suggerisci-prezzo",
    ),
    # Indirizzi
    path(
        "<int:preventivo_id>/indirizzi/",
        ApiPreventivoIndirizzi.as_view(),
        name="vendite-preventivi-indirizzi",
    ),
    # Integrazione: push commessa
    path(
        "<int:preventivo_id>/push-commessa/",
        ApiPreventivoPushCommessa.as_view(),
        name="vendite-preventivi-push-commessa",
    ),
    # Integrazione: stato fatturazione
    path(
        "<int:preventivo_id>/stato-fatturazione/",
        ApiPreventivoStatoFatturazione.as_view(),
        name="vendite-preventivi-stato-fatturazione",
    ),
    # Integrazione: genera pratica
    path(
        "<int:preventivo_id>/genera-pratica/",
        ApiPreventivoGeneraPratica.as_view(),
        name="vendite-preventivi-genera-pratica",
    ),
    # Integrazione: pratiche collegate
    path(
        "<int:preventivo_id>/pratiche/",
        ApiPreventivoPratiche.as_view(),
        name="vendite-preventivi-pratiche",
    ),
]
