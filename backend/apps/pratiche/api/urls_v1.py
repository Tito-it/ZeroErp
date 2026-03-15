# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Routing API v1 modulo pratiche.
#        Tutti gli endpoint sotto /api/v1/pratiche/.
# ------------------------------------------------------------

from django.urls import path

from apps.pratiche.api.views import (
    ApiFormuleTempo,
    ApiPraticaAssegnazione,
    ApiPraticaCalcoliTempo,
    ApiPraticaDetail,
    ApiPraticaFlussiList,
    ApiPraticaFlussoCanali,
    ApiPraticaFlussoDetail,
    ApiPraticaFlussoGenera,
    ApiPraticaFlussoPraticheGenerate,
    ApiPraticaFlussoPrerequisiti,
    ApiPraticaFlussoRegoleGenerazione,
    ApiPraticaFlussoRiattiva,
    ApiPraticaFlussoSospendi,
    ApiPraticaFlussoStato,
    ApiPraticaGiornale,
    ApiPraticaRiattiva,
    ApiPraticaSospendi,
    ApiPraticaSospensioni,
    ApiPraticaStato,
    ApiPraticheList,
)

urlpatterns = [
    # --- Formule tempo ---
    path("formule-tempo/", ApiFormuleTempo.as_view(), name="pratiche-formule-tempo"),
    # --- Pratiche ---
    path("", ApiPraticheList.as_view(), name="pratiche-list"),
    path("<int:pratica_id>/", ApiPraticaDetail.as_view(), name="pratiche-detail"),
    path("<int:pratica_id>/stato/", ApiPraticaStato.as_view(), name="pratiche-stato"),
    path("<int:pratica_id>/assegnazione/", ApiPraticaAssegnazione.as_view(), name="pratiche-assegnazione"),
    path("<int:pratica_id>/giornale/", ApiPraticaGiornale.as_view(), name="pratiche-giornale"),
    path("<int:pratica_id>/sospendi/", ApiPraticaSospendi.as_view(), name="pratiche-sospendi"),
    path("<int:pratica_id>/riattiva/", ApiPraticaRiattiva.as_view(), name="pratiche-riattiva"),
    path("<int:pratica_id>/sospensioni/", ApiPraticaSospensioni.as_view(), name="pratiche-sospensioni"),
    path("<int:pratica_id>/calcoli-tempo/", ApiPraticaCalcoliTempo.as_view(), name="pratiche-calcoli-tempo"),
    # --- Flussi ---
    path("<int:pratica_id>/flussi/", ApiPraticaFlussiList.as_view(), name="pratiche-flussi-list"),
    path("<int:pratica_id>/flussi/<int:flusso_id>/", ApiPraticaFlussoDetail.as_view(), name="pratiche-flusso-detail"),
    path("<int:pratica_id>/flussi/<int:flusso_id>/stato/", ApiPraticaFlussoStato.as_view(), name="pratiche-flusso-stato"),
    path("<int:pratica_id>/flussi/<int:flusso_id>/prerequisiti/", ApiPraticaFlussoPrerequisiti.as_view(), name="pratiche-flusso-prerequisiti"),
    path("<int:pratica_id>/flussi/<int:flusso_id>/canali/", ApiPraticaFlussoCanali.as_view(), name="pratiche-flusso-canali"),
    # --- Generazione cross-pratica ---
    path("<int:pratica_id>/flussi/<int:flusso_id>/regole-generazione/", ApiPraticaFlussoRegoleGenerazione.as_view(), name="pratiche-flusso-regole-generazione"),
    path("<int:pratica_id>/flussi/<int:flusso_id>/genera/", ApiPraticaFlussoGenera.as_view(), name="pratiche-flusso-genera"),
    path("<int:pratica_id>/flussi/<int:flusso_id>/pratiche-generate/", ApiPraticaFlussoPraticheGenerate.as_view(), name="pratiche-flusso-pratiche-generate"),
    # --- Sospensioni flusso ---
    path("<int:pratica_id>/flussi/<int:flusso_id>/sospendi/", ApiPraticaFlussoSospendi.as_view(), name="pratiche-flusso-sospendi"),
    path("<int:pratica_id>/flussi/<int:flusso_id>/riattiva/", ApiPraticaFlussoRiattiva.as_view(), name="pratiche-flusso-riattiva"),
]
