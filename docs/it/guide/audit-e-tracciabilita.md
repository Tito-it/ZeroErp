# Guida — Audit e Tracciabilità

> **Ultimo aggiornamento**: 8 novembre 2026
>
> **Destinatari**: sviluppatori database, backend, analisti funzionali
>
> **Vedi anche** — schemi DB:
>
> * [dbops.sessioni_utente](/dbzero/dbops/tabelle/sessioni_utente) — lo strato 2: il ciclo di vita dei token JWT
> * [dbops.request_log](/dbzero/dbops/tabelle/request_log) — lo strato 3: le chiamate API
> * [dbops.audit_log](/dbzero/dbops/tabelle/audit_log) — il log di sistema delle automazioni DB
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — le regole di retention
> * [dbops.transaction_ids](/dbzero/dbops/tabelle/transaction_ids) — il registro delle transazioni
>
> **Vedi anche** — funzioni e trigger DB:
>
> * [script.trgfn_audit_data_user_generic](/dbzero/script/funzioni/trgfn_audit_data_user_generic) — i campi `user_insert`/`user_update`
> * [dbops.trgfn_tx_id_managed](/dbzero/dbops/funzioni/trgfn_tx_id_managed) — il `tx_id` su ogni scrittura
> * [script.trgfn_storico_generic](/dbzero/script/funzioni/trgfn_storico_generic) — lo snapshot storico
> * [dbops.trgfn_cleanup_at_alla_nascita](/dbzero/dbops/funzioni/trgfn_cleanup_at_alla_nascita) / [dbops.fn_cleanup_at_params](/dbzero/dbops/funzioni/fn_cleanup_at_params) — la scadenza scritta all'INSERT
> * [dbops.fn_apply_cleanup_at](/dbzero/dbops/funzioni/fn_apply_cleanup_at) / [dbops.fn_run_automations_cleanup](/dbzero/dbops/funzioni/fn_run_automations_cleanup) — il cleanup in batch
> * [dbops.fn_audit_log_once](/dbzero/dbops/funzioni/fn_audit_log_once) — l'esito delle automazioni
>
> **Vedi anche** — guide correlate:
>
> * [Architettura Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni) — il prerequisito
> * [Storicizzazione tabelle](/guide/storicizzazione-tabelle) — gli snapshot
> * [Automazione DB](/guide/automazione-db) — il framework che orchestra il cleanup
> * [Messaggi di errore e generazione log](/guide/Messaggi-di-Errore-e-Generazione-Log) — il registro errori
> * [Messaggi di audit](/guide/messaggi-audit)
> * [Contratto GUC `app.*`](/guide/contratto-guc-app) — i parametri di sessione

---

## 1. Filosofia

ZeroERP adotta un modello di tracciabilità a **tre strati sovrapposti**, ognuno con
uno scopo distinto e un proprio livello di granularità.

```text
┌─────────────────────────────────────────────────┐
│  Strato 3 — Request log                         │
│  Chi ha chiamato quale endpoint, quando, esito  │
├─────────────────────────────────────────────────┤
│  Strato 2 — Sessioni utente                     │
│  Ciclo di vita del token JWT                    │
├─────────────────────────────────────────────────┤
│  Strato 1 — Audit DB                            │
│  Chi ha modificato quale record, con quale tx   │
└─────────────────────────────────────────────────┘
```

I tre strati sono **autonomi ma correlabili**: ognuno funziona indipendentemente,
ma `tx_id` e `request_id` permettono di attraversarli per ricostruire
l'intera catena di un'azione — dall'HTTP request fino al record modificato nel DB.

Questo sistema non è un'aggiunta posteriore: è parte dell'Anello 0 infrastrutturale
e si attiva automaticamente per ogni modulo costruito sopra. Un endpoint di pratiche,
vendite o acquisti viene tracciato senza che il dominio debba fare nulla.

---

## 2. Strato 1 — Audit DB

### 2.1 Cosa traccia

