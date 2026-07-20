## 📘 Documentazione Concettuale – Tabella `dbops.coda_lavori`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [dbops.coda_lavori_tipi](/dbzero/dbops/manual/coda_lavori_tipi)  
> • [dbops.idempotency_keys](/dbzero/dbops/manual/idempotency_keys)  
> • [vendite.fatture_stampa_coda](/dbzero/vendite/manual/fatture_stampa_coda)  
>
**Approfondimento funzioni:**
>
• [dbops.fn_accoda_lavoro](/dbzero/dbops/manual/fn_accoda_lavoro)  
>

### 🎯 Scopo Principale
(latest review 20-07-2026)

`dbops.coda_lavori` è la **coda di lavori generica DB-native** dell'ERP: la
variante su Postgres, transazionale e **senza broker**, del pattern "task queue"
(SolidQueue / pg-boss / Oban). Una riga = **un job asincrono** (`job_type` +
`payload`). L'**enqueue è atomico col dato di business** (stessa transazione, no
dual-write) via [dbops.fn_accoda_lavoro](/dbzero/dbops/manual/fn_accoda_lavoro),
callable anche da trigger. Un **worker unico** la drena e dispatcha per
`job_type` verso l'handler Python.

È la **fondazione async** dell'ERP: ogni nuovo lavoro asincrono (fatturazione
on-demand, PEC/SDI, report, export…) è **un handler + un enqueue**, non una
nuova tabella + nuovo worker + nuova migration. Primo consumatore:
`FATTURAZIONE_GIRO` (giro fatturazione on-demand, C-3).

---

### Campi chiave

* `job_type`: tipo del job (hard FK a
  [coda_lavori_tipi.codice](/dbzero/dbops/manual/coda_lavori_tipi)); chiave di
  dispatch.
* `payload`: argomenti del job (JSONB), es. `{competenza, fino_a_stato}`.
* `run_as` / `scope`: **chi esegue**. `SISTEMA` → il worker apre
  `system_process_context` (BYPASSRLS); `OPERATORE` → applica lo `scope`
  **catturato all'enqueue** (es. `{emittente_ids, auth_user_id}`), senza bypass.
  Il CHECK `chk_coda_lavori_run_as_scope` impone: OPERATORE ⇒ `scope` NOT NULL,
  SISTEMA ⇒ `scope` NULL (un job OPERATORE senza scope girerebbe senza filtro RLS).
* `origine`: chi ha **accodato** — `API` | `CRON` | `COMMAND` | `TRIGGER`
  (enqueue DB-native da dominio). Set proprio della coda, **distinto** da
  `maintenance.job_run_log.origine` (che descrive chi *esegue* il run).
* `priorita`: minore = più urgente; il worker fa claim a **batch misto**
  `ORDER BY priorita, id` (no starvation tra `job_type` diversi).
* `stato`: `PENDING` → `IN_CORSO` → `FATTO` | `ERRORE` | `ANNULLATO`.
* `tentativi` / `max_tentativi`: oltre soglia → `ERRORE` terminale.
* `run_after`: eleggibile al claim solo se NULL o ≤ `now()`. Copre i **job
  differiti** e il **backoff** sui retry (`run_after = now() + f(tentativi)`).
* `claimed_at`: istante del claim, autoritativo per il **reaper** (nessun trigger
  lo tocca; lo setta il claim BE).
* `idempotency_key`: chiave di **business** per la dedup dei job **vivi** (vedi
  sotto). `job_run_id`: link a `maintenance.job_run_log`. `result`: esito/summary.

---

### Ciclo di vita e transizioni (worker BE, SQL diretto)

Il DB fornisce **solo l'enqueue**. Claim/marca/reaper li fa il worker in SQL
diretto (come per `fatture_stampa_coda`):

* **Claim**: `… WHERE stato='PENDING' AND (run_after IS NULL OR run_after ≤ now())
  ORDER BY priorita, id FOR UPDATE SKIP LOCKED` → flip a `IN_CORSO`. Più worker
  in parallelo non si pestano (indice `ix_coda_lavori_da_lavorare`).
* **Esito**: `FATTO` (con `result`) oppure — su fallimento — `PENDING`
  riprovabile (con backoff su `run_after`) fino a `max_tentativi`, poi `ERRORE`.
* **Nessuna interruzione a metà**: se i permessi dell'operatore vengono revocati
  mentre un job `OPERATORE` gira, il job **completa** con lo scope catturato; la
  revoca vale per i job futuri.
* **Cancel**: ammesso **solo** su `PENDING` → `ANNULLATO` (`WHERE stato='PENDING'`,
  fallisce silente se già claimato: no race col worker).
* **Reaper**: `IN_CORSO` con `claimed_at < now()-soglia` → `PENDING` (worker morto).
* **Sblocco manuale (requeue)**: azione admin che rimette a `PENDING` un job
  bloccato/`ERRORE`, **mantenendo** `tentativi` (storia) e alzando
  `max_tentativi += N` per consentire i nuovi tentativi.

---

### Idempotenza a due layer

* **Questa coda** deduplica i job **vivi** (`PENDING`/`IN_CORSO`) per chiave di
  **business** via l'unique parziale `uq_coda_lavori_vivo_idem`
  `(job_type, idempotency_key)`. Non impedisce di ri-accodare a job
  `FATTO`/`ERRORE`/`ANNULLATO` (ri-esecuzione intenzionale).
* **Layer HTTP** ([dbops.idempotency_keys](/dbzero/dbops/manual/idempotency_keys)):
  deduplica per **header** `Idempotency-Key` e replica la risposta memorizzata.
  I due sono **complementari**: la `idempotency_key` della coda è la chiave di
  business (es. `competenza+scope`), **non** l'header HTTP.

---

### Perché è distinta da `fatture_stampa_coda`

`vendite.fatture_stampa_coda` **resta specializzata** (non è assorbita qui): è un
**outbox di documenti tipizzato** (FK sorgente reale, destino `documenti.*`) —
asse diverso dalla coda-*job*. L'anti-duplicazione non è l'unione delle tabelle
ma il **motore di drenaggio condiviso** (`QueueDrainEngine` lato BE): un solo
loop reaper→claim→retry, backend tipizzati distinti. Vedi
`brief-design-coda-lavori-generica` §5.

---

### Audit e coerenza transazionale

Tabella **multi-writer** (ogni dominio accoda, worker, cancel, requeue): monta
**entrambi** i trigger `script.trgfn_audit_data_user_generic` (audit
`data_update`/`user_update`) e `dbops.trgfn_tx_id_managed` (`tx_id`), come
[dbops.idempotency_keys](/dbzero/dbops/manual/idempotency_keys) — **non** il
no-trigger di `fatture_stampa_coda` (single-writer).

Brief: `brief-db-coda-lavori-generica` §1.

---

{% include-markdown "signature-core.md" %}
