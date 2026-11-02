# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
# ⛔ DISABILITATO non e' piu' un tipo di veste (2026-10-02, R-DB-1): resta
#    nell'enum come voce STORICA (`storico.identita_digitali`), la tabella
#    viva lo rifiuta. Una veste spenta e' `attivo = false` col suo tipo.

RUOLO_APPLICATIVO_OPERATORE = "OPERATORE"
RUOLO_APPLICATIVO_CLIENTE_PORTALE = "CLIENTE_PORTALE"
RUOLO_APPLICATIVO_FORNITORE_PORTALE = "FORNITORE_PORTALE"
RUOLO_APPLICATIVO_SHOP_CUSTOMER = "SHOP_CUSTOMER"
RUOLO_APPLICATIVO_API_CLIENT = "API_CLIENT"

RUOLO_APPLICATIVO: tuple[str, ...] = (
    RUOLO_APPLICATIVO_OPERATORE,
    RUOLO_APPLICATIVO_CLIENTE_PORTALE,
    RUOLO_APPLICATIVO_FORNITORE_PORTALE,
    RUOLO_APPLICATIVO_SHOP_CUSTOMER,
    RUOLO_APPLICATIVO_API_CLIENT,
)

# ── Categoria di una credenziale (il tab dell'area «Accessi») ──

# Scopo: Il vocabolario di `script.fn_categoria_accesso(auth_user_id)`, la
# classificazione che rende i tre tab una PARTIZIONE (brief-db-be-fe-area-accessi,
# R-DB-A1): ogni credenziale ne ha una sola. La regola sta nel DB; qui ci sono
# solo i tre valori che il backend confronta.
# OPERATORE = almeno una veste OPERATORE di una persona (anche spenta).
# SISTEMA = almeno una veste di una macchina (`tecnica` o API_CLIENT).
# ALTRO = tutte le altre persone, comprese le credenziali senza alcuna veste.
CATEGORIA_ACCESSO_OPERATORE = "OPERATORE"
CATEGORIA_ACCESSO_SISTEMA = "SISTEMA"
CATEGORIA_ACCESSO_ALTRO = "ALTRO"

CATEGORIA_ACCESSO: tuple[str, ...] = (
    CATEGORIA_ACCESSO_OPERATORE,
    CATEGORIA_ACCESSO_SISTEMA,
    CATEGORIA_ACCESSO_ALTRO,
)

# ⛔ I TRE ATTORI D'AUDIT DEL CANALE DI SISTEMA SONO STATI RITIRATI (2026-09-05,
# R-2): `AUDIT_ACTOR_BATCH_FATTURAZIONE`, `AUDIT_ACTOR_WORKER_STAMPA`,
# `AUDIT_ACTOR_WORKER_CODA_LAVORI`. Erano nomi generici scritti in
# `app.jwt_user` dal gateway `BYPASSRLS` per rendere riconoscibili nel giornale
# le righe di un processo che non aveva un'identita' propria.
# ⭐ Adesso ce l'ha: i processi scrivono con l'USERNAME del proprio utente
# tecnico (`run_fatturazione_batch@ACME`), che dice anche PER QUALE AZIENDA —
# cosa che un attore unico non poteva dire. Tenerli sarebbe stato lasciare in
# giro tre costanti che nessuno chiama e che al primo processo nuovo sembrano
# la strada da seguire.

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
# ⭐ `sid` — identificativo STABILE della sessione: sopravvive alla rotazione del
#    refresh (che cambia `jti` a ogni giro) ed e' quindi l'unica cosa con cui si
#    puo' dire «questa sessione» invece di «questo token». Lo mette
#    `SidTokenObtainPairSerializer` al login e SimpleJWT lo copia sull'access.
#    Con gli altri due e' un claim OBBLIGATORIO del JWT interno
#    (`api_multi_veste_token.md`): senza, la revoca delle altre sessioni non sa
#    quale risparmiare e il diario non sa a quale riga attribuire logout e
#    refresh — verificato in autenticazione, non nelle singole view.
JWT_CLAIM_SID = "sid"

# Scopo: Emittente fiscale ATTIVO della sessione (impersonazione di scope,
# brief-db-impersonazione-scope-emittente). Porta la PK reale
# `anagrafiche.emittenti_fiscali.id`; alimenta la GUC `app.current_emittente_id`
# da cui il DB restringe liste, RLS e write-guard.
#
# **Claim assente = modalità «Tutti gli emittenti»**, cioè il comportamento
# storico (nessuna restrizione). Non esiste un valore sentinella per «tutti»:
# l'assenza È la modalità globale, e questo tiene vero il contratto del §3 del
# brief — «GUC assente = comportamento identico a oggi» — senza casi speciali.
#
# Per l'OPERATORE il claim vale il suo emittente di whitelist: l'intersezione a
# DB dà lo stesso insieme di prima (misurato), ma rende vera per tutti la frase
# «si lavora sempre dentro un emittente». Per gli altri ruoli applicativi
# (portale, shop) il claim non viene emesso: non hanno emittente.
JWT_CLAIM_EMITTENTE_ATTIVO_ID = "emittente_attivo_id"


# ── Email di sistema delle credenziali ─────────────────────

# Scopo: Il nome con cui le email di sistema (invito, reset password) firmano
# il sistema, variabile `azienda` dei loro template. Una sede sola: era
# scritto a mano in quattro punti. ⚠️ E' il nome del PRODOTTO, non quello
# dell'azienda che lo usa: se i template dovranno dire il nome del cliente
# installato, va letto da un dato (emittente, parametro), non scritto qui.
NOME_SISTEMA_EMAIL = "ZeroErp"
