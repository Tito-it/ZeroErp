# API Contratti `vendite.contratti`

## Scopo

CRUD operativo dei contratti commerciali cliente-listino, con sub-entita'
**righe** (`vendite.contratti_righe`) e **utility 1:1**
(`vendite.contratti_utilities`). E' il ponte tra il cliente (BA) e il
listino di riferimento.

### Modello unificato (refactor 2026-05-15)

Le vecchie **modalita' A/B/C** sono state rimosse come scelta utente. Il
contratto ha ora una **forma** derivata dai campi di testata:

| Forma derivata | `listino_id` | Eccezioni in `contratti_righe` |
|---|---|---|
| **`con_listino`** | NOT NULL | Opzionali. Tipi: `OVERRIDE` (prezzo personalizzato), `ESCLUSIONE` (articolo non disponibile), `AGGIUNTA` (articolo fuori-listino) |
| **`senza_listino`** | NULL | Tutte `AGGIUNTA` con `prezzo_unitario` NOT NULL (sostituisce ex-modalita' C "interamente negoziato") |

In forma "con_listino" la variazione globale (`tipo_variazione_globale` +
`valore_variazione_globale`) e' un campo opzionale che si applica alle righe
non-eccezione lette dal listino. Il vecchio vincolo "A/B/C" e' droppato:
qualunque combinazione di listino + variazione + eccezioni e' ammessa.

### Snapshot versione listino all'attivazione

Il contratto referenzia `listino_id` + nuovo campo `listino_versione_id`.
In `DRAFT` la versione e' NULL (il contratto segue la versione corrente del
listino). All'attivazione, il trigger
`trgfn_contratti_freeze_listino_versione` fissa la versione corrente:
da quel momento la versione e' **immutabile** (Profilo A), e cambi del
listino non si propagano al contratto. Le eccezioni sono blindate in
ogni fase.

Riferimento: [refactor-contratti-modalita.md](/dev/work-in-progress/refactor-contratti-modalita) §3-bis-A/A-schema.

## Contesto

- Il **numero contratto** e' generato lato service via
  `script.fn_generate_codice('contratto')` (prefix `CNT`, len 7,
  config in `config.sistema_codici`). NON e' accettato in payload (lock
  via trigger `trgfn_lock_columns('numero', 'CODICE_NON_MODIFICABILE')`).
- Lo **stato iniziale** di ogni contratto e' `DRAFT` (risolto dal service
  via `config.stati_doc_contratti.codice_interno`).
- Le coerenze cross-table (tipo/classe utenza per ambito utility, no-overlap,
  coerenza tipo_eccezione/prezzo) sono enforced dai trigger DB e dal
  temporal UNIQUE PG18:
  - `trgfn_contratti_freeze_listino_versione_upd` — fissa
    `listino_versione_id` al passaggio DRAFT→ATTIVO
  - `trgfn_contratti_lock_post_attivazione_upd` — testata immutabile
    (listino, versione, variazione globale) dopo l'attivazione
  - `trgfn_contratti_righe_lock_post_attivazione_*` — eccezioni immutabili
    dopo l'attivazione del contratto padre
  - `trgfn_contratti_righe_guard_aggiunta_fuori_listino` — blocca AGGIUNTA
    su articolo gia' presente nel listino
  - `trgfn_contratti_utilities_guard_tipo_classe`
  - CHECK `chk_contrighe_prezzo_per_tipo_eccezione` — ESCLUSIONE ↔ prezzo NULL
  - Temporal UNIQUE `uq_contratti_no_overlap` su `(billing_account_id, istanza_utility_id, utility_id, ambito, validita WITHOUT OVERLAPS)`.
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
| `listino_id` | int | Filtro listino di pricing (debug forma con_listino vs senza_listino) |
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

Note (refactor 2026-05-15):

- `numero` e `stato_doc_contratto_id` **NON vanno mai inviati** in
  payload (rifiutati con `E_VENDITE_VALIDATION`).
- `utility` (sub-payload opzionale): se presente, crea la riga utility 1:1
  nello stesso round-trip. `istanza_utility_id` e `utility_id` sono
  derivati dalla testata, NON dal sub-payload.
