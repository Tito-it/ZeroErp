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
- `409`: transizione non in matrice (`E_PRATICHE_TRANSIZIONE_NON_AMMESSA`);
  **chiusura bloccata** (`PRATICHE_CHIUSURA_FLUSSI_OBBLIGATORI_MANCANTI`,
  catalogo DB id 485, workflow v2 D4): la pratica sta andando a `CHIUSA` ma
  esistono template flussi `obbligatorio=true` ancora **percorribili**
  (prerequisiti soddisfatti) e mai completati. Il messaggio elenca i flussi
  mancanti. I rami resi non percorribili dall'esito di un bivio (ramo morto)
  **non** bloccano.
- `500`: stato non trovato in `config.stati_pratiche` (`E_CONFIG_MANCANTE`)

## Regole

- `pratica_id` deve essere > 0.
- `nuovo_stato` non puo' essere vuoto.
- Lo stato viene risolto da `config.stati_pratiche.codice_interno` a `id`; se non trovato → errore.
- Guard chiusura (2026-06-12, D4): la transizione a `CHIUSA` e' validata a DB
  da `trg_pratiche_a10_guard_chiusura_flussi_upd` (su
  `fn_check_chiusura_pratica`); il service traduce l'errore DB nel codice
  parlante 485 via marker sul messaggio (vedi
  `pratiche_service._KNOWN_DB_ERROR_MARKERS`).
- Wrappato in `@transaction.atomic()`.
- Permission: `cambia_stato_pratica` (area `pratiche`).
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `pratiche.pratiche` (UPDATE stato_id)
- `config.stati_pratiche` (risoluzione codice_interno → id)
- `pratiche.trgfn_pratiche_guard_chiusura_flussi` + `fn_check_chiusura_pratica`
  (guard chiusura D4, workflow v2)

## Note di migrazione

- La risoluzione stato avviene esplicitamente prima dell'UPDATE per evitare SET NULL su colonna NOT NULL.
