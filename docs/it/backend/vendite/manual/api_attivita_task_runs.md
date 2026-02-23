# API attivita_task_runs (Django)

## Scopo

Esporre via HTTP i task run runtime del lotto attivita fatturabili per monitoraggio
operativo e diagnostica pipeline.

## Contesto

Endpoint di consultazione che invoca `fn_get_attivita_task_runs` in
`apps/vendite/services/attivita_pipeline_service.py`, il quale legge da
`vendite.attivita_fatturabili_lotti_task_runs` tramite `AttivitaPipelineRepository`.

View in `apps/vendite/api/views.py`:

- `ApiAttivitaTaskRuns`
- `ApiAttivitaTaskRunsV1`

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/vendite/attivita_fatturabili/pipeline/{lotto_id}/task-runs/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Path params: `lotto_id` (int)
- Query params:
  - `limit` (int, opzionale): numero massimo di task run restituiti (default 100, max 500)
  - `branch_code` (string, opzionale): filtra i task run per branch (es. `DEFAULT`, `PREVENTIVI`)

## Output

- `200`:

```json
{
  "data": {
    "lotto_id": 10,
    "count": 2,
    "task_runs": [
      {
        "id": 1,
        "lotto_attivita_id": 10,
        "pipeline_id": 1,
        "sorgente_tipo_id": 1,
        "branch_code": "DEFAULT",
        "task_code": "acquisisci_preventivi",
        "fase": "Acquisizione",
        "tentativo": 1,
        "task_stato": "COMPLETATO",
        "block_scope": "BRANCH",
        "depends_on": [],
        "started_at": "2026-02-23T10:00:00",
        "ended_at": "2026-02-23T10:00:02",
        "error_code": null,
        "error_message": null,
        "meta": {}
      }
    ]
  },
  "meta": { ... }
}
```

- `400`: `lotto_id` non valido, o `limit` fuori intervallo 1-500 (`E_ATTIVITA_VALIDATION`)

## Regole

- `lotto_id` obbligatorio e > 0 (validato con `ErrorManager.require`).
- `limit` deve essere compreso tra 1 e 500 (default 100); il repository applica `max(1, min(limit, 500))` come guard aggiuntivo.
- `branch_code` passato direttamente a `list_attivita_task_runs`; se omesso, restituisce tutti i branch.
- `started_at` e `ended_at` in formato ISO 8601 (o `null`).
- `block_scope` — `BRANCH` o `GLOBAL` — indica la politica di blocco applicata al task run.
- `depends_on` — lista di `task_code` da cui questo task dipende (da configurazione policy).
- Endpoint di sola lettura: nessun `Idempotency-Key` richiesto.
- Endpoint v1 richiede JWT.

## Differenze rispetto a `api_lotto_task_runs`

| Campo              | Lotto (`lotti_task_runs`)         | Attivita (`attivita_lotti_task_runs`) |
|--------------------|-----------------------------------|---------------------------------------|
| FK principale      | `lotto_id`                        | `lotto_attivita_id`                   |
| Step key           | `stato_doc_fiscale_id` (int)      | `task_code` (varchar)                 |
| Branch visibility  | assente                           | `branch_code` per ogni task run       |
| Block scope        | assente                           | `block_scope` (`BRANCH`\|`GLOBAL`)    |
| Filtro branch      | non supportato                    | query param `branch_code`             |

## Dipendenze DB

- `vendite.attivita_fatturabili_lotti_task_runs` (tabella sorgente)
- `vendite.fn_list_attivita_lotto_task_runs` (funzione DB di lettura)
- `apps.vendite.db.attivita_pipeline_repository.AttivitaPipelineRepository.list_attivita_task_runs`
