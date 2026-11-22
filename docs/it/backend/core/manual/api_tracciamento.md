# API Tracciamento Processi e Job

## Scopo

> **Ultimo aggiornamento**: 22 novembre 2026

Espone in lettura i tre livelli di tracciamento del sistema: audit log operativo, task registry multi-dominio e il giornale delle corse dei lavori automatici. È la vista **grezza e trasversale**: la vista per processo, con le sue corse, sta nella schermata dei processi automatici (vedi [Vedi anche](#vedi-anche)).

## Contesto

Il sistema di tracciamento Zero ERP opera su tre livelli distinti (vedi [Guida Tracciamento Processi e Job](/guide/analisi-tracciamento-processi-e-job)):

1. **Audit log** (`dbops.audit_log`) -- operazioni generiche trasversali
2. **Task registry** (`dbops.domini_task`, `pipeline_task_registry`, `pipeline_task_registry_impl`) -- catalogo task multi-dominio
3. **Job run log** (`maintenance.job_run_log`) -- il giornale delle corse di **qualunque** lavoro automatico, una riga per corsa (o per passo)

⚠️ Il giornale **non è solo dei job pgAgent**. Ci scrivono due porte, distinte
dalla colonna `origine`:

| `origine` | Chi scrive | Da dove |
|-----------|-----------|---------|
| `PGAGENT` | i job del database | `maintenance.fn_run_and_log`, chiamata dai wrapper `maintenance.proc_*_job` |
| `CRON` / `COMMAND` | i comandi del backend (timer systemd, lancio manuale) | `script.fn_job_run_start` / `script.fn_job_run_end`, attraverso il BB `registered_job` di `apps/core/services/job_run.py` |

Questo documento copre 6 endpoint GET paginati in `apps/core/api/views_tracciamento.py`, orchestrati dal service `apps/core/services/tracciamento_service.py` che delega a due repository:

- `DbopsRepository` (`apps/core/db/dbops_repository.py`) -- audit log + task registry
- `MaintenanceRepository` (`apps/core/db/maintenance_repository.py`) -- job run log

Architettura a strati: View -> Service (validazione) -> Repository (SQL) -> DB.

## Endpoint

I 6 endpoint sono sotto `/api/v1/core/tracciamento/` e richiedono autenticazione JWT e
permesso sull'area funzionale `core` (`area_funzionale = "core"`).

Lo stesso prefisso ospita anche la gestione delle code (conteggi, coda lavori, coda
stampa, con le azioni POST annulla/requeue/archivia/ripristina, area `strumenti`):
sono documentate in [api_gestione_code.md](api_gestione_code.md).

### Audit Log

```http
GET /api/v1/core/tracciamento/audit-log/
```

| Parametro       | Tipo   | Obbligatorio | Default | Note                                        |
|-----------------|--------|:------------:|---------|---------------------------------------------|
| `status`        | string | No           | --      | Filtra: `SUCCESS`, `FAILED`, `WARNING`      |
| `function_name` | string | No           | --      | Filtra per function_name (ILIKE)            |
| `date_from`     | string | No           | --      | Data inizio (YYYY-MM-DD)                    |
| `date_to`       | string | No           | --      | Data fine (YYYY-MM-DD)                      |
| `search`        | string | No           | --      | Ricerca libera ILIKE su function_name/message |
| `limit`         | int    | No           | 25      | Righe per pagina (1-200, fuori → 400)|
| `offset`        | int    | No           | 0       | Righe da saltare (negativo → 400)             |

### Domini Task

```http
GET /api/v1/core/tracciamento/domini-task/
```

| Parametro     | Tipo | Obbligatorio | Default | Note                          |
|---------------|------|:------------:|---------|-------------------------------|
| `attivo_only` | bool | No           | true    | Filtra solo domini attivi     |
| `search`      | str  | No           | --      | ILIKE su codice/descrizione   |
| `limit`       | int  | No           | 25      | Righe per pagina (1-200, fuori → 400)|
| `offset`      | int  | No           | 0       | Righe da saltare (negativo → 400)|

### Task Registry

```http
GET /api/v1/core/tracciamento/task-registry/
```

| Parametro     | Tipo   | Obbligatorio | Default | Note                                |
|---------------|--------|:------------:|---------|-------------------------------------|
| `dominio`     | string | No           | --      | Filtra per codice dominio (es. FATTURAZIONE) |
| `attivo_only` | bool   | No           | true    | Filtra solo task attivi             |
| `search`      | str    | No           | --      | ILIKE su task_code/descrizione      |
| `limit`       | int    | No           | 25      | Righe per pagina (1-200, fuori → 400)|
| `offset`      | int    | No           | 0       | Righe da saltare (negativo → 400)     |

### Task Implementations

```http
GET /api/v1/core/tracciamento/task-implementations/
```

| Parametro     | Tipo   | Obbligatorio | Default | Note                          |
|---------------|--------|:------------:|---------|-------------------------------|
| `task_code`   | string | No           | --      | Filtra per task_code          |
| `dominio`     | string | No           | --      | Filtra per codice dominio     |
| `attivo_only` | bool   | No           | true    | Filtra solo impl attive       |
| `limit`       | int    | No           | 25      | Righe per pagina (1-200, fuori → 400)|
| `offset`      | int    | No           | 0       | Righe da saltare (negativo → 400)|

### Job Runs

```http
GET /api/v1/core/tracciamento/job-runs/
```

| Parametro   | Tipo   | Obbligatorio | Default | Note                          |
|-------------|--------|:------------:|---------|-------------------------------|
| `jobname`   | string | No           | --      | Filtra per jobname esatto     |
| `ok`        | bool   | No           | --      | Filtra per esito: `true` = riuscite, `false` = fallite; vuoto = nessun filtro; ogni altro valore è un 400 `E_VALIDATION_INPUT` (dal 2026-10-20: prima `1`/`yes`/`y` = riuscite e tutto il resto fallite, in silenzio) |
| `date_from` | string | No           | --      | Data inizio (YYYY-MM-DD)      |
| `date_to`   | string | No           | --      | Data fine (YYYY-MM-DD)        |
| `search`    | str    | No           | --      | ILIKE su jobname/stepname/message |
| `limit`     | int    | No           | 25      | Righe per pagina (1-200, fuori → 400)|
| `offset`    | int    | No           | 0       | Righe da saltare (negativo → 400)|

Ordine fisso: `started_at DESC, id DESC`. Ogni riga (`JobRunLogRow` in
`apps/core/types.py`) porta `id`, `jobname`, `stepname`, `started_at`,
`ended_at` (testo PG), `ok`, `rows_affected`, `message`, `error_code`,
`error_detail`, `agent_host`, `run_uuid`, `saltata`.

⚠️ Non porta `origine`, `processo_codice`, `meta`, `auth_user_id`,
`ruolo_sessione` né `sqlstate`, che la tabella ha. Le corse **di un processo**
(filtro su `processo_codice`, con `origine` e l'operatore che le ha lanciate) le
dà `GET /api/v1/amm-software/processi/{codice}/run/`, riservato a
`SUPER_ADMIN` ([api_amm_software.md](../../amm-software/manual/api_amm_software.md)
§6.9), che dal 2026-11-22 porta anche il resoconto della corsa (`meta`,
`error_detail`).

Ogni riga porta `saltata`: `true` sulla corsa che ha trovato il lock della corsia
occupato (dal 2026-10-10, brief `brief-db-corsa-saltata-non-e-una-corsa`). Una
saltata è chiusa e **senza esito** (`ok = null`), quindi `ok` da solo non la
distingue da una corsa aperta: la distingue `saltata`. Il filtro `ok` la esclude
in entrambi i versi. Le saltate scritte prima di quel giorno restano
`ok = true`, `saltata = false`.

### Job Summary

```http
GET /api/v1/core/tracciamento/job-summary/
```

| Parametro   | Tipo | Obbligatorio | Default | Note                    |
|-------------|------|:------------:|---------|-------------------------|
| `limit`     | int  | No           | 25      | Righe per pagina (1-200, fuori → 400)|
| `offset`    | int  | No           | 0       | Righe da saltare (negativo → 400)|

Restituisce per ogni jobname: `total_runs` (le corse **vere**: una saltata non è
un'esecuzione), `ok_count`, `fail_count`, `saltate_count`,
`last_run_at` (la riga più recente, testo PG: anche una saltata, che è segno di
vita della sveglia), `in_corso` (quella riga è ancora
aperta) e `ultima_conclusa = {started_at, ended_at, ok}` in ISO-8601: l'ultima
corsa **vera** chiusa, mai una saltata (`null` se nessuna corsa vera è mai stata
chiusa). ⛔ Dal 2026-09-14 al posto di `last_ok`:
un esito accanto alla data di un'*altra* corsa (l'ultima avviata) si leggeva
come uno — stessa forma di `job_liveness`, vedi
[api_gestione_code.md](api_gestione_code.md) §1. Ordine: la riga più recente
prima (`last_run_at DESC`), poi `jobname`.

L'endpoint non ha filtri. I due filtri del repository (`jobname_prefix`,
`meta_month_equals`) li usa solo il pannello esiti della fatturazione
([api_fatturazione.md](../../vendite/manual/api_fatturazione.md)), e la chiave
`meta` la sceglie il codice chiamante, mai il client.

## Output

Tutti gli endpoint restituiscono l'envelope paginato standard:

```json
{
  "data": {
    "count": 42,
    "page": 1,
    "page_size": 25,
    "total_pages": 1,
    "results": [...]
  },
  "meta": {"request_id": "..."}
}
```

## Regole

- I 6 endpoint di questo documento sono in sola lettura (GET).
- Il parametro `status` per audit-log e` validato server-side: solo `SUCCESS`, `FAILED`, `WARNING`.
- Paginazione `limit`/`offset`, letta da `pagina_da_query`: `limit` default 25,
  max 200. Un valore non intero è un `400 E_VALIDATION_INPUT`
  (`limit_invalid`/`offset_invalid`); dal 2026-10-21 anche il fuori limite
  (`limit` fuori da 1..200: `limit_fuori_limiti_1_200`; `offset` negativo:
  `offset_negativo`), che prima si riportava nei limiti in silenzio.
- ⛔ `page`/`page_size` in query sono un `400 E_VALIDATION_INPUT`
  (`page_non_ammesso_usare_limit_offset`) dal 2026-10-21: fino a quel giorno
  erano il contratto di questi sei endpoint. La risposta porta ancora `page` e
  `page_size`, ricavati dall'offset (`envelope_da_offset`).
- I filtri date (`date_from`/`date_to`, `YYYY-MM-DD`) sono giorni **dell'azienda** (fuso `SYSTEM_FUSO_ORARIO`, confini calcolati dal DB col BB `predicato_giorno_operativo`, dal 2026-10-09), `date_to` incluso. Malformate → `400 E_VALIDATION_INPUT` (fino al 2026-10-09 arrivavano al DB come stringa, e il confine alto era compreso: `<= date_to + 1 giorno`).
- Throttling `SearchBurstRateThrottle` su cinque endpoint su sei: tutti tranne
  `job-summary`, che non ha né ricerca né filtri.
- Nessun dato viene modificato. Le corse le scrivono i lavori stessi (vedi
  [Contesto](#contesto)), il tracciamento dei task i service di dominio (es.
  `VenditePipelineRepository`).

## Dipendenze DB

Lette da questi endpoint:

- `dbops.audit_log` -- registro operazioni generiche (indici: `ix_audit_fn_ts`, `ix_audit_status_ts`)
- `dbops.domini_task` -- catalogo domini task
- `dbops.pipeline_task_registry` -- catalogo task per dominio
- `dbops.pipeline_task_registry_impl` -- implementazioni handler
- `maintenance.job_run_log` -- il giornale delle corse, di entrambe le origini

Scrivono il giornale, e questi endpoint **non** le chiamano:

- `maintenance.fn_run_and_log` -- la porta dei job del database (`origine = PGAGENT`)
- `script.fn_job_run_start` / `script.fn_job_run_end` -- la porta dei comandi del backend (`CRON`/`COMMAND`)

## Il resto di `MaintenanceRepository`

Il repository non serve solo questi endpoint. Gli altri metodi, e chi li usa:

| Metodo | Che cosa risponde | Chi lo usa |
|--------|-------------------|-----------|
| `sveglia_accesa(processo_codice)` | `maintenance.fn_sveglia_accesa`: la sveglia del processo deve far partire il lavoro? Mai `NULL`: se la funzione non sa decidere, solleva | `e_dovuto` (l'`ExecCondition` delle sveglie) |
| `corsa_riuscita_dal(jobname, dal)` | c'è una corsa **riuscita** della corsia da `dal` in poi (fallite, aperte e saltate non contano) | `e_dovuto`, sveglie calendariali |
| `corsa_chiusa_dal(jobname, dal)` | c'è una corsa **chiusa con esito**, riuscita o fallita, da `dal` in poi | `e_dovuto` con `basta_una_corsa` |
| `job_liveness(jobnames=… \| processo_codice=…, soglia_minuti)` | per jobname: segno di vita (`last_run_at` ISO-8601, `attivo`, `in_corso`) + `ultima_conclusa`. Esattamente **una** delle due chiavi: senza, leggerebbe il giornale intero | stato dei worker in [api_gestione_code.md](api_gestione_code.md), digest dei presidi |
| `list_job_summary(jobname_prefix=…, meta_month_equals=…)` | come `job-summary`, coi due filtri facoltativi | `job-summary` (senza filtri), pannello esiti della fatturazione |

⭐ Le corse si raccontano in **una forma sola** in tutto il backend: la riga più
recente come segno di vita, l'ultima corsa vera chiusa come `ultima_conclusa`
(factory `corsa_conclusa` in `apps/core/db/_helpers.py`, condivisa con la coda
lavori).

## File coinvolti

| Layer      | File                                              |
|------------|---------------------------------------------------|
| Types      | `apps/core/types.py`                              |
| Repository | `apps/core/db/dbops_repository.py`                |
| Repository | `apps/core/db/maintenance_repository.py`          |
| Service    | `apps/core/services/tracciamento_service.py`       |
| API        | `apps/core/api/views_tracciamento.py`              |
| URL        | `apps/core/api/urls_v1.py`                         |
| Test       | `apps/core/tests/services/test_tracciamento_service.py` |
| Test       | `apps/core/tests/services/test_tracciamento_repositories.py` |
| Test       | `apps/core/tests/api/test_tracciamento_api.py`     |

## Codici errore

| Codice              | HTTP | Causa                                          |
|---------------------|------|------------------------------------------------|
| `E_CORE_VALIDATION` | 400  | `status` fuori elenco                          |
| `E_VALIDATION_INPUT` | 400 | `limit`/`offset` non interi o fuori limiti, `page`/`page_size` presenti, date malformate, `ok`/`attivo_only` non booleani |
| `E_GENERICO`        | 500  | Errore imprevisto                              |

## Note

- Le query sono dirette, senza funzioni né viste SQL dedicate. ⚠️ Gli indici
  li ha `dbops.audit_log`; `maintenance.job_run_log` ha **solo** la chiave
  primaria (doc DB al 2026-11-22), quindi `job-runs` e `job-summary` (e
  `job_liveness`, con i suoi `DISTINCT ON (jobname)`) leggono la tabella intera.
  Fino a questa revisione la nota diceva che gli indici esistenti coprivano i
  pattern di accesso, e per il giornale non era vero. Un indice è lavoro DB:
  va chiesto con un brief, non deciso da qui.
- I tipi condivisi (`AuditLogRow`, `DominioTaskRow`, `TaskRegistryRow`, `TaskRegistryImplRow`, `JobRunLogRow`) sono in `apps/core/types.py` per riuso cross-dominio.
- Gli helper generici `qp_bool_optional`, `qp_str`, `pagina_da_query`, `envelope_da_offset` sono in `apps/core/api/payload_validators.py` e riusabili da qualsiasi endpoint GET.
- 2026-10-21: i sei endpoint leggono la finestra come `limit`/`offset` (`pagina_da_query`); `page`/`page_size` in query diventano un 400. Envelope invariato.
- 2026-11-22: revisione dei riferimenti a `maintenance`. Il giornale è di
  entrambe le origini (prima: «esecuzioni job pgAgent»); censiti i campi di
  `job-runs` e i metodi di `MaintenanceRepository` fuori da questi endpoint;
  tolta l'ipotesi `maintenance.vw_job_summary`, una vista che non esiste.

## Vedi anche

- [api_gestione_code.md](api_gestione_code.md) -- code, e stato dei worker letto dal giornale
- [api_amm_software.md](../../amm-software/manual/api_amm_software.md) §6 -- processi automatici e presidi, fra cui `maintenance.vw_job_run_da_guardare`
- [sveglie_processi.md](sveglie_processi.md) -- le sveglie dichiarate, confrontate col giornale
- [api_fatturazione.md](../../vendite/manual/api_fatturazione.md) -- pannello esiti, che fonde il giornale e la coda lavori
- DB: [schema `maintenance`](/dbzero/maintenance/), [tabella `job_run_log`](/dbzero/maintenance/tabelle/job_run_log)