L'audit DB risponde alla domanda: **quale record è stato modificato, da chi, quando**.
Funziona interamente a livello di database tramite trigger automatici — nessuna
cooperazione richiesta al codice Django.

### 2.2 Campi audit standard

Ogni tabella operativa del sistema include quattro campi di audit:

| Campo         | Tipo        | Descrizione                                     |
| ------------- | ----------- | ----------------------------------------------- |
| `data_insert` | TIMESTAMPTZ | Timestamp di creazione del record               |
| `user_insert` | TEXT        | Utente che ha creato il record                  |
| `data_update` | TIMESTAMPTZ | Timestamp dell'ultimo aggiornamento             |
| `user_update` | TEXT        | Utente che ha effettuato l'ultimo aggiornamento |

I trigger [`trgfn_audit_data_user_generic`](/dbzero/script/funzioni/trgfn_audit_data_user_generic) popolano questi campi automaticamente
su ogni INSERT e UPDATE. Il valore di `user_insert` / `user_update` non è
l'utente di sistema PostgreSQL ma **l'utente applicativo JWT reale**, reso
disponibile tramite il GUC `app.jwt_user` impostato dal middleware Django
ad ogni request autenticata.

**`app.jwt_user` non è più solo.** Dopo il refactor multi-face auth i GUC propagati
a ogni request autenticata sono **sei** — `app.jwt_user`, `app.current_user_id`,
`app.current_identita_id`, `app.ruolo_applicativo`, `app.soggetto_ruolo_id`,
`app.current_emittente_id` — e non servono solo all'audit: la **RLS** delle tabelle
sensibili risolve lo scope emittente proprio a partire da `app.current_emittente_id`.
Due invarianti conseguenti:

* `JwtAuditMiddleware.process_request` **azzera i 6 GUC all'inizio di ogni richiesta
  `/api/`**, prima che l'auth class li ripopoli, in modo **fail-closed**: se il reset
  fallisce la richiesta non viene servita (500 `E_GUC_RESET_FAILED`). Chiude il leak
  cross-request sulle connessioni persistenti;
* una connessione del percorso richiesta che gira su un ruolo `BYPASSRLS` viene
  rifiutata (500 `E_DB_ROLE_UNSAFE`): il bypass è ammesso solo ai canali di sistema
  headless (`system_process_context`).

Contratto completo e semantica per GUC: [contratto-guc-app.md](contratto-guc-app.md) e
[risorse-umane-e-accessi.md](risorse-umane-e-accessi.md) sezione GUC. Conseguenze lato
API (liste filtrate, 404 su dettaglio fuori scope): [api.md](../dev/api.md) sezione
"Scope emittente".

### 2.3 Transaction ID

Ogni INSERT e UPDATE su tabelle operative genera un `tx_id UUID`, assegnato dal
trigger [`trgfn_tx_id_managed`](/dbzero/dbops/funzioni/trgfn_tx_id_managed). Il `tx_id` vale per l'intera transazione PostgreSQL:
due record modificati nella stessa transazione condividono lo stesso `tx_id`.

Questo permette di raggruppare tutte le scritture avvenute in un'unica operazione
atomica — ad esempio, la creazione di una pratica che genera contestualmente
il primo flusso e la prima voce di giornale.

⚠️ **Le tabelle che scrive solo la migrazione non hanno `tx_id`.** Nello schema `dbops` i
cataloghi seminati dai CSV (processi, presidi, tipi di lavoro, i registri del debito) non portano
né `tx_id` né `data_update`/`user_update`: legherebbero la riga alla sola migrazione, e direbbero
«il migratore» a chi cerca chi l'ha cambiata. Lo dicono già lo storico delle migrazioni e git.
Le tabelle di `dbops` che si scrivono a runtime (la coda lavori, le identità tecniche, i registri)
tengono il `tx_id` col trigger, montato a mano o dal framework: la regola sta in
[automazione-db.md](automazione-db.md) §1.1.

