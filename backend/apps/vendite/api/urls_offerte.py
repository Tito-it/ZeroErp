# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: URL routing per CRUD vendite.offerte_commerciali.
#        Perimetro iniziale (D4): testata + cambio stato (emetti, registra-
#        esito, annulla) + eccezioni + utility 1:1. Endpoint per
#        crea-revisione e push-contratto saranno aggiunti quando il team DB
#        chiudera' step 7-8 del brief originale.
# ------------------------------------------------------------

from django.urls import path

from apps.vendite.api.views_offerte import (
    ApiOffertaAnnulla,
    ApiOffertaCreaRevisione,
    ApiOffertaDetail,
    ApiOffertaEccezioneDetail,
    ApiOffertaEccezioni,
    ApiOffertaEmetti,
    ApiOffertaRegistraEsito,
    ApiOffertaRevisioni,
    ApiOffertaUtility,
    ApiOffertaUtilityDetail,
    ApiOfferteList,
)

urlpatterns = [
    # Lista + creazione testata.
    path("", ApiOfferteList.as_view(), name="vendite-offerte-list"),
    path(
        "<int:offerta_id>/",
        ApiOffertaDetail.as_view(),
        name="vendite-offerta-detail",
    ),
    # Transizioni di stato manuali.
    path(
        "<int:offerta_id>/emetti/",
        ApiOffertaEmetti.as_view(),
        name="vendite-offerta-emetti",
    ),
    path(
        "<int:offerta_id>/registra-esito/",
        ApiOffertaRegistraEsito.as_view(),
        name="vendite-offerta-registra-esito",
    ),
    path(
        "<int:offerta_id>/annulla/",
        ApiOffertaAnnulla.as_view(),
        name="vendite-offerta-annulla",
    ),
    # Revisioni (Step 6-7 brief DB, atterrati 2026-05-25).
    path(
        "<int:offerta_id>/crea-revisione/",
        ApiOffertaCreaRevisione.as_view(),
        name="vendite-offerta-crea-revisione",
    ),
    path(
        "<int:offerta_id>/revisioni/",
        ApiOffertaRevisioni.as_view(),
        name="vendite-offerta-revisioni-list",
    ),
    # Eccezioni.
    path(
        "<int:offerta_id>/eccezioni/",
        ApiOffertaEccezioni.as_view(),
        name="vendite-offerta-eccezioni-list",
    ),
    path(
        "<int:offerta_id>/eccezioni/<int:eccezione_id>/",
        ApiOffertaEccezioneDetail.as_view(),
        name="vendite-offerta-eccezione-detail",
    ),
    # Utility 1:1.
    path(
        "<int:offerta_id>/utility/",
        ApiOffertaUtility.as_view(),
        name="vendite-offerta-utility",
    ),
    path(
        "<int:offerta_id>/utility/<int:utility_id>/",
        ApiOffertaUtilityDetail.as_view(),
        name="vendite-offerta-utility-detail",
    ),
]
