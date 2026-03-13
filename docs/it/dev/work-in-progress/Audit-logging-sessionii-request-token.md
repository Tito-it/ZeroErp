# Audit Sessioni, Request Logging e Sicurezza Token

**Data**: 2026-03-05
**Stato**: COMPLETATO — FASE 1 (DB) + FASE 2 (Backend) + FASE 3 (Test unitari) implementati il 6 marzo 2026
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
| `id` | BIGINT PK | autoincrement (BY DEFAULT) |
| `auth_user_id` | INTEGER NOT NULL | FK auth_user |
| `evento` | TEXT NOT NULL | LOGIN, REFRESH, LOGOUT, SCADENZA, REVOCA |
| `jti` | TEXT | JWT ID (claim univoco del token) |
| `ip_address` | INET | IP del client |
| `user_agent` | TEXT | browser/client |
| `request_id` | UUID | correlazione con request_log |
| `dettaglio` | JSONB DEFAULT '{}' | dati aggiuntivi |
| `tx_id` | UUID | transaction ID (pattern dbops, trigger `trgfn_tx_id_managed`) |
| `cleanup_at` | TIMESTAMPTZ | retention schedulata (pattern `dbops.audit_log`) |
| `data_insert` | TIMESTAMPTZ DEFAULT now() | |
| `user_insert` | TEXT DEFAULT CURRENT_USER | |

**Constraint**:
- PK: `pk_sessioni_utente`
- CHECK: `chk_sessioni_utente_evento CHECK (evento IN ('LOGIN','REFRESH','LOGOUT','SCADENZA','REVOCA'))`

**Indici**: `ix_sessioni_utente_auth_user_id`, `ix_sessioni_utente_data_insert`, `ix_sessioni_utente_jti`, `ix_sessioni_utente_cleanup_at`

**Trigger**: `trg_sessioni_utente_gen_tx_id_ins_upd` -> `dbops.trgfn_tx_id_managed()`

**GRANT**: automatico via CI grant dinamico su schema `dbops` (SELECT, INSERT per `zeroerp_app`)

**NO storicizzazione** (e' gia' un log, non serve snapshot)
**NO data_update/user_update** (insert-only, non aggiornabile)

**Changeset**: `db/changelog/migrations_v2/00_schema/dbops/20260305-01-create-sessioni-utente-mctit.yaml`

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
| `id` | BIGINT PK | autoincrement (BY DEFAULT) |
| `auth_user_id` | INTEGER | NULL se anonimo |
| `username` | TEXT | JWT user |
| `request_id` | UUID | da RequestContextMiddleware |
| `method` | TEXT NOT NULL | GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD |
| `path` | TEXT NOT NULL | /api/v1/pratiche/ |
| `query_string` | TEXT | parametri query (senza dati sensibili) |
| `status_code` | SMALLINT | 200, 400, 500... (nullable: transazione interrotta) |
| `duration_ms` | INTEGER | tempo di risposta (nullable: transazione interrotta) |
| `ip_address` | INET | |
| `user_agent` | TEXT | |
| `error_code` | TEXT | codice errore se presente (E_PRATICA_NOT_FOUND) |
| `idempotency_key` | TEXT | per correlazione replay |
| `tx_id` | UUID | transaction ID (pattern dbops, trigger `trgfn_tx_id_managed`) |
| `cleanup_at` | TIMESTAMPTZ | retention schedulata (es. 90 giorni) |
| `data_insert` | TIMESTAMPTZ DEFAULT now() | |
| `user_insert` | TEXT DEFAULT CURRENT_USER | audit inserimento |

**Constraint**:

- PK: `pk_request_log`
- CHECK: `chk_request_log_method CHECK (method IN ('GET','POST','PUT','PATCH','DELETE','OPTIONS','HEAD'))`

**Indici**: `ix_request_log_auth_user_id`, `ix_request_log_data_insert`, `ix_request_log_path`, `ix_request_log_request_id`, `ix_request_log_cleanup_at`

**Trigger**: `trg_request_log_gen_tx_id_ins_upd` -> `dbops.trgfn_tx_id_managed()`

**GRANT**: automatico via CI grant dinamico su schema `dbops` (SELECT, INSERT per `zeroerp_app`)

**Volume**: alto — valutare partizionamento per mese se necessario

**Changeset**: `db/changelog/migrations_v2/00_schema/dbops/20260305-02-create-request-log-mctit.yaml`

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

