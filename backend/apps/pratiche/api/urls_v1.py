# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Routing API v1 modulo pratiche.
#        Tutti gli endpoint sotto /api/v1/pratiche/.
# ------------------------------------------------------------

from django.urls import path

from apps.pratiche.api.views import (
    ApiFormuleTempoV1,
    ApiPraticaAssegnazioneV1,
    ApiPraticaCalcoliTempoV1,
    ApiPraticaDetailV1,
    ApiPraticaFlussiListV1,
    ApiPraticaFlussoCanaliV1,
    ApiPraticaFlussoDetailV1,
    ApiPraticaFlussoGeneraV1,
    ApiPraticaFlussoPraticheGenerateV1,
    ApiPraticaFlussoPrerequistiV1,
    ApiPraticaFlussoRegoleGenerazioneV1,
    ApiPraticaFlussoRiattivaV1,
    ApiPraticaFlussoSospendiV1,
    ApiPraticaFlussoStatoV1,
    ApiPraticaGiornaleV1,
    ApiPraticaRiattivaV1,
    ApiPraticaSospendiV1,
    ApiPraticaSospensioniV1,
    ApiPraticaStatoV1,
    ApiPraticheListV1,
)

urlpatterns = [
    # --- Formule tempo ---
    path("formule-tempo/", ApiFormuleTempoV1.as_view(), name="pratiche-v1-formule-tempo"),
    # --- Pratiche ---
    path("", ApiPraticheListV1.as_view(), name="pratiche-v1-list"),
    path("<int:pratica_id>/", ApiPraticaDetailV1.as_view(), name="pratiche-v1-detail"),
    path("<int:pratica_id>/stato/", ApiPraticaStatoV1.as_view(), name="pratiche-v1-stato"),
    path("<int:pratica_id>/assegnazione/", ApiPraticaAssegnazioneV1.as_view(), name="pratiche-v1-assegnazione"),
    path("<int:pratica_id>/giornale/", ApiPraticaGiornaleV1.as_view(), name="pratiche-v1-giornale"),
    path("<int:pratica_id>/sospendi/", ApiPraticaSospendiV1.as_view(), name="pratiche-v1-sospendi"),
    path("<int:pratica_id>/riattiva/", ApiPraticaRiattivaV1.as_view(), name="pratiche-v1-riattiva"),
    path("<int:pratica_id>/sospensioni/", ApiPraticaSospensioniV1.as_view(), name="pratiche-v1-sospensioni"),
    path("<int:pratica_id>/calcoli-tempo/", ApiPraticaCalcoliTempoV1.as_view(), name="pratiche-v1-calcoli-tempo"),
    # --- Flussi ---
    path("<int:pratica_id>/flussi/", ApiPraticaFlussiListV1.as_view(), name="pratiche-v1-flussi-list"),
    path("<int:pratica_id>/flussi/<int:flusso_id>/", ApiPraticaFlussoDetailV1.as_view(), name="pratiche-v1-flusso-detail"),
    path("<int:pratica_id>/flussi/<int:flusso_id>/stato/", ApiPraticaFlussoStatoV1.as_view(), name="pratiche-v1-flusso-stato"),
    path("<int:pratica_id>/flussi/<int:flusso_id>/prerequisiti/", ApiPraticaFlussoPrerequistiV1.as_view(), name="pratiche-v1-flusso-prerequisiti"),
    path("<int:pratica_id>/flussi/<int:flusso_id>/canali/", ApiPraticaFlussoCanaliV1.as_view(), name="pratiche-v1-flusso-canali"),
    # --- Generazione cross-pratica ---
    path("<int:pratica_id>/flussi/<int:flusso_id>/regole-generazione/", ApiPraticaFlussoRegoleGenerazioneV1.as_view(), name="pratiche-v1-flusso-regole-generazione"),
    path("<int:pratica_id>/flussi/<int:flusso_id>/genera/", ApiPraticaFlussoGeneraV1.as_view(), name="pratiche-v1-flusso-genera"),
    path("<int:pratica_id>/flussi/<int:flusso_id>/pratiche-generate/", ApiPraticaFlussoPraticheGenerateV1.as_view(), name="pratiche-v1-flusso-pratiche-generate"),
    # --- Sospensioni flusso ---
    path("<int:pratica_id>/flussi/<int:flusso_id>/sospendi/", ApiPraticaFlussoSospendiV1.as_view(), name="pratiche-v1-flusso-sospendi"),
    path("<int:pratica_id>/flussi/<int:flusso_id>/riattiva/", ApiPraticaFlussoRiattivaV1.as_view(), name="pratiche-v1-flusso-riattiva"),
]
