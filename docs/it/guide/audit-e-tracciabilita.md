# Guida Tecnica — Audit e Tracciabilità

> **Destinatari:** sviluppatori database, backend, analisti funzionali
>
> **Prerequisiti:** [Guida Permessi e Autorizzazioni](/guide/permessi-autorizzazioni)
>
> **Stato:** Implementato — Anello 0 (nucleo infrastrutturale)
>
> **Riferimenti sorgente:**
> `db/changelog/migrations_v2/00_schema/dbops/` —
> `backend/apps/core/db/session_audit_repository.py` —
> `backend/apps/core/middleware/request_log_middleware.py`

---

## 1. Filosofia

ZeroERP adotta un modello di tracciabilità a **tre strati sovrapposti**, ognuno con
uno scopo distinto e un proprio livello di granularità.

```
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

I trigger `trgfn_audit_data_user_generic` popolano questi campi automaticamente
su ogni INSERT e UPDATE. Il valore di `user_insert` / `user_update` non è
l'utente di sistema PostgreSQL ma **l'utente applicativo JWT reale**, reso
disponibile tramite il GUC `app.jwt_user` impostato dal middleware Django
ad ogni request autenticata.

Per i dettagli sull'implementazione del GUC e della catena middleware si rimanda
a `docs/it/dev/work-in-progress/brief-db-audit-jwt-user.md`.

### 2.3 Transaction ID

Ogni INSERT e UPDATE su tabelle operative genera un `tx_id UUID`, assegnato dal
trigger `trgfn_tx_id_managed`. Il `tx_id` vale per l'intera transazione PostgreSQL:
due record modificati nella stessa transazione condividono lo stesso `tx_id`.

Questo permette di raggruppare tutte le scritture avvenute in un'unica operazione
atomica — ad esempio, la creazione di una pratica che genera contestualmente
il primo flusso e la prima voce di giornale.

### 2.4 Storicizzazione

Le tabelle operative con `storicizza = true` vengono fotografate dal trigger
`trgfn_storico_generic` ad ogni UPDATE e DELETE. Ogni snapshot finisce in
`storico.<nome_tabella>` con il valore completo del record prima della modifica.

La storicizzazione è l'ultimo livello di difesa: anche se un record viene
aggiornato più volte, la storia completa di ogni versione è recuperabile.

### 2.5 Giornale di bordo (modulo pratiche)

Il modulo pratiche introduce un ulteriore meccanismo di audit specifico per
il ciclo di vita delle pratiche: la tabella `pratiche.giornale`. È un log
append-only alimentato da trigger dedicati che registra ogni evento semantico
(pratica creata, stato cambiato, flusso completato, nota aggiunta).

A differenza dei campi audit standard — che rispondono a "quando è stato
toccato il record" — il giornale risponde a "cosa è accaduto nel processo".

Per i dettagli si rimanda a `docs/it/dev/gestione-pratiche.md`, sezione 4.

---

## 3. Strato 2 — Sessioni Utente

### 3.1 Cosa traccia

Le sessioni utente rispondono alla domanda: **quando un utente ha ottenuto
o rinnovato un token, da dove, e quando quella sessione è terminata**.

### 3.2 Ciclo di vita tracciato

La tabella `dbops.sessioni_utente` registra ogni evento significativo
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

La tabella `dbops.request_log` registra per ogni request API:

| Dato          | Descrizione                                          |
| ------------- | ---------------------------------------------------- |
| Utente        | `auth_user_id` e `username` dal token JWT            |
| Endpoint      | `method` + `path`                                    |
| Parametri     | `query_string` (solo parametri URL, mai body)        |
| Esito         | `status_code` HTTP                                   |
| Performance   | `duration_ms` — tempo di risposta in millisecondi    |
| Contesto rete | `ip_address`, `user_agent`                           |
| Correlazione  | `request_id` UUID — condiviso con sessioni_utente    |
| Errore        | `error_code` — codice errore applicativo se presente |

Il body della request e della response non viene mai loggato: riduce
il volume e previene la registrazione accidentale di dati sensibili.

### 4.3 Implementazione

`RequestLogMiddleware` si inserisce nella catena middleware Django dopo
`JwtAuditMiddleware`. Per ogni request su path `/api/*`:

1. Salva il timestamp di avvio in `process_request()`
2. Al termine, calcola la durata e inserisce il record in `dbops.request_log`

Il middleware filtra automaticamente path esclusi (`/health`, `/api/docs/`)
configurabili tramite `DJANGO_REQUEST_LOG_EXCLUDE_PATHS`. Può essere
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

```
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

**Passo 1 — Identificare la modifica nel DB**

```sql
-- Trovare quando e da chi è stato modificato il record
SELECT data_update, user_update, tx_id
FROM pratiche.pratiche
WHERE id = :pratica_id;
```

**Passo 2 — Recuperare la versione precedente dallo storico**

```sql
-- Trovare lo snapshot prima della modifica
SELECT *
FROM storico.pratiche
WHERE id = :pratica_id
ORDER BY data_update DESC
LIMIT 5;
```

**Passo 3 — Risalire alla request HTTP tramite tx_id**

Il `tx_id` è propagato nel giornale e nelle tabelle operative nella stessa
transazione. Se il sistema ha loggato il `tx_id` nel request log (fase
futura), la correlazione è diretta. Oggi la correlazione avviene tramite
la finestra temporale: `data_update` del record combacia con `data_insert`
del request log per quell'utente in quel momento.

```sql
-- Request dell'utente nel minuto della modifica
SELECT *
FROM dbops.request_log
WHERE username = :user_update
  AND data_insert BETWEEN :data_update - interval '5s'
                      AND :data_update + interval '5s';
```

**Passo 4 — Verificare la sessione attiva in quel momento**

```sql
-- Sessione JWT attiva al momento della modifica
SELECT *
FROM dbops.sessioni_utente
WHERE user_insert = :user_update
  AND data_insert <= :data_update
ORDER BY data_insert DESC
LIMIT 1;
```

---

## 6. Copertura automatica per i moduli

Un modulo che si appoggia sull'Anello 0 ottiene la tracciabilità completa
senza scrivere codice di logging:

| Capacità                                    | Chi la fornisce                                  | Configurazione richiesta          |
| ------------------------------------------- | ------------------------------------------------ | --------------------------------- |
| Campi `user_insert/update` con utente reale | `trgfn_audit_data_user_generic` + GUC middleware | Nessuna                           |
| `tx_id` su ogni scrittura                   | `trgfn_tx_id_managed`                            | Nessuna                           |
| Snapshot storico ad ogni modifica           | `trgfn_storico_generic` + `storicizza=true`      | `storicizza = true` sulla tabella |
| Log di ogni request API                     | `RequestLogMiddleware`                           | Nessuna (middleware globale)      |
| Log login/refresh JWT                       | `AuditTokenObtainPairView/RefreshView`           | Nessuna (view globale)            |

L'unica cosa che un modulo deve fornire autonomamente è il **giornale di dominio**
(come `pratiche.giornale`) quando vuole tracciare eventi semantici specifici
oltre al semplice "quando è stato toccato il record".

---

## 7. Manutenzione e retention

### Retention configurabile

Entrambe le tabelle di audit condividono il campo `cleanup_at TIMESTAMPTZ`
che indica quando il record può essere rimosso. Il valore viene impostato
all'inserimento in base alla policy configurata per ciascuna tabella.

| Tabella                 | Retention default | Note             |
| ----------------------- | ----------------- | ---------------- |
| `dbops.sessioni_utente` | 365 giorni        | Audit compliance |
| `dbops.request_log`     | 90 giorni         | Volume elevato   |

### Job pgAgent

Un job schedulato giornaliero esegue la pulizia:

```sql
DELETE FROM dbops.sessioni_utente WHERE cleanup_at < NOW();
DELETE FROM dbops.request_log     WHERE cleanup_at < NOW();
```

Il job segue il pattern `fn_run_and_log` — il suo esito è tracciato
in `maintenance.job_run_log` come tutti i job pgAgent del sistema.

### Token blacklist

I token scaduti nella blacklist SimpleJWT vengono puliti dal command
Django `manage.py flushexpiredtokens`, anch'esso schedulato tramite
pgAgent come script shell.

---

## 8. Evoluzione futura

Le seguenti funzionalità sono pianificate ma non ancora implementate:

- **Propagazione `request_id` → `tx_id`**: oggi la correlazione tra
  request HTTP e scrittura DB avviene per finestra temporale. In futuro
  il `request_id` verrà propagato come GUC PostgreSQL e scritto
  nelle tabelle operative, rendendo la correlazione diretta e inequivocabile.

- **API di consultazione**: endpoint `GET /api/v1/core/users/{id}/sessioni/`
  e `GET /api/v1/core/request-log/` per ADMIN, con filtri per data/path/status.

- **Dashboard anomalie**: vista operativa che segnala pattern inusuali —
  login da IP multipli, volume request anomalo, token revocati riutilizzati.

- **Audit trail permessi**: log delle modifiche ai profili reparto e override
  individuali, per tracciare chi ha concesso o revocato accessi e quando.

---

*Documento tecnico — Audit e Tracciabilità — ZeroERP (marzo 2026)*