# API commesse_push_log (Django)

## Scopo

Esporre via HTTP il dettaglio di un singolo push log commesse, per consultazione
operativa e diagnostica delle esecuzioni push.

## Contesto

Endpoint applicativo che invoca il servizio Python `fn_get_commesse_push_log`
(`apps.vendite.services.commesse_service`), il quale legge il record da
`CommesseRepository.get_push_log()` con una `SELECT` diretta su
`vendite.commesse_push_log` (nessuna funzione DB).

View: `ApiCommessePushLog` `ApiCommessePushLog` (`apps.vendite.api.views`).

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/vendite/commesse/push/<push_log_id>/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Parametri path:
  - `push_log_id` (int) — ID del push log da consultare

## Output

- `200`: push log trovato

```json
{
  "data": {
    "id": 5,
    "run_at": "2026-02-26T10:00:00",
    "dry_run": false,
    "source_types": ["PREVENTIVO", "ORDINE_VENDITA"],
    "risultato": { "HandlerPreventivi": { "created": 1 } },
    "stato": "COMPLETATO",
    "durata_ms": 100
  },
  "meta": { ... }
}
```

- `400`: `push_log_id` non valido (`E_COMMESSA_VALIDATION`)
- `404`: push log non trovato (`E_COMMESSA_PUSH_LOG_NOT_FOUND`)

## Regole

- Endpoint read-only, nessuna `Idempotency-Key` richiesta.
- Endpoint v1 richiede JWT.
- `push_log_id` deve essere > 0, altrimenti errore di validazione.
- Implementa il pattern standard `success_response` / `exception_to_error_response`.

## Dipendenze DB

- `vendite.commesse_push_log` (tabella consultata)
