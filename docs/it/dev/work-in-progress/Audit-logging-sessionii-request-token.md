# Audit Sessioni, Request Logging e Sicurezza Token

**Data**: 2026-03-05
**Stato**: WIP — piano approvato, implementazione non ancora avviata
**Autore**: tid / Claude

---

## Posizionamento nello Sviluppo Concentrico

Tutte e tre le aree di questo piano appartengono all'**Anello 0 — Nucleo Infrastrutturale**.

```
    Anello 0 (Nucleo)
    ┌────────────────────────────────────────────────┐
    │  core          dbops          script            │
    │                                                │
    │  + sessioni_utente  (AREA 1 — nuovo)           │
    │  + request_log      (AREA 2 — nuovo)           │
    │  + token_blacklist  (AREA 3 — nuovo)           │
    │                                                │
    │  + session_audit_service     (nuovo)            │
    │  + request_log_middleware    (nuovo)            │
    │  + auth_views audit         (nuovo)            │
    └────────────────────────────────────────────────┘
```

### Perche' Anello 0

1. **Infrastruttura trasversale** — sessioni, request log e revoca token sono servizi che tutti gli anelli esterni consumano senza alcuna modifica al proprio codice. Un endpoint di vendite, pratiche o acquisti viene loggato automaticamente dal middleware.

2. **Estensioni non-breaking** — nuove tabelle in `dbops`, nuovi middleware in `core`, override view JWT. Nessun contratto esistente viene rotto. La mappa concentrica ammette esplicitamente *"modifiche solo per correzioni o estensioni non-breaking (nuove policy, nuovi middleware)"*.

3. **Principio 3 applicato** — *"Se un anello esterno rivela una debolezza interna, si corregge alla fonte."* I smoke test su vendite e pratiche hanno rivelato che il nucleo non traccia sessioni ne' request. La correzione va nel nucleo, non nei singoli domini.

4. **Principio 5 — "Metti le regole dove non possono essere aggirate"** — Il request log via middleware e' ineludibile: ogni request `/api/*` viene catturata. Non serve che i domini "si ricordino" di loggare.

