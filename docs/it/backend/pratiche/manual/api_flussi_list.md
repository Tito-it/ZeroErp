# API flussi_list (Django)

## Scopo

Esporre via HTTP la lista e la creazione dei flussi di una pratica.

## Contesto

GET restituisce i flussi ordinati per sequenza dal repository. POST delega a `pratiche_service.crea_flusso` che risolve lo stato iniziale DA_ESEGUIRE. Il trigger DB `trgfn_flussi_guard_prerequisiti` valida automaticamente i prerequisiti all'INSERT.

## Input

### GET — Lista flussi

- Metodo: `GET`
- Path canonico: `/api/v1/pratiche/<pratica_id>/flussi/`
- Header sicurezza: `Authorization: Bearer <access_token>`

### POST — Creazione flusso

- Metodo: `POST`
- Path canonico: `/api/v1/pratiche/<pratica_id>/flussi/`
- Header: `Content-Type: application/json`, `Authorization: Bearer <access_token>`
- Body:
  - `template_flusso_id` (int, **obbligatorio**, > 0) — template flusso del
    percorso. Ogni flusso e' template-driven (workflow v2): il vecchio "flusso
    generico" senza template e' stato rimosso. Assente/non valido →
    `E_FLUSSO_VALIDATION` (400).
  - `risorsa_umana_id` (int, opzionale) — risorsa umana assegnata
  - `unita_organizzativa_id` (int, opzionale) — unita' organizzativa
  - `sequenza` (int, opzionale, default `0`) — ordine esecuzione nel workflow
  - `data_scadenza` (date, opzionale) — scadenza
  - `meta` (dict, opzionale) — metadati JSON

## Output

### GET 200:
```json
{
  "data": {
    "results": [
      {
        "id": 5,
        "pratica_id": 1,
        "template_flusso_id": 10,
        "template_flusso_codice": "PREVENTIVAZIONE",
        "template_azione_ui_key": "APRI_PREVENTIVO",
        "stato_id": 1,
        "sequenza": 0,
        "esito": null,
        "data_scadenza": null,
        "meta": {},
        "pratica_istanza_utility_id": 42,
        "pratica_billing_account_id": 7,
        "data_insert": "2026-03-04T10:00:00+00:00",
        "user_insert": "zeroerp"
      }
    ]
  }
}
```

### POST 200:
```json
{
  "data": {
    "flusso_id": 99,
    "status": "ok"
  }
}
```

- `400`: `pratica_id` non valido (`E_INVALID_ID`), JSON non valido
- `409`: **prerequisiti non soddisfatti** (`PRATICHE_PREREQUISITI_NON_SODDISFATTI`,
  catalogo DB id 300): il flusso non e' ancora eseguibile, mancano i prerequisiti
  del template. Guard `trgfn_flussi_guard_prerequisiti`; messaggio parlante con
  l'elenco dei template mancanti.
- `401`: JWT mancante o non valido
- `409`: **flusso non ripetibile** (`PRATICHE_FLUSSO_NON_RIPETIBILE`, catalogo
  DB id 483, workflow v2 D3): la regola `template_flussi.ripetibilita` vieta
  una nuova istanza — `MAI` = esiste gia' un'istanza non annullata;
  `SE_NON_POSITIVO` = l'ultima istanza (`MAX(id)`) e' ancora aperta oppure
  chiusa con esito `POSITIVO`. `SEMPRE` non blocca mai.
- `409`: **pratica terminale** (`PRATICHE_TERMINALE_NUOVO_FLUSSO_BLOCCATO`,
  catalogo DB id 490): non si possono creare flussi su una pratica in stato
  terminale (`CHIUSA`/`ANNULLATA`). Guard `trg_flussi_a10_guard_pratica_terminale_ins_upd`.

## Regole

- GET: ordinamento `sequenza ASC, id ASC`.
- GET (2026-06-15): ogni riga espone, oltre ai display fields, il contesto
  data-driven per la UI: `template_azione_ui_key` (catalogo `pratiche.azioni_ui` —
  attività/drawer di dominio apribile dal flusso; `null` se nessuna) e il contesto
  cliente della pratica `pratica_istanza_utility_id` + `pratica_billing_account_id`
  (BA derivato via `script.fn_get_billing_account_by_istanza`, `null` se prospect).
  Alimentano l'apertura del documento dal flusso (eredità+lock cliente/istanza).
- POST: `pratica_id` deve essere > 0.
- POST (2026-06-14): `template_flusso_id` e' **obbligatorio** (> 0) — guard
  fail-fast `E_FLUSSO_VALIDATION` nel service. Chiude il path morto del vecchio
  "flusso generico" senza template (rimosso dal FE). I read-path
  (`verifica_prerequisiti`, `canali`) restano tolleranti ai flussi legacy con
  `template_flusso_id` NULL eventualmente ancora presenti a DB.
- POST: lo stato iniziale `DA_ESEGUIRE` viene risolto da `config.stati_flussi_pratiche`.
- POST: il trigger DB `trgfn_flussi_guard_prerequisiti` verifica che tutti i prerequisiti del template siano soddisfatti; in caso contrario l'INSERT fallisce e il service traduce l'errore nel codice parlante `PRATICHE_PREREQUISITI_NON_SODDISFATTI` (id 300, HTTP 409) via marker.
- POST (2026-06-12, D3): il guard `trg_flussi_a10_guard_ripetibilita_ins`
  applica la regola di ripetibilita' del template; il service traduce
  l'errore DB nel codice parlante 483 via marker sul messaggio (vedi
  `pratiche_service._KNOWN_DB_ERROR_MARKERS`). Il FE decide se proporre
  "Ripeti" dal campo `ripetibile_adesso` del percorso (vedi
  [api_percorso](api_percorso.md)).
- POST (2026-06-14): il guard `trg_flussi_a10_guard_pratica_terminale_ins_upd`
  blocca la creazione di flussi su pratica terminale (`CHIUSA`/`ANNULLATA`); il
  service traduce l'errore nel codice parlante `PRATICHE_TERMINALE_NUOVO_FLUSSO_BLOCCATO`
  (id 490) via marker.
- POST: wrappato in `@transaction.atomic()`.
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `pratiche.flussi` (tabella principale)
- `config.stati_flussi_pratiche` (risoluzione stato iniziale)
- `pratiche.fn_guard_prerequisiti_flusso` (trigger su INSERT)

## Note di migrazione

- La validazione prerequisiti e' interamente lato DB (trigger fail-fast).
- (2026-06-14) `template_flusso_id` reso obbligatorio in creazione: non esistono
  piu' flussi "generici" senza template via API. La colonna `pratiche.flussi.template_flusso_id`
  resta NULLABLE a DB per i record legacy; vedi il brief di pulizia dati
  `brief-db-pratiche-flussi-generici-legacy.md` (cleanup + eventuale NOT NULL).