### 2.4 Storicizzazione

Le tabelle operative con `storicizza = true` vengono fotografate dal trigger
[`trgfn_storico_generic`](/dbzero/script/funzioni/trgfn_storico_generic) ad ogni UPDATE e DELETE. Ogni snapshot finisce in
`storico.<nome_tabella>` con il valore completo del record prima della modifica.

La storicizzazione è l'ultimo livello di difesa: anche se un record viene
aggiornato più volte, la storia completa di ogni versione è recuperabile.

### 2.5 Giornale di bordo (modulo pratiche)

Il modulo pratiche introduce un ulteriore meccanismo di audit specifico per
il ciclo di vita delle pratiche: la tabella [`pratiche.giornale`](/dbzero/pratiche/tabelle/giornale). È un log
append-only alimentato da trigger dedicati che registra ogni evento semantico
(pratica creata, stato cambiato, flusso completato, nota aggiunta).

A differenza dei campi audit standard — che rispondono a "quando è stato
toccato il record" — il giornale risponde a "cosa è accaduto nel processo".

Il modello completo, con gli eventi e i trigger che lo alimentano, sta in
[Gestione Pratiche e Workflow](/guide/gestione-pratiche), capitolo *Il giornale di bordo*.

---

## 3. Strato 2 — Sessioni Utente

### 3.1 Cosa traccia

Le sessioni utente rispondono alla domanda: **quando un utente ha ottenuto
o rinnovato un token, da dove, e quando quella sessione è terminata**.

### 3.2 Ciclo di vita tracciato

La tabella [`dbops.sessioni_utente`](/dbzero/dbops/tabelle/sessioni_utente) registra ogni evento significativo
del ciclo di vita JWT:

| Evento     | Quando si genera                                           |
| ---------- | ---------------------------------------------------------- |
| `LOGIN`    | Emissione token al login (`/api/token/`)                   |
| `REFRESH`  | Rinnovo token (`/api/token/refresh/`)                      |
| `LOGOUT`   | Revoca esplicita da parte dell'utente                      |
| `SCADENZA` | Token scaduto naturalmente                                 |
| `REVOCA`   | Token invalidato forzatamente (es. disabilitazione utente) |

Per ogni evento vengono registrati: l'utente (`auth_user_id`), il JWT ID
univoco del token (`jti`), l'indirizzo IP, lo user agent del client e
il `request_id` che correla l'evento con il request log.

### 3.3 Implementazione

Le view JWT di SimpleJWT sono sovrascritte da `AuditTokenObtainPairView`
e `AuditTokenRefreshView` — definite in `apps/core/api/auth_views.py`.
Dopo ogni emissione o rinnovo di token riuscito, le view chiamano
`session_audit_service.record_login()` / `record_refresh()`.

Il service scrive in modo silenzioso: un errore di logging non blocca
mai l'autenticazione dell'utente.

### 3.4 Revoca token (blacklist)

ZeroERP usa il modulo `rest_framework_simplejwt.token_blacklist`.
Con `BLACKLIST_AFTER_ROTATION = true` ogni refresh consuma il token
precedente: il vecchio refresh token viene inserito nella blacklist
immediatamente. Un token compromesso può essere revocato manualmente
aggiungendolo alla blacklist; al successivo utilizzo verrà rifiutato
a livello di autenticazione, prima ancora che la request raggiunga
qualsiasi view.

---

## 4. Strato 3 — Request Log

### 4.1 Cosa traccia

Il request log risponde alla domanda: **quale utente ha chiamato quale
endpoint, quando, con quale esito e in quanto tempo**.

### 4.2 Dati registrati

La tabella [`dbops.request_log`](/dbzero/dbops/tabelle/request_log) registra per ogni request API:

