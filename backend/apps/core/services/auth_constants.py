# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Costanti del sistema multi-face auth (ruolo applicativo, tipo profilo
#        accesso). Fonte unica per Python. Gli equivalenti DB sono ENUM
#        `config.ruolo_applicativo` e `config.tipo_profilo_accesso`.
# ------------------------------------------------------------

from __future__ import annotations


# ── Ruolo applicativo (categoria di utente) ────────────────

# Scopo: Ogni auth_user e' un'identita in un contesto specifico.
# OPERATORE = dipendente interno (unico caso pre-multi-face).
# CLIENTE_PORTALE / FORNITORE_PORTALE = cliente/fornitore che accede al portale.
# SHOP_CUSTOMER = cliente del negozio online (self-service).
# API_CLIENT = chiamate programmatiche da sistema terzo.
# DISABILITATO = identita sospesa (bypassa la risoluzione, nega accesso).

RUOLO_APPLICATIVO_OPERATORE = "OPERATORE"
RUOLO_APPLICATIVO_CLIENTE_PORTALE = "CLIENTE_PORTALE"
RUOLO_APPLICATIVO_FORNITORE_PORTALE = "FORNITORE_PORTALE"
RUOLO_APPLICATIVO_SHOP_CUSTOMER = "SHOP_CUSTOMER"
RUOLO_APPLICATIVO_API_CLIENT = "API_CLIENT"
RUOLO_APPLICATIVO_DISABILITATO = "DISABILITATO"

RUOLO_APPLICATIVO: tuple[str, ...] = (
    RUOLO_APPLICATIVO_OPERATORE,
    RUOLO_APPLICATIVO_CLIENTE_PORTALE,
    RUOLO_APPLICATIVO_FORNITORE_PORTALE,
    RUOLO_APPLICATIVO_SHOP_CUSTOMER,
    RUOLO_APPLICATIVO_API_CLIENT,
    RUOLO_APPLICATIVO_DISABILITATO,
)

# Contesto di SISTEMA per i processi headless (es. batch fatturazione cron):
# sentinel GUC-only per `app.ruolo_applicativo`, usato dalle policy RLS "_sistema"
# (visibilità/scrittura piena, tutti gli emittenti). NON è un'identità digitale né un
# valore dell'enum DB `config.ruolo_applicativo`: per questo resta FUORI dalla tupla
# `RUOLO_APPLICATIVO` (che rispecchia l'enum). Vedi brief
# work-in-progress/brief-db-contesto-sistema-batch-fatturazione-rls.md (RLS opzione B).
RUOLO_APPLICATIVO_SISTEMA = "SISTEMA"

# Scopo: Ruoli che accedono ai namespace portale (`/api/portale/*`).
RUOLI_PORTALE: frozenset[str] = frozenset({
    RUOLO_APPLICATIVO_CLIENTE_PORTALE,
    RUOLO_APPLICATIVO_FORNITORE_PORTALE,
})

# Scopo: Ruoli che accedono al namespace shop (`/api/shop/*`) da autenticati.
RUOLI_SHOP: frozenset[str] = frozenset({
    RUOLO_APPLICATIVO_SHOP_CUSTOMER,
})


# ── Tipo profilo accesso (classificazione profilo) ─────────

# Scopo: `profili_accesso.tipo` discrimina come un profilo viene assegnato.
# REPARTO: ereditato da `unita_organizzativa` (operatori interni).
# PORTALE: set statico per un ruolo applicativo non-operatore.
# AD_HOC: assegnato direttamente a una singola identita (override fine).
# SUPER_ADMIN: privilegio di bypass totale, bindato solo su identita.

TIPO_PROFILO_REPARTO = "REPARTO"
TIPO_PROFILO_PORTALE = "PORTALE"
TIPO_PROFILO_AD_HOC = "AD_HOC"
TIPO_PROFILO_SUPER_ADMIN = "SUPER_ADMIN"

TIPO_PROFILO_ACCESSO: tuple[str, ...] = (
    TIPO_PROFILO_REPARTO,
    TIPO_PROFILO_PORTALE,
    TIPO_PROFILO_AD_HOC,
    TIPO_PROFILO_SUPER_ADMIN,
)

# Scopo: Codice riservato del profilo di bypass totale (seed id 9100, §4.6.A.4).
SUPER_ADMIN_PROFILO_CODICE = "SUPER_ADMIN"


# ── Claim JWT custom (multi-face auth) ─────────────────────

# Scopo: Nomi dei claim custom che MultiVesteTokenSerializer (§8.3.2) inietta
# nel JWT dopo login. JwtAuditAuthentication (§8.3.4) li rilegge per popolare
# le GUC di sessione in un unico round-trip, senza risoluzione aggiuntiva.
# Centralizzare i nomi qui evita typo cross-file (producer/consumer).
JWT_CLAIM_IDENTITA_ID = "identita_id"
JWT_CLAIM_RUOLO_APPLICATIVO = "ruolo_applicativo"
