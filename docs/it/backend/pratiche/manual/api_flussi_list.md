# API flussi_list (Django)

## Scopo

Esporre via HTTP la lista e la creazione dei flussi di una pratica.

## Contesto

GET e' la lista a catalogo `pratiche.flussi` (`lista_codice` della view `ApiPraticaFlussiList`): paginata, ordinabile e ricercabile, servita da `PraticheRepository.list_flussi_pagina`. POST delega a `pratiche_service.crea_flusso` che risolve lo stato iniziale DA_ESEGUIRE. Il trigger DB `trgfn_flussi_guard_prerequisiti` valida automaticamente i prerequisiti all'INSERT.

## Input

### GET — Lista flussi

- Metodo: `GET`
- Path canonico: `/api/v1/pratiche/<pratica_id>/flussi/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Parametri di query (contratto di lista standard, lista a catalogo `pratiche.flussi`):

| Parametro | Tipo | Descrizione |
|---|---|---|
| `search` | string | Ricerca libera sulle colonne accese a catalogo (`template_flusso_descrizione`); sotto la soglia della lista non filtra |
| `limit` / `offset` | integer | Paginazione (default 25, massimo 200) |
| `order_by` | string | Whitelist `FLUSSI_ORDER_COLS`: `sequenza`, `template_flusso_descrizione`, `stato_descrizione`, `esito_descrizione`, `data_scadenza`, `risorsa_umana_display`, `unita_organizzativa_descrizione`, `data_insert`; fuori whitelist = default |
| `order_dir` | string | `asc` / `desc`; assente = ASC, DESC sulle date (`data_scadenza`, `data_insert`) |
| `emittente_fiscale_id` | integer | Emittente (PK) della pratica aperta — `lista_emittente_param` della view: scioglie il cancello di perimetro per chi ha piu' emittenti nello scope. **Non filtra**: le righe le decide la pratica del path, sotto la sua RLS |

Senza ordinamento: `sequenza` ASC, spareggio su `id`.

### POST — Creazione flusso

- Metodo: `POST`
- Path canonico: `/api/v1/pratiche/<pratica_id>/flussi/`
- Header: `Content-Type: application/json`, `Authorization: Bearer <access_token>`
- Query: `emittente_fiscale_id` (integer, opzionale) — stesso parametro del GET.
  Il cancello di perimetro della lista vale per **ogni metodo** della rotta e
  legge solo la query: il FE lo passa anche in creazione
  (`pratiche-api.js::createFlusso(praticaId, payload, params)`), altrimenti chi
  vede piu' emittenti (il super admin su «Tutti») prende 422.
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
    "count": 1,
    "page": 1,
    "page_size": 25,
    "total_pages": 1,
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

- `422` (GET e POST): `E_UI_LISTA_EMITTENTE_DA_SCEGLIERE` — cancello di
  perimetro della lista: l'utente ha piu' emittenti nello scope e la richiesta
  non porta `emittente_fiscale_id` in query.
- `400`: `pratica_id` non valido (`E_INVALID_ID`), JSON non valido
- `409`: **prerequisiti non soddisfatti** (`E_PRATICHE_PREREQUISITI_NON_SODDISFATTI`,
  catalogo DB id 300): il flusso non e' ancora eseguibile, mancano i prerequisiti
  del template. Guard `trgfn_flussi_guard_prerequisiti`; messaggio parlante con
  l'elenco dei template mancanti.
- `401`: JWT mancante o non valido
- `409`: **flusso non ripetibile** (`E_PRATICHE_FLUSSO_NON_RIPETIBILE`, catalogo
  DB id 483, workflow v2 D3): la regola `template_flussi.ripetibilita` vieta
  una nuova istanza — `MAI` = esiste gia' un'istanza non annullata;
  `SE_NON_POSITIVO` = l'ultima istanza (`MAX(id)`) e' ancora aperta oppure
  chiusa con esito `POSITIVO`. `SEMPRE` non blocca mai.
- `409`: **pratica terminale** (`E_PRATICHE_TERMINALE_NUOVO_FLUSSO_BLOCCATO`,
  catalogo DB id 490): non si possono creare flussi su una pratica in stato
  terminale (`CHIUSA`/`ANNULLATA`). Guard `trg_flussi_a10_guard_pratica_terminale_ins_upd`.

## Regole

- GET (dal 2026-09-27): lista a catalogo `pratiche.flussi` con envelope
  paginato (`count`/`page`/`page_size`/`total_pages`/`results`); default
  `sequenza ASC, id ASC` (la posizione del flusso nella pratica). Il conteggio
  usa lo stesso FROM+JOIN della pagina: il JOIN su `pratiche.pratiche` (con
  RLS) resta anche nel `COUNT`, perche' `pratiche.flussi` non ha RLS propria.
- GET (2026-06-15): ogni riga espone, oltre ai display fields, il contesto
  data-driven per la UI: `template_azione_ui_key` (catalogo `pratiche.azioni_ui` —
  attività/drawer di dominio apribile dal flusso; `null` se nessuna) e il contesto
  cliente della pratica `pratica_istanza_utility_id` + `pratica_billing_account_id`
  (dal 2026-10-08 la colonna `billing_account_id` della pratica, D-9 di
  brief-db-istanza-nasce-col-ba; `null` per pratiche di altri ruoli, interne o con la
  sola istanza).
  Alimentano l'apertura del documento dal flusso (eredità+lock cliente/istanza).
- POST: `pratica_id` deve essere > 0.
- POST (2026-06-14): `template_flusso_id` e' **obbligatorio** (> 0) — guard
  fail-fast `E_FLUSSO_VALIDATION` nel service. Chiude il path morto del vecchio
  "flusso generico" senza template (rimosso dal FE). I read-path
  (`verifica_prerequisiti`, `canali`) restano tolleranti ai flussi legacy con
  `template_flusso_id` NULL eventualmente ancora presenti a DB.
- POST: lo stato iniziale `DA_ESEGUIRE` viene risolto da `config.stati_flussi_pratiche`.
- POST: il trigger DB `trgfn_flussi_guard_prerequisiti` verifica che tutti i prerequisiti del template siano soddisfatti; in caso contrario l'INSERT fallisce e il service traduce l'errore nel codice parlante `E_PRATICHE_PREREQUISITI_NON_SODDISFATTI` (id 300, HTTP 409) via marker.
- POST (2026-06-12, D3): il guard `trg_flussi_a10_guard_ripetibilita_ins`
  applica la regola di ripetibilita' del template; il service traduce
  l'errore DB nel codice parlante 483 via marker sul messaggio (vedi
  `pratiche_service._KNOWN_DB_ERROR_MARKERS`). Il FE decide se proporre
  "Ripeti" dal campo `ripetibile_adesso` del percorso (vedi
  [api_percorso](api_percorso.md)).
- POST (2026-06-14): il guard `trg_flussi_a10_guard_pratica_terminale_ins_upd`
  blocca la creazione di flussi su pratica terminale (`CHIUSA`/`ANNULLATA`); il
  service traduce l'errore nel codice parlante `E_PRATICHE_TERMINALE_NUOVO_FLUSSO_BLOCCATO`
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
