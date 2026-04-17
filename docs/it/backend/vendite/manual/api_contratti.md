# API Contratti `vendite.contratti`

## Scopo

CRUD operativo dei contratti commerciali cliente-listino, con sub-entita'
**righe** (`vendite.contratti_righe`) e **utility 1:1**
(`vendite.contratti_utilities`). E' il ponte tra il cliente (BA) e il
listino, e veicola le tre **modalita' pricing v5** (A/B/C):

| Modalita' | `listino_id` | `tipo_variazione_globale` | `contratti_righe` |
|---|---|---|---|
| **A** — listino + variazione globale | NOT NULL | NOT NULL | vuote o override mirati |
| **B** — listino con override | NOT NULL | NULL | righe con `prezzo_unitario` per articoli specifici |
| **C** — interamente negoziato | NULL | NULL | tutte le righe con `prezzo_unitario` NOT NULL |

Riferimento concettuale: [sviluppo-listini-v5.md](/dev/work-in-progress/sviluppo-listini-v5) §5.

## Contesto

- Il **numero contratto** e' generato lato service via
  `script.fn_generate_codice('contratto')` (prefix `CNT`, len 7,
  config in `config.sistema_codici`). NON e' accettato in payload (lock
  via trigger `trgfn_lock_columns('numero', 'CODICE_NON_MODIFICABILE')`).
- Lo **stato iniziale** di ogni contratto e' `DRAFT` (risolto dal service
  via `config.stati_doc_contratti.codice_interno`).
- Le coerenze cross-table (modalita' C senza righe/prezzi all'attivazione,
  tipo/classe utenza per ambito utility, EXCLUDE no-overlap) sono
  enforced dai trigger DB:
  - `trgfn_contratti_guard_modalita_c_activation`
  - `trgfn_contratti_righe_guard_modalita_c`
  - `trgfn_contratti_utilities_guard_tipo_classe`
  - EXCLUDE `ex_contratti_no_overlap` su `(billing_account_id, istanza_utility_id, utility_id, ambito, validita)`.
- Il service `ContrattiService` traduce gli errori `P0001` dei trigger nei
  codici applicativi documentati piu' sotto.

## Input

### Lista contratti `GET /api/v1/vendite/contratti/`

