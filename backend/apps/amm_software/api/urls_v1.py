# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: URL routing API v1 per il modulo Amm. Software.
# ------------------------------------------------------------

from django.urls import path

from . import accessi_views, email_views, invito_views, views

urlpatterns = [
    # Operatori
    path("operatori/", views.OperatoriListView.as_view(), name="amm-operatori-list"),
    path("operatori/credenziale-per-email/", views.CredenzialePerEmailView.as_view(), name="amm-operatori-credenziale-per-email"),
    path("operatori/<int:auth_user_id>/", views.OperatoriDetailView.as_view(), name="amm-operatori-detail"),
    path("operatori/<int:auth_user_id>/disabilita/", views.OperatoriDisabilitaView.as_view(), name="amm-operatori-disabilita"),
    # Override permessi operatore
    path("operatori/<int:auth_user_id>/override-aree/", views.OverrideAreeView.as_view(), name="amm-override-aree"),
    path("operatori/<int:auth_user_id>/override-azioni/", views.OverrideAzioniView.as_view(), name="amm-override-azioni"),
    path("operatori/<int:auth_user_id>/override-oggetti/", views.OverrideOggettiView.as_view(), name="amm-override-oggetti"),
    path("operatori/<int:auth_user_id>/emittenti-scope/", views.EmittentiScopeView.as_view(), name="amm-emittenti-scope"),
    # Livelli EREDITATI dal profilo (sola lettura): la colonna «ereditato» del
    # pannello permessi. Non e' `reparti/<uo_id>/profilo/` — vedi la view.
    path("operatori/<int:auth_user_id>/permessi-ereditati/", views.PermessiEreditatiView.as_view(), name="amm-permessi-ereditati"),
    # Permessi EFFETTIVI su azioni e oggetti, col tetto d'area (sola lettura):
    # l'etichetta «limitata dall'area» del pannello. Non e' il `core`
    # `users/<id>/permessi-effettivi/` — vedi la view.
    path("operatori/<int:auth_user_id>/permessi-effettivi/", views.PermessiEffettiviOperatoreView.as_view(), name="amm-permessi-effettivi"),
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
    # ⚠️ `presidi/` e `vocabolari/` PRIMA di `<str:codice>/`, o Django li
    #    leggerebbe come il codice di un processo che si chiama cosi'.
    path("processi/", views.ProcessiListView.as_view(), name="amm-processi-list"),
    path("processi/presidi/", views.ProcessiPresidiView.as_view(), name="amm-processi-presidi"),
    # La testata sola, per il pallino della topbar: stessa regola d'ordine.
    path("processi/presidi/conteggi/", views.ProcessiPresidiConteggiView.as_view(), name="amm-processi-presidi-conteggi"),
    # I vocabolari dei filtri del pannello: stessa regola d'ordine.
    path("processi/vocabolari/", views.ProcessiVocabolariView.as_view(), name="amm-processi-vocabolari"),
    path("processi/<str:codice>/", views.ProcessiDetailView.as_view(), name="amm-processi-detail"),
    path("processi/<str:codice>/run/", views.ProcessiRunView.as_view(), name="amm-processi-run"),
    path("processi/<str:codice>/identita/", views.ProcessiIdentitaView.as_view(), name="amm-processi-identita"),
    path("processi/<str:codice>/identita/riattiva/", views.ProcessiIdentitaRiattivaView.as_view(), name="amm-processi-identita-riattiva"),
    path("processi/<str:codice>/esegui-ora/", views.ProcessiEseguiOraView.as_view(), name="amm-processi-esegui-ora"),
    path("processi/<str:codice>/accensione/", views.ProcessiAccensioneView.as_view(), name="amm-processi-accensione"),
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
    # Area «Accessi» (brief-db-be-fe-area-accessi): le altre due liste che,
    # con quella degli operatori, censiscono TUTTE le credenziali.
    path("accessi/altri/", accessi_views.AccessiAltriListView.as_view(), name="amm-accessi-altri"),
    path("accessi/sistema/", accessi_views.AccessiSistemaListView.as_view(), name="amm-accessi-sistema"),
    # Le azioni della CREDENZIALE (valgono per tutte le sue vesti, A-4/A-5):
    # blocco dell'amministratore e secondo fattore. Fino al 2026-10-02 il
    # secondo fattore stava sotto `operatori/<id>/`: ritirato.
    path("credenziali/<int:auth_user_id>/", accessi_views.CredenzialeDetailView.as_view(), name="amm-credenziali-detail"),
    path("credenziali/<int:auth_user_id>/blocca/", accessi_views.CredenzialeBloccaView.as_view(), name="amm-credenziali-blocca"),
    path("credenziali/<int:auth_user_id>/sblocca/", accessi_views.CredenzialeSbloccaView.as_view(), name="amm-credenziali-sblocca"),
    path("credenziali/<int:auth_user_id>/secondo-fattore/", accessi_views.CredenzialeSecondoFattoreView.as_view(), name="amm-credenziali-secondo-fattore"),
    path("credenziali/<int:auth_user_id>/secondo-fattore/obbligo/", accessi_views.CredenzialeSecondoFattoreObbligoView.as_view(), name="amm-credenziali-secondo-fattore-obbligo"),
    path("credenziali/<int:auth_user_id>/secondo-fattore/disattiva/", accessi_views.CredenzialeSecondoFattoreDisattivaView.as_view(), name="amm-credenziali-secondo-fattore-disattiva"),
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
