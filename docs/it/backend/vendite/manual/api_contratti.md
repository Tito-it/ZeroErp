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

### Detail `GET /api/v1/vendite/contratti/<id>/`

Output: testata + `utility` + `righe[]` + **capabilities** spalmate top-level
(Fase 1.B2 refactor frontend vendite, da `script.fn_available_actions_contratto`):

| Campo | Tipo | Significato |
| --- | --- | --- |
| `available_actions[]` | array | Azioni cambio stato disponibili. L'azione `cessa` e' arricchita runtime con `requires_date=true`, `default_date=today`, `min_date=valido_dal` |
| `can_change_state` | bool | `true` se almeno un'azione manuale disponibile |
| `can_edit_testata` | bool | `true` in DRAFT (full whitelist) e in ATTIVO (solo `valido_al`+`meta`); `false` in CESSATO |
| `can_edit_righe` | bool | `true` solo in DRAFT |
| `non_editable_fields[]` | string[] | Whitelist BE coerente con `_CONTRATTO_PATCH_ALLOWED_BY_STATE`. In ATTIVO include tutto eccetto `valido_al`+`meta`; in CESSATO include tutto |

Il frontend (`ContrattoDrawer.vue`) usa `default_date`/`min_date` dell'azione
`cessa` per pre-popolare il dialog di cessazione: niente `new Date()` cablato.

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

### Componenti BoM riga contratto (modello unificato 2026-05-13)

Specchio simmetrico del pattern preventivi (vedi
[api_preventivi.md](api_preventivi.md) §8c-8f). Quando si crea una riga
contratto per un articolo `is_composito=TRUE`, il service invoca
automaticamente `fn_contratto_riga_componenti_init` che popola
`vendite.contratti_righe_componenti` per tutti i figli BoM validi alla
data `valido_dal` del contratto. Il resolver pricing usato e' quello
bundle-aware (`fn_resolve_prezzo_listino_v2` con `p_articolo_padre_contesto`).

Auto-init transazione atomica con `create_riga`: se l'init fallisce
(BoM scaduta, componente obbligatorio senza prezzo, ecc.) tutta la
create rolla back.

Payload `POST /righe/` accetta anche `componenti_overrides` (opzionale,
mappa `{componente_id: prezzo_numeric}`) per pre-impostare prezzi
manuali su componenti specifici al momento della create.

#### Preview componenti `POST /api/v1/vendite/contratti/<id>/righe/preview-componenti/`

```json
{
  "articolo_id": "abc-uuid",
  "uom_operativa_id": 2,
  "quantita": "1"
}
```

Read-only (no side-effect): ritorna i componenti BoM validi con
`prezzo_suggerito` dal resolver bundle-aware. Il FE
(`ComponentiDialog.vue`) chiama PRIMA del save di una riga composita per
mostrare i prezzi pre-popolati. Per ogni componente vengono restituiti
`prezzo_suggerito` ed `origine_prezzo`, oppure `null` con
`resolver_error_reason` se il listino manca. Solleva
`E_VENDITE_VALIDATION` se `valido_dal`/`utility_id` contratto NULL o
emittente non risolvibile.

#### Lista componenti `GET /api/v1/vendite/contratti/<id>/righe/<rid>/componenti/`

Query param `solo_attivi` (bool, default `true`):

- `true`: solo componenti `attivo=TRUE` (vista compatta)
- `false`: include opzionali disattivati — usato dall'EDIT panel FE per
  consentire riattivazione via toggle. Accetta `"false"`/`"0"`/`"no"`/`"off"`

Output: una riga per componente con denormalizzazioni
articolo/uom/iva + flag `obbligatorio` ed `esposto_in_fattura` (JOIN
runtime su `articoli_componenti`).

#### Update componente `PATCH /api/v1/vendite/contratti/<id>/righe/<rid>/componenti/<cid>/`

```json
{
  "prezzo_unitario": "12.50",
  "iva_id": 1,
  "attivo": true,
  "meta": {}
}
```