| #  | Area            | Tipo    | Descrizione                                      | Prerequisiti | Stato                        |
|----|-----------------|---------|--------------------------------------------------|--------------|------------------------------|
| 1A | Sessioni        | DB      | Tabella `dbops.sessioni_utente`                  | —            | DONE (changeset + doc)       |
| 1B | Sessioni        | Backend | Repository + service + auth views override       | 1A           | DONE (7 test)                |
| 2A | Request log     | DB      | Tabella `dbops.request_log`                      | —            | DONE (changeset + doc)       |
| 2B | Request log     | Backend | Middleware `RequestLogMiddleware`                 | 2A           | DONE (8 test)                |
| 3A | Token blacklist | DB      | `INSTALLED_APPS` + migrate                       | —            | DONE (settings)              |
| 3B | Token blacklist | Backend | Settings rotation + integrazione disabilitazione | 3A           | DONE (settings)              |

---

## File da creare / modificare

### Nuovi file

| File | Area |
|------|------|
| `db/changelog/migrations_v2/00_schema/dbops/20260305-01-create-sessioni-utente-mctit.yaml` | 1A |
| `db/changelog/migrations_v2/00_schema/dbops/20260305-02-create-request-log-mctit.yaml` | 2A |
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

### Test unitari creati (DONE)

| File | Contenuto | Test |
|------|-----------|------|
| `backend/apps/core/tests/services/test_session_audit_service.py` | Mock DB, verifica chiamate repository per login/refresh, IP, UA, errori silent | 7 |
| `backend/apps/core/tests/api/test_auth_views.py` | Mock service, verifica che le view audit chiamino `record_login`/`record_refresh` | 4 |
| `backend/apps/core/tests/middleware/test_request_log_middleware.py` | Mock DB, verifica INSERT, esclusione path, disabilitazione, errori silent | 8 |

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

---

## Analisi post-implementazione — Incongruenze guida vs codice

> **Data analisi:** 2026-03-07
> **Documenti confrontati:** questa specifica WIP, `docs/it/guide/audit-e-tracciabilita.md`,
> `docs/it/dev/work-in-progress/brief-db-audit-jwt-user.md`,
> `docs/it/dev/work-in-progress/proposta-8.2-audit-trail-permessi.md`,
> codice backend implementato.

### Riepilogo incongruenze trovate

| #   | Sezione guida | Tipo               | Gravità      | Descrizione                                                                                                                                                                                                                                                                                                          |
| --- | ------------- | ------------------ | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | 5.2 passo 3   | Doc fuorviante     | Media        | Spiegazione confusa su `tx_id` nel `request_log` — il `tx_id` presente è quello della propria INSERT (trigger `trgfn_tx_id_managed`), non quello della transazione operativa. La correlazione diretta non esiste ancora; il problema reale è la mancata propagazione di `request_id` come GUC nelle tabelle operative |
| 2   | 5.2 passo 4   | Errore SQL         | Alta         | La query usa `user_insert` per filtrare `sessioni_utente`, ma `user_insert` contiene il ruolo DB (`zeroerp_app`), non lo username JWT. La colonna corretta è `auth_user_id` (con join su `auth_user`)                                                                                                               |
| 3   | 6             | Doc incompleta     | Bassa        | Manca il nome esplicito `JwtAuditMiddleware` nella tabella copertura automatica — la guida dice solo "GUC middleware"                                                                                                                                                                                                |
| 4   | 6 + codice    | Campo non popolato | Bassa        | La colonna `idempotency_key` in `request_log` è definita nella migrazione DB ma il middleware non la popola mai e la guida non la menziona                                                                                                                                                                           |
| 5   | 7             | **Risolto**        | ~~Critica~~ | ~~BUG CRITICO~~ Pattern corretto (INSERT NULL + batch `fn_apply_cleanup_at`). Override TTL aggiunti in `automation_rules_tbl`: id=13 sessioni_utente 180gg, id=14 request_log 90gg. Guida sez. 7 da allineare (dichiarava 365gg sessioni) |
| 6   | 7             | Doc disallineata   | Media        | La guida descrive un job pgAgent dedicato con `DELETE ... WHERE cleanup_at < NOW()`. L'implementazione reale usa il framework generico `fn_run_automations_cleanup` (job `automations_cleanup_weekly`)                                                                                                                |
| 7   | 8             | Doc non aggiornata | Media        | La guida lista "Audit trail permessi" come idea futura generica, ma esiste già la specifica completa `proposta-8.2-audit-trail-permessi.md` con implementazione via storicizzazione su 7 tabelle permessi                                                                                                            |
| 8   | 5 + 8         | Incoerenza interna | Media        | In sez. 5 la formulazione "Se il sistema ha loggato il tx_id nel request log (fase futura)" confonde, perché il tx_id c'è già (è quello dell'INSERT del log stesso). In sez. 8 la formulazione è corretta: "il request_id verrà propagato come GUC". Le due sezioni non sono coerenti tra loro                       |