| Dato          | Descrizione                                                       |
| ------------- | ----------------------------------------------------------------- |
| Utente        | `auth_user_id` e `username` dal token JWT                         |
| Endpoint      | `method` + `path`                                                 |
| Parametri     | `query_string` (solo parametri URL, mai body)                     |
| Esito         | `status_code` HTTP                                                |
| Performance   | `duration_ms` — tempo di risposta in millisecondi                 |
| Contesto rete | `ip_address`, `user_agent`                                        |
| Correlazione  | `request_id` UUID — condiviso con sessioni_utente                 |
| Errore        | `error_code` — codice errore applicativo se presente              |
| Idempotenza   | `idempotency_key` — chiave idempotenza dalla request, se presente |

Il body della request e della response non viene mai loggato: riduce
il volume e previene la registrazione accidentale di dati sensibili.

### 4.3 Implementazione

`RequestLogMiddleware` si inserisce nella catena middleware Django dopo
`JwtAuditMiddleware`. Per ogni request su path `/api/*`:

1. Salva il timestamp di avvio in `process_request()`
2. Al termine, calcola la durata e inserisce il record in `dbops.request_log`

Il middleware non registra i percorsi tecnici (`/health`, `/api/docs/`,
`/api/schema/`, file statici e caricati). Può essere
disabilitato completamente con `DJANGO_REQUEST_LOG_ENABLED = false`.

L'inserimento è silenzioso: un errore di scrittura nel log non produce
mai un errore HTTP verso il client.

### 4.4 Considerazioni sul volume

Il request log è la tabella con il volume di scrittura più alto del sistema.
Ogni request API autenticata genera una riga. Per ambienti con traffico
elevato è previsto partizionamento per mese tramite PostgreSQL table
partitioning. La retention è configurabile tramite `cleanup_at`: un job
pgAgent periodico rimuove i record oltre la soglia (default 90 giorni).

---

## 5. Correlazione tra strati

### 5.1 Il filo conduttore

I tre strati sono attraversabili grazie a due identificatori condivisi:

```text
request_id (UUID)
  │
  ├── dbops.request_log.request_id       (quale endpoint è stato chiamato)
  │
  └── dbops.sessioni_utente.request_id   (se la request era un login/refresh)

tx_id (UUID)
  │
  ├── pratiche.pratiche.tx_id            (record creato/modificato)
  ├── pratiche.flussi.tx_id              (nella stessa transazione)
  ├── pratiche.giornale.tx_id            (voci di giornale correlate)
  └── storico.<tabella>.tx_id            (snapshot storici della stessa tx)
```

Il `request_id` collega il livello HTTP al livello sessione.
Il `tx_id` collega le scritture DB tra loro all'interno di una transazione.
Il `username` / `user_insert` collega entrambi all'identità dell'utente.

### 5.2 Investigare un'anomalia — percorso tipo

Scenario: un record in `pratiche.pratiche` risulta modificato con un valore
inatteso. Come risalire alla causa.

**Passo 1 — Identificare la modifica nel DB.** Si legge il record operativo per
ricavare `data_update`, `user_update` e `tx_id`: sono i tre appigli per tutto il
resto.

**Passo 2 — Recuperare la versione precedente dallo storico.** Lo snapshot è in
`storico.<tabella>`: le righe più recenti di quell'id dicono com'era il record prima
della modifica.

**Passo 3 — Risalire alla request HTTP.** La correlazione tra la request HTTP e la
scrittura DB avviene **per finestra temporale**: il `data_update` del record
operativo combacia con il `data_insert` del request log per lo stesso utente nello
stesso istante. Il `tx_id` presente nel `request_log` è quello della propria INSERT
di log (generato dal trigger [`trgfn_tx_id_managed`](/dbzero/dbops/funzioni/trgfn_tx_id_managed)), non quello
della transazione operativa — quindi non è utilizzabile per correlazione diretta.
In futuro la correlazione diventerà diretta, con il `request_id` propagato come GUC
PostgreSQL nelle tabelle operative (vedi §8).

**Passo 4 — Verificare la sessione attiva in quel momento.** L'ultima riga di
`dbops.sessioni_utente` per quell'utente prima della modifica dice con quale sessione
JWT è stata fatta.