- **Niente piu' "modalita"**: `listino_id` e variazione globale sono campi
  opzionali liberi. Forma "senza_listino" → omettere `listino_id`; la
  variazione e' comunque ammessa (anche se il suo effetto sara' visibile
  solo se aggiungerai eccezioni AGGIUNTA con prezzo > 0).
- **Coppia variazione coerente**: `tipo_variazione_globale` e
  `valore_variazione_globale` devono essere **entrambi NULL** o **entrambi
  NOT NULL**. Pre-validation in `_validate_variazione_globale_coppia_coerente`
  → `E_VENDITE_VALIDATION` ("tipo e valore devono essere entrambi
  presenti o entrambi NULL").

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

**Post-attivazione** (refactor 2026-05-15 §3-bis-A): `listino_id`,
`listino_versione_id`, `tipo_variazione_globale`, `valore_variazione_globale`
diventano **immutabili** (Profilo A). Tentativo di modifica → 409 con
`E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE`. Per cambi sostanziali serve
un nuovo contratto.

**Blocco rimozione listino con eccezioni** (refactor §3-bis-F): se il PATCH
porta `listino_id` da NOT NULL a NULL e ci sono OVERRIDE/ESCLUSIONE attive,
il service ritorna 422 con `E_CONTRATTO_LISTINO_RIMOZIONE_CON_ECCEZIONI`.
AGGIUNTA non blocca (resta valida anche senza listino). L'operatore deve
rimuovere/sostituire prima le eccezioni.

**Gate L2 sulla variazione globale** (refactor §3-bis-E): se il PATCH tocca
`valore_variazione_globale` con `tipo_variazione_globale = PERCENTUALE`,
si applica il gate L2 (cascata user → categoria_cliente → group → emittente).
Sconto/maggiorazione oltre soglia → 403 retryable con
`E_PREV_SCONTO_ECCESSIVO`/`E_PREV_MAGGIORAZIONE_ECCESSIVA`. VALORE_FISSO
skip (non e' percentuale, gate non applicabile). Superuser bypass.

### Cambio stato `POST /api/v1/vendite/contratti/<id>/cambia-stato/`

```json
{"codice_interno": "ATTIVO"}
```

Stati ammessi: `DRAFT`, `ATTIVO`, `SOSPESO`, `CESSATO` (FK
`config.stati_doc_contratti`). L'attivazione di un contratto in forma
"senza_listino" senza righe AGGIUNTA con prezzo valorizzato fallisce
fail-fast lato DB → `E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE` (422).

Alla transizione `DRAFT → ATTIVO`, il trigger
`trgfn_contratti_freeze_listino_versione` fissa
`listino_versione_id = versione operativa` (stato `IN ('ATTIVA','CHIUSA')`)
alla data del contratto. Versioni in stato `BOZZA` vengono ignorate anche
se hanno date sovrapposte. Da quel momento la versione e' immutabile e
il pricing del contratto e' blindato da cambi del listino.

### Righe `POST /api/v1/vendite/contratti/<id>/righe/`

Refactor 2026-05-15: le righe sono **eccezioni tipizzate** del listino. Il
campo `tipo_eccezione` e' obbligatorio in CREATE e immutabile in UPDATE
(per cambiare tipo serve DELETE + INSERT).

```json
{
  "articolo_id": "00000000-0000-0000-0000-000000000001",
  "tipo_eccezione": "OVERRIDE",
  "tipo_erogazione": "CANONE",
  "prezzo_unitario": "25.50",
  "quantita_fissa": "1",
  "uom_operativa_id": 5,
  "ordine": 10
}
```

Tipi ammessi (allineati col CHECK DB `chk_contrighe_prezzo_per_tipo_eccezione`):

| `tipo_eccezione` | Significato | `prezzo_unitario` |
| --- | --- | --- |
| `OVERRIDE` | Prezzo personalizzato per un articolo presente nel listino | NOT NULL |
| `ESCLUSIONE` | L'articolo del listino non e' disponibile per il cliente | NULL |
| `AGGIUNTA` | Articolo fuori-listino, aggiunto al contratto | NOT NULL |

Vincoli:

- **AGGIUNTA su articolo presente nel listino**: bloccata dal trigger
  `trgfn_contratti_righe_guard_aggiunta_fuori_listino` →
  `E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO` (422). L'operatore avrebbe dovuto
  usare OVERRIDE.
- **Coerenza prezzo/tipo**: ESCLUSIONE con prezzo NOT NULL o
  OVERRIDE/AGGIUNTA con prezzo NULL → `E_VENDITE_VALIDATION` (pre-DB) o
  CHECK violation (DB).
- **Unicita' eccezione**: max 1 eccezione `OVERRIDE`/`ESCLUSIONE` per coppia
  `(contratto_id, articolo_id)`. Stessa univocita' per AGGIUNTA.
- **Post-attivazione**: tutte le eccezioni sono immutabili (INSERT/UPDATE/DELETE
  bloccati dal trigger `trgfn_contratti_righe_lock_post_attivazione*`) →
  `E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE` (409).

`PATCH /api/v1/vendite/contratti/<id>/righe/<riga_id>/` aggiorna i campi
mutabili; `articolo_id` e `tipo_eccezione` immutabili. Cambio di
`prezzo_unitario` validato in coerenza col `tipo_eccezione` esistente
(pre-DB con messaggio parlante).

`DELETE /api/v1/vendite/contratti/<id>/righe/<riga_id>/` hard-delete
(bloccato dal trigger se note collegate o contratto ATTIVO).

### Contesto pricing `GET /api/v1/vendite/contratti/<id>/contesto-pricing/`

Endpoint readonly mutuato dal pattern preventivi (`/preventivi/<id>/contesto-pricing/`).
Ritorna la "forma" derivata e i riferimenti pricing per il banner FE:

```json
{
  "data": {
    "contratto_id": 42,
    "forma": "con_listino",
    "stato_codice": "ATTIVO",
    "listino_id": 100,
    "listino_codice": "LST-001",
    "listino_descrizione": "Listino energia 2026",
    "listino_versione_id": 5,
    "listino_versione_codice": "V5",
    "listino_versione_fissata": true,
    "tipo_variazione_globale": "PERCENTUALE",
    "valore_variazione_globale": "-5.00",
    "categoria_cliente_id": 7,
    "categoria_cliente_codice": "PREMIUM",
    "categoria_cliente_descrizione": "Cliente premium"
  }
}
```

`listino_versione_fissata` = `true` se `c.listino_versione_id IS NOT NULL`
(contratto ATTIVO con snapshot). Versione FE: badge "Versione fissata"
nell'header del drawer righe.

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

### Preview righe contratto `GET /api/v1/vendite/contratti/<id>/righe-preview/`

Endpoint readonly che restituisce tutte le righe del drawer `ContrattoRigheDrawer`:
articoli dal listino (con overlay eccezioni) + AGGIUNTA fuori-listino.
Delega tutto a `vendite.fn_contratto_righe_preview` — il BE e' thin wrapper.

**Shape risposta** (una riga per articolo padre; i bundle hanno `componenti` annidato):

```json
{
  "data": [
    {
      "articolo_id": "uuid",
      "articolo_codice": "GAS-STD",
      "articolo_descrizione": "Gas Standard",
      "is_composito": false,
      "uom_id": 3,
      "uom_codice": "MWh",
      "prezzo_listino": "10.50",
      "tipo_variazione": "PERCENTUALE",
      "valore_variazione": "-5.00",
      "override_riga_id": null,
      "override_prezzo": null,
      "tipo_eccezione": null,
      "origine": "DA_LISTINO",
      "prezzo_finale": "9.975",
      "componenti": null
    },
    {
      "articolo_id": "uuid-bundle",
      "articolo_codice": "KIT-ATTIV",
      "articolo_descrizione": "Kit attivazione",
      "is_composito": true,
      "uom_id": 1,
      "uom_codice": "PZ",
      "prezzo_listino": null,
      "tipo_variazione": "PERCENTUALE",
      "valore_variazione": "-5.00",
      "override_riga_id": null,
      "override_prezzo": null,
      "tipo_eccezione": null,
      "origine": "DA_LISTINO",
      "prezzo_finale": "48.00",
      "componenti": [
        {
          "componente_id": "uuid-figlio",
          "componente_codice": "COMP-A",
          "componente_descrizione": "Componente A",
          "uom_id": 2,
          "uom_codice": "H",
          "coeff_qta": "2.0",
          "prezzo": "15.00",
          "obbligatorio": true,
          "esposto_in_fattura": false
        },
        {
          "componente_id": "uuid-figlio2",
          "componente_codice": "COMP-B",
          "componente_descrizione": "Componente B",
          "uom_id": 1,
          "uom_codice": "PZ",
          "coeff_qta": "1.0",
          "prezzo": "18.00",
          "obbligatorio": false,
          "esposto_in_fattura": true
        }
      ]
    }
  ]
}
```

**Valori `origine`**: `DA_LISTINO` | `OVERRIDE` | `ESCLUSIONE` | `AGGIUNTA`.  
**Bundle** (`is_composito=true`): `prezzo_finale` = SUM aggregato in DB
(`lrc.prezzo × ac.coeff_qta` da listino, o `prezzo_unitario` del padre AGGIUNTA).  
**ESCLUSIONE**: `prezzo_finale = null`, articolo mostrato con badge "Escluso".  
**Versione listino**: per contratti ATTIVI usa `listino_versione_id` snapshot;
per DRAFT usa la versione operativa corrente (`stato IN ('ATTIVA','CHIUSA')`).

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
    "righe": [{"id": 99, "articolo_codice": "ART-001", "is_composito": false, "prezzo_unitario": "25.50"}, ...]
  }
}
```

Ogni riga espone `is_composito` denormalizzato (JOIN `catalogo.articoli`) sia
nel detail (`/righe` interne al contratto) sia nella preview righe applicate
(`/righe-preview/`). Driver lato FE per detection auto-apertura
`ComponentiDialog` e visibilita' `ComponentiPanel` in EDIT senza round-trip
extra al catalogo.

## Regole

1. Numero contratto generato dal service (mai in payload).
2. Stato iniziale DRAFT; transizioni via endpoint dedicato.
   La transizione `DRAFT -> ATTIVO` genera e salva il documento contratto +
   fissa `listino_versione_id` alla versione corrente del listino.
3. Identificativi (BA, istanza, utility) immutabili in update — per
   cambiarli si crea un nuovo contratto.
4. **Forma "senza_listino"** valida a livello DB solo se esistono righe
   AGGIUNTA con `prezzo_unitario` valorizzato. Il guard di attivazione
   solleva `E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE` (422). Sostituisce i
   vecchi guard di "modalita' C" rimossi col refactor 2026-05-15.
5. **Profilo A — congelamento post-attivazione**: dopo `DRAFT → ATTIVO`,
   tutti i campi pricing della testata (`listino_id`, `listino_versione_id`,
   `tipo_variazione_globale`, `valore_variazione_globale`) sono immutabili,
   cosi' come le eccezioni in `contratti_righe`. Tentativi di modifica
   sollevano `E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE` (409). Per
   modifiche sostanziali serve un nuovo contratto.
6. **Coerenza coppia variazione globale**: `tipo_variazione_globale` e
   `valore_variazione_globale` entrambi NULL o entrambi NOT NULL
   (pre-validation `_validate_variazione_globale_coppia_coerente`).
7. **Coerenza prezzo/tipo_eccezione**: ESCLUSIONE ↔ prezzo NULL,
   OVERRIDE/AGGIUNTA ↔ prezzo NOT NULL. Validato in service (pre-DB con
   messaggio parlante) e in DB (`chk_contrighe_prezzo_per_tipo_eccezione`).
8. Tipo/classe utenza obbligatori per utility con dimensione (es. GAS,
   EE), vietati per utility commercio (Base). Coerenza
   `classi_utenze.tipo_utenza_id = contratti_utilities.tipo_utenza_id`
   imposta dal trigger DB.
9. EXCLUDE no-overlap: un solo contratto attivo per
   `(BA, istanza_utility, utility, ambito)` su validita' sovrapposta.
10. `categoria_cliente_id_snapshot` e' congelato alla creazione del
    contratto (dal trigger DB, che lo popola dal BA). Rappresenta la
    categoria commerciale del cliente al momento della stipula. Non e'
    modificabile in update. In risposta vengono esposti anche
    `categoria_cliente_snapshot_codice` e
    `categoria_cliente_snapshot_descrizione` (JOIN display).

## Codici errore

| Codice | HTTP | Origine | Trigger DB |
|---|---|---|---|
| `E_VENDITE_VALIDATION` | 400 | Service (struttura/coerenza coppia variazione globale, tipo_eccezione obbligatorio + coerenza prezzo, componenti_overrides non finito o non numerico, preview senza emittente/utility/valido_dal) | — |
| `E_VENDITE_NOT_FOUND` | 404 | Service (contratto/riga/componente; anti-tampering URL componenti) | — |
| `E_VENDITE_DUPLICATO` | 400 | UNIQUE `uq_contratti_numero` o `uq_contratti_utilities_contratto_id` o `uq_contrighe_one_eccezione_per_articolo` o `uq_contrighe_one_aggiunta_per_articolo` | — |
| `E_VENDITE_FK` | 400 | FK su BA/istanza/utility/listino/listino_versione/parent/stato/articolo/UoM/tipo/classe utenza/categoria cliente snapshot | — |
| `E_VENDITE_CONTRATTO_OVERLAP` | 409 | Temporal UNIQUE `uq_contratti_no_overlap` (WITHOUT OVERLAPS, PG18) | — |
| `E_CONTRATTO_NON_MODIFICABILE` | 409 | Service (operazioni righe/componenti su contratto post-DRAFT) | — |
| `E_CONTRATTO_VALIDO_AL_RETROATTIVO` | 409 | DB P0001 (cessazione manuale con `valido_al < CURRENT_DATE`, bypass GUC per job notturno) | `trgfn_contratti_a10_guard_cessazione_no_retroattiva` |
| `E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE` | 422 | DB P0001 (refactor modalita 2026-05-15) — attivazione di contratto senza listino senza righe AGGIUNTA con prezzo valorizzato | `trgfn_contratti_freeze_listino_versione` (guard interno) |
| `E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO` | 422 | DB P0001 (refactor 2026-05-15) — INSERT/UPDATE riga `tipo_eccezione=AGGIUNTA` per articolo gia' presente nel listino di riferimento | `trgfn_contratti_righe_guard_aggiunta_fuori_listino` |
| `E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA` | 422 | DB P0001 (§6.1 2026-05-16) — INSERT/UPDATE riga `tipo_eccezione=ESCLUSIONE` per articolo che e' `articolo_figlio_id` in un bundle del listino del contratto. L'ESCLUSIONE si applica al padre bundle, non al singolo componente | `trgfn_contratti_righe_guard_esclusione_figlio_bundle` |
| `E_ARTICOLO_ESCLUSO_DA_CONTRATTO` | 422 | DB P0001 (resolver pricing) — tentativo di prezzare un articolo che ha eccezione ESCLUSIONE sul contratto attivo del cliente | `fn_resolve_prezzo_listino_v2` (STADIO 1 eccezioni) |
| `E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE` | 409 | DB P0001 (refactor §3-bis-A) — UPDATE su `listino_id`/`listino_versione_id`/`tipo_variazione_globale`/`valore_variazione_globale` di contratto ATTIVO, oppure INSERT/UPDATE/DELETE eccezione su contratto ATTIVO | `trgfn_contratti_lock_post_attivazione` + `trgfn_contratti_righe_lock_post_attivazione` |
| `E_CONTRATTO_LISTINO_RIMOZIONE_CON_ECCEZIONI` | 422 | Service (refactor §3-bis-F) — PATCH testata che porta `listino_id` da NOT NULL a NULL con eccezioni OVERRIDE/ESCLUSIONE attive | — |
| `E_PREV_SCONTO_ECCESSIVO` / `E_PREV_MAGGIORAZIONE_ECCESSIVA` | 403 (retryable=True) | Service (refactor §3-bis-E) — gate L2 sulla variazione globale del contratto al PATCH testata. Cascata user → categoria → group → emittente. VALORE_FISSO non applicabile (skip) | — |
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
