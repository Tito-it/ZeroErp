# API pratica_sospendi (Django)

## Scopo

Esporre via HTTP la sospensione di una pratica con motivo obbligatorio, data/ora di sospensione opzionale (anche retroattiva) e data di riattivazione prevista opzionale.

## Contesto

Endpoint di scrittura che delega a `pratiche_service.sospendi_pratica`. Il servizio verifica che non esista gia' una sospensione attiva sulla pratica, cambia lo stato a SOSPESA e inserisce il record in `pratiche.sospensioni`. I trigger DB propagano la sospensione ai flussi attivi e registrano nel giornale.

`data_inizio` consente di registrare a posteriori una sospensione realmente avvenuta in un momento passato. Se assente, il DB usa `NOW()`. La difesa sulle date e' a DB (DB-first): l'EXCLUDE `ex_sospensioni_no_overlap` rifiuta i periodi sovrapposti sullo stesso scope (pratica intera o singolo flusso), il guard `trg_sospensioni_a10_guard_data_non_futura` rifiuta le date nel futuro (tolleranza 2 minuti).

## Input

- Metodo: `POST`
- Path canonico: `/api/v1/pratiche/<pratica_id>/sospendi/`
- Header: `Content-Type: application/json`, `Authorization: Bearer <access_token>`
- Body:
  - `motivo` (string, **obbligatorio**) — motivazione della sospensione
  - `data_inizio` (string, opzionale) — data/ora ISO 8601 timestamptz (es. `2026-06-20T09:30:00Z`) della sospensione effettiva, anche retroattiva. Default DB `NOW()` se assente/nulla. ⛔ **L'offset è obbligatorio** (`Z` o `+02:00`): senza, `400 E_VALIDATION_INPUT` (`…_senza_offset`; dal 2026-10-09, `payload_validators.optional_istante`) — PostgreSQL leggerebbe l'ora nel fuso della sessione.
  - `data_riattivazione_prevista` (string, opzionale) — data ISO `YYYY-MM-DD` di riattivazione automatica prevista (puo' essere nel futuro)

## Output

### 200:
```json
{ "data": { "sospensione_id": 100, "status": "ok" } }
```

- `400`: motivo vuoto (`E_PRATICA_VALIDATION`), pratica gia' sospesa (`E_PRATICA_VALIDATION`), `pratica_id` non valido (`E_INVALID_ID`)
- `401`: JWT mancante o non valido
- `409`: sospensione con periodo sovrapposto sullo stesso scope (`E_SOSPENSIONE_OVERLAP`); transizione di stato non ammessa (`E_PRATICHE_TRANSIZIONE_NON_AMMESSA`)
- `422`: `data_inizio` nel futuro (`E_SOSPENSIONE_DATA_FUTURA`)

## Regole

- `pratica_id` deve essere > 0.
- `motivo` non puo' essere vuoto o solo spazi.
- Non puo' esistere una sospensione attiva (data_fine IS NULL) sulla stessa pratica.
- `data_inizio` non puo' essere nel futuro (guard DB a10, tolleranza 2 min); se assente il DB usa `NOW()`.
- Il periodo della sospensione non puo' sovrapporsi ad altre sospensioni dello stesso scope (EXCLUDE DB). Pratica e flusso sono assi indipendenti: una sospensione di pratica e una di flusso possono coesistere.
- Il trigger DB valida la transizione di stato verso SOSPESA.
- Il trigger DB propaga la sospensione ai flussi con stato IN_CORSO.
- Wrappato in `@transaction.atomic()`: errore DB → rollback completo (incluso il cambio stato).
- Mapping errori: `IntegrityError` su `ex_sospensioni_no_overlap` → `E_SOSPENSIONE_OVERLAP` (via `map_integrity_error`); `DatabaseError` del guard a10 → `E_SOSPENSIONE_DATA_FUTURA` (via marker `_KNOWN_DB_ERROR_MARKERS`).
- Permission: `sospendi_pratica` (area `pratiche`).
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `pratiche.sospensioni` (INSERT sospensione; `data_inizio = COALESCE(%s::timestamptz, NOW())`)
- vincolo `ex_sospensioni_no_overlap` (EXCLUDE GiST, framework `dbops.automazione_overlap`)
- trigger `trg_sospensioni_a10_guard_data_non_futura` (guard data non futura)
- `pratiche.pratiche` (UPDATE stato_id → SOSPESA)
- `pratiche.flussi` (propagazione sospensione via trigger)
- `pratiche.giornale` (INSERT automatico via trigger)

## Note di migrazione

- La validazione motivo e' centralizzata nel service (non nella view).
- La propagazione ai flussi e' gestita interamente dai trigger DB `z90` (`trgfn_sospensioni_propaga`, `trgfn_sospensioni_giornale_ins`).
- Parametro `data_inizio` aggiunto 2026-06-26 (UI gestione sospensioni con data/ora manuale). Prima la `data_inizio` era sempre `NOW()` hardcoded nel repository; ora e' parametrizzata con default `NOW()` (retro-compatibile).
