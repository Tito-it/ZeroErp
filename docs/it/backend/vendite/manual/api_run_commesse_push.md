# API run_commesse_push (Django)

## Scopo

Esporre via HTTP l'avvio dell'orchestratore push commesse, che sincronizza documenti sorgente
(preventivi, ordini, contratti, DDT, consumi) verso `commesse` e `commesse_attivita`.

## Contesto

Endpoint applicativo che invoca il servizio Python `pr_run_commesse_push`
(`apps.vendite.services.commesse_service`), il quale istanzia `CommessaPushOrchestrator`
con i 5 handler sorgente registrati e ne esegue il metodo `run()`.

View: `ApiRunCommessePush` / `ApiRunCommessePushV1` (`apps.vendite.api.views`).

## Input

- Metodo: `POST`
- Path canonico: `/api/v1/vendite/commesse/push/run/`
- Header richiesto: `Idempotency-Key`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Body JSON (tutti i campi opzionali):
  - `source_types` (list[string]) — filtro sorgenti da processare (es. `["PREVENTIVO", "ORDINE_VENDITA"]`). Se omesso processa tutte le sorgenti registrate.
  - `dry_run` (bool) — `true` = simula senza effetti reali (default `false`)
- `user_run` viene rilevato automaticamente dall'utente JWT autenticato (non inviare nel payload).

## Output

- `200`: esecuzione completata (o skippata per lock occupato)

```json
{
  "data": {
    "stato": "COMPLETATO",
    "dry_run": false,
    "push_log_id": 10,
    "durata_ms": 150,
    "handlers": [
      {
        "handler_name": "HandlerPreventivi",
        "created": 2,
        "updated": 0,
        "skipped": 0,
        "errors": []
      }
    ]
  },
  "meta": { ... }
}
```

- `200` con `stato: "SKIPPED"`: advisory lock occupato, nessuna esecuzione.
- `400`: payload non valido o errore applicativo (`E_COMMESSA_VALIDATION`).

## Regole

- Implementa il pattern standard core `handle_post_json(...)`.
- Endpoint write protetto con obbligo `Idempotency-Key`.
- Endpoint v1 richiede JWT.
- Concorrenza gestita via `pg_try_advisory_lock(hashtext('commesse_push_orchestrator'))`:
  lock occupato → `stato: "SKIPPED"` (HTTP 200, non errore).
- `source_types` filtrano i handler da eseguire; codici non riconosciuti vengono ignorati.
- Il risultato per handler include contatori `created`, `updated`, `skipped` e lista `errors`.

## Dipendenze DB

- `vendite.fn_list_preventivi_da_pushare`
- `vendite.fn_list_ordini_da_pushare`
- `vendite.fn_list_contratti_da_pushare`
- `vendite.fn_list_ddt_da_pushare`
- `vendite.fn_list_consumi_da_pushare`
- `vendite.fn_get_or_create_commessa`
- `vendite.fn_upsert_commessa_attivita`
- `vendite.commesse_push_log` (log esecuzione)
- Advisory lock: `pg_try_advisory_lock(hashtext('commesse_push_orchestrator'))`
