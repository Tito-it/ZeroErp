# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: URL routing API v1 per il modulo Amm. Software.
# ------------------------------------------------------------

from django.urls import path

from . import email_views, invito_views, secondo_fattore_views, views

urlpatterns = [
    # Operatori
    path("operatori/", views.OperatoriListView.as_view(), name="amm-operatori-list"),
    path("operatori/credenziale-per-email/", views.CredenzialePerEmailView.as_view(), name="amm-operatori-credenziale-per-email"),
    path("operatori/<int:auth_user_id>/", views.OperatoriDetailView.as_view(), name="amm-operatori-detail"),
    path("operatori/<int:auth_user_id>/disabilita/", views.OperatoriDisabilitaView.as_view(), name="amm-operatori-disabilita"),
    path("operatori/<int:auth_user_id>/riattiva/", views.OperatoriRiattivaView.as_view(), name="amm-operatori-riattiva"),
    # Override permessi operatore
    path("operatori/<int:auth_user_id>/override-aree/", views.OverrideAreeView.as_view(), name="amm-override-aree"),
    path("operatori/<int:auth_user_id>/override-azioni/", views.OverrideAzioniView.as_view(), name="amm-override-azioni"),
    path("operatori/<int:auth_user_id>/override-oggetti/", views.OverrideOggettiView.as_view(), name="amm-override-oggetti"),
    path("operatori/<int:auth_user_id>/emittenti-scope/", views.EmittentiScopeView.as_view(), name="amm-emittenti-scope"),
    # Livelli EREDITATI dal profilo (sola lettura): la colonna «ereditato» del
    # pannello permessi. Non e' `reparti/<uo_id>/profilo/` — vedi la view.
    path("operatori/<int:auth_user_id>/permessi-ereditati/", views.PermessiEreditatiView.as_view(), name="amm-permessi-ereditati"),
    # Riepilogo permessi e audit
    path("permessi-riepilogo/", views.PermessiRiepilogoView.as_view(), name="amm-permessi-riepilogo"),
    path("audit-log/", views.AuditLogView.as_view(), name="amm-audit-log"),
    # La consultazione di `dbops.error_log` (pezzo E dell'osservabilita'):
    # stessa porta dei due diari accanto. `export/` PRIMA — e' una rotta
    # sorella della lista, con lo stesso `lista_codice` (presidio
    # `test_export_lista_codice_pari`).
    path("error-log/", views.ErrorLogListView.as_view(), name="amm-error-log"),
    path("error-log/export/", views.ErrorLogExportView.as_view(), name="amm-error-log-export"),
    # Processi automatici (registro + presidi + utenti tecnici).
    # ⚠️ `presidi/` PRIMA di `<str:codice>/`, o Django lo leggerebbe come il
    #    codice di un processo che si chiama "presidi".
    path("processi/", views.ProcessiListView.as_view(), name="amm-processi-list"),
    path("processi/presidi/", views.ProcessiPresidiView.as_view(), name="amm-processi-presidi"),
    # La testata sola, per il pallino della topbar: stessa regola d'ordine.
    path("processi/presidi/conteggi/", views.ProcessiPresidiConteggiView.as_view(), name="amm-processi-presidi-conteggi"),
    path("processi/<str:codice>/", views.ProcessiDetailView.as_view(), name="amm-processi-detail"),
    path("processi/<str:codice>/run/", views.ProcessiRunView.as_view(), name="amm-processi-run"),
    path("processi/<str:codice>/identita/", views.ProcessiIdentitaView.as_view(), name="amm-processi-identita"),
    path("processi/<str:codice>/identita/riattiva/", views.ProcessiIdentitaRiattivaView.as_view(), name="amm-processi-identita-riattiva"),
    path("processi/<str:codice>/esegui-ora/", views.ProcessiEseguiOraView.as_view(), name="amm-processi-esegui-ora"),
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
    path("lookup/model-overrides/", views.ModelOverridesLookupView.as_view(), name="amm-model-overrides"),
    path("lookup/rounding-modes/", views.EmittenteRoundingModesLookupView.as_view(), name="amm-rounding-modes-lookup"),
    # Form-defaults emittente fiscale (Fase 3)
    path("emittenti-fiscali/form-defaults/", views.EmittentiFormDefaultsView.as_view(), name="amm-emittenti-form-defaults"),
    # Audit hardening + email log lookup (Fase 5)
    path("lookup/audit-sources/", views.AuditSourcesLookupView.as_view(), name="amm-audit-sources-lookup"),
    # Secondo fattore dell'operatore (brief sicurezza §3.4-bis, T-3)
    path("operatori/<int:auth_user_id>/secondo-fattore/", secondo_fattore_views.OperatoreSecondoFattoreView.as_view(), name="amm-operatori-secondo-fattore"),
    path("operatori/<int:auth_user_id>/secondo-fattore/obbligo/", secondo_fattore_views.OperatoreSecondoFattoreObbligoView.as_view(), name="amm-operatori-secondo-fattore-obbligo"),
    path("operatori/<int:auth_user_id>/secondo-fattore/disattiva/", secondo_fattore_views.OperatoreSecondoFattoreDisattivaView.as_view(), name="amm-operatori-secondo-fattore-disattiva"),
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
