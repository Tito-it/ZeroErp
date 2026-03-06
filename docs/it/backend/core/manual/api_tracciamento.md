# API Tracciamento Processi e Job

## Scopo

Espone in lettura i tre livelli di tracciamento del sistema: audit log operativo, task registry multi-dominio e log esecuzioni job pgAgent. Fornisce agli anelli esterni e alla futura UI una vista unificata sulle operazioni del sistema.

## Contesto

Il sistema di tracciamento Zero ERP opera su tre livelli distinti (vedi [Guida Tracciamento Processi e Job](/guide/Analisi-tracciamento-processi-e-job)):

1. **Audit log** (`dbops.audit_log`) -- operazioni generiche trasversali
2. **Task registry** (`dbops.domini_task`, `pipeline_task_registry`, `pipeline_task_registry_impl`) -- catalogo task multi-dominio
3. **Job run log** (`maintenance.job_run_log`) -- esecuzioni job pgAgent

Il backend espone 6 endpoint GET paginati in `apps/core/api/views_tracciamento.py`, orchestrati dal service `apps/core/services/tracciamento_service.py` che delega a due repository:

- `DbopsRepository` (esteso) -- audit log + task registry
- `MaintenanceRepository` (nuovo) -- job run log

Architettura a strati: View -> Service (validazione) -> Repository (SQL) -> DB.

## Endpoint

Tutti gli endpoint richiedono autenticazione JWT e sono sotto `/api/v1/core/tracciamento/`.

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
| `page`          | int    | No           | 1       | Pagina (>= 1)                               |
| `page_size`     | int    | No           | 50      | Righe per pagina (1-200)                    |

### Domini Task

```http
GET /api/v1/core/tracciamento/domini-task/
```

| Parametro     | Tipo | Obbligatorio | Default | Note                          |
|---------------|------|:------------:|---------|-------------------------------|
| `attivo_only` | bool | No           | true    | Filtra solo domini attivi     |
| `search`      | str  | No           | --      | ILIKE su codice/descrizione   |
| `page`        | int  | No           | 1       | Pagina                        |
| `page_size`   | int  | No           | 50      | Righe per pagina (1-200)      |

### Task Registry

```http
GET /api/v1/core/tracciamento/task-registry/
```

| Parametro     | Tipo   | Obbligatorio | Default | Note                                |
|---------------|--------|:------------:|---------|-------------------------------------|
| `dominio`     | string | No           | --      | Filtra per codice dominio (es. FATTURAZIONE) |
| `attivo_only` | bool   | No           | true    | Filtra solo task attivi             |
| `search`      | str    | No           | --      | ILIKE su task_code/descrizione      |
| `page`        | int    | No           | 1       | Pagina                              |
| `page_size`   | int    | No           | 100     | Righe per pagina (1-200)            |

### Task Implementations

```http
GET /api/v1/core/tracciamento/task-implementations/
```

| Parametro     | Tipo   | Obbligatorio | Default | Note                          |
|---------------|--------|:------------:|---------|-------------------------------|
| `task_code`   | string | No           | --      | Filtra per task_code          |
| `dominio`     | string | No           | --      | Filtra per codice dominio     |
| `attivo_only` | bool   | No           | true    | Filtra solo impl attive       |
| `page`        | int    | No           | 1       | Pagina                        |
| `page_size`   | int    | No           | 100     | Righe per pagina (1-200)      |

### Job Runs

```http
GET /api/v1/core/tracciamento/job-runs/
```

| Parametro   | Tipo   | Obbligatorio | Default | Note                          |
|-------------|--------|:------------:|---------|-------------------------------|
| `jobname`   | string | No           | --      | Filtra per jobname esatto     |
| `ok`        | bool   | No           | --      | Filtra per esito              |
| `date_from` | string | No           | --      | Data inizio (YYYY-MM-DD)      |
| `date_to`   | string | No           | --      | Data fine (YYYY-MM-DD)        |
| `search`    | str    | No           | --      | ILIKE su jobname/stepname/message |
| `page`      | int    | No           | 1       | Pagina                        |
| `page_size` | int    | No           | 50      | Righe per pagina (1-200)      |

