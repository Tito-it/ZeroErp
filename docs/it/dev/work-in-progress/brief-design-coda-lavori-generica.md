# Brief di design — Coda lavori generica (job queue DB-native)

> **Tipo**: brief di design (design-of-record) · **Data**: 2026-07-20 · **Owner**: Tid
> · **Stato**: 🟡 proposta — in attesa approvazione ambito + prerequisiti DB
> · **Target codice**: `dev/backend-tid` · **Target DB**: `dev/db-tid`
>
> **Contesto**: emerso durante la Fase C del cockpit fatturazione (C-3, giro
> on-demand). Regola del 2 a livello architetturale: `vendite.fatture_stampa_coda`
> (1ª coda, C-2b) stava per essere seguita da `fatturazione_richieste` (2ª). Invece
> di **una tabella per batch**, si estrae **una coda lavori generica** — la
> variante DB-native, transazionale e senza broker del pattern "task queue"
> (Rails SolidQueue, pg-boss, Oban: l'industria sta tornando alle code su DB).
>
> **Decisione di ambito (Tid, 2026-07-20)**: **fondazione completa**. La coda
> generica è la base async di tutto l'ERP; C-3 ne è il **primo consumatore**.
>
> **Documenti collegati**:
> [brief-be-fe-processi-fatturazione.md](brief-be-fe-processi-fatturazione.md)
> (Fase C, C-3 consumatore) · brief DB dedicato (DDL) da produrre su `dev/db-tid`
> ([[feedback_db_actions_passaggio_team]]).

---

## 0. Scopo in una riga

Una **sola** coda di lavori generica su Postgres — enqueue **atomico** col dato di
business, drenata da un **worker unico** che dispatcha per tipo di job — così ogni
nuovo lavoro asincrono dell'ERP (fatturazione on-demand, invio PEC/SDI, report,
export…) è **un handler + un enqueue**, non una nuova tabella + nuovo worker + nuova
migration.

## 1. Perché DB-native e non un broker (celery/RQ)

Deciso in discussione 2026-07-20 (vedi cronologia Fase C). Sintesi:

| Criterio | Coda su DB (questa) | Broker (redis + celery/RQ) |
| --- | --- | --- |
| **Enqueue atomico** col dato di business | ✅ stessa transazione (no dual-write) | ❌ commit DB + enqueue redis = due fallimenti possibili |
| Nuova infrastruttura | nessuna (Postgres c'è) | broker + worker + (beat) + monitoring |
| Osservabilità | SQL diretto + `job_run_log` | flower/dashboard esterni |
| Compat Python 3.14 | nativa | rischio (celery/billiard laggano sulle Python nuove) |
| Scheduling temporale | resta a **pgAgent + systemd** (già in uso) | celery beat (terzo modo di fare i cron) |
| Adatto a job **transazionali** (fatturazione, SDI) | ✅ ideale | ⚠️ dual-write sul dato fiscale |

**Confine**: la coda-broker resta un'opzione **futura** per l'async *non transazionale
ed eterogeneo di massa* (se e quando servirà); non è questo brief. I **cron/schedulati**
restano su **pgAgent + systemd** — la coda non li sostituisce.

## 2. Cosa si riusa (non si reinventa nulla)

La fondazione è già per metà nel progetto:

* **Dispatch controllato via registry** — `dbops.domini_task` +
  `dbops.pipeline_task_registry` + `dbops.pipeline_task_registry_impl`
  (`implementation_key` → `handler_code`, **no dynamic import**) e il
  `PipelineStepExecutor.handler_registry` Python (dict `handler_code → callable`).
  La coda generica adotta la **stessa filosofia**: `job_type` → `handler_code` →
  callable, dispatch controllato.
* **Worker drainer** — `draina_coda_stampa` (C-2b) è già il **90%** del worker
  generico: claim `FOR UPDATE SKIP LOCKED`, reaper righe stantie, tentativi/errore,
  best-effort per-riga. Va **generalizzato** (dispatch per `job_type` invece di
  "renderizza fattura").
* **Tracciamento run** — `maintenance.job_run_log` (tabella ledger) via il
  context-manager Python `registered_job` (in `apps/core/services/job_run.py`, lock
  advisory anti-overlap; **non** è una tabella) per il worker.
* **Canale sistema / scope** — `system_process_context` (BYPASSRLS) per i job di
  sistema; cattura dello scope operatore all'enqueue per i job on-demand.

## 3. Modello dati (proposta — DDL nel brief DB)

Schema tecnico cross-dominio: **`dbops`** (registry-adjacent). Il worker scrive il
run in `maintenance.job_run_log` (riuso).

### 3.1 `dbops.coda_lavori` — la coda

| Colonna | Tipo | Note |
| --- | --- | --- |
| `id` | bigint IDENTITY | PK |
| `uid` | uuid | `uuidv7()` |
| `job_type` | text NOT NULL | chiave di dispatch (FK logica a `coda_lavori_tipi.codice`) |
| `payload` | jsonb NOT NULL DEFAULT '{}' | argomenti del job |
| `run_as` | text NOT NULL | `SISTEMA` \| `OPERATORE` (chi esegue) — CHECK |
| `scope` | jsonb | scope autorizzativo **catturato all'enqueue** (es. `{emittente_ids:[…], auth_user_id:N}`) per i job OPERATORE |
| `origine` | text NOT NULL DEFAULT 'API' | `API` \| `CRON` \| `COMMAND` \| `TRIGGER` (chi ha **accodato**). Set proprio della coda: NON identico a `maintenance.job_run_log.origine` = `PGAGENT`/`CRON`/`COMMAND` (chi *esegue* il run). `TRIGGER` copre l'enqueue DB-native |
| `priorita` | smallint NOT NULL DEFAULT 100 | minore = più urgente |
| `stato` | text NOT NULL DEFAULT 'PENDING' | `PENDING`/`IN_CORSO`/`FATTO`/`ERRORE`/`ANNULLATO` — CHECK |
| `tentativi` | int NOT NULL DEFAULT 0 | CHECK ≥ 0 |
| `max_tentativi` | int NOT NULL DEFAULT 5 | oltre → `ERRORE` terminale |
| `ultimo_errore` | jsonb | `{code, message, detail}` |
| `run_after` | timestamptz | eleggibile solo se NULL o ≤ now() (**job differiti**) |
| `claimed_at` | timestamptz | istante del claim (reaper; esplicito, no trigger audit) |
| `started_at` / `ended_at` | timestamptz | finestra esecuzione |
| `job_run_id` | bigint | link a `maintenance.job_run_log` |
| `idempotency_key` | text | dedup job vivi (vedi indice) |
| `result` | jsonb | esito/summary (es. `{lotto_id, documento_id}`) |
| `data_insert/user_insert/data_update/user_update` | audit | standard (`data_*`, convenzione it-IT) — via trigger `script.trgfn_audit_data_user_generic` (vedi brief DB Q-A) |
| `tx_id` | uuid | policy tx-id |

> ⚠️ **Nessun trigger audit** sulla tabella (come `fatture_stampa_coda`): i metodi
> di lavorazione settano `data_update`/`user_update` **espliciti** — `claimed_at` è
> il timestamp autoritativo per il reaper.

**Indici / vincoli chiave**:

* **Corsia del claim** — `ix_coda_lavori_da_lavorare` su `(priorita, id)`
  `WHERE stato = 'PENDING'`: alimenta il `SELECT … WHERE stato='PENDING' AND
  (run_after IS NULL OR run_after <= now()) ORDER BY priorita, id FOR UPDATE SKIP LOCKED`.
* **Idempotenza job vivi** — `uq_coda_lavori_vivo_idem` UNIQUE `(job_type,
  idempotency_key)` `WHERE idempotency_key IS NOT NULL AND stato IN ('PENDING','IN_CORSO')`:
  impedisce doppioni vivi con la stessa chiave (equivalente generico dell'unique
  parziale della stampa coda).
* CHECK su `stato`, `run_as`, `tentativi ≥ 0`.

### 3.2 `dbops.coda_lavori_tipi` — registry dei tipi di job

Piccola tabella di configurazione (mirror leggero di `pipeline_task_registry_impl`),
per validare `job_type` e portare i default per-tipo:

| Colonna | Tipo | Note |
| --- | --- | --- |
| `id` | bigint IDENTITY | PK |
| `codice` | text NOT NULL UNIQUE | = `job_type` |
| `handler_code` | text NOT NULL | chiave dispatch → `handler_registry` Python |
| `descrizione` | text | |
| `run_as_default` | text NOT NULL | default `run_as` del tipo |
| `max_tentativi_default` | int NOT NULL DEFAULT 5 | |
| `attivo` | boolean NOT NULL DEFAULT true | |
| `meta` | jsonb NOT NULL DEFAULT '{}' | |
| audit | | standard |

> **Perché una tabella e non solo il dict Python**: coerenza con la filosofia
> DB-first del progetto (il pipeline registry vive in DB) + config per-tipo
> (`max_tentativi`, `run_as`) tarabile senza deploy. Il **binding** `handler_code →
> callable` resta in Python (controllato, no dynamic import).

### 3.3 Funzione di enqueue (DB, per l'atomicità e i trigger)

`dbops.fn_accoda_lavoro(p_job_type text, p_payload jsonb, p_run_as text,
p_scope jsonb, p_idempotency_key text, p_priorita smallint, p_run_after timestamptz,
p_max_tentativi int) RETURNS bigint` — INSERT idempotente (`ON CONFLICT` sull'unique
parziale vivo → ritorna l'id esistente). Callable sia da Python sia **da trigger/altro
codice DB** (es. un trigger che accoda un job al cambio stato — DB-first).

## 4. Dispatch e worker (Python — dopo prerequisiti DB)

```
apps/core/services/coda_lavori/
  ├── drain_engine.py        QueueDrainEngine — il LOOP generico riusabile:
  │                          reaper → claim(batch misto per priorità) → per item:
  │                          best-effort → tally → decisione retry/backoff.
  │                          Parametrizzato da un backend (protocol QueueBackend).
  ├── repository.py          CodaLavoriRepository implements QueueBackend:
  │                          enqueue, claim (SKIP LOCKED), marca_fatto/errore,
  │                          reaper, requeue, count_per_stato. SQL tipizzato QUI.
  ├── handler_registry.py    dict handler_code → callable + register_handler(...)
  ├── drainer_service.py     draina_coda_lavori(...) = QueueDrainEngine(CodaLavori
  │                          Backend, per_item=dispatch_handler). run_as SISTEMA/
  │                          OPERATORE (applica scope).
  └── (handler dei domini registrati al ready() delle app, come i context builder)

apps/vendite/management/commands/draina_coda_lavori.py   (chiamante sottile)
```

* **Contratto handler**: `handler(payload: dict, *, scope: dict|None, ctx) -> dict`
  (ritorna il `result`); solleva `ServiceError` su fallimento di dominio.
* **run_as**: `SISTEMA` → il worker apre `system_process_context` (BYPASSRLS);
  `OPERATORE` → applica lo `scope` catturato (emittente_ids/auth_user_id) senza
  BYPASSRLS. Un solo worker, due modalità. **Nessuna interruzione a metà**: revoca
  permessi mentre il job gira → il job completa con lo scope catturato (§brief DB 3a).
* **Registrazione handler**: esplicita al boot (come `register_builder` dei context
  builder / `handler_registry` del pipeline executor) — **no auto-discovery, no
  dynamic import**.

### 4a. Un solo motore di drenaggio, tabelle tipizzate distinte (decisione 2026-07-20)

Analisi del riuso reale (`draina_coda_stampa` + repo `pipeline_repository`): **ciò che si
duplica NON è la tabella, è il *loop*** — reaper→claim→per-item best-effort→tally→retry
(~30 righe, identiche per qualsiasi coda). L'SQL di claim/reaper/marca (~120 righe) è
invece **per-tabella** (colonne diverse: `sorgente_id` vs `payload`). Generalizzare via
*una tabella sola* o via *SQL dinamico su N tabelle* è l'astrazione sbagliata (si perde la
FK tipizzata, o si scrive SQL dinamico eterogeneo).

**Astrazione giusta = al layer Python, non SQL**: `QueueDrainEngine` possiede il loop +
la policy retry/backoff/priorità **una volta**; ogni coda fornisce un `QueueBackend`
(protocol: `reap_stale`, `claim`, `mark_done`, `mark_error`, `requeue`) col **proprio**
SQL tipizzato; il *per-item* è una callback (render per la stampa, dispatch-handler per la
generica). Coerente con la filosofia dispatch del progetto (`handler_code`→callable),
niente SQL dinamico, **zero perdita di FK**.

Rollout senza rifare lavoro:

1. **Ora**: `coda_lavori` + `QueueDrainEngine` + `CodaLavoriBackend`.
2. **Convergenza (Q-4), refactor non riscrittura**: `draina_coda_stampa` si aggancia allo
   **stesso** `QueueDrainEngine` implementando `QueueBackend` sui metodi repo **già
   esistenti** (`claim_stampe_pending`/`reset_stale`/`marca_*`) — la tabella
   `fatture_stampa_coda` resta com'è, si deduplica solo il loop.
3. **Email async**: `config.email_outbox` **non** è una work-queue autonoma (è un draft
   box operatore con invio **sincrono** in `confirm_and_send`). L'invio asincrono con
   retry/backoff diventa un `job_type=INVIA_EMAIL` in `coda_lavori`; `email_outbox` resta
   lo store dei draft. Bonus: chiude il TODO «riconciliazione READY fantasma» già
   annotato in `email_outbox_service.py` (saga: recupero idempotente, non re-send).

## 5. `fatture_stampa_coda`: resta specializzata (decisione)

`vendite.fatture_stampa_coda` è **già costruita, committata e mergiata**.

**Cosa è replicabile e cosa no** (verifica onesta, non «non si può»):

* L'**unique tipizzato** `(sorgente_tipo_id, sorgente_id) WHERE vivo` **È replicabile**
  nella generica via `idempotency_key = 'FATTURA:'||id` sull'unique parziale vivo: la
  *garanzia di dedup* si conserva; si perde solo la *tipizzazione* (bigint vs text).
* L'**irriproducibile** è la **FK `sorgente_id → vendite.fatture` con ON DELETE CASCADE**:
  in una coda polimorfa il riferimento vive in `payload jsonb`, quindi niente integrità
  referenziale né auto-pulizia dei work-item vivi alla cancellazione della fattura.
  (Nota: il drainer stampa già tollera il caso «fattura sparita» → l'orfano diventa
  `ERRORE`, quindi la CASCADE è comodità, non load-bearing.)
* La **delega RLS via colonna `sorgente_id`** (`fn_scope_ef_whitelist_via_fattura`) oggi
  **non è esercitata** (G1: nessuna superficie di lettura operatore; il render gira in
  contesto **sistema**). Quindi non è un vero costo di convergenza *oggi*.

**Decisione (2026-07-20): `fatture_stampa_coda` NON si assorbe in `coda_lavori`** — e
non perché infattibile (lo è: la FK non è load-bearing, l'orfano→ERRORE è già gestito),
ma perché il **target sarebbe sbagliato**. Il destino della stampa è un **outbox di
documenti tipizzato** (`documenti.*`, sorgente polimorfa `config.sorgenti` + `key_selector`,
FK reale) che servirà **tutti** i tipi di documento (fattura oggi; DDT/preventivi/ordini
domani) — non un job generico con riferimento sciolto nel `payload`. Tre segnali: (1) le
sue colonne sono già «a forma di `documenti.genera_documento`»; (2) `DocumentGenerationService`
è già source-generic; (3) B-4 del cockpit aveva già nominato `documenti.*`.

**Conseguenza (risolve il timore «lavoro throwaway», Tid 2026-07-20)**: la
`fatture_stampa_coda` di oggi **non è usa-e-getta** — è già l'80% di `documenti.coda_stampa`;
la promozione è **additiva** (più tipi sorgente), non una riscrittura, e i suoi test
(claim/reaper/retry/resilienza) restano validi. Assorbirla in `coda_lavori` ora sarebbe
churn verso un target che poi si invertirebbe. L'unico anti-duplicazione necessario è il
**motore condiviso** `QueueDrainEngine` (§4a), costruito una volta e riusato da entrambe.

> Due assi di generalizzazione distinti, entrambi legittimi: **outbox documenti
> tipizzato** (`documenti.*`, con FK sorgente) e **coda job generica** (`dbops.coda_lavori`,
> polimorfa). Possono **comporsi**: un `job_type=STAMPA_DOCUMENTO` nella generica che
> *orchestra* l'outbox tipizzato — non uno che assorbe l'altro. ([[feedback_regola_del_2_estrai_bb]],
> caveat: si generalizza alla 2ª occorrenza *con* i requisiti in mano.)
>
> **Nota (2026-07-20)**: la 2ª occorrenza di outbox specializzato **esiste già** ed è
> `config.email_outbox` (drenato da `send_pending_emails`, cron) — stesso pattern
> stato/tentativi/retry. PEC/SDI (citati come futuri consumatori della generica) sono
> quindi già un outbox specializzato costruito. La domanda «una famiglia o tre code?»
> va posta ora con **due** specializzate in mano (stampa + email), non ipotizzate.

## 6. Primo consumatore: C-3 giro fatturazione

* **Endpoint** `POST /vendite/fatturazione/run/` → `fn_accoda_lavoro('FATTURAZIONE_GIRO',
  payload={competenza, fino_a_stato}, run_as='OPERATORE', scope={emittente_ids,
  auth_user_id}, idempotency_key=<competenza+scope>)` **nella transazione** → risponde
  con l'handle (`coda_lavori.id` + `job_run` quando parte).
  > ⚠️ **Due layer di idempotenza, chiavi distinte** (vedi brief DB Q-E). La
  > `idempotency_key` della coda = chiave di **business** (`competenza+scope`), per
  > deduplicare i giri **vivi**. L'header HTTP `Idempotency-Key` resta gestito dal layer
  > esistente `dbops.idempotency_keys` (`handle_post_json` + `idempotency_store.py`), che
  > replica la risposta memorizzata. **NON** includere l'header nella chiave della coda:
  > lo renderebbe per-richiesta e vanificherebbe la dedup di business (due click con
  > header diversi accoderebbero due giri).
* **Handler** `FATTURAZIONE_GIRO` → chiama il core C-1
  `esegui_giro_fatturazione(...)` con lo scope catturato. **I-1 rispettato** (stesso
  core del cron; il cron continua a chiamarlo diretto).
* **UI** fa polling sullo stato del job → I-3 (non bloccante) soddisfatto **senza
  broker**.

## 7. Cron e schedulazione — invariati

La coda **non** tocca lo scheduling temporale: `run_fatturazione_batch` (giro
notturno/orario), `draina_coda_stampa`, i job SQL restano su **pgAgent + systemd**.
Il worker `draina_coda_lavori` è a sua volta un job schedulato (systemd timer ~1 min)
o, per presa in carico istantanea, un servizio always-on con `LISTEN/NOTIFY`
(opzionale, futuro — sempre senza broker). **Precedente già in codebase**: il long-runner
`anagrafiche/listen_cambio_reparto.py` è già un listener `LISTEN/NOTIFY` bloccante — il
pattern «servizio always-on con NOTIFY» non è ipotetico (utile per Q-3).

## 8. Sequenza di rilascio

1. ✅ **DB** (team, `dev/db-tid`): `coda_lavori` + `coda_lavori_tipi` + `fn_accoda_lavoro`
   + seed `FATTURAZIONE_GIRO` + pgTAP `plan(57)`. Applicato (`20260720-07..10`).
2. ✅ **BE core FATTO (2026-07-21, working tree)**: `apps/core/services/coda_lavori/`
   — `backend.py` (protocol `QueueBackend` + `QueueItem`), `drain_engine.py`
   (`QueueDrainEngine`: reaper→claim→per-item best-effort→retry con **backoff
   esponenziale cappato**; **deviazione da brief DB §3a, ok Tid 2026-07-21**: il
   reaper consuma un tentativo per riga recuperata — oltre soglia → ERRORE
   terminale, anti poison-job che uccide il worker; stesso fix sul reaper della
   coda stampa), `repository.py` (`CodaLavoriRepository` implements
   QueueBackend: enqueue via `fn_accoda_lavoro` + claim SKIP LOCKED + marca/reaper/
   annulla/requeue/count/get_stato), `handler_registry.py` (dispatch controllato),
   `context.py` (`operator_identity_context`: identità COMPLETA operatore — i 5
   GUC del web via `set_jwt_gucs`, RLS che risolve come nel ciclo web; fail-loud
   se l'identità non è più attiva; fix 2026-07-21: il solo `app.jwt_user` non
   bastava, le policy RLS leggono `app.ruolo_applicativo`+`app.current_user_id`),
   `drainer_service.py` (dispatch `run_as` SISTEMA/OPERATORE). Command
   **`apps/core/management/commands/draina_coda_lavori.py`** (chiamante sottile).
   11 test core verdi. **Deviazioni motivate dalla proposta**: (a) command in
   `apps/core` NON `apps/vendite` (la coda è infrastruttura core, worker generico);
   (b) **nessun `lock_key`** anti-overlap (SKIP LOCKED rende i worker concorrenti
   sicuri, e un lock di sessione verrebbe rilasciato dal `system_process_context`
   per-item dei job SISTEMA); (c) alias di sistema per i job SISTEMA = `system_fatturazione`
   (unico BYPASSRLS oggi; alias dominio-neutro = cleanup futuro, nessun job SISTEMA
   seedato ora).
3. ✅ **BE consumatore C-3 FATTO (2026-07-21, working tree)**: handler
   `apps/vendite/services/fatturazione_giro_handler.py` (registrato in
   `VenditeConfig.ready()`, chiama il core C-1 sotto RLS operatore, corsia
   differita→EMESSA, codici errore registrati); endpoint `ApiFatturazioneRun`
   (`POST /vendite/fatturazione/run/`, enqueue OPERATORE + scope catturato +
   chiave business per-mese; header HTTP + `dbops.idempotency_keys` = 2° layer);
   polling `ApiFatturazioneRunStato` (`GET run/<job_id>/`, ownership operatore).
   Codici HTTP `E_LOTTO_NON_NUMERABILE`(409)/`E_JOB_NON_TROVATO`(404) registrati
   in `error_policies`. 10 test. C-4/C-5 già FATTI e indipendenti.
4. ⬜ **Deploy**: systemd timer per `draina_coda_lavori` (+ validazione in-app,
   DB dev senza dati di processo).

## 9. Punti aperti da decidere

| # | Punto | Nota |
| --- | --- | --- |
| Q-1 | Schema della coda: `dbops` (registry-adjacent, proposto) vs `maintenance` (job_run_log-adjacent) | scelta del team DB |
| Q-2 | `coda_lavori_tipi` come tabella (proposto) vs solo dict Python | DB-first → tabella; confermare |
| Q-3 | Presa in carico: systemd timer ~1 min (semplice) vs LISTEN/NOTIFY istantaneo | timer per v1, NOTIFY futuro (precedente: `listen_cambio_reparto`) |
| Q-4 | Convergenza outbox specializzati → generica | **DECISO (2026-07-20)**: la stampa **non** si assorbe in `coda_lavori` — target = `documenti.*` tipizzato (additivo, non riscrittura); `email_outbox` resta draft-store, l'invio async diventa `job_type=INVIA_EMAIL`. L'unificazione è al livello **motore** (`QueueDrainEngine`, §4a), non tabella. Vedi §5. |
| Q-5 | Priorità e fairness fra job_type diversi (un giro lungo non affama le PEC) | worker: claim per priorità; eventuale cap per-tipo |
| Q-6 | Idempotenza a due layer — coda (business) vs `dbops.idempotency_keys` (HTTP) | separate; chiave coda = business (§6). Confermato. |
| Q-7 | Trigger audit+tx_id (come `idempotency_keys`) vs no-trigger (come `fatture_stampa_coda`) | **entrambi i trigger** (multi-writer); vedi brief DB Q-A. |
| Q-8 | Backoff sui retry via `run_after = now()+f(tentativi)` | sì, per non affamare con poison-job; vedi brief DB §6. |

---

*Brief di design vivo: alla conferma dell'ambito, si generano (a) il brief DB dedicato
per il team, (b) il piano operativo BE. A costruzione avvenuta il documento passa in
`work-done/` con il consuntivo.*
