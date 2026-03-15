# API lotto_task_runs (Django)

## Scopo

Esporre via HTTP i task run runtime di un lotto per monitoraggio operativo e diagnostica pipeline.

## Contesto

Endpoint di consultazione che invoca `fn_get_lotto_task_runs` in `apps/vendite/services/pipeline_service.py`,
il quale legge dalla tabella `vendite.fatturazione_lotti_task_runs` tramite `VenditePipelineRepository`.

View in `apps/vendite/api/views.py`:

- `ApiLottoTaskRuns`
- `ApiLottoTaskRuns`

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/vendite/lotti/{lotto_id}/task-runs/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Path params: `lotto_id` (int)
- Query params:
  - `limit` (int, opzionale): numero massimo di task run restituiti (default 100, max 500)

## Output

- `200`:

```json
{
  "data": {
    "lotto_id": 42,
    "count": 3,
    "task_runs": [
      {
        "id": 1,
        "lotto_id": 42,
        "pipeline_id": 5,
        "stato_doc_fiscale_id": 2,
        "task_code": "GENERA_FATTURE",
        "fase": "MAIN",
        "tentativo": 1,
        "task_stato": "OK",
        "started_at": "2026-02-20T10:00:00",
        "ended_at": "2026-02-20T10:00:05",
        "error_code": null,
        "error_message": null,
        "meta": {}
      }
    ]
  },
  "meta": { ... }
}
```

- `400`: `lotto_id` non valido, o `limit` fuori intervallo 1-500
- `500`: errore applicativo gestito dal middleware

## Regole

- `lotto_id` obbligatorio e > 0 (validato dal servizio con `ErrorManager.require`).
- `limit` deve essere compreso tra 1 e 500 (default 100); il repository applica `max(1, min(limit, 500))` come guard aggiuntivo.
- I task run sono filtrati per `attivo = true` e ordinati per `started_at DESC, id DESC`.
- `started_at` e `ended_at` sono restituiti in formato ISO 8601 (o `null`).
- Endpoint di sola lettura: nessun `Idempotency-Key` richiesto.
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `vendite.fatturazione_lotti_task_runs` (tabella sorgente)
- `apps.vendite.db.pipeline_repository.VenditePipelineRepository.list_lotto_task_runs`

## Note di migrazione

- Endpoint introdotto con il runtime task tracing (`vendite.fatturazione_lotti_task_runs`).
- Utile per diagnostica step pipeline e verifica esiti task per lotto specifico.