> Le quattro query, pronte da adattare, stanno nell'[Area tecnica](#area-tecnica-esempi).

---

## 6. Copertura automatica per i moduli

Un modulo che si appoggia sull'Anello 0 ottiene la tracciabilità completa
senza scrivere codice di logging:

| Capacità                                    | Chi la fornisce                                                                                                 | Configurazione richiesta          |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | --------------------------------- |
| Campi `user_insert/update` con utente reale | [`trgfn_audit_data_user_generic`](/dbzero/script/funzioni/trgfn_audit_data_user_generic) + `JwtAuditMiddleware` | Nessuna                           |
| `tx_id` su ogni scrittura                   | [`trgfn_tx_id_managed`](/dbzero/dbops/funzioni/trgfn_tx_id_managed)                                             | Nessuna                           |
| Snapshot storico ad ogni modifica           | [`trgfn_storico_generic`](/dbzero/script/funzioni/trgfn_storico_generic) + `storicizza=true`                    | `storicizza = true` sulla tabella |
| Log di ogni request API                     | `RequestLogMiddleware`                                                                                          | Nessuna (middleware globale)      |
| Log login/refresh JWT                       | `AuditTokenObtainPairView/RefreshView`                                                                          | Nessuna (view globale)            |

L'unica cosa che un modulo deve fornire autonomamente è il **giornale di dominio**
(come [`pratiche.giornale`](/dbzero/pratiche/tabelle/giornale)) quando vuole tracciare eventi semantici specifici
oltre al semplice "quando è stato toccato il record".

### Nota: `dbops.audit_log`

La tabella [`dbops.audit_log`](/dbzero/dbops/tabelle/audit_log) non fa parte dei tre strati di tracciabilità
descritti in questa guida: è il **log di sistema delle automazioni DB**.
Tutte le funzioni del framework di automazione (`fn_run_automations_*`)
registrano il proprio esito — regola applicata, tabella, righe modificate,
errori — tramite [`fn_audit_log_once()`](/dbzero/dbops/funzioni/fn_audit_log_once). È lo strumento per verificare
che il cleanup, la storicizzazione, i lock e le altre automazioni
infrastrutturali funzionino correttamente.

Retention: 30 giorni (regola CLEANUP_AT default, id=11).

---

## 7. Manutenzione e retention

### Retention configurabile

Entrambe le tabelle di audit condividono il campo `cleanup_at TIMESTAMPTZ`
che indica quando il record può essere rimosso. Il valore non viene
impostato all'inserimento ma calcolato in batch dal framework di
automazione [`fn_apply_cleanup_at()`](/dbzero/dbops/funzioni/fn_apply_cleanup_at), che applica un TTL configurato
in [`dbops.automation_rules_tbl`](/dbzero/dbops/tabelle/automation_rules_tbl) a partire dalla colonna `data_insert`.

| Tabella                  | Retention  | Regola override     | Note                                       |
| ------------------------ | ---------- | ------------------- | ------------------------------------------ |
| `dbops.sessioni_utente`  | 180 giorni | id=13, priorità 190 | Audit compliance                           |
| `dbops.request_log`      | 90 giorni  | id=14, priorità 190 | Volume elevato; scadenza scritta alla nascita |
| `dbops.idempotency_keys` | 1 giorno   | id=24, priorità 190 | Base `data_insert`; scadenza scritta alla nascita |
| `dbops.error_log`        | 90 giorni  | id=25, priorità 190 | Base `occurred_at`; scadenza calcolata dal job |
| `dbops.audit_log`        | 90 giorni  | id=26, priorità 190 | Base `executed_at`; scadenza calcolata dal job |
| `dbops.ai_query_log`     | 90 giorni  | id=28, priorità 190 | Testo scritto all'assistente; base `data_insert`; scadenza scritta alla nascita |

