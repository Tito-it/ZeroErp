# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: URL routing API v1 per il modulo Amm. Software.
# ------------------------------------------------------------

from django.urls import path

from . import views

urlpatterns = [
    # Utenti
    path("utenti/", views.UtentiListView.as_view(), name="amm-utenti-list"),
    path("utenti/<int:auth_user_id>/", views.UtentiDetailView.as_view(), name="amm-utenti-detail"),
    path("utenti/<int:auth_user_id>/disabilita/", views.UtentiDisabilitaView.as_view(), name="amm-utenti-disabilita"),
    # Override permessi utente
    path("utenti/<int:auth_user_id>/override-aree/", views.OverrideAreeView.as_view(), name="amm-override-aree"),
    path("utenti/<int:auth_user_id>/override-azioni/", views.OverrideAzioniView.as_view(), name="amm-override-azioni"),
    path("utenti/<int:auth_user_id>/emittenti-scope/", views.EmittentiScopeView.as_view(), name="amm-emittenti-scope"),
    # Reparti e profili
    path("reparti/", views.RepartiListView.as_view(), name="amm-reparti-list"),
    path("reparti/<int:uo_id>/profilo/", views.RepartoProfiloView.as_view(), name="amm-reparto-profilo"),
    # Lookup
    path("lookup/unita-organizzative/", views.UtentiUOListView.as_view(), name="amm-uo-list"),
    path("lookup/aree-funzionali/", views.LookupAreeView.as_view(), name="amm-aree-list"),
    path("lookup/azioni-processo/", views.LookupAzioniView.as_view(), name="amm-azioni-list"),
    path("lookup/emittenti-fiscali/", views.LookupEmittentiView.as_view(), name="amm-emittenti-list"),
]
