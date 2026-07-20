# Brief DB — Coda lavori generica (`dbops.coda_lavori`)

> **Tipo**: brief operativo per il **team DB** · **Target**: `dev/db-tid` · **Data**: 2026-07-20
> · **Owner**: Tid · **Stato**: 🟡 **DA COSTRUIRE** — prerequisito del giro fatturazione
> on-demand (C-3) e fondazione async dell'ERP.
>
> **Design-of-record**:
> [brief-design-coda-lavori-generica.md](brief-design-coda-lavori-generica.md) — leggere
> §3 (modello) e §4 (dispatch) prima di implementare.
> **Consumatore 1**:
> [brief-be-fe-processi-fatturazione.md](brief-be-fe-processi-fatturazione.md) C-3.
> **Continuità**: è la *«promozione al 2° consumatore»* già prevista da **B-4** del
> [brief-db-processi-fatturazione-cockpit.md](brief-db-processi-fatturazione-cockpit.md)
> (la stampa coda era "scoped a fatturazione ora, generalizzabile al 2° consumatore").
> **Contesto**: non in produzione ([[project_no_produzione_solo_sviluppo]]) → breaking
> ammessi. **Gate**: il BE parte a oggetti applicati ([[feedback_be_fe_attende_prerequisiti_db]]).
> **Regole DDL/trigger**: `linee-guida-sql.md`, `linee-guida-trigger.md`. DDL nuovo in
> `migrations_v2/` (un changeSet per file, `logicalFilePath`).

---

## 0. Cosa costruire (in una riga)

Due tabelle in **`dbops`** — la coda `coda_lavori` + il registry tipi `coda_lavori_tipi`
— e la funzione di **enqueue atomico** `fn_accoda_lavoro(...)`, più il seed del primo
tipo (`FATTURAZIONE_GIRO`) e i pgTAP. **Nessuna** modifica a `fatture_stampa_coda`
(resta specializzata, vedi design §5).

## 1. `dbops.coda_lavori` — la coda

| Colonna | Tipo | Null | Default | Note |
| --- | --- | --- | --- | --- |
| `id` | bigint | NO | IDENTITY | PK |
| `uid` | uuid | NO | `uuidv7()` | UNIQUE |
| `job_type` | text | NO | | = `coda_lavori_tipi.codice` |
| `payload` | jsonb | NO | `'{}'` | argomenti del job |
| `run_as` | text | NO | | CHECK IN (`SISTEMA`,`OPERATORE`) |
| `scope` | jsonb | YES | | scope autorizzativo catturato all'enqueue (job OPERATORE) |
| `origine` | text | NO | `'API'` | CHECK IN (`API`,`CRON`,`COMMAND`) |
| `priorita` | smallint | NO | `100` | minore = più urgente |
| `stato` | text | NO | `'PENDING'` | CHECK IN (`PENDING`,`IN_CORSO`,`FATTO`,`ERRORE`,`ANNULLATO`) |
| `tentativi` | int | NO | `0` | CHECK ≥ 0 |
| `max_tentativi` | int | NO | `5` | CHECK ≥ 1 |
| `ultimo_errore` | jsonb | YES | | `{code,message,detail}` |
| `run_after` | timestamptz | YES | | eleggibile se NULL o ≤ now() (job differiti) |
| `claimed_at` | timestamptz | YES | | istante del claim (reaper) |
| `started_at` | timestamptz | YES | | |
| `ended_at` | timestamptz | YES | | |
| `job_run_id` | bigint | YES | | link a `maintenance.job_run_log` (no FK cross-schema se sconveniente) |
| `idempotency_key` | text | YES | | dedup job vivi |
| `result` | jsonb | YES | | esito/summary |
| `date_insert/user_insert/date_update/user_update` | | | | audit standard |
| `tx_id` | uuid | YES | | policy tx-id |

**Indici / vincoli**:

* `pk_coda_lavori` PK su `id`; `uq_coda_lavori_uid` su `uid`.
* **Corsia claim** — `ix_coda_lavori_da_lavorare` su `(priorita, id)`
  `WHERE stato = 'PENDING'`. (Alimenta `… WHERE stato='PENDING' AND (run_after IS
  NULL OR run_after <= now()) ORDER BY priorita, id FOR UPDATE SKIP LOCKED`.)
* **Idempotenza job vivi** — `uq_coda_lavori_vivo_idem` UNIQUE `(job_type,
  idempotency_key)` `WHERE idempotency_key IS NOT NULL AND stato IN ('PENDING','IN_CORSO')`.
* Indice di monitoraggio su `(stato)` se utile ai conteggi.
* **FK** `job_type → coda_lavori_tipi.codice` (o guard trigger se si preferisce non
  vincolare in hard FK per flessibilità operativa — scelta del team).

