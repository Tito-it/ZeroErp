# API lotto_task_runs (Django)

## Scopo

Esporre via HTTP i task run runtime di un lotto per monitoraggio operativo e diagnostica pipeline.

## Contesto

Endpoint di consultazione che invoca `fn_get_lotto_task_runs` in `apps/vendite/services/pipeline_service.py`,
il quale legge dalla tabella `vendite.fatturazione_lotti_task_runs` tramite `VenditePipelineRepository`.

View in `apps/vendite/api/views.py`: `ApiLottoTaskRuns` (lista),
`ApiLottoTaskRunsExport` (export).

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/vendite/lotti/{lotto_id}/task-runs/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Path params: `lotto_id` (int)
- Query params (tutti opzionali):
  - `page_size` (int): righe per pagina, default `100`, max `500`. `limit` è
    accettato come sinonimo (letto solo se `page_size` manca)
  - `offset` (int): default `0`, non negativo
  - `order_by` (string): passato intatto alla funzione DB
    `vendite.fn_list_lotto_task_runs`, che possiede la whitelist
  - `order_dir` (`asc` | `desc`, default `desc`; maiuscole e spazi ammessi)
  - `task_stato` (string, multi-valore: ripetuto o separato da virgole):
    `COMPLETATO` · `ERRORE` · `ANNULLATO`. Il vocabolario lo possiede la funzione
    DB: uno stato che non conosce non aggiunge e non toglie nulla
  - `solo_giro_corrente` (bool): solo l'ultima **passata** della pipeline
    (ancora: l'ultimo `PIPELINE_STARTED`). ⚠️ Passata, non click: un
    `run-until-done` ne incatena più d'una — leggere sempre `esclusi_count`

## Output

- `200`:

```json
{
  "data": {
    "lotto_id": 42,
    "count": 90,
    "page": 1,
    "page_size": 100,
    "total_pages": 1,
    "esclusi_count": 0,
    "results": [
      {
        "id": 1,
        "lotto_id": 42,
        "pipeline_id": 5,
        "stato_doc_fiscale_id": 2,
        "task_code": "GENERA_FATTURE",
        "fase": "MAIN",
        "tentativo": 1,
        "task_stato": "COMPLETATO",
        "started_at": "2026-02-20T10:00:00+01:00",
        "ended_at": "2026-02-20T10:00:05+01:00",
        "error_code": null,
        "error_message": null,
        "meta": {},
        "giro_corrente": true
      }
    ],
    "task_runs": [ "...stesse righe di results..." ]
  },
  "meta": { ... }
}
```

- `count` è il **totale** del perimetro filtrato, non le righe della pagina;
  `esclusi_count` = quante righe i filtri (`task_stato`, `solo_giro_corrente`)
  lasciano fuori. `task_runs` è un alias di `results` tenuto per il consumatore
  storico del drawer.
- `400 E_PIPELINE_VALIDATION`: `lotto_id` ≤ 0, `page_size` fuori 1–500, `offset`
  negativo, `order_dir` non ammessa (un intero non leggibile →
  `E_VALIDATION_INPUT`)
- `404 E_LOTTO_NON_TROVATO`: lotto inesistente o fuori perimetro — la testata si
  legge prima dell'elenco. ⚠️ 2026-10-20: prima `200` con zero righe

## Regole

- `started_at` e `ended_at` sono restituiti in formato ISO 8601 (o `null`).
- Endpoint di sola lettura: nessun `Idempotency-Key` richiesto.
- Endpoint v1 richiede JWT.

## Export

- `GET /api/v1/vendite/lotti/{lotto_id}/task-runs/export/?formato=csv|xlsx`
- Stessi filtri e ordinamento (`order_by`, `order_dir`, `task_stato`,
  `solo_giro_corrente`), senza paginazione; stesso `404`.
- Colonne dal catalogo `vendite.lotto_task_runs`; oltre `EXPORT_MAX_ROWS` →
  `422 E_UI_EXPORT_LIMIT_EXCEEDED`.

## Dipendenze DB

- `vendite.fatturazione_lotti_task_runs` (tabella sorgente), letta da `vendite.fn_list_lotto_task_runs`
- `apps.vendite.db.pipeline_repository.VenditePipelineRepository.list_lotto_task_runs`

## Note di migrazione

- Endpoint introdotto con il runtime task tracing (`vendite.fatturazione_lotti_task_runs`).
- Utile per diagnostica step pipeline e verifica esiti task per lotto specifico.
