# Guida – Tracciamento Processi e Job

> (latest review 04-03-26)
>
> Destinatari: sviluppatori database, backend e analisti funzionali
>
> Questa guida descrive l'infrastruttura attuale per il tracciamento dei processi e dei job
> in Zero ERP: cosa esiste, come e organizzato, e come si estende a nuovi domini.
>
> Vedi anche
>
> * [Guida Sistema di Audit Logging](/guide/messaggi-audit) — il registro delle operazioni
> * [Guida Messaggi di Errore e Generazione Log](/guide/Messaggi-di-Errore-e-Generazione-Log) — error logging e routing di dominio
> * [Guida Framework di Automazione DB](/guide/automazione-db) — automazioni dichiarative e audit
> * [PostgreSQL: pgAgent](/postgresql/pgAgent) — lo scheduler integrato

---

## Introduzione

In Zero ERP convivono processi di natura diversa: automazioni schedulati via pgAgent, pipeline di fatturazione orchestrate da Django, operazioni batch di manutenzione. Ognuno ha bisogno di registrare cosa ha fatto, quanto ha impiegato e se ha avuto successo.

Il sistema di tracciamento e organizzato su **tre livelli**, ciascuno con un ruolo preciso:

* **Audit log** (`dbops.audit_log`) — traccia le operazioni generiche: automazioni, deploy, processi batch. E il livello trasversale, usato da qualsiasi componente
* **Job run log** (`maintenance.job_run_log`) — traccia le esecuzioni dei job schedulati via pgAgent. Un record per ogni esecuzione con esito, durata e dettaglio errori
* **Task registry e task runs** (`dbops` + `vendite`) — traccia l'esecuzione dei task all'interno delle pipeline applicative, con stato, tentativi e policy di resume

Questi tre livelli non si sostituiscono: si affiancano. Un job pgAgent puo produrre record sia in `job_run_log` (per il job schedulato) sia in `audit_log` (per le automazioni che esegue), e un errore grave viene catturato anche in `error_log`.

**Cosa troverai in questa guida:**

* L'architettura dei tre livelli di tracciamento
* Il task registry multi-dominio e come registrare nuovi task
* Il tracciamento runtime delle pipeline (esecuzione, tentativi, policy)
* I job schedulati e l'integrazione con pgAgent
* Il rapporto tra i vari sistemi di logging

---

## Tabelle coinvolte

**Tracciamento operazioni (trasversale):**

* [dbops.audit_log](/dbzero/dbops/tabelle/audit_log) — registro operazioni generiche

**Task registry (multi-dominio):**

* [dbops.domini_task](/dbzero/dbops/tabelle/domini_task) — catalogo dei domini (es. FATTURAZIONE, ATTIVITA_FATTURABILI)
* [dbops.pipeline_task_registry](/dbzero/dbops/tabelle/pipeline_task_registry) — catalogo task per dominio
* [dbops.pipeline_task_registry_impl](/dbzero/dbops/tabelle/pipeline_task_registry_impl) — implementazioni dei task (handler, varianti)

**Task runtime (vendite — pipeline fatturazione):**

* [vendite.fatturazione_pipeline_task_policy](/dbzero/vendite/tabelle/fatturazione_pipeline_task_policy) — policy di esecuzione per task
* [vendite.fatturazione_lotti_task_runs](/dbzero/vendite/tabelle/fatturazione_lotti_task_runs) — esecuzioni runtime per lotto

**Job schedulati:**

* [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) — log esecuzioni pgAgent

---

## Il modello in sintesi

```text
dbops (trasversale)
    │
    ├── audit_log
    │       registro operazioni generiche (automazioni, batch, deploy)
    │
    ├── domini_task
    │       catalogo domini: FATTURAZIONE, ATTIVITA_FATTURABILI, ...
    │       │
    │       └── pipeline_task_registry
    │               catalogo task per dominio
    │               │
    │               └── pipeline_task_registry_impl
    │                       implementazioni: handler_code, is_default
    │
vendite (dominio specifico)
    │
    ├── fatturazione_pipeline_task_policy
    │       policy per task: resume_mode, annullabile
    │
    └── fatturazione_lotti_task_runs
            esecuzioni: lotto + task + tentativo → stato, durata, errori
    │
maintenance (job schedulati)
    │
    └── job_run_log
            un record per esecuzione pgAgent: jobname, ok, rows_affected
```

