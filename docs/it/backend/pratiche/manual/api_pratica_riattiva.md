# API pratica_riattiva (Django)

## Scopo

Esporre via HTTP la riattivazione di una pratica sospesa, con data/ora di riattivazione opzionale (anche retroattiva).

## Contesto

Endpoint di scrittura che delega a `pratiche_service.riattiva_pratica`. Il servizio cerca la sospensione attiva (data_fine IS NULL, flusso_id IS NULL), cambia lo stato pratica ad APERTA e chiude la sospensione impostando `data_fine`. Il trigger DB ripristina gli stati dei flussi sospesi e registra nel giornale.

`data_fine` consente di registrare a posteriori il momento effettivo di riattivazione. Se assente, il DB usa `NOW()`. La difesa sulle date e' a DB: il CHECK `chk_sospensioni_data_fine` impone `data_fine > data_inizio`, il guard `a10` rifiuta le date nel futuro (tolleranza 2 minuti).

## Input

- Metodo: `POST`
- Path canonico: `/api/v1/pratiche/<pratica_id>/riattiva/`
- Header: `Content-Type: application/json`, `Authorization: Bearer <access_token>`
- Body:
  - `data_fine` (string, opzionale) — data/ora ISO 8601 timestamptz (es. `2026-06-21T18:00:00Z`) della riattivazione effettiva, anche retroattiva. Default DB `NOW()` se assente/nulla. ⛔ **L'offset è obbligatorio** (`Z` o `+02:00`): senza, `400 E_VALIDATION_INPUT` (`…_senza_offset`; dal 2026-10-09, `payload_validators.optional_istante`) — PostgreSQL leggerebbe l'ora nel fuso della sessione.

## Output

### 200:
```json
{ "data": { "status": "ok" } }
```

- `400`: `pratica_id` non valido (`E_INVALID_ID`), nessuna sospensione attiva (`E_PRATICA_VALIDATION`)
- `401`: JWT mancante o non valido
- `400`: `data_fine` senza offset o illeggibile (`E_VALIDATION_INPUT`)
- `404`: sospensione non trovata o gia' chiusa (`E_SOSPENSIONE_NOT_FOUND`)
- `409`: transizione di stato non ammessa (`E_PRATICHE_TRANSIZIONE_NON_AMMESSA`)
- `422`: `data_fine` nel futuro (`E_SOSPENSIONE_DATA_FUTURA`); `data_fine` anteriore o uguale all'inizio della sospensione (`E_SOSPENSIONE_DATA_FINE`)

## Regole

- `pratica_id` deve essere > 0.
- Deve esistere una sospensione attiva sulla pratica (flusso_id IS NULL, data_fine IS NULL).
- `data_fine` non puo' essere nel futuro (guard DB a10) e deve essere successiva a `data_inizio` (CHECK DB); se assente il DB usa `NOW()`.
- Lo stato pratica torna ad APERTA.
- Il trigger DB ripristina i flussi che erano stati sospesi automaticamente.
- Wrappato in `@transaction.atomic()`.
- Mapping errori: `IntegrityError` su `chk_sospensioni_data_fine` → `E_SOSPENSIONE_DATA_FINE` (via `map_integrity_error`, intercettato PRIMA di `DatabaseError` poiche' ne e' sottoclasse); `DatabaseError` del guard a10 → `E_SOSPENSIONE_DATA_FUTURA`.
- Permission: `riattiva_pratica` (area `pratiche`).
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `pratiche.sospensioni` (UPDATE `data_fine = COALESCE(%s::timestamptz, NOW())` con guard `data_fine IS NULL`)
- CHECK `chk_sospensioni_data_fine` (`data_fine > data_inizio`)
- trigger `trg_sospensioni_a10_guard_data_non_futura` (guard data non futura)
- `pratiche.pratiche` (UPDATE stato_id → APERTA)
- `pratiche.flussi` (ripristino stati via trigger)
- `pratiche.giornale` (INSERT automatico via trigger)

## Note di migrazione

- La chiusura sospensione con guard `data_fine IS NULL` previene doppie chiusure concorrenti.
- Parametro `data_fine` aggiunto 2026-06-26 (UI gestione sospensioni con data/ora manuale). Prima la `data_fine` era sempre `NOW()` hardcoded nel repository; ora e' parametrizzata con default `NOW()` (retro-compatibile).
