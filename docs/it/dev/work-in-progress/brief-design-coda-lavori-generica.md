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
* **Tracciamento run** — `maintenance.job_run_log` + `registered_job` (lock
  anti-overlap) per il worker.
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
| `origine` | text NOT NULL DEFAULT 'API' | `API` \| `CRON` \| `COMMAND` (allineato a `job_run` ORIGINE_*) |
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
| `date_insert/user_insert/date_update/user_update` | audit | standard |
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
  ├── repository.py          CodaLavoriRepository: enqueue, claim (SKIP LOCKED),
  │                          marca_fatto/errore, reaper, count_per_stato
  ├── handler_registry.py    dict handler_code → callable + register_handler(...)
  ├── drainer_service.py     draina_coda_lavori(...) — generalizza draina_coda_stampa:
  │                          reaper → claim → per job: risolve handler → esegue →
  │                          marca esito. run_as SISTEMA/OPERATORE (applica scope).
  └── (handler dei domini registrati al ready() delle app, come i context builder)

apps/vendite/management/commands/draina_coda_lavori.py   (chiamante sottile)
```

* **Contratto handler**: `handler(payload: dict, *, scope: dict|None, ctx) -> dict`
  (ritorna il `result`); solleva `ServiceError` su fallimento di dominio.
* **run_as**: `SISTEMA` → il worker apre `system_process_context` (BYPASSRLS);
  `OPERATORE` → applica lo `scope` catturato (emittente_ids/auth_user_id) senza
  BYPASSRLS. Un solo worker, due modalità.
* **Registrazione handler**: esplicita al boot (come `register_builder` dei context
  builder / `handler_registry` del pipeline executor) — **no auto-discovery, no
  dynamic import**.

## 5. `fatture_stampa_coda`: resta specializzata (decisione)

`vendite.fatture_stampa_coda` è **già costruita, committata e mergiata** con
integrità **tipizzata forte** che una coda generica polimorfa non può replicare:
FK `sorgente_id → vendite.fatture` e l'unique parziale `(sorgente_tipo_id, sorgente_id)`.

**Decisione**: la stampa coda **resta specializzata** (non la si migra nella generica
ora — si butterebbe lavoro DB committato e si perderebbe la FK). La generica serve i
job nuovi. Convergenza eventuale = ondata futura, sui suoi meriti (non urgente).

> Due code con **ragione esplicita**: una generica (polimorfa, molti tipi), una
> specializzata (stampa, FK+idempotenza tipizzata). Non duplicazione: specializzazione
> motivata ([[feedback_regola_del_2_estrai_bb]], caveat astrazione: si generalizza alla
> 2ª occorrenza *con* i requisiti in mano, non prima).

## 6. Primo consumatore: C-3 giro fatturazione

* **Endpoint** `POST /vendite/fatturazione/run/` → `fn_accoda_lavoro('FATTURAZIONE_GIRO',
  payload={competenza, fino_a_stato}, run_as='OPERATORE', scope={emittente_ids,
  auth_user_id}, idempotency_key=<competenza+scope+Idempotency-Key>)` **nella
  transazione** → risponde con l'handle (`coda_lavori.id` + `job_run` quando parte).
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
(opzionale, futuro — sempre senza broker).

## 8. Sequenza di rilascio

1. **DB** (team, `dev/db-tid`): `coda_lavori` + `coda_lavori_tipi` + `fn_accoda_lavoro`
   + seed tipo `FATTURAZIONE_GIRO` + pgTAP. → **brief DB dedicato** (prerequisito).
2. **BE core** (io): `apps/core/services/coda_lavori/*` (repository + registry +
   drainer generalizzato) + command `draina_coda_lavori` + test.
3. **BE consumatore C-3** (io): endpoint `run/` (enqueue) + handler `FATTURAZIONE_GIRO`
   + polling stato job. C-4/C-5 sono **indipendenti** e procedono in parallelo.
4. **Deploy**: systemd timer per `draina_coda_lavori`.

## 9. Punti aperti da decidere

| # | Punto | Nota |
| --- | --- | --- |
| Q-1 | Schema della coda: `dbops` (registry-adjacent, proposto) vs `maintenance` (job_run_log-adjacent) | scelta del team DB |
| Q-2 | `coda_lavori_tipi` come tabella (proposto) vs solo dict Python | DB-first → tabella; confermare |
| Q-3 | Presa in carico: systemd timer ~1 min (semplice) vs LISTEN/NOTIFY istantaneo | timer per v1, NOTIFY futuro |
| Q-4 | Convergenza futura `fatture_stampa_coda` → generica | fuori ambito, quando/se |
| Q-5 | Priorità e fairness fra job_type diversi (un giro lungo non affama le PEC) | worker: claim per priorità; eventuale cap per-tipo |

---

*Brief di design vivo: alla conferma dell'ambito, si generano (a) il brief DB dedicato
per il team, (b) il piano operativo BE. A costruzione avvenuta il documento passa in
`work-done/` con il consuntivo.*
