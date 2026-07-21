# Brief DB — Coda lavori generica (`dbops.coda_lavori`)

> **Tipo**: brief operativo per il **team DB** · **Target**: `dev/db-tid` · **Data**: 2026-07-20
> · **Owner**: Tid · **Stato**: 🟢 **APPLICATO + TESTATO + COMMITTATO** (2026-07-20/21) —
> changeSet `20260720-07..10` migrati, pgTAP `test-coda-lavori.sql` verde `plan(57)`, doc
> manual + guida divulgativa fatte, autogen rigenerato. Prerequisito del giro fatturazione
> on-demand (C-3) e fondazione async dell'ERP. **BE realizzato e committato** (`2895f9653`:
> core `apps/core/services/coda_lavori/` + consumatore C-3), vedi design §8. **✅ CHIUSO**,
> spostato in `work-done/` il 2026-07-21.
>
> **Design-of-record**:
> [brief-design-coda-lavori-generica.md](brief-design-coda-lavori-generica.md) — leggere
> §3 (modello) e §4 (dispatch) prima di implementare.
> **Consumatore 1**:
> [brief-be-fe-processi-fatturazione.md](../work-in-progress/brief-be-fe-processi-fatturazione.md) C-3.
> **Relazione con B-4**: **NON** è la promozione prevista da **B-4** del
> [brief-db-processi-fatturazione-cockpit.md](../work-in-progress/brief-db-processi-fatturazione-cockpit.md).
> B-4 generalizza `fatture_stampa_coda` lungo l'asse **documentale** (→ `documenti.*`,
> outbox di *documenti* con FK sorgente tipizzata); questa è una coda di **job**
> generici (asse diverso). Le due generalizzazioni sono distinte e possono coesistere
> (vedi §5 Q-F). Questa coda si motiva sui propri meriti (async DB-native), non come
> continuazione di B-4.
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
| `origine` | text | NO | `'API'` | CHECK IN (`API`,`CRON`,`COMMAND`,`TRIGGER`) — chi ha **accodato**. Set proprio della coda: NON identico a `maintenance.job_run_log.origine` (`PGAGENT`/`CRON`/`COMMAND`), che descrive chi *esegue* il run. `API` = enqueue da endpoint; `TRIGGER` = enqueue DB-native da trigger/dominio (il caso distintivo di §3) |
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
| `data_insert/user_insert/data_update/user_update` | | | | audit standard (`data_*`, convenzione it-IT del progetto) |
| `tx_id` | uuid | YES | | policy tx-id |

**Indici / vincoli**:

* `pk_coda_lavori` PK su `id`; `uq_coda_lavori_uid` su `uid`.
* **Corsia claim** — `ix_coda_lavori_da_lavorare` su `(priorita, id)`
  `WHERE stato IN ('PENDING','IN_CORSO')`. (Alimenta `… WHERE stato='PENDING' AND
  (run_after IS NULL OR run_after <= now()) ORDER BY priorita, id FOR UPDATE SKIP
  LOCKED`.) **Nota**: il predicato include `IN_CORSO` — come
  `ix_fatture_stampa_coda_da_lavorare` — così lo **stesso** indice serve il reaper
  (`WHERE stato='IN_CORSO' AND claimed_at < now()-soglia`); restringerlo a solo
  `PENDING` lascerebbe la scansione del reaper senza indice.
* **Idempotenza job vivi** — `uq_coda_lavori_vivo_idem` UNIQUE `(job_type,
  idempotency_key)` `WHERE idempotency_key IS NOT NULL AND stato IN ('PENDING','IN_CORSO')`.
  ⚠️ Vedi §5 Q-E: questa è dedup **di business** (job vivo) — distinta e complementare
  al layer HTTP `dbops.idempotency_keys`; la chiave qui è la chiave di business, NON
  l'header `Idempotency-Key`.
* Indice di monitoraggio su `(stato)` se utile ai conteggi.
* **CHECK coerenza `run_as`↔`scope`** — `chk_coda_lavori_run_as_scope`:
  `(run_as='OPERATORE' AND scope IS NOT NULL) OR (run_as='SISTEMA' AND scope IS NULL)`.
  Evita job OPERATORE senza scope (girerebbero senza filtro RLS) e job SISTEMA con
  scope spurio. (Decisione Q-5-sec, 2026-07-20.)
* **FK** `job_type → coda_lavori_tipi.codice` (hard FK; `codice` è UNIQUE). L'indice
  FK NON si crea a mano: `dbops.apply_fk_index_policy()` (90_end). Su tabella nuova la
  policy registra `consentito=false` di default e NON crea l'indice → se lo si vuole,
  serve un seed esplicito `consentito=true` ([[reference_fk_index_policy_optin]]).
  Data la bassa cardinalità di `coda_lavori_tipi`, l'indice è di norma superfluo.

