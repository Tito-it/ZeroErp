# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: URL routing API v1 per il modulo Amm. Software.
# ------------------------------------------------------------

from django.urls import path

from . import views

urlpatterns = [
    # Operatori
    path("operatori/", views.OperatoriListView.as_view(), name="amm-operatori-list"),
    path("operatori/<int:auth_user_id>/", views.OperatoriDetailView.as_view(), name="amm-operatori-detail"),
    path("operatori/<int:auth_user_id>/disabilita/", views.OperatoriDisabilitaView.as_view(), name="amm-operatori-disabilita"),
    path("operatori/<int:auth_user_id>/riattiva/", views.OperatoriRiattivaView.as_view(), name="amm-operatori-riattiva"),
    # Override permessi operatore
    path("operatori/<int:auth_user_id>/override-aree/", views.OverrideAreeView.as_view(), name="amm-override-aree"),
    path("operatori/<int:auth_user_id>/override-azioni/", views.OverrideAzioniView.as_view(), name="amm-override-azioni"),
    path("operatori/<int:auth_user_id>/emittenti-scope/", views.EmittentiScopeView.as_view(), name="amm-emittenti-scope"),
    # Riepilogo permessi e audit
    path("permessi-riepilogo/", views.PermessiRiepilogoView.as_view(), name="amm-permessi-riepilogo"),
    path("audit-log/", views.AuditLogView.as_view(), name="amm-audit-log"),
    # Reparti e profili
    path("reparti/", views.RepartiListView.as_view(), name="amm-reparti-list"),
    path("reparti/<int:uo_id>/profilo/", views.RepartoProfiloView.as_view(), name="amm-reparto-profilo"),
    # Lookup
    path("lookup/unita-organizzative/", views.UtentiUOListView.as_view(), name="amm-uo-list"),
    path("lookup/aree-funzionali/", views.LookupAreeView.as_view(), name="amm-aree-list"),
    path("lookup/azioni-processo/", views.LookupAzioniView.as_view(), name="amm-azioni-list"),
    path("lookup/emittenti-fiscali/", views.LookupEmittentiView.as_view(), name="amm-emittenti-list"),
]