> ⚠️ **Niente trigger audit** su questa tabella (come `fatture_stampa_coda`): i metodi
> di lavorazione BE settano `data_update`/`user_update` espliciti. `claimed_at` è il
> timestamp autoritativo del reaper. Se il team preferisce il trigger audit standard,
> il BE si adegua — **da confermare** (vedi §5 Q-A).

## 2. `dbops.coda_lavori_tipi` — registry dei tipi di job

| Colonna | Tipo | Null | Default | Note |
| --- | --- | --- | --- | --- |
| `id` | bigint | NO | IDENTITY | PK |
| `codice` | text | NO | | UNIQUE (= `job_type`) |
| `handler_code` | text | NO | | chiave dispatch → `handler_registry` Python |
| `descrizione` | text | YES | | |
| `run_as_default` | text | NO | | CHECK IN (`SISTEMA`,`OPERATORE`) |
| `max_tentativi_default` | int | NO | `5` | |
| `attivo` | boolean | NO | `true` | |
| `meta` | jsonb | NO | `'{}'` | |
| audit | | | | standard |

Mirror leggero di `pipeline_task_registry_impl`: il DB valida il tipo e porta i default;
il binding `handler_code → callable` resta in Python (controllato, no dynamic import).

## 3. `dbops.fn_accoda_lavoro(...)` — enqueue atomico

```
dbops.fn_accoda_lavoro(
    p_job_type        text,
    p_payload         jsonb    DEFAULT '{}',
    p_run_as          text     DEFAULT NULL,   -- NULL → run_as_default del tipo
    p_scope           jsonb    DEFAULT NULL,
    p_idempotency_key text     DEFAULT NULL,
    p_priorita        smallint DEFAULT 100,
    p_run_after       timestamptz DEFAULT NULL,
    p_max_tentativi   int      DEFAULT NULL     -- NULL → max_tentativi_default del tipo
) RETURNS bigint   -- id della riga (nuova o esistente se idempotente)
```

* Guard: `p_job_type` deve esistere e `attivo` in `coda_lavori_tipi` (errore parlante
  via `script.fn_log_and_raise_error`).
* `run_as`/`max_tentativi` risolti dai default del tipo se NULL.
* **Idempotente**: `INSERT … ON CONFLICT (job_type, idempotency_key) WHERE …vivo… DO
  NOTHING`; se conflitto → `SELECT` dell'id vivo esistente e ritorno (nessun doppione).
* Callable **anche da trigger/altro codice DB** (enqueue transazionale da dominio).

> **Claim/marca/reaper**: NON servono funzioni DB — li fa il BE in SQL diretto
> (SKIP LOCKED + UPDATE), come già per `fatture_stampa_coda` (coerenza col worker
> `draina_coda_stampa`). Il DB fornisce solo l'**enqueue** (che deve essere atomico e
> callable da trigger).

## 4. Seed — primo tipo di job

`coda_lavori_tipi`:

| codice | handler_code | run_as_default | descrizione |
| --- | --- | --- | --- |
| `FATTURAZIONE_GIRO` | `fatturazione_giro_default` | `OPERATORE` | Giro fatturazione on-demand (C-3): discovery terne + lotto + pipeline fino a `fino_a_stato`. |

(Altri tipi — PEC, report, export — si aggiungono al bisogno: seed + handler BE, zero
DDL.)

## 5. Punti da confermare col team DB

| # | Punto | Proposta |
| --- | --- | --- |
| Q-A | Trigger audit su `coda_lavori`? | **No** (come `fatture_stampa_coda`); BE setta audit esplicito. Confermare. |
| Q-B | Schema: `dbops` (proposto, registry-adjacent) vs `maintenance` | `dbops` |
| Q-C | FK `job_type` hard vs guard trigger | team DB decide |
| Q-D | `tx_id` gestito da trigger `dbops.trgfn_tx_id_managed` come le altre tabelle | sì |

## 6. Verifica attesa (pgTAP)

* `coda_lavori` / `coda_lavori_tipi` esistono con colonne/CHECK/indici attesi.
* `fn_accoda_lavoro`: enqueue base; **idempotenza** (2ª chiamata stessa
  `idempotency_key` viva → stesso id, nessun doppione); guard su `job_type` inesistente/
  inattivo; risoluzione default `run_as`/`max_tentativi` dal tipo.
* Unique parziale vivo: due PENDING con stessa `(job_type, idempotency_key)` → violazione.
* Seed `FATTURAZIONE_GIRO` presente e attivo.

## 7. Sequenza

1. Team DB: DDL + `fn_accoda_lavoro` + seed + pgTAP → push `dev/db-tid`.
2. BE (io): core `apps/core/services/coda_lavori/*` + worker `draina_coda_lavori` + C-3
   consumatore. **A worker deployato** si può eventualmente far accodare da trigger DB
   (non C-3, che accoda da Python).

---

*Alla costruzione, il BE si aggancia a questi nomi/firme. Aggiornare la colonna Stato in
testata (🟡 → 🟢) ad apply avvenuto, con il commit.*