### Dettaglio per punto

#### Punto 1 — Sez. 5.2 passo 3: correlazione `tx_id` fuorviante

**Stato attuale:** Il `tx_id` nella tabella `request_log` è quello generato dal trigger `trgfn_tx_id_managed` al momento dell'INSERT del record di log stesso. Non ha alcuna relazione con il `tx_id` delle tabelle operative modificate dalla request.

**Cosa serve:** Propagare `request_id` come GUC PostgreSQL (`SET LOCAL app.request_id = ...`), così che le tabelle operative possano registrarlo. Questo renderebbe la correlazione diretta: dato un `request_id` nel `request_log`, si troverebbe lo stesso `request_id` nei record operativi modificati da quella request.

**Correzione guida:** Riscrivere il passo 3 per chiarire che oggi la correlazione è solo temporale (finestra ±5s su `data_update`/`data_insert` + username) e che la correlazione diretta via `request_id` come GUC è l'evoluzione pianificata.

#### Punto 2 — Sez. 5.2 passo 4: query SQL errata

**Codice errato nella guida:**
```sql
SELECT *
FROM dbops.sessioni_utente
WHERE user_insert = :user_update    -- SBAGLIATO: user_insert = 'zeroerp_app'
  AND data_insert <= :data_update
ORDER BY data_insert DESC
LIMIT 1;
```

**Correzione:** La tabella `sessioni_utente` è insert-only e non ha le colonne `data_update`/`user_update` — il trigger `trgfn_audit_data_user_generic` non è applicabile perché su INSERT scrive anche su `data_update`/`user_update` che qui non esistono. Di conseguenza `user_insert` mantiene il DEFAULT `CURRENT_USER` (ruolo DB, es. `zeroerp_app`), non l'utente JWT. L'utente reale è nella colonna dedicata `auth_user_id`. Per filtrare per utente serve usare `auth_user_id`:

```sql
SELECT *
FROM dbops.sessioni_utente su
JOIN auth_user au ON au.id = su.auth_user_id
WHERE au.username = :user_update
  AND su.data_insert <= :data_update
ORDER BY su.data_insert DESC
LIMIT 1;
```

#### Punto 3 — Sez. 6: nome middleware mancante

La tabella di copertura automatica dice "GUC middleware" senza specificare che si tratta di `JwtAuditMiddleware` (`apps/core/middleware/jwt_audit_middleware.py`). Il nome esplicito aiuta la navigazione.

#### Punto 4 — `idempotency_key` non popolata

**Risolto (7 marzo 2026).**

La colonna `idempotency_key` è ora popolata dal middleware `request_log_middleware.py`:

- Aggiunto import `get_idempotency_key` da `request_context`
- Il valore viene letto dalla ContextVar (popolata da `RequestContextMiddleware` dall'header `Idempotency-Key` / `X-Idempotency-Key`) e scritto nell'INSERT
- La guida `audit-e-tracciabilita.md` sez. 4.2 aggiornata con la riga `Idempotenza`

#### Punto 5 — `cleanup_at`: non è un bug, ma la retention dichiarata non corrisponde

**~~BUG CRITICO~~ Riclassificato a "Doc disallineata" (Media).**

Il `cleanup_at` viene lasciato NULL all'INSERT da tutti i repository del progetto — è il pattern standard. La valorizzazione avviene in batch tramite il framework di automazione:

1. `dbops.fn_apply_cleanup_at()` (regola `CLEANUP_AT`, id=11 in `automation_rules_tbl`) scansiona tutte le tabelle con colonna `cleanup_at` e per ogni riga con `cleanup_at IS NULL` calcola: `base_timestamp + TTL_DAYS days`
2. `dbops.fn_purge_cleanup_expired()` (regola `CLEANUP_PURGE`, id=12) elimina in batch le righe con `cleanup_at <= now()`
3. Orchestrate da `fn_run_automations_cleanup()`, eseguita dal job pgAgent `automations_cleanup_weekly` (domenica 23:00 UTC)

Lo stesso pattern è usato da `error_log`, `audit_log` e `idempotency_keys`.

**Risolto:** Aggiunte righe di override in `automation_rules_tbl` (id=13 e id=14, priorità 190 < default 200):

- `sessioni_utente`: TTL **180 giorni** (id=13)
- `request_log`: TTL **90 giorni** (id=14)

Le regole specifiche hanno priorità 190, eseguite prima della regola generica `*all` (priorità 200). Poiché `apply_on_update=false`, la regola generica trova `cleanup_at` già valorizzato e non sovrascrive.

**Guida da allineare:** La sez. 7 dichiarava 365 giorni per sessioni — il valore reale è ora 180 giorni.

#### Punto 6 — Job pgAgent: dedicato vs generico

**Guida (sez. 7):** descrive un job specifico con SQL esplicito `DELETE FROM dbops.sessioni_utente WHERE cleanup_at < NOW()`.

**Implementazione reale:** Il cleanup è gestito dal job generico `automations_cleanup_weekly` che invoca `maintenance.proc_automations_cleanup_job()` → `dbops.fn_run_automations_cleanup()`. Questo framework gestisce tutte le tabelle con colonna `cleanup_at` in modo centralizzato.

**Correzione guida:** Allineare la descrizione al meccanismo reale (framework generico), mantenendo la tabella retention come riferimento.

#### Punto 7 — Audit trail permessi: stato reale

**Guida (sez. 8):** *"Audit trail permessi: log delle modifiche ai profili reparto e override individuali, per tracciare chi ha concesso o revocato accessi e quando."*

**Realtà:** Esiste la specifica completa `proposta-8.2-audit-trail-permessi.md` che definisce:
- 7 tabelle target (6 config + `risorse_umane_auth_user`)
- Approccio: riutilizzo framework storicizzazione generica (`storicizza = true` + `tx_id`)
- Migrazioni Liquibase specificate
- Query di consultazione di esempio

**Stato implementazione:** Migrazioni applicate e operative. Le 7 tabelle hanno `storicizza = true`, `tx_id` e trigger `trgfn_tx_id_managed` attivi (verificato sulla doc auto-generata 2026-03-07). L'audit trail permessi è quindi **completato a livello DB** — manca solo l'allineamento della guida (sez. 8) che lo elenca ancora come "evoluzione futura".

#### Punto 8 — Incoerenza tra sez. 5 e sez. 8

**Sez. 5.2 passo 3:** *"Se il sistema ha loggato il tx_id nel request log (fase futura), la correlazione è diretta."* — Fuorviante: il `tx_id` nel request_log c'è già, ma non serve a correlare con le tabelle operative.

**Sez. 8:** *"il request_id verrà propagato come GUC PostgreSQL e scritto nelle tabelle operative"* — Formulazione corretta.

**Correzione:** Allineare sez. 5 alla formulazione di sez. 8: il problema non è "loggare tx_id nel request_log" ma "propagare request_id nelle tabelle operative via GUC".

### Azioni necessarie

| # | Azione | Tipo | Priorità |
|---|--------|------|----------|
| A | ~~Decidere TTL retention~~ **FATTO**: override aggiunti in `automation_rules_tbl` (id=13: sessioni 180gg, id=14: request_log 90gg). Resta da allineare guida sez. 7 (dichiarava 365gg sessioni) | ~~Config~~ Doc fix | ~~Alta~~ Bassa |
| B | Correggere sez. 5.2 della guida (query SQL + spiegazione correlazione) | Doc fix | Alta |
| C | Aggiornare sez. 7 della guida (cleanup generico, nota su cleanup_at) | Doc fix | Media |
| D | Aggiornare sez. 8 della guida (stato audit trail permessi) | Doc fix | Media |
| E | ~~Aggiornare sez. 6 della guida (nome middleware, nota idempotency_key)~~ **FATTO**: sez. 4.2 aggiornata con riga Idempotenza | ~~Doc fix~~ Completato | ~~Bassa~~ |
| F | ~~Decidere se popolare `idempotency_key` nel middleware~~ **FATTO**: implementato in `request_log_middleware.py` (7 marzo 2026) | ~~Decisione~~ Completato | ~~Bassa~~ |