---

## Componenti del modello

### 1. Task registry multi-dominio

Il task registry e il catalogo centralizzato di tutti i task disponibili nei vari domini applicativi. E pensato per essere **riusabile**: quando si aggiunge un nuovo dominio (es. PRATICHE, ATTIVITA_FATTURABILI), si registrano i task nello stesso registry senza creare nuove tabelle di catalogo.

L'architettura e a tre livelli: dominio → task → implementazione.

#### `dbops.domini_task`

Definisce i domini applicativi. Ogni dominio e un perimetro logico che raggruppa task correlati.

Da un punto di vista tecnico:

| Colonna | Tipo | Descrizione |
| --- | --- | --- |
| `id` | BIGINT, PK | Chiave primaria |
| `codice` | TEXT, UNIQUE | Codice dominio (es. `FATTURAZIONE`, `ATTIVITA_FATTURABILI`) |
| `descrizione` | TEXT | Descrizione funzionale |
| `attivo` | BOOLEAN | Flag attivo/disattivo |
| `meta` | JSONB | Estensione libera |

> Documentazione dettagliata: [dbops.domini_task](/dbzero/dbops/tabelle/domini_task)

#### `dbops.pipeline_task_registry`

Catalogo dei task per dominio. Ogni task ha un codice univoco all'interno del proprio dominio e rappresenta un'operazione ben definita (es. `select_attivita`, `generate_fatture_righe`).

Da un punto di vista tecnico:

| Colonna | Tipo | Descrizione |
| --- | --- | --- |
| `id` | BIGINT, PK | Chiave primaria |
| `dominio_id` | BIGINT, FK | Riferimento a `domini_task` |
| `task_code` | TEXT | Codice task (UNIQUE per dominio) |
| `descrizione` | TEXT | Descrizione funzionale |
| `attivo` | BOOLEAN | Flag attivo/disattivo |
| `meta` | JSONB | Estensione libera |

Vincolo: `UNIQUE (dominio_id, task_code)` — impedisce task duplicati nello stesso dominio.

> Documentazione dettagliata: [dbops.pipeline_task_registry](/dbzero/dbops/tabelle/pipeline_task_registry)

#### `dbops.pipeline_task_registry_impl`

Definisce le implementazioni concrete di ogni task. Un task puo avere piu varianti (es. `default`, `v2`, `gas_v1`), ciascuna con il proprio `handler_code` che il layer Python usa per risolvere il codice da eseguire.

Questa tabella e la chiave del modello di dispatch **controllato**: nessun import dinamico, il codice Python consulta il registry e mappa `handler_code` a un handler statico nel proprio registro interno.

Da un punto di vista tecnico:

| Colonna | Tipo | Descrizione |
| --- | --- | --- |
| `id` | BIGINT, PK | Chiave primaria |
| `task_registry_id` | BIGINT, FK | Riferimento a `pipeline_task_registry` |
| `implementation_key` | TEXT | Identificativo variante (es. `default`, `v2`) |
| `handler_code` | TEXT | Codice handler logico (mappato dal Python) |
| `is_default` | BOOLEAN | Flag implementazione default (un solo default per task) |
| `attivo` | BOOLEAN | Flag attivo/disattivo |
| `meta` | JSONB | Estensione libera |

Vincoli:

* `UNIQUE (task_registry_id, implementation_key)` — una variante per task
* `UNIQUE (task_registry_id) WHERE is_default IS TRUE` — un solo default per task

> Documentazione dettagliata: [dbops.pipeline_task_registry_impl](/dbzero/dbops/tabelle/pipeline_task_registry_impl)

---

### 2. Task runtime: esecuzione e policy

Il task registry definisce **cosa** puo essere eseguito. Il task runtime traccia **come** viene eseguito: con quale policy, quanti tentativi, in quale stato.

Attualmente il runtime e implementato nel dominio vendite (pipeline fatturazione). Quando si aggiungeranno nuovi domini, ciascuno avra le proprie tabelle di policy e task_runs — seguendo lo stesso schema.