⛔ **Una tabella con `cleanup_at` si pulisce solo se sta in
[`dbops.automation_scope`](/dbzero/dbops/tabelle/automation_scope)**: l'orchestratore scorre
le tabelle dello scope, non tutte quelle che hanno la colonna. Per lo schema `dbops` lo
scope elenca `sessioni_utente`, `processi_accensione`, `idempotency_keys`, `request_log`,
`error_log`, `audit_log` e `ai_query_log`. Una tabella con `cleanup_at` fuori dallo scope la
segnala il presidio
[`dbops.vw_marcatori_automazione_senza_esecutore`](/dbzero/dbops/views/vw_marcatori_automazione_senza_esecutore).

Errori e chiamate restano **90 giorni** insieme: chi indaga su una richiesta guarda la
chiamata (`request_log`) e l'errore che ne è uscito (`error_log`), e i due registri devono
scadere insieme. `audit_log`, il registro dei giri delle automazioni, segue la stessa regola, e
così `ai_query_log`, le domande all'assistente con le risposte: testo degli utenti che non si
tiene oltre.

⚠️ `error_log` e `audit_log` **non** hanno il trigger alla nascita: li scrivono anche
sessioni dblink, con un ruolo che non legge le regole di scadenza, e il trigger farebbe
fallire la registrazione degli errori. La scadenza la calcola il job settimanale sulle righe
che non l'hanno ancora.

Una key di idempotenza vive un giorno perché serve solo finché il client può rimandare la
**stessa** richiesta: il frontend la tiene per un gesto, al massimo dieci minuti, poi ne
genera una nuova.

#### ⭐ I registri di dominio: la scadenza si scrive alla nascita

I **registri** di vendite non aspettano il batch:
`cleanup_at` lo scrive **all'`INSERT`** il trigger generico
[`dbops.trgfn_cleanup_at_alla_nascita`](/dbzero/dbops/funzioni/trgfn_cleanup_at_alla_nascita)
(`trg_<tabella>_m50_cleanup_at_ins`), leggendo termine **e colonna base** dalla stessa
regola che userebbe il job, via
[`dbops.fn_cleanup_at_params`](/dbzero/dbops/funzioni/fn_cleanup_at_params).
Su un registro l'UPDATE notturno riscriverebbe `data_update`/`user_update` di ogni riga
fresca e passerebbe dai trigger di `UPDATE`; alla nascita la riga sa già quando scade. Il
batch resta per il **pregresso** (righe a `NULL`), una volta.

| Tabella                                | Retention  | Colonna base | Regola |
| -------------------------------------- | ---------- | ------------ | ------ |
| `vendite.event_log`                    | 750 giorni | `event_time` | id=15  |
| `vendite.fatturazione_lotti_log`       | 750 giorni | `data_ora`   | id=16  |
| `vendite.fatture_log`                  | 750 giorni | `data_ora`   | id=17  |
| `vendite.fatturazione_lotti_task_runs` | 750 giorni | `started_at` | id=18  |
| `vendite.commesse_push_log`            | 750 giorni | `run_at`     | id=19  |

Lo stesso trigger è montato anche su tre registri di `dbops`, `request_log` e `ai_query_log`
(90 giorni) e `idempotency_keys` (un giorno), con le regole della tabella sopra.

750 e non 30: sono i quattro registri che `script.vw_giornale_entita` legge insieme (più
il registro di giro del push, a cui punta il `correlation_id` di `event_log`) e la storia
di un caso non deve perdere un pezzo prima degli altri — due chiusure annuali. I guard
sul `DELETE` di quei registri (`trgfn_event_log_append_only`, `trgfn_logs_guard_delete`)
lasciano passare la riga **scaduta** senza GUC: il criterio non è *chi* cancella ma *cosa*.
⚠️ Su `fatture_log` il purge ricalcola `fatture.critical`: il critico deriva dal registro e
ne eredita la scadenza.

### Framework cleanup automatico

