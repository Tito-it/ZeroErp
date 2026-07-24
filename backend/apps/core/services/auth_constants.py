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

# Attore d'audit dei processi di sistema HEADLESS (es. batch fatturazione cron).
# Path A (brief work-in-progress/brief-db-contesto-sistema-batch-fatturazione-rls.md):
# la RLS è bypassata dal RUOLO DB del canale (`zeroerp_batch_fatturazione`), NON da un
# sentinel applicativo. Questo valore è SOLO l'identità d'audit settata in `app.jwt_user`
# dal gateway del canale di sistema (apps.core.services.system_context) per rendere
# riconoscibili le righe scritte dal batch nel giornale. (Ritirato
# `RUOLO_APPLICATIVO_SISTEMA`/Opzione B: non era una veste.)
AUDIT_ACTOR_BATCH_FATTURAZIONE = "BATCH_FATTURAZIONE"

# Attore d'audit del worker DRAINER della coda stampa documentale (Fase C
# C-2b): gira sullo stesso canale di sistema del batch fatturazione (ruolo
# BYPASSRLS), identità d'audit distinta per riconoscere nel giornale le stampe
# prodotte dal worker rispetto ai giri di fatturazione.
AUDIT_ACTOR_WORKER_STAMPA = "WORKER_STAMPA_DOCUMENTI"

# Attore d'audit del worker DRAINER della coda lavori generica
# (`dbops.coda_lavori`): identità dei job `run_as=SISTEMA` eseguiti sul canale
# di sistema. I job `run_as=OPERATORE` girano invece con `app.jwt_user` =
# l'operatore che li ha accodati (scope catturato), non con questo attore.
AUDIT_ACTOR_WORKER_CODA_LAVORI = "WORKER_CODA_LAVORI"

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
