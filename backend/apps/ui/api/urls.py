# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: URL namespace `/api/v1/ui/*` — endpoint personalizzazioni
#        liste (config, catalogo, preferenza upsert/delete).
# ------------------------------------------------------------

from __future__ import annotations

from django.urls import path

from apps.ui.api.views import (
    ApiListaCatalogoView,
    ApiListaConfigView,
    ApiListaPreferenzaView,
)


# `codice` ammette punto e due punti (convenzione `<schema>.<entita>`
# o `<schema>.<entita>:<contesto>`). Il converter `<str:>` di default
# rifiuta lo slash, gli altri caratteri passano: nessun rischio di
# collisioni con sotto-risorse.
urlpatterns = [
    path(
        "liste/<str:codice>/config/",
        ApiListaConfigView.as_view(),
        name="ui-liste-config",
    ),
    path(
        "liste/<str:codice>/catalogo/",
        ApiListaCatalogoView.as_view(),
        name="ui-liste-catalogo",
    ),
    path(
        "liste/<str:codice>/preferenza/",
        ApiListaPreferenzaView.as_view(),
        name="ui-liste-preferenza",
    ),
]
