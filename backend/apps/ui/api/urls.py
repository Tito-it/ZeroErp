# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
    ApiListaIgnorePresetUpdateView,
    ApiListaPreferenzaView,
    ApiMisurePaginaView,
)
from apps.ui.api.views_dashboard import (
    ApiDashboardConfigView,
    ApiDashboardContatoriView,
    ApiDashboardIgnorePresetUpdateView,
    ApiDashboardPreferenzaView,
)
from apps.ui.api.views_admin import (
    ApiAdminListaColonnaDetailView,
    ApiAdminListaColonnaListView,
    ApiAdminListaColonneView,
    ApiAdminListaDefinizioneAdminDetailView,
    ApiAdminListaDefinizioneAdminView,
    ApiAdminListaDefinizioneListView,
    ApiAdminPermessoCreateView,
    ApiAdminPermessoDetailView,
    ApiAdminPermessoListView,
    ApiAdminPresetColonneView,
    ApiAdminPresetDetailView,
    ApiAdminPresetListView,
)


# `codice` ammette punto e due punti (convenzione `<schema>.<entita>`
# o `<schema>.<entita>:<contesto>`). Il converter `<str:>` di default
# rifiuta lo slash, gli altri caratteri passano: nessun rischio di
# collisioni con sotto-risorse.
urlpatterns = [
    # ── Runtime FE (Blocco C) ───────────────────────────────────────────
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
    # DEF-2: tombstone "ignora banner preset aggiornato"
    path(
        "liste/<str:codice>/preferenza/ignore-preset-update/",
        ApiListaIgnorePresetUpdateView.as_view(),
        name="ui-liste-preferenza-ignore-preset-update",
    ),
    # Misure «righe per pagina» per tutti i paginatori (catalogo DB)
    path(
        "misure-pagina/",
        ApiMisurePaginaView.as_view(),
        name="ui-misure-pagina",
    ),
    # ── Dashboard configurabili (card KPI home) ─────────────────────────
    path(
        "dashboard/<str:codice>/config/",
        ApiDashboardConfigView.as_view(),
        name="ui-dashboard-config",
    ),
    path(
        "dashboard/<str:codice>/contatori/",
        ApiDashboardContatoriView.as_view(),
        name="ui-dashboard-contatori",
    ),
    path(
        "dashboard/<str:codice>/preferenza/",
        ApiDashboardPreferenzaView.as_view(),
        name="ui-dashboard-preferenza",
    ),
    path(
        "dashboard/<str:codice>/preferenza/ignore-preset-update/",
        ApiDashboardIgnorePresetUpdateView.as_view(),
        name="ui-dashboard-preferenza-ignore-preset-update",
    ),
    # ── Admin CRUD (Blocco F Fase 1) ────────────────────────────────────
    # Selectore "Lista corrente" + catalogo colonne grezzo
    path(
        "admin/liste/",
        ApiAdminListaDefinizioneListView.as_view(),
        name="ui-admin-liste-list",
    ),
    path(
        "admin/liste/<int:lista_id>/colonne/",
        ApiAdminListaColonneView.as_view(),
        name="ui-admin-liste-colonne",
    ),
    # Preset
    path(
        "admin/liste/<int:lista_id>/preset/",
        ApiAdminPresetListView.as_view(),
        name="ui-admin-preset-list",
    ),
    path(
        "admin/preset/<int:preset_id>/",
        ApiAdminPresetDetailView.as_view(),
        name="ui-admin-preset-detail",
    ),
    path(
        "admin/preset/<int:preset_id>/colonne/",
        ApiAdminPresetColonneView.as_view(),
        name="ui-admin-preset-colonne",
    ),
    # Permessi colonna
    path(
        "admin/liste/<int:lista_id>/permessi/",
        ApiAdminPermessoListView.as_view(),
        name="ui-admin-permessi-list",
    ),
    path(
        "admin/permessi/",
        ApiAdminPermessoCreateView.as_view(),
        name="ui-admin-permessi-create",
    ),
    path(
        "admin/permessi/<int:permesso_id>/",
        ApiAdminPermessoDetailView.as_view(),
        name="ui-admin-permessi-detail",
    ),
    # ── Admin CRUD definizioni (Blocco F Fase 2 — DEF-5b, SUPER_ADMIN) ──
    path(
        "admin/definizioni/",
        ApiAdminListaDefinizioneAdminView.as_view(),
        name="ui-admin-definizioni-list",
    ),
    path(
        "admin/definizioni/<int:lista_id>/",
        ApiAdminListaDefinizioneAdminDetailView.as_view(),
        name="ui-admin-definizioni-detail",
    ),
    path(
        "admin/definizioni/<int:lista_id>/colonne/",
        ApiAdminListaColonnaListView.as_view(),
        name="ui-admin-colonne-list",
    ),
    path(
        "admin/colonne/<int:colonna_id>/",
        ApiAdminListaColonnaDetailView.as_view(),
        name="ui-admin-colonne-detail",
    ),
]