#### `vendite.fatturazione_pipeline_task_policy`

Definisce le regole di esecuzione per ogni task all'interno di una pipeline: se il task e annullabile, quale strategia di recovery usare in caso di errore.

Da un punto di vista tecnico:

| Colonna | Tipo | Descrizione |
| --- | --- | --- |
| `id` | BIGINT, PK | Chiave primaria |
| `pipeline_id` | BIGINT, FK | Riferimento a `fatturazione_pipeline` |
| `task_code` | VARCHAR | Codice task |
| `annullabile` | BOOLEAN | Se il task e cancellabile (default: true) |
| `resume_mode` | VARCHAR | Strategia recovery: `RESET_STEP`, `RESUME_STEP`, `RESUME_TASK` |
| `attivo` | BOOLEAN | Policy attiva/inattiva |
| `meta` | JSONB | Estensione |

Vincolo: `UNIQUE (pipeline_id, task_code)`.

> Documentazione dettagliata: [vendite.fatturazione_pipeline_task_policy](/dbzero/vendite/tabelle/fatturazione_pipeline_task_policy)

#### `vendite.fatturazione_lotti_task_runs`

Traccia ogni singola esecuzione di un task su un lotto. E il cuore del tracciamento runtime: registra lo stato corrente, i tentativi, gli errori e i metadati di progresso.

Il campo `tentativo` permette di gestire retry deterministici: ogni nuovo tentativo crea un record distinto, mantenendo lo storico completo.

Da un punto di vista tecnico:

| Colonna | Tipo | Descrizione |
| --- | --- | --- |
| `id` | BIGINT, PK | Chiave primaria |
| `lotto_id` | BIGINT, FK | Lotto in elaborazione |
| `pipeline_id` | BIGINT, FK | Pipeline di contesto |
| `stato_doc_fiscale_id` | INTEGER, FK | Fase del processo |
| `task_code` | VARCHAR | Task in esecuzione |
| `fase` | VARCHAR | Sotto-fase (opzionale) |
| `tentativo` | SMALLINT | Numero tentativo (default: 1) |
| `task_stato` | VARCHAR | Stato: `IN_ESECUZIONE`, `COMPLETATO`, `ERRORE`, `ANNULLATO` |
| `started_at` | TIMESTAMPTZ | Inizio esecuzione |
| `ended_at` | TIMESTAMPTZ | Fine esecuzione |
| `error_code` | VARCHAR | Codice errore (se fallito) |
| `error_message` | TEXT | Messaggio errore |
| `meta` | JSONB | Metadati runtime (progresso, metriche) |

Vincoli:

* `UNIQUE (lotto_id, stato_doc_fiscale_id, task_code, tentativo)` — tracciamento deterministico
* `CHECK (ended_at >= started_at)` — coerenza temporale

> Documentazione dettagliata: [vendite.fatturazione_lotti_task_runs](/dbzero/vendite/tabelle/fatturazione_lotti_task_runs)

---

### 3. Job schedulati: pgAgent e maintenance

I job schedulati via pgAgent sono processi periodici gestiti dallo scheduler PostgreSQL: pulizia log, applicazione indici FK, storicizzazione, aggiornamento audit. Ogni job ha il proprio wrapper nel schema `maintenance` e registra le esecuzioni in `job_run_log`.

#### `maintenance.job_run_log`

Un record per ogni esecuzione di un job schedulato. La struttura e piatta e semplice: nome del job, step, esito, errore, righe coinvolte.

Da un punto di vista tecnico:

| Colonna | Tipo | Descrizione |
| --- | --- | --- |
| `id` | BIGSERIAL, PK | Chiave primaria |
| `jobname` | TEXT | Identificativo del job (es. `apply_storicizza_weekly`) |
| `stepname` | TEXT | Step del job |
| `started_at` | TIMESTAMPTZ | Inizio (default: `clock_timestamp()`) |
| `ended_at` | TIMESTAMPTZ | Fine |
| `ok` | BOOLEAN | Successo si/no |
| `rows_affected` | BIGINT | Righe coinvolte |
| `message` | TEXT | Messaggio esito |
| `error_code` | TEXT | SQLSTATE se errore |
| `error_detail` | TEXT | Dettaglio errore (DETAIL + HINT + CONTEXT) |
| `agent_host` | TEXT | Host di origine |
| `run_uuid` | UUID | Correlatore di sessione (default: `uuidv7()`) |

