# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Routing API v1 modulo pratiche.
#        Tutti gli endpoint sotto /api/v1/pratiche/.
# ------------------------------------------------------------

from django.urls import path

from apps.pratiche.api.views_definizioni import (
    ApiDefinizioneFork,
    ApiDefinizioneNuovaVersione,
    ApiDefinizionePubblica,
    ApiDefinizioniWorkflow,
)
from apps.pratiche.api.views import (
    ApiCodaLavoro,
    ApiCompetenzaFlussoDetail,
    ApiCompetenzeFlussiList,
    ApiFormuleTempo,
    ApiOperatoriReparto,
    ApiPraticaAllegatoDetail,
    ApiPraticaAllegatiList,
    ApiPraticaAssegnazione,
    ApiPraticaCalcoliTempo,
    ApiPraticaDetail,
    ApiPraticaFlussiList,
    ApiPraticaFlussoAssegnazione,
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
    ApiPraticaPercorso,
    ApiPraticaNotaDetail,
    ApiPraticaNoteList,
    ApiPraticaRiattiva,
    ApiPraticaSospendi,
    ApiPraticaSospensioni,
    ApiPraticaStato,
    ApiPraticheList,
    ApiPrendiInCarico,
)

urlpatterns = [
    # --- Coda lavoro e competenze ---
    path("coda-lavoro/", ApiCodaLavoro.as_view(), name="pratiche-coda-lavoro"),
    path("operatori/", ApiOperatoriReparto.as_view(), name="pratiche-operatori-reparto"),
    path("competenze-flussi/", ApiCompetenzeFlussiList.as_view(), name="pratiche-competenze-flussi-list"),
    path("competenze-flussi/<int:competenza_id>/", ApiCompetenzaFlussoDetail.as_view(), name="pratiche-competenza-flusso-detail"),
    # --- Formule tempo ---
    path("formule-tempo/", ApiFormuleTempo.as_view(), name="pratiche-formule-tempo"),
    # --- Definizioni workflow versionate (admin, Fase 2) ---
    path("definizioni/", ApiDefinizioniWorkflow.as_view(), name="pratiche-definizioni-list"),
    path("definizioni/<int:definizione_id>/fork/", ApiDefinizioneFork.as_view(), name="pratiche-definizione-fork"),
    path("definizioni/<int:definizione_id>/nuova-versione/", ApiDefinizioneNuovaVersione.as_view(), name="pratiche-definizione-nuova-versione"),
    path("definizioni/<int:definizione_id>/pubblica/", ApiDefinizionePubblica.as_view(), name="pratiche-definizione-pubblica"),
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
    # --- Note ---
    path("<int:pratica_id>/note/", ApiPraticaNoteList.as_view(), name="pratiche-note-list"),
    path("<int:pratica_id>/note/<int:nota_id>/", ApiPraticaNotaDetail.as_view(), name="pratiche-nota-detail"),
    # --- Allegati ---
    path("<int:pratica_id>/allegati/", ApiPraticaAllegatiList.as_view(), name="pratiche-allegati-list"),
    path("<int:pratica_id>/allegati/<int:allegato_id>/", ApiPraticaAllegatoDetail.as_view(), name="pratiche-allegato-detail"),
    # --- Flussi ---
    path("<int:pratica_id>/percorso/", ApiPraticaPercorso.as_view(), name="pratiche-percorso"),
    path("<int:pratica_id>/flussi/", ApiPraticaFlussiList.as_view(), name="pratiche-flussi-list"),
    path("<int:pratica_id>/flussi/<int:flusso_id>/", ApiPraticaFlussoDetail.as_view(), name="pratiche-flusso-detail"),
    path("<int:pratica_id>/flussi/<int:flusso_id>/stato/", ApiPraticaFlussoStato.as_view(), name="pratiche-flusso-stato"),
    path("<int:pratica_id>/flussi/<int:flusso_id>/assegnazione/", ApiPraticaFlussoAssegnazione.as_view(), name="pratiche-flusso-assegnazione"),
    path("<int:pratica_id>/flussi/<int:flusso_id>/prerequisiti/", ApiPraticaFlussoPrerequisiti.as_view(), name="pratiche-flusso-prerequisiti"),
    path("<int:pratica_id>/flussi/<int:flusso_id>/canali/", ApiPraticaFlussoCanali.as_view(), name="pratiche-flusso-canali"),
    # --- Generazione cross-pratica ---
    path("<int:pratica_id>/flussi/<int:flusso_id>/regole-generazione/", ApiPraticaFlussoRegoleGenerazione.as_view(), name="pratiche-flusso-regole-generazione"),
    path("<int:pratica_id>/flussi/<int:flusso_id>/genera/", ApiPraticaFlussoGenera.as_view(), name="pratiche-flusso-genera"),
    path("<int:pratica_id>/flussi/<int:flusso_id>/pratiche-generate/", ApiPraticaFlussoPraticheGenerate.as_view(), name="pratiche-flusso-pratiche-generate"),
    # --- Prendi in carico flusso ---
    path("flussi/<int:flusso_id>/prendi-in-carico/", ApiPrendiInCarico.as_view(), name="pratiche-flusso-prendi-in-carico"),
    # --- Sospensioni flusso ---
    path("<int:pratica_id>/flussi/<int:flusso_id>/sospendi/", ApiPraticaFlussoSospendi.as_view(), name="pratiche-flusso-sospendi"),
    path("<int:pratica_id>/flussi/<int:flusso_id>/riattiva/", ApiPraticaFlussoRiattiva.as_view(), name="pratiche-flusso-riattiva"),
]