Whitelist campi modificabili: `prezzo_unitario`, `iva_id`,
`uom_operativa_id`, `factor_to_base`, `qta_operativa`, `origine_prezzo`,
`prezzo_resolver_context`, `stato_approvazione_prezzo`,
`pratica_approvazione_prezzo_id`, `meta`, `ordine`, `attivo`. Campi
struttura immutabili (`componente_id`, `articolo_componente_id`,
`coeff_qta_snapshot`, `riga_contratto_id`) silenziosamente ignorati.

Anti-tampering URL: `riga_id` URL deve matchare riga reale del
componente; mismatch → `E_VENDITE_NOT_FOUND`. Solo contratto in stato
DRAFT modificabile (altrimenti `E_CONTRATTO_NON_MODIFICABILE`).

#### Delete componente `DELETE /api/v1/vendite/contratti/<id>/righe/<rid>/componenti/<cid>/`

Soft delete (`attivo=FALSE`). Il trigger DB di ricalcolo padre lo esclude
dalla SUM. Idempotente: se gia' soft-deleted ritorna `{deleted: false}`
senza errore. Stesso scope check anti-tampering di update.

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

### Documenti contratto

Endpoint dedicati alla generazione PDF tramite motore documentale
parametrico:

| Metodo | Path | Effetto |
| --- | --- | --- |
| `GET` | `/api/v1/vendite/contratti/<id>/documenti/` | Lista documenti generati dal contratto |
| `POST` | `/api/v1/vendite/contratti/<id>/documenti/anteprima/` | Render PDF temporaneo, non persistito |
| `POST` | `/api/v1/vendite/contratti/<id>/documenti/genera/` | Genera PDF, salva record e file |
| `GET` | `/api/v1/vendite/contratti/<id>/documenti/<documento_id>/file/` | Download PDF principale |

Payload opzionale per `anteprima/` e `genera/`:

```json
{
  "template_documento_id": 123,
  "tipo_documento_output_id": 2
}
```

Se `template_documento_id` non e' indicato, il service usa il template
`is_default=true` per `(sorgente=CONTRATTO, emittente_fiscale_id,
tipo_documento_output_id)`. Il context builder backend e'
`CONTRATTO`; il template iniziale e' documentato in
[template_contratto_iniziale](template_contratto_iniziale.md).

### Regole stampa contratto

- In stato `DRAFT`, il frontend usa `anteprima/`: il PDF viene renderizzato ma
  non viene persistito in `documenti.documenti_generati`.
- Nel passaggio `DRAFT -> ATTIVO`, il service genera il PDF contrattuale nella
  stessa transazione applicativa e lo salva come documento generato collegato a
  `sorgente=CONTRATTO`.
- Dopo l'attivazione, ristampe/download usano il documento salvato; non viene
  rigenerato il layout storico.
- La lista `GET /documenti/` espone i documenti gia' generati per il contratto,
  ed e' la fonte usata dal drawer e dalla tabella ricerca per le ristampe.
