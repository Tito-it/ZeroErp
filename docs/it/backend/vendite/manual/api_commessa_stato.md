# API commessa_stato (Django)

## Scopo

Esporre via HTTP lo stato e i contatori aggregati di una singola commessa,
per dashboard e monitoraggio avanzamento.

## Contesto

Endpoint applicativo che invoca il servizio Python `fn_get_commessa_stato`
(`apps.vendite.services.commesse_service`), il quale legge i contatori da
`CommesseRepository.get_commessa_stato()`.

View: `ApiCommessaStato` `ApiCommessaStato` (`apps.vendite.api.views`).

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/vendite/commesse/<commessa_id>/stato/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Parametri path:
  - `commessa_id` (int) — ID della commessa

## Output

- `200`: commessa trovata

```json
{
  "data": {
    "commessa_id": 1,
    "stato_codice_interno": "PRONTA_FATTURAZIONE",
    "total_attivita": 10,
    "total_approvate": 8,
    "total_emesse": 5
  },
  "meta": { ... }
}
```

`stato_codice_interno` (2026-06-10): codice stato della testata
(`vendite.stati_commessa.codice_interno`) — permette a FE/smoke di verificare
l'esito del ponte di emittibilità post-push senza una seconda chiamata.

- `400`: `commessa_id` non valido (`E_COMMESSA_VALIDATION`)
- `404`: commessa non trovata (`E_COMMESSA_NOT_FOUND`)

## Regole

- Endpoint read-only, nessuna `Idempotency-Key` richiesta.
- Endpoint v1 richiede JWT.
- `commessa_id` deve essere > 0, altrimenti errore di validazione.
- I contatori (`total_attivita`, `total_approvate`, `total_emesse`) sono calcolati
  nel DB in un unico round-trip.
- Implementa il pattern standard `success_response` / `exception_to_error_response`.

## Dipendenze DB

- `vendite.fn_get_commessa_stato` (funzione DB che calcola i contatori)
- `vendite.commesse` (tabella principale)
- `vendite.commesse_attivita` (per aggregazioni)