> Documentazione dettagliata: [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log)

#### `maintenance.fn_run_and_log`

La funzione wrapper standard per i job pgAgent. Gestisce:

* Advisory lock (evita esecuzioni parallele)
* Logging automatico su `job_run_log` con esito e durata
* Cattura errori con SQLSTATE e contesto

Ogni job schedulato ha una procedura dedicata (es. `proc_automations_storico_job`, `proc_automations_cleanup_job`) che internamente usa `fn_run_and_log` per la parte di logging.

---

## Flusso tipico: pipeline fatturazione

Per concretizzare come i tre livelli interagiscono, questo e il flusso di una pipeline di fatturazione:

```text
1. Django runner (LottoPipelineRunner)
   │
   ├── Lookup task registry (dbops.pipeline_task_registry)
   │     quale task eseguire, quale implementazione usare
   │
   ├── Per ogni task:
   │     │
   │     ├── INSERT vendite.fatturazione_lotti_task_runs
   │     │     task_stato = 'IN_ESECUZIONE', tentativo = N
   │     │
   │     ├── Esecuzione handler Python
   │     │     (chiama funzioni SQL di dominio)
   │     │
   │     ├── UPDATE task_runs → 'COMPLETATO' o 'ERRORE'
   │     │     con ended_at, error_code/message se fallito
   │     │
   │     └── In caso di errore SQL:
   │           script.fn_log_and_raise_error → dbops.error_log
   │           vendite.fn_log_pipeline_fase → fatturazione_lotti_log
   │
   └── Chiusura pipeline
         vendite.fn_log_lotto_esito_fatture
         (aggrega esiti C > W > I)
```

---

## Flusso tipico: job pgAgent

```text
1. pgAgent triggera il job schedulato
   │
   └── maintenance.proc_<nome>_job()
         │
         ├── maintenance.fn_run_and_log(jobname, stepname)
         │     advisory lock + INSERT job_run_log (started_at)
         │
         ├── Esecuzione operazione
         │     (es. dbops.fn_run_automations per STORICO)
         │
         ├── UPDATE job_run_log → ok=true/false, ended_at
         │
         └── Audit log (opzionale)
               dbops.fn_audit_begin / fn_audit_end
               (se il processo usa il framework di automazione)
```

---

## Come estendere a un nuovo dominio

Quando si aggiunge un nuovo dominio (es. `PRATICHE`), il pattern e:

**1. Registrare il dominio e i task (una tantum):**

```sql
-- Dominio
INSERT INTO dbops.domini_task (codice, descrizione)
VALUES ('PRATICHE', 'Gestione pratiche');

-- Task
INSERT INTO dbops.pipeline_task_registry (dominio_id, task_code, descrizione)
VALUES
  ((SELECT id FROM dbops.domini_task WHERE codice = 'PRATICHE'),
   'assegna_pratica', 'Assegnazione pratica a operatore'),
  ((SELECT id FROM dbops.domini_task WHERE codice = 'PRATICHE'),
   'valida_documenti', 'Validazione documenti allegati');

-- Implementazione default
INSERT INTO dbops.pipeline_task_registry_impl
  (task_registry_id, implementation_key, handler_code, is_default)
SELECT id, 'default', 'pratiche_assegna_v1', true
FROM dbops.pipeline_task_registry
WHERE task_code = 'assegna_pratica';
```

**2. Creare le tabelle di runtime nel dominio** (seguendo lo schema di vendite):

* `<dominio>.pratiche_task_policy` — policy di esecuzione
* `<dominio>.pratiche_task_runs` — esecuzioni runtime

