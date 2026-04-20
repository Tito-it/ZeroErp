# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: URL namespace `/api/v1/portale/*` — endpoint flussi auth portale
#        + (futuri) endpoint MVP (me, billing-account, fatture, scadenze,
#        ordini-ricevuti, pagamenti).
# ------------------------------------------------------------

from __future__ import annotations

from django.urls import path

from apps.portale.api.views import (
    AttivazionePortaleValidateView,
    AttivazionePortaleView,
)

urlpatterns = [
    # Flussi auth portale (pubblici, no JWT richiesto).
    path(
        "attivazione/validate/<str:token>/",
        AttivazionePortaleValidateView.as_view(),
        name="portale-attivazione-validate",
    ),
    path(
        "attivazione/conferma/",
        AttivazionePortaleView.as_view(),
        name="portale-attivazione-conferma",
    ),
]
