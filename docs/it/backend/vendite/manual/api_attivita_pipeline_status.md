# API attivita_pipeline_status (Django)

## Scopo

Esporre via HTTP lo stato corrente della pipeline attivita fatturabili di un lotto,
con riepilogo aggregato per branch.

## Contesto

Endpoint di consultazione che invoca `fn_get_attivita_pipeline_status` in
`apps/vendite/services/attivita_pipeline_service.py`.

View in `apps/vendite/api/views.py`:

- `ApiAttivitaPipelineStatus`
- `ApiAttivitaPipelineStatusV1`

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/vendite/attivita_fatturabili/pipeline/{lotto_id}/status/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Path params: `lotto_id` (int)

## Output

- `200`:

```json
{
  "data": {
    "lotto_id": 10,
    "stato_lotto": "COMPLETATO",
    "stato_operativo": "APERTO",
    "branch_summary": {
      "DEFAULT": {
        "COMPLETATO": 3
      },
      "PREVENTIVI": {
        "COMPLETATO": 2,
        "ERRORE": 1
      }
    }
  },
  "meta": { ... }
}
```

- `400`: `lotto_id` non valido o <= 0 (`E_ATTIVITA_VALIDATION`)
- `404`: lotto non trovato (`E_ATTIVITA_LOTTO_NOT_FOUND`)

## Regole

- `lotto_id` obbligatorio e > 0 (validato con `ErrorManager.require`).
- `stato_lotto` — stato tecnico della pipeline: `DRAFT` | `IN_ESECUZIONE` | `COMPLETATO` | `ERRORE`.
- `stato_operativo` — stato business del lotto: `APERTO` | `CHIUSO` | `ANNULLATO`.
- `branch_summary` — contatori task run aggregati per `branch_code` e `task_stato`.
  - Derivato dai task run in `attivita_fatturabili_lotti_task_runs` (fino a 500 righe).
  - Chiavi del sommario: valori di `task_stato` presenti (`IN_ESECUZIONE`, `COMPLETATO`, `ERRORE`).
- Endpoint di sola lettura: nessun `Idempotency-Key` richiesto.
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `vendite.attivita_fatturabili_lotti` — `stato_lotto` e `stato_operativo`
- `vendite.fn_list_attivita_lotto_task_runs` — task run sorgente per `branch_summary`
- `apps.vendite.db.attivita_pipeline_repository.AttivitaPipelineRepository.get_lotto_attivita_full_stato`
- `apps.vendite.db.attivita_pipeline_repository.AttivitaPipelineRepository.list_attivita_task_runs`