**3. Creare le tabelle di log di dominio** (vedi [contratto standard](/guide/Messaggi-di-Errore-e-Generazione-Log#contratto-standard-per-i-log-di-dominio)):

* Tabella log con `scope`, `severity`, `code`, `meta`

---

## Rapporto tra i sistemi di logging

| Sistema | Cosa traccia | Persistenza | Scope |
| --- | --- | --- | --- |
| `dbops.audit_log` | Operazioni (successi, skip, errori) | In-transazione o dblink | Trasversale |
| `dbops.error_log` | Errori con codice e contesto | Sempre dblink | Trasversale |
| `maintenance.job_run_log` | Esecuzioni job pgAgent | In-transazione | Job schedulati |
| `vendite.fatturazione_lotti_task_runs` | Esecuzioni task pipeline | In-transazione | Dominio vendite |
| `vendite.fatturazione_lotti_log` | Log di dominio (fasi, esiti) | In-transazione | Dominio vendite |

Un errore durante una pipeline produce record in **tre** sistemi:

1. `fatturazione_lotti_task_runs` — il task va in stato `ERRORE` con `error_code` e `error_message`
2. `dbops.error_log` — il record tecnico persistente (via dblink)
3. `vendite.fatturazione_lotti_log` — il log di dominio con severita e fase

---

## Best practice

* **Registrare sempre i task nel registry** prima di usarli nel codice Python — il dispatch controllato impedisce l'esecuzione di task non censiti
* **Un solo `is_default` per task** — il vincolo UNIQUE lo garantisce a livello DB
* **Usare `tentativo` per i retry** invece di sovrascrivere il record precedente — lo storico completo aiuta la diagnosi
* **Separare policy da esecuzione**: la tabella `task_policy` definisce il comportamento (annullabile, resume_mode), la tabella `task_runs` registra cosa e successo
* **Per i job pgAgent, usare sempre `fn_run_and_log`** come wrapper — garantisce logging uniforme e advisory lock
* **Non duplicare il tracciamento**: se un processo usa `task_runs`, non serve anche un `fn_audit_begin`/`fn_audit_end` sullo stesso perimetro

---

## Diagrammi ER

### Task registry (dbops)

```mermaid
erDiagram
    domini_task {
        bigint id PK
        text codice
        text descrizione
        boolean attivo
    }

    pipeline_task_registry {
        bigint id PK
        bigint dominio_id FK
        text task_code
        text descrizione
        boolean attivo
    }

    pipeline_task_registry_impl {
        bigint id PK
        bigint task_registry_id FK
        text implementation_key
        text handler_code
        boolean is_default
        boolean attivo
    }

    domini_task ||--o{ pipeline_task_registry : "ha task"
    pipeline_task_registry ||--o{ pipeline_task_registry_impl : "ha implementazioni"
```

### Task runtime (vendite)

```mermaid
erDiagram
    fatturazione_pipeline {
        bigint id PK
    }

    fatturazione_lotti {
        bigint id PK
    }

    fatturazione_pipeline_task_policy {
        bigint id PK
        bigint pipeline_id FK
        varchar task_code
        boolean annullabile
        varchar resume_mode
    }

    fatturazione_lotti_task_runs {
        bigint id PK
        bigint lotto_id FK
        bigint pipeline_id FK
        varchar task_code
        smallint tentativo
        varchar task_stato
        timestamptz started_at
        timestamptz ended_at
        jsonb meta
    }

    fatturazione_pipeline ||--o{ fatturazione_pipeline_task_policy : "policy"
    fatturazione_pipeline ||--o{ fatturazione_lotti_task_runs : "contesto"
    fatturazione_lotti ||--o{ fatturazione_lotti_task_runs : "esecuzioni"
```

---

## Note finali

Questa guida copre l'infrastruttura di tracciamento processi e job nello stato attuale. Per i singoli sistemi di logging:

* [Guida Sistema di Audit Logging](/guide/messaggi-audit) — `dbops.audit_log` in dettaglio
* [Guida Messaggi di Errore](/guide/Messaggi-di-Errore-e-Generazione-Log) — `dbops.error_log` e routing di dominio
* [Guida Framework di Automazione DB](/guide/automazione-db) — le automazioni dichiarative
* [PostgreSQL: pgAgent](/postgresql/pgAgent) — lo scheduler e i concetti di job/schedule/step

---

{% include-markdown "signature-core.md" %}
