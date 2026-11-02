# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Routing API per il dominio config (CRUD admin tabelle di sistema).
# ------------------------------------------------------------

from django.urls import path

from apps.config.api.views_utilities_tipi_ruolo import (
    UtilitiesTipiRuoloDetailView,
    UtilitiesTipiRuoloUsageView,
    UtilitiesTipiRuoloView,
)
from apps.config.api.views_tipi_ruolo_tipi_indirizzo import (
    TipiRuoloTipiIndirizzoDetailView,
    TipiRuoloTipiIndirizzoView,
)


urlpatterns = [
    # Matrice utilities x tipi_ruolo
    path(
        "utilities-tipi-ruolo/<int:record_id>/usage/",
        UtilitiesTipiRuoloUsageView.as_view(),
        name="config-utilities-tipi-ruolo-usage",
    ),
    path(
        "utilities-tipi-ruolo/<int:record_id>/",
        UtilitiesTipiRuoloDetailView.as_view(),
        name="config-utilities-tipi-ruolo-detail",
    ),
    path(
        "utilities-tipi-ruolo/",
        UtilitiesTipiRuoloView.as_view(),
        name="config-utilities-tipi-ruolo-list",
    ),
    # Matrice tipi_ruolo x tipi_indirizzo
    path(
        "tipi-ruolo-tipi-indirizzo/<int:record_id>/",
        TipiRuoloTipiIndirizzoDetailView.as_view(),
        name="config-tipi-ruolo-tipi-indirizzo-detail",
    ),
    path(
        "tipi-ruolo-tipi-indirizzo/",
        TipiRuoloTipiIndirizzoView.as_view(),
        name="config-tipi-ruolo-tipi-indirizzo-list",
    ),
]