### Job Summary

```http
GET /api/v1/core/tracciamento/job-summary/
```

| Parametro   | Tipo | Obbligatorio | Default | Note                    |
|-------------|------|:------------:|---------|-------------------------|
| `page`      | int  | No           | 1       | Pagina                  |
| `page_size` | int  | No           | 50      | Righe per pagina (1-200)|

Restituisce per ogni jobname: `total_runs`, `ok_count`, `fail_count`, `last_run_at`, `last_ok`.

## Output

Tutti gli endpoint restituiscono l'envelope paginato standard:

```json
{
  "data": {
    "count": 42,
    "page": 1,
    "page_size": 50,
    "total_pages": 1,
    "results": [...]
  },
  "meta": {"request_id": "..."}
}
```

## Regole

- Tutti gli endpoint sono in sola lettura (GET).
- Il parametro `status` per audit-log e` validato server-side: solo `SUCCESS`, `FAILED`, `WARNING`.
- La paginazione e` validata: `page >= 1`, `page_size` tra 1 e 200.
- I filtri date usano `>=` per date_from e `<= date_to + 1 giorno` per includere l'intero giorno.
- Gli endpoint search hanno throttling `SearchBurstRateThrottle`.
- Nessun dato viene modificato: il tracciamento runtime (INSERT/UPDATE task_runs) resta nei service di dominio (es. `VenditePipelineRepository`).

## Dipendenze DB

- `dbops.audit_log` -- registro operazioni generiche (indici: `ix_audit_fn_ts`, `ix_audit_status_ts`)
- `dbops.domini_task` -- catalogo domini task
- `dbops.pipeline_task_registry` -- catalogo task per dominio
- `dbops.pipeline_task_registry_impl` -- implementazioni handler
- `maintenance.job_run_log` -- log esecuzioni pgAgent
- `maintenance.fn_run_and_log` -- wrapper standard job (non chiamato dal backend, solo da pgAgent)

## File coinvolti

| Layer      | File                                              |
|------------|---------------------------------------------------|
| Types      | `apps/core/types.py`                              |
| Repository | `apps/core/db/dbops_repository.py` (esteso)       |
| Repository | `apps/core/db/maintenance_repository.py` (nuovo)  |
| Service    | `apps/core/services/tracciamento_service.py`       |
| API        | `apps/core/api/views_tracciamento.py`              |
| URL        | `apps/core/api/urls_v1.py`                         |
| Test       | `apps/core/tests/services/test_tracciamento_service.py` |
| Test       | `apps/core/tests/services/test_tracciamento_repositories.py` |
| Test       | `apps/core/tests/api/test_tracciamento_api.py`     |

## Codici errore

| Codice              | HTTP | Causa                                          |
|---------------------|------|------------------------------------------------|
| `E_CORE_VALIDATION` | 400  | Parametri non validi (status, page, page_size) |
| `E_GENERICO`        | 500  | Errore imprevisto                              |

## Note

- Non servono funzioni/view SQL aggiuntive: le query sono dirette e gli indici DB esistenti coprono i pattern di accesso.
- Se `job-summary` diventa lenta su grossi volumi, valutare una view materializzata `maintenance.vw_job_summary` refreshata dal job di cleanup settimanale.
- I tipi condivisi (`AuditLogRow`, `DominioTaskRow`, `TaskRegistryRow`, `TaskRegistryImplRow`, `JobRunLogRow`) sono in `apps/core/types.py` per riuso cross-dominio.
- Gli helper generici `qp_bool`, `qp_int`, `qp_str`, `paginated_envelope` sono in `apps/core/api/payload_validators.py` e riusabili da qualsiasi endpoint GET.
