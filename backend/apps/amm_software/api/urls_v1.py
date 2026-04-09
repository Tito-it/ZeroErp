# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: URL routing API v1 per il modulo Amm. Software.
# ------------------------------------------------------------

from django.urls import path

from . import email_views, invito_views, views

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
    # Setup status (refactor operatore-emittenti)
    path("setup-status/", views.SetupStatusView.as_view(), name="amm-setup-status"),
    # Reparti e profili
    path("reparti/", views.RepartiListView.as_view(), name="amm-reparti-list"),
    path("reparti/<int:uo_id>/profilo/", views.RepartoProfiloView.as_view(), name="amm-reparto-profilo"),
    # Lookup
    path("lookup/unita-organizzative/", views.UtentiUOListView.as_view(), name="amm-uo-list"),
    path("lookup/aree-funzionali/", views.LookupAreeView.as_view(), name="amm-aree-list"),
    path("lookup/azioni-processo/", views.LookupAzioniView.as_view(), name="amm-azioni-list"),
    path("lookup/emittenti-fiscali/", views.LookupEmittentiView.as_view(), name="amm-emittenti-list"),
    # Invito operatore
    path("operatori/<int:auth_user_id>/invita/", invito_views.InvitaOperatoreView.as_view(), name="amm-operatori-invita"),
    path("operatori/<int:auth_user_id>/reinvia-invito/", invito_views.ReinviaInvitoView.as_view(), name="amm-operatori-reinvia-invito"),
    # Email — Account SMTP
    path("email-accounts/", email_views.EmailAccountListView.as_view(), name="amm-email-accounts-list"),
    path("email-accounts/<int:account_id>/", email_views.EmailAccountDetailView.as_view(), name="amm-email-accounts-detail"),
    path("email-accounts/<int:account_id>/test/", email_views.EmailAccountTestView.as_view(), name="amm-email-accounts-test"),
    # Email — Template
    path("email-templates/", email_views.EmailTemplateListView.as_view(), name="amm-email-templates-list"),
    path("email-templates/<int:template_id>/", email_views.EmailTemplateDetailView.as_view(), name="amm-email-templates-detail"),
    path("email-templates/<int:template_id>/preview/", email_views.EmailTemplatePreviewView.as_view(), name="amm-email-templates-preview"),
    # Email — Log
    path("email-log/", email_views.EmailLogListView.as_view(), name="amm-email-log-list"),
    path("email-log/<int:log_id>/", email_views.EmailLogDetailView.as_view(), name="amm-email-log-detail"),
]