> ⚠️ **Trigger audit — DA DECIDERE, con l'analogo giusto in mano** (§5 Q-A).
> `fatture_stampa_coda` è **senza** trigger audit, ma è **single-writer** (solo il
> drainer repo la scrive) e RLS-off per il loop di render: caso particolare. L'analogo
> davvero pertinente è `dbops.idempotency_keys` (stessa schema `dbops`, natura
> tecnica-transazionale, **molti writer**), che monta **entrambi** i trigger
> `script.trgfn_audit_data_user_generic` (audit) + `dbops.trgfn_tx_id_managed` (tx_id).
> La coda generica è multi-writer (ogni dominio accoda; worker; cancel; retry). Senza
> trigger audit, `data_update` **non** si aggiorna sugli UPDATE (i default `now()`
> valgono solo all'INSERT) → ogni path BE deve ricordarsi di settarlo a mano: footgun.
> **Proposta: usare entrambi i trigger come `idempotency_keys`.** `claimed_at` resta il
> timestamp autoritativo del reaper a prescindere.

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

```text
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
  Copre **solo** i job vivi (`PENDING`/`IN_CORSO`): a job `FATTO`/`ERRORE` la stessa
  chiave riparte (ri-accodamento intenzionale). Il replay «stessa richiesta → stessa
  risposta» a job completato è responsabilità del layer HTTP `dbops.idempotency_keys`
  (vedi §5 Q-E), NON di questa unique.
* Callable **anche da trigger/altro codice DB** (enqueue transazionale da dominio →
  `origine='TRIGGER'`).

> **Claim/marca/reaper**: NON servono funzioni DB — li fa il BE in SQL diretto
> (SKIP LOCKED + UPDATE), come già per `fatture_stampa_coda` (coerenza col worker
> `draina_coda_stampa`). Il DB fornisce solo l'**enqueue** (che deve essere atomico e
> callable da trigger).

### 3a. Transizioni di stato (BE, SQL diretto) — decisioni 2026-07-20

* **Claim a batch misto per priorità** — il worker NON drena un `job_type` alla volta:
  claim di ≤`limit` righe eleggibili `ORDER BY priorita, id` (mix di tipi), così un
  giro lungo non affama le PEC (Q-5). Fairness fine (cap per-tipo) = follow-up.
* **Nessuna interruzione di job in corso** — se i permessi dell'operatore vengono
  revocati **mentre** un job OPERATORE gira, il job **termina normalmente** con lo
  scope catturato: non si strozza (kill) nulla a metà. La revoca vale per i job
  **futuri**, non per quelli `IN_CORSO`. (Decisione 2026-07-20.)
* **Cancel solo su `PENDING`** → `ANNULLATO`: `UPDATE … SET stato='ANNULLATO' WHERE
  id=? AND stato='PENDING'` (fallisce silente = 0 righe se già claimato: no race col
  worker). Un job già `IN_CORSO` non è annullabile pulito.
* **Reaper automatico** (worker morto): `IN_CORSO` con `claimed_at < now()-soglia` →
  `PENDING` (soglia ≫ durata job). Serve l'indice che include `IN_CORSO` (vedi §1).
* **Sblocco manuale (requeue)** — azione amministrativa oltre al reaper: rimette a
  `PENDING` un job bloccato `IN_CORSO` (a prescindere dalla soglia) o un `ERRORE`
  terminale da ri-tentare. **Decisione 2026-07-20**: `tentativi` **si mantiene**
  (storia dei fallimenti preservata) e si **alza `max_tentativi += N`** per consentire
  i nuovi tentativi — così il job riparte senza cancellare la traccia. `payload`/`scope`
  preservati. Da esporre come endpoint admin.

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
| Q-A | Trigger audit su `coda_lavori`? | **Sì, entrambi** (`script.trgfn_audit_data_user_generic` + `dbops.trgfn_tx_id_managed`) come l'analogo multi-writer `dbops.idempotency_keys` — NON il no-trigger di `fatture_stampa_coda` (single-writer). Vedi nota §1. |
| Q-B | Schema: `dbops` (proposto, registry-adjacent) vs `maintenance` | `dbops` |
| Q-C | FK `job_type` hard vs guard trigger | hard FK (Q-C risolto in §1: `codice` UNIQUE, indice via policy opt-in) |
| Q-D | `tx_id` gestito da trigger `dbops.trgfn_tx_id_managed` come le altre tabelle | sì (coerente con `idempotency_keys`; incluso in Q-A) |
| Q-E | **Idempotenza a due layer** — riconciliare con l'esistente `dbops.idempotency_keys` (+ `idempotency_store.py` + `handle_post_json`) | La coda dedup i **job vivi** per chiave di **business** (`competenza+scope`); il layer HTTP dedup per **header** `Idempotency-Key` e ri-getta la risposta memorizzata. Complementari. La chiave passata a `fn_accoda_lavoro` è quella di business — **NON** includere l'header (vanificherebbe la dedup di business). Correggere di conseguenza il design §6. |
| Q-F | Convergenza `fatture_stampa_coda`? | **DECISO (2026-07-20): NON si assorbe in `coda_lavori`.** Fattibile tecnicamente (FK non load-bearing), ma target sbagliato: la stampa è un **outbox di documenti tipizzato** (destino `documenti.*`, sorgente polimorfa `config.sorgenti`), non un job generico. `fatture_stampa_coda` **resta com'è** (non è throwaway: è già l'80% di `documenti.coda_stampa`, la promozione è **additiva**). L'anti-duplicazione è il **motore condiviso** `QueueDrainEngine`, non l'unificazione delle tabelle. Vedi design §4a/§5. |

## 6. Verifica attesa (pgTAP)

* `coda_lavori` / `coda_lavori_tipi` esistono con colonne/CHECK/indici attesi.
* `fn_accoda_lavoro`: enqueue base; **idempotenza** (2ª chiamata stessa
  `idempotency_key` viva → stesso id, nessun doppione); guard su `job_type` inesistente/
  inattivo; risoluzione default `run_as`/`max_tentativi` dal tipo.
* Unique parziale vivo: due PENDING con stessa `(job_type, idempotency_key)` → violazione.
* **Eleggibilità `run_after`**: un job differito (`run_after` nel futuro) NON è eleggibile
  al claim finché `run_after > now()`; diventa eleggibile a scadenza. (Test della query
  di claim, se il team la include nel perimetro DB.)
* Se si adotta Q-A (trigger): `data_update`/`user_update` si aggiornano sugli UPDATE.
* Seed `FATTURAZIONE_GIRO` presente e attivo.

> **Backoff sui retry** (nota per il BE, ma la colonna è DB): il path di retry dovrebbe
> settare `run_after = now() + f(tentativi)` per evitare che un poison-job ritenti a
> ogni poll fino a esaurire `max_tentativi`. La colonna `run_after` esiste già a questo
> scopo oltre che per i job differiti.

## 7. Sequenza

1. ✅ **FATTO (2026-07-20)** — Team DB: DDL + `fn_accoda_lavoro` + seed + pgTAP,
   applicati e verdi (vedi §8). Commit pendente.
2. ⬜ BE (io): core `apps/core/services/coda_lavori/*` + worker `draina_coda_lavori`
   (`QueueDrainEngine` + `QueueBackend`) + C-3 consumatore. **A worker deployato** si può
   eventualmente far accodare da trigger DB (non C-3, che accoda da Python).

## 8. Esito costruzione (2026-07-20) — ✅ APPLICATO + TESTATO

| Deliverable | File / oggetto | Stato |
| --- | --- | --- |
| Registry tipi | `00_schema/dbops/20260720-07-create-coda-lavori-tipi` → `dbops.coda_lavori_tipi` | ✅ migrato |
| Coda | `00_schema/dbops/20260720-08-create-coda-lavori` → `dbops.coda_lavori` (4 indici, 6 CHECK incl. `run_as↔scope`, FK, 2 trigger) | ✅ migrato |
| Enqueue | `20_code/dbops/20260720-09-create-fn-accoda-lavoro` → `dbops.fn_accoda_lavoro` (+`p_origine`) | ✅ migrato |
| Seed | `80_data/20260720-10-seed-…-fatturazione-giro` + `sql/dbops/coda_lavori_tipi.csv` | ✅ migrato |
| Codici errore | `messaggi_errore.csv` +548/549 (append, no nuovo loader) | ✅ migrato |
| pgTAP | `db/pgtap/dbops/test-coda-lavori.sql` | ✅ verde `plan(57)` |
| Doc manual | `dbzero/dbops/manual/{coda_lavori,coda_lavori_tipi,fn_accoda_lavoro}.md` | ✅ scritte (serve ri-run autogen per l'include) |
| GRANT app | `90_end/ci_apply/apply-runtime-grants-ci` (blanket su `dbops`) | ✅ auto-coperto, nessun changeset |

**Decisioni implementative oltre la §3**: aggiunto `p_origine` alla firma di
`fn_accoda_lavoro` (default `'API'`) per rendere valorizzabile `origine='TRIGGER'`;
guard parlante OPERATORE⇒scope prima del CHECK; indice claim esteso a `IN_CORSO` (serve
il reaper). Nessuna deviazione dal modello dati.

**Aperti (fuori ambito di questo brief DB)**: (a) ri-run autogen dbzero per agganciare
le manual; (b) commit su `dev/db-tid`; (c) tutto il BE (design §8). L'enqueue-da-trigger
reale e i tipi PEC/report/export sono *future by design* (seed + handler, zero DDL).

---

*Alla costruzione, il BE si aggancia a questi nomi/firme. Aggiornare la colonna Stato in
testata (🟡 → 🟢) ad apply avvenuto, con il commit.*