| Parametro | Tipo | Descrizione |
|---|---|---|
| `search` | string | ILIKE su `numero` contratto e `ragione_sociale` BA |
| `billing_account_id` | int | Filtro cliente |
| `stato_doc_contratto_id` | int | Filtro stato (FK `config.stati_doc_contratti`) |
| `utility_id` | int | Filtro utility |
| `ambito` | string | `COMMODITY` o `COMMERCIO` |
| `listino_id` | int | Filtro listino di pricing (debug modalita' A/B vs C) |
| `data_da` | ISO date | Filtro su `validita` daterange. **Default: 1 gennaio anno-1** (regola standard liste con date) |
| `data_a` | ISO date | Filtro su `validita` daterange |
| `limit` | int | Default 25, max 200 |
| `offset` | int | Default 0 |
| `order_by` | string | `numero` `data` `valido_dal` `valido_al` `ba_ragione_sociale` `stato_codice` `categoria_cliente_snapshot_codice` `data_insert` `data_update` |
| `order_dir` | string | `asc` (default) o `desc` |

### Create testata `POST /api/v1/vendite/contratti/`

```json
{
  "billing_account_id": 10,
  "istanza_utility_id": 20,
  "utility_id": 3,
  "ambito": "COMMODITY",
  "valido_dal": "2026-01-01",
  "valido_al": "2026-12-31",
  "data": "2026-01-01",
  "listino_id": 100,
  "tipo_variazione_globale": "PERCENTUALE",
  "valore_variazione_globale": "10",
  "meta": {"note": "Cliente Gold"},
  "utility": {
    "tipo_utenza_id": 2,
    "classe_utenza_id": 7,
    "param_2_txt": "POD-XYZ"
  }
}
```

Note:

- `numero` e `stato_doc_contratto_id` **NON vanno mai inviati** in
  payload (rifiutati con `E_VENDITE_VALIDATION`).
- `utility` (sub-payload opzionale): se presente, crea la riga utility 1:1
  nello stesso round-trip. `istanza_utility_id` e `utility_id` sono
  derivati dalla testata, NON dal sub-payload.
- Modalita' C → omettere `listino_id`/`tipo_variazione_globale`/
  `valore_variazione_globale`. Variazione presente con `listino_id` NULL
  fallisce pre-DB con `E_VENDITE_VALIDATION` ("modalita' C: tipo/valore
  variazione globale devono essere NULL").

### Update testata `PATCH /api/v1/vendite/contratti/<id>/`

Solo campi mutabili: `ambito`, `valido_dal`, `valido_al`,
`parent_contratto_id`, `data`, `listino_id`, `tipo_variazione_globale`,
`valore_variazione_globale`, `categoria_cliente_id_snapshot`, `meta`.
Identificativi (numero, BA, istanza, utility, stato) sono immutabili.
`categoria_cliente_id_snapshot` e' modificabile **solo in stato DRAFT**;
in altri stati il service lo rifiuta con `E_VENDITE_VALIDATION`.

### Cambio stato `POST /api/v1/vendite/contratti/<id>/cambia-stato/`

```json
{"codice_interno": "ATTIVO"}
```

Stati ammessi: `DRAFT`, `ATTIVO`, `SOSPESO`, `CESSATO` (FK
`config.stati_doc_contratti`). L'attivazione di un contratto in
modalita' C senza righe complete fallisce fail-fast lato DB →
codici applicativi `E_CONTRATTO_MODALITA_C_SENZA_RIGHE` o
`E_CONTRATTO_MODALITA_C_RIGHE_INCOMPLETE`.

### Righe `POST /api/v1/vendite/contratti/<id>/righe/`

```json
{
  "articolo_id": "00000000-0000-0000-0000-000000000001",
  "tipo_erogazione": "CANONE",
  "prezzo_unitario": "25.50",
  "quantita_fissa": "1",
  "uom_operativa_id": 5,
  "ordine": 10
}
```

`PATCH /api/v1/vendite/contratti/<id>/righe/<riga_id>/` aggiorna i campi
mutabili; `articolo_id` immutabile.

`DELETE /api/v1/vendite/contratti/<id>/righe/<riga_id>/` hard-delete
(bloccato dal trigger se note collegate).

### Utility 1:1 `POST /api/v1/vendite/contratti/<id>/utility/`

```json
{
  "tipo_utenza_id": 2,
  "classe_utenza_id": 7,
  "istanza_dati_precontrattuali_id": 88,
  "param_1_num": "1500",
  "param_2_txt": "POD-XYZ",
  "meta": {}
}
```

`istanza_utility_id` e `utility_id` sono derivati dalla testata; non si
passano nel payload (rifiutati). `PATCH` aggiorna solo i campi mutabili.

## Output

Tutte le risposte usano l'envelope `success_response`:

```json
{"data": { ... }, "meta": {"timestamp": "2026-04-15T10:00:00Z"}}
```

Il dettaglio (`GET /<id>/`) include:

```json
{
  "data": {
    "id": 1, "numero": "CNT0000001", "billing_account_id": 10,
    "ba_ragione_sociale": "...", "utility_id": 3, "utility_codice": "GAS",
    "stato_codice": "DRAFT", "stato_descrizione": "Bozza",
    "listino_id": 100, "listino_codice": "LST-GAS-2026",
    "tipo_variazione_globale": "PERCENTUALE", "valore_variazione_globale": "10",
    "categoria_cliente_id_snapshot": 3,
    "categoria_cliente_snapshot_codice": "GOLD",
    "categoria_cliente_snapshot_descrizione": "Cliente gold",
    "valido_dal": "2026-01-01", "valido_al": "2026-12-31",
    "utility": {"id": 5, "tipo_utenza_codice": "DOM", ...},
    "righe": [{"id": 99, "articolo_codice": "ART-001", "prezzo_unitario": "25.50"}, ...]
  }
}
```

## Regole

1. Numero contratto generato dal service (mai in payload).
2. Stato iniziale DRAFT; transizioni via endpoint dedicato.
3. Identificativi (BA, istanza, utility) immutabili in update — per
   cambiarli si crea un nuovo contratto.
4. Modalita' C valida a livello DB solo se tutte le righe attive hanno
   `prezzo_unitario`; il guard si arma sull'attivazione e su INSERT/UPDATE
   righe quando il contratto e' gia' ATTIVO.
5. Tipo/classe utenza obbligatori per utility con dimensione (es. GAS,
   EE), vietati per utility commercio (Base). Coerenza
   `classi_utenze.tipo_utenza_id = contratti_utilities.tipo_utenza_id`
   imposta dal trigger DB.
6. EXCLUDE no-overlap: un solo contratto attivo per
   `(BA, istanza_utility, utility, ambito)` su validita' sovrapposta.
7. `categoria_cliente_id_snapshot` e' congelato alla creazione del
   contratto (dal trigger DB, che lo popola dal BA). Rappresenta la
   categoria commerciale del cliente al momento della stipula. Non e'
   modificabile in update. In risposta vengono esposti anche
   `categoria_cliente_snapshot_codice` e
   `categoria_cliente_snapshot_descrizione` (JOIN display).

## Codici errore

| Codice | HTTP | Origine | Trigger DB |
|---|---|---|---|
| `E_VENDITE_VALIDATION` | 400 | Service (struttura/coerenza modalita') | — |
| `E_VENDITE_NOT_FOUND` | 404 | Service | — |
| `E_VENDITE_DUPLICATO` | 400 | UNIQUE `uq_contratti_numero` o `uq_contratti_utilities_contratto_id` | — |
| `E_VENDITE_FK` | 400 | FK su BA/istanza/utility/listino/parent/stato/articolo/UoM/tipo/classe utenza/categoria cliente snapshot | — |
| `E_VENDITE_CONTRATTO_OVERLAP` | 409 | EXCLUDE `ex_contratti_no_overlap` | — |
| `E_CONTRATTO_MODALITA_C_SENZA_RIGHE` | 400 | DB P0001 | `trgfn_contratti_guard_modalita_c_activation` |
| `E_CONTRATTO_MODALITA_C_RIGHE_INCOMPLETE` | 400 | DB P0001 | `trgfn_contratti_guard_modalita_c_activation` |
| `E_CONTRATTO_MODALITA_C_RIGA_SENZA_PREZZO` | 400 | DB P0001 | `trgfn_contratti_righe_guard_modalita_c` |
| `E_CONTRATTO_UTILITY_TIPO_CLASSE_OBBLIGATORI` | 400 | DB P0001 | `trgfn_contratti_utilities_guard_tipo_classe` |
| `E_CONTRATTO_CLASSE_TIPO_INCOERENTE` | 400 | DB P0001 | `trgfn_contratti_utilities_guard_tipo_classe` |
| `E_CONTRATTO_UTILITY_SENZA_DIMENSIONE_TIPO_CLASSE_VIETATI` | 400 | DB P0001 | `trgfn_contratti_utilities_guard_tipo_classe` |

## Dipendenze DB

Tabelle: `vendite.contratti`, `vendite.contratti_righe`,
`vendite.contratti_utilities`. Funzioni: `script.fn_generate_codice`.
Trigger autoritativi: come da tabella codici errore. Stati gestiti via
`config.stati_doc_contratti` (DRAFT/ATTIVO/SOSPESO/CESSATO).
