# API pratica_stato (Django)

## Scopo

Esporre via HTTP il cambio stato di una pratica tramite codice_interno.

## Contesto

Endpoint di scrittura che delega a `pratiche_service.cambia_stato_pratica`. Il servizio risolve il codice_interno dello stato nella tabella `config.stati_pratiche` e aggiorna la FK `stato_id` sulla pratica.

## Input

- Metodo: `POST`
- Path canonico: `/api/v1/pratiche/<pratica_id>/stato/`
- Header: `Content-Type: application/json`, `Authorization: Bearer <access_token>`
- Body:
  - `nuovo_stato` (string, **obbligatorio**) — codice_interno dello stato (es. `APERTA`, `CHIUSA`, `ANNULLATA`)

## Output

### 200:
```json
{ "data": { "status": "ok" } }
```

- `400`: `nuovo_stato` vuoto (`E_PRATICA_VALIDATION`), `pratica_id` non valido (`E_INVALID_ID`)
- `401`: JWT mancante o non valido
- `404`: pratica non trovata (`E_PRATICA_NOT_FOUND`)
- `500`: stato non trovato in `config.stati_pratiche` (`E_CONFIG_MANCANTE`)

## Regole

- `pratica_id` deve essere > 0.
- `nuovo_stato` non puo' essere vuoto.
- Lo stato viene risolto da `config.stati_pratiche.codice_interno` a `id`; se non trovato → errore.
- Wrappato in `@transaction.atomic()`.
- Permission: `cambia_stato_pratica` (area `pratiche`).
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `pratiche.pratiche` (UPDATE stato_id)
- `config.stati_pratiche` (risoluzione codice_interno → id)

## Note di migrazione

- La risoluzione stato avviene esplicitamente prima dell'UPDATE per evitare SET NULL su colonna NOT NULL.