5. **Direzione dipendenze rispettata** — Le nuove tabelle `dbops` non hanno FK verso anelli esterni. Il middleware `core` usa solo `request_context` (gia' Anello 0). Nessuna dipendenza inversa.

### Cosa aggiunge all'Anello 0

Dopo implementazione, l'Anello 0 fornira' agli anelli esterni:

| Capacita' | Prima | Dopo |
|-----------|-------|------|
| Chi si e' connesso e quando | Non tracciato | `dbops.sessioni_utente` con IP, user_agent, jti |
| Quale utente ha chiamato quale endpoint | Non tracciato | `dbops.request_log` con metodo, path, status, durata |
| Revoca immediata token compromesso | Solo blocco 403 via middleware | Token rifiutato a livello di autenticazione |
| Correlazione sessione-request | Nessuna | `request_id` condiviso tra le due tabelle |

---

## Contesto

Il sistema ha un buon audit a livello DB (trigger `user_insert/user_update` con JWT user reale via GUC `app.jwt_user`, storicizzazione temporale), ma **manca completamente il tracking delle sessioni utente e delle request HTTP**.

Non c'e' modo di sapere:
- Quando un utente ha fatto login (ottenuto token)
- Quando il token e' stato refreshato
- Quando la sessione e' scaduta
- Quale utente ha chiamato quale endpoint, quando, e con quale esito
- Se un token compromesso e' stato usato dopo la disabilitazione dell'utente

Le funzionalita' da implementare si dividono in **3 aree**, ognuna con componente DB e backend.

---

## AREA 1: Audit Sessioni (login / token / scadenza)

### Obiettivo

Tracciare il ciclo di vita delle sessioni JWT: emissione token, refresh, scadenza, revoca.

### 1A — DB

**Prerequisiti**: nessuno

**Tabella `dbops.sessioni_utente`**:

| Colonna | Tipo | Note |
|---------|------|------|
| `id` | BIGINT PK | autoincrement |
| `auth_user_id` | INTEGER NOT NULL | FK auth_user |
| `evento` | TEXT NOT NULL | LOGIN, REFRESH, LOGOUT, SCADENZA, REVOCA |
| `jti` | TEXT | JWT ID (claim univoco del token) |
| `ip_address` | INET | IP del client |
| `user_agent` | TEXT | browser/client |
| `request_id` | UUID | correlazione con request |
| `dettaglio` | JSONB DEFAULT '{}' | dati aggiuntivi |
| `data_insert` | TIMESTAMPTZ DEFAULT now() | |
| `user_insert` | TEXT DEFAULT CURRENT_USER | |

**Indici**: `ix_sessioni_utente_auth_user_id`, `ix_sessioni_utente_data_insert`

**Retention**: colonna `cleanup_at` per pulizia schedulata (pattern `dbops.audit_log`)

**GRANT**: SELECT, INSERT per `zeroerp_app`

**NO storicizzazione** (e' gia' un log, non serve snapshot)

**Changeset**: `db/changelog/migrations_v2/00_schema/dbops/YYYYMMDD-NN-create-sessioni-utente-mctit.yaml`

### 1B — Backend

**Prerequisiti**: tabella 1A creata

**Nuovo file** `apps/core/db/session_audit_repository.py`:
- `log_session_event(auth_user_id, evento, jti, ip_address, user_agent, request_id, dettaglio)`
- INSERT diretto, nessuna logica complessa

**Nuovo file** `apps/core/services/session_audit_service.py`:
- `record_login(user, request)` — chiamato dopo token emesso
- `record_refresh(user, request)` — chiamato dopo token refreshato
- `record_logout(user, request)` — chiamato su revoca esplicita (futuro)

**Integrazione**: Override delle view SimpleJWT per agganciare il logging:

**Nuovo file** `apps/core/api/auth_views.py`:
- `AuditTokenObtainPairView(TokenObtainPairView)` — override `post()`, dopo successo chiama `record_login()`
- `AuditTokenRefreshView(TokenRefreshView)` — override `post()`, dopo successo chiama `record_refresh()`

**Modifica** `zeroerp_backend/urls.py` — sostituire le view JWT con quelle audit

**API di consultazione** (opzionale, fase 2):
- `GET /api/v1/core/users/{user_id}/sessioni/` — lista sessioni con filtri data

---

## AREA 2: Request Logging (chi chiama cosa)

### Obiettivo

Registrare ogni request API autenticata: utente, endpoint, metodo, status, durata.

### 2A — DB

**Prerequisiti**: nessuno (parallelo a 1A)

**Tabella `dbops.request_log`**:

| Colonna | Tipo | Note |
|---------|------|------|
| `id` | BIGINT PK | autoincrement |
| `auth_user_id` | INTEGER | NULL se anonimo |
| `username` | TEXT | JWT user |
| `request_id` | UUID | da RequestContextMiddleware |
| `method` | TEXT NOT NULL | GET, POST, PATCH, DELETE |
| `path` | TEXT NOT NULL | /api/v1/pratiche/ |
| `query_string` | TEXT | parametri query (senza dati sensibili) |
| `status_code` | SMALLINT | 200, 400, 500... |
| `duration_ms` | INTEGER | tempo di risposta |
| `ip_address` | INET | |
| `user_agent` | TEXT | |
| `error_code` | TEXT | codice errore se presente (E_PRATICA_NOT_FOUND) |
| `idempotency_key` | TEXT | per correlazione replay |
| `data_insert` | TIMESTAMPTZ DEFAULT now() | |

**Indici**: `ix_request_log_auth_user_id`, `ix_request_log_data_insert`, `ix_request_log_path`

**Retention**: `cleanup_at` con pulizia schedulata (es. 90 giorni)

**GRANT**: SELECT, INSERT per `zeroerp_app`

**Volume**: alto — valutare partizionamento per mese se necessario

**Changeset**: `db/changelog/migrations_v2/00_schema/dbops/YYYYMMDD-NN-create-request-log-mctit.yaml`

### 2B — Backend

**Prerequisiti**: tabella 2A creata

**Nuovo file** `apps/core/middleware/request_log_middleware.py`:
- `RequestLogMiddleware(MiddlewareMixin)`:
  - `process_request()`: salva `start_time`
  - `process_response()`: calcola durata, INSERT asincrono nel DB
  - Filtra solo `/api/*` (ignora static, health, docs)
  - NON logga body request/response (sicurezza + volume)
  - Logga solo header-level: method, path, status, durata, user

**Modifica** `zeroerp_backend/settings.py` — aggiungere middleware DOPO `JwtAuditMiddleware`

**Configurazione**:
- `DJANGO_REQUEST_LOG_ENABLED` — flag on/off (default True)
- `DJANGO_REQUEST_LOG_EXCLUDE_PATHS` — lista path da escludere (es. `/health`, `/api/docs/`)

**API di consultazione** (opzionale, fase 2):
- `GET /api/v1/core/request-log/` — solo ADMIN, con filtri user/data/path/status

---

## AREA 3: Token Blacklist e Revoca

### Obiettivo

Permettere la revoca immediata di token compromessi o alla disabilitazione utente.

### 3A — DB

**Prerequisiti**: nessuno (parallelo a 1A e 2A)

Usare il modulo built-in di SimpleJWT: `rest_framework_simplejwt.token_blacklist`

Questo crea automaticamente 2 tabelle Django-managed:
- `token_blacklist_outstandingtoken` — token emessi
- `token_blacklist_blacklistedtoken` — token revocati

**Azione**: aggiungere `'rest_framework_simplejwt.token_blacklist'` a `INSTALLED_APPS` e fare `manage.py migrate`

### 3B — Backend

**Prerequisiti**: 3A (migrate)

**Modifica** `zeroerp_backend/settings.py`:

```python
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,       # nuovo refresh ad ogni refresh
    "BLACKLIST_AFTER_ROTATION": True,     # vecchio refresh in blacklist
}
```

**Integrazione con disabilitazione utente**:
- Quando `ruolo_sistema` -> `DISABILITATO`, invalidare tutti i token outstanding dell'utente
- Il middleware `JwtAuditMiddleware` gia' blocca le request (403), ma i token restano tecnicamente validi
- Con blacklist: il token viene proprio rifiutato a livello di autenticazione

**Cleanup**: `manage.py flushexpiredtokens` — command schedulato per pulire token scaduti

---

## Riepilogo dipendenze e ordine

```
FASE 1 (parallela DB):
  DB:  1A (sessioni_utente) + 2A (request_log) + 3A (token_blacklist)
       <- tutte indipendenti, eseguibili in parallelo

FASE 2 (Backend, dopo DB):
  BE:  1B session_audit_service + auth_views override    <- richiede 1A
  BE:  2B request_log_middleware                          <- richiede 2A
  BE:  3B settings blacklist + rotation                   <- richiede 3A

FASE 3 (Test + Smoke):
  Test unitari per ogni componente
  Aggiornamento smoke-test-core.sh

FASE 4 (Documentazione):
  Aggiornamento documenti esistenti (vedi sezione dedicata)
```

### Tabella riassuntiva

| # | Area | Tipo | Descrizione | Prerequisiti |
|---|------|------|-------------|-------------|
| 1A | Sessioni | DB | Tabella `dbops.sessioni_utente` | — |
| 1B | Sessioni | Backend | Repository + service + auth views override | 1A |
| 2A | Request log | DB | Tabella `dbops.request_log` | — |
| 2B | Request log | Backend | Middleware `RequestLogMiddleware` | 2A |
| 3A | Token blacklist | DB | `INSTALLED_APPS` + migrate | — |
| 3B | Token blacklist | Backend | Settings rotation + integrazione disabilitazione | 3A |

---

## File da creare / modificare

### Nuovi file

| File | Area |
|------|------|
| `db/changelog/migrations_v2/00_schema/dbops/YYYYMMDD-NN-create-sessioni-utente-mctit.yaml` | 1A |
| `db/changelog/migrations_v2/00_schema/dbops/YYYYMMDD-NN-create-request-log-mctit.yaml` | 2A |
| `backend/apps/core/db/session_audit_repository.py` | 1B |
| `backend/apps/core/services/session_audit_service.py` | 1B |
| `backend/apps/core/api/auth_views.py` | 1B |
| `backend/apps/core/middleware/request_log_middleware.py` | 2B |

### File da modificare

| File | Area | Modifica |
|------|------|----------|
| `backend/zeroerp_backend/settings.py` | 2B, 3A, 3B | INSTALLED_APPS, SIMPLE_JWT, MIDDLEWARE |
| `backend/zeroerp_backend/urls.py` | 1B | Sostituire view JWT con audit views |
| `backend/scripts/smoke-test-core.sh` | Test | Aggiungere test sessioni e request log |

### File di riferimento (pattern esistenti da riusare)

| File | Pattern |
|------|---------|
| `apps/core/db/permissions_audit_repository.py` | Repository con raw SQL |
| `apps/core/services/idempotency_store.py` | INSERT con request_id |
| `apps/core/middleware/jwt_audit_middleware.py` | Middleware Django |
| `apps/core/services/request_context.py` | ContextVar per request_id/idempotency_key |

---

## Aggiornamenti a documenti e configurazioni esistenti

Dopo l'implementazione, i seguenti documenti e file devono essere aggiornati per mantenere coerenza con il modello concentrico.

### Documenti da aggiornare

| Documento | Cosa aggiornare |
|-----------|----------------|
| `docs/it/mappa-concentrica.md` | Aggiungere le 3 nuove capacita' nella tabella Anello 0 e nella sezione "Cosa fornisce agli anelli esterni" |
| `.codex/PROJECT_CONTEXT.md` | Aggiornare sezione "Struttura App Django" con i nuovi file `core`. Aggiornare sezione "Completato" quando implementato. Aggiungere `dbops.sessioni_utente` e `dbops.request_log` nella descrizione schema `dbops` |
| `.codex/AGENTS.md` | Aggiungere riferimento ai nuovi middleware nella lista middleware. Documentare il pattern auth_views override come esempio per future estensioni JWT |
| `docs/it/dev/work-in-progress/brief-db-audit-jwt-user.md` | Aggiornare: il brief copre solo il GUC audit, ora va esteso o collegato a questo piano per sessioni e request log |
| `docs/it/dev/work-in-progress/permessi-e-autorizzazioni.md` | Collegare la sezione token blacklist/revoca come evoluzione del sistema permessi |
| `docs/it/dev/work-in-progress/proposta-8.2-audit-trail-permessi.md` | Verificare sovrapposizioni con Area 1 (sessioni) e consolidare |

### Configurazioni runtime da aggiornare

| File/Config | Cosa aggiornare |
|-------------|----------------|
| `db/changelog/migrations_v2/90_end/ci_apply/` | Il GRANT `ci_apply` deve gia' coprire `dbops` — verificare che le nuove tabelle ricevano i grant automaticamente. Se il changeset usa `GRANT ... ON ALL TABLES IN SCHEMA dbops`, non serve modifica |
| `maintenance` / pgAgent | Aggiungere job schedulato per: (1) pulizia `dbops.sessioni_utente` oltre retention, (2) pulizia `dbops.request_log` oltre retention, (3) `manage.py flushexpiredtokens` per blacklist |
| `backend/zeroerp_backend/settings.py` | Variabili ambiente nuove: `DJANGO_REQUEST_LOG_ENABLED`, `DJANGO_REQUEST_LOG_EXCLUDE_PATHS` — documentare in `.env.example` o equivalente |

### Smoke test da aggiornare

| Script | Cosa aggiungere |
|--------|----------------|
| `backend/scripts/smoke-test-core.sh` | Test 18: login -> verifica riga in `sessioni_utente`. Test 19: refresh -> verifica riga REFRESH. Test 20: chiamata API -> verifica riga in `request_log`. Test 21: blacklist token -> verifica 401 |
| `backend/scripts/smoke-test-pratiche.sh` | Nessuna modifica (beneficia automaticamente del request log) |
| `backend/scripts/smoke-test-vendite.sh` | Nessuna modifica (beneficia automaticamente del request log) |

### Test unitari da creare

| File | Contenuto |
|------|-----------|
| `backend/apps/core/tests/services/test_session_audit_service.py` | Mock DB, verifica chiamate repository per login/refresh/logout |
| `backend/apps/core/tests/api/test_auth_views.py` | Mock service, verifica che le view audit chiamino `record_login`/`record_refresh` |
| `backend/apps/core/tests/middleware/test_request_log_middleware.py` | Mock DB, verifica INSERT con campi corretti, verifica esclusione path |

### Documentazione backend da creare

| File | Contenuto |
|------|-----------|
| `docs/it/backend/core/manual/session-audit.md` | Scopo, contesto, input/output, regole, dipendenze DB — template standard |
| `docs/it/backend/core/manual/request-log.md` | Scopo, contesto, configurazione, esclusioni, retention |
| `docs/it/dbzero/dbops/manual/sessioni-utente.md` | Documentazione manuale tabella |
| `docs/it/dbzero/dbops/manual/request-log.md` | Documentazione manuale tabella |

---

## Verifica

1. **Smoke test sessioni**: login -> verifica riga in `dbops.sessioni_utente` -> refresh -> verifica riga REFRESH
2. **Smoke test request log**: chiamata API -> verifica riga in `dbops.request_log` con user/path/status/durata
3. **Smoke test blacklist**: login -> blacklist token -> verifica 401 su richiesta successiva
4. **Test unitari**: mock DB per ogni service/middleware — CI-compatibili (no DB reale)
5. **Test suite completa**: `./manage-test.sh -v 2` — tutti i test devono passare
6. **Coerenza concentrica**: verificare che nessun file in anelli 1/2/3 importi direttamente da session_audit o request_log (le dipendenze devono andare solo dall'interno verso l'esterno)
7. **Documenti aggiornati**: tutti i file nella sezione "Aggiornamenti" devono riflettere le nuove capacita'