- La generazione richiede un `emittente_fiscale_id` sul contratto e almeno una
  versione `PUBBLICATA` attiva del template applicabile alla data corrente.

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
   La transizione `DRAFT -> ATTIVO` genera e salva il documento contratto.
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
| `E_VENDITE_VALIDATION` | 400 | Service (struttura/coerenza modalita', componenti_overrides non finito o non numerico, preview senza emittente/utility/valido_dal) | — |
| `E_VENDITE_NOT_FOUND` | 404 | Service (contratto/riga/componente; anti-tampering URL componenti) | — |
| `E_VENDITE_DUPLICATO` | 400 | UNIQUE `uq_contratti_numero` o `uq_contratti_utilities_contratto_id` | — |
| `E_VENDITE_FK` | 400 | FK su BA/istanza/utility/listino/parent/stato/articolo/UoM/tipo/classe utenza/categoria cliente snapshot | — |
| `E_VENDITE_CONTRATTO_OVERLAP` | 409 | EXCLUDE `ex_contratti_no_overlap` | — |
| `E_CONTRATTO_NON_MODIFICABILE` | 409 | Service (operazioni righe/componenti su contratto post-DRAFT) | — |
| `E_CONTRATTO_VALIDO_AL_RETROATTIVO` | 409 | DB P0001 (cessazione manuale con `valido_al < CURRENT_DATE`, bypass GUC per job notturno) | `trgfn_contratti_a10_guard_cessazione_no_retroattiva` |
| `E_CONTRATTO_MODALITA_C_SENZA_RIGHE` | 400 | DB P0001 | `trgfn_contratti_guard_modalita_c_activation` |
| `E_CONTRATTO_MODALITA_C_RIGHE_INCOMPLETE` | 400 | DB P0001 | `trgfn_contratti_guard_modalita_c_activation` |
| `E_CONTRATTO_MODALITA_C_RIGA_SENZA_PREZZO` | 400 | DB P0001 | `trgfn_contratti_righe_guard_modalita_c` |
| `E_CONTRATTO_UTILITY_TIPO_CLASSE_OBBLIGATORI` | 400 | DB P0001 | `trgfn_contratti_utilities_guard_tipo_classe` |
| `E_CONTRATTO_CLASSE_TIPO_INCOERENTE` | 400 | DB P0001 | `trgfn_contratti_utilities_guard_tipo_classe` |
| `E_CONTRATTO_UTILITY_SENZA_DIMENSIONE_TIPO_CLASSE_VIETATI` | 400 | DB P0001 | `trgfn_contratti_utilities_guard_tipo_classe` |
| `E_DOC_COMPOSITO_BOM_VUOTA` | 400 | DB P0001 (auto-init componenti riga: articolo composito senza figli BoM validi alla data) | `fn_contratto_riga_componenti_init` |
| `E_DOC_COMPONENTE_OBBLIGATORIO` | 400 | DB P0001 (tentativo di disattivare un componente obbligatorio) | `trgfn_contratti_righe_componenti_guard_obbligatorio` |
| `E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO` | 400 | DB P0001 (override prezzo 0 su componente obbligatorio) | `trgfn_contratti_righe_componenti_guard_prezzo` |
| `E_BOM_IVA_DISCORDANTE` | 400 | DB P0001 (IVA componente diversa da padre — vincolo modello unificato) | trigger catalogo IVA coerenza |

## Dipendenze DB

**Tabelle**: `vendite.contratti`, `vendite.contratti_righe`,
`vendite.contratti_utilities`, `vendite.contratti_righe_componenti`
(modello unificato BoM 2026-05-13, simmetrico a `preventivi_righe_componenti`).

**Funzioni**:

- `script.fn_generate_codice('contratto')` — numero contratto (prefix `CNT`).
- `vendite.fn_contratto_riga_componenti_init(riga_id, emittente_sr_id, data_riferimento, componenti_overrides::jsonb) -> integer`
  — auto-init componenti BoM idempotente. Default `attivo=TRUE` per tutti i
  componenti (BoM contratto immutabile, decisione 2026-05-13).
- `vendite.fn_contratto_riga_componenti_preview(articolo_id, uom_id, quantita_padre, data_riferimento, ba_id, utility_id, emittente_sr_id, classe_utenza_id) -> SETOF record`
  — read-only STABLE, ritorna 14 colonne (vedi `contratti_repository.preview_componenti_riga`).
- `vendite.fn_resolve_prezzo_listino_v2(..., p_articolo_padre_contesto)` — resolver
  bundle-aware usato dalla preview (vedi [api_pricing.md](api_pricing.md)).

**Trigger autoritativi**: come da tabella codici errore. Inoltre su
`contratti_righe_componenti`:

- `trg_contratti_righe_propaga_qta_componenti` — ricalcolo `quantita` componente
  al cambio `quantita` riga padre.
- `trgfn_contratti_righe_componenti_guard_pending` — immutabilita' componenti
  quando `stato_approvazione_prezzo = PENDING` (L3 approvazioni prezzo).

**Stati** gestiti via `config.stati_doc_contratti`
(DRAFT/ATTIVO/SOSPESO/CESSATO). Cessazione manuale solo con
`valido_al >= CURRENT_DATE`; il job pgAgent `fn_apply_chiusura_scadenze`
chiude i contratti scaduti via GUC `app.cessazione_automatica='true'`.