La manutenzione è gestita dal framework generico di automazione tramite
due regole in [`dbops.automation_rules_tbl`](/dbzero/dbops/tabelle/automation_rules_tbl):

1. **`CLEANUP_AT`** (id=11, default 30gg; override id=13/14 per le tabelle
   audit): calcola `cleanup_at = data_insert + TTL` per ogni riga con
   `cleanup_at IS NULL`
2. **`CLEANUP_PURGE`** (id=12): elimina in batch (5000 righe) i record
   con `cleanup_at <= now()`

Entrambe sono orchestrate da [`dbops.fn_run_automations_cleanup()`](/dbzero/dbops/funzioni/fn_run_automations_cleanup),
invocata dal job pgAgent `automations_cleanup_weekly` (domenica 23:00 UTC)
tramite `maintenance.proc_automations_cleanup_job()`. L'esito è tracciato
in [`dbops.audit_log`](/dbzero/dbops/tabelle/audit_log).

### Token blacklist

I token scaduti nella blacklist SimpleJWT vengono puliti dal command
Django `manage.py flushexpiredtokens`, anch'esso schedulato tramite
pgAgent come script shell.

---

## 8. Consultazione e sviluppi aperti

**Le API che ci sono.** Due viste di consultazione sono disponibili:

* il registro degli **errori** — `GET /api/v1/amm-software/error-log/` (con
  `export/`), schermata «Errori tecnici»: [api_error_log](/backend/amm-software/manual/api_error_log);
* il **giornale degli eventi di dominio**, trasversale — `GET /api/v1/vendite/giornale/`:
  [api_giornale](/backend/vendite/manual/api_giornale).

Il `tx_id` è il ponte fra i due.

**Cosa resta aperto.**

* **Propagazione del `request_id` come GUC**: la correlazione tra request HTTP e
  scrittura DB passa ancora per la finestra temporale (§5.2, passo 3). Portare il
  `request_id` nei parametri di sessione PostgreSQL e scriverlo nelle tabelle
  operative renderebbe la correlazione diretta.
* **API di `request-log` e sessioni**: `GET /api/v1/core/users/{id}/sessioni/` e
  `GET /api/v1/core/request-log/` per gli amministratori, con filtri per
  data/path/status.
* **Dashboard anomalie**: una vista operativa che segnala pattern inusuali — login da
  IP multipli, volume di richieste anomalo, token revocati riutilizzati.

---

## Area tecnica — esempi

### Il percorso di indagine, in query

Le quattro query del §5.2, pronte da adattare (i `:parametri` sono quelli del caso
in esame).

**Identificare la modifica.** Chi e quando ha toccato il record, e con quale
`tx_id`.

```sql
SELECT data_update, user_update, tx_id
FROM pratiche.pratiche
WHERE id = :pratica_id;
```

**Recuperare lo snapshot precedente.** Com'era il record prima della modifica.

```sql
SELECT *
FROM storico.pratiche
WHERE id = :pratica_id
ORDER BY data_update DESC
LIMIT 5;
```

**Trovare la request HTTP.** Sulla finestra temporale della modifica, per lo stesso
utente.

```sql
SELECT *
FROM dbops.request_log
WHERE username = :user_update
  AND data_insert BETWEEN :data_update - interval '5s'
                      AND :data_update + interval '5s';
```

**Trovare la sessione JWT.** L'ultima attiva prima della modifica.

```sql
SELECT su.*
FROM dbops.sessioni_utente su
JOIN auth_user au ON au.id = su.auth_user_id
WHERE au.username = :user_update
  AND su.data_insert <= :data_update
ORDER BY su.data_insert DESC
LIMIT 1;
```

### Dove sta il codice

* Schema DB: `db/changelog/migrations_v2/00_schema/dbops/`
* Repository delle sessioni: `backend/apps/core/db/session_audit_repository.py`
* Middleware del request log: `backend/apps/core/middleware/request_log_middleware.py`

---
{% include-markdown "signature-core.md" %}
