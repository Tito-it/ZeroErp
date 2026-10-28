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
In `DRAFT` la versione e' NULL (il contratto segue la versione **in vigore
oggi**, `vendite.fn_documento_listino_operativo`: la stessa per righe, pricing e
capability). All'attivazione, il trigger
`trgfn_contratti_freeze_listino_versione` fissa quella versione:
da quel momento la versione e' **immutabile** (Profilo A), e cambi del
listino non si propagano al contratto. Le eccezioni sono blindate in
ogni fase.

⛔ **Un contratto con listino non si attiva senza una versione in vigore**
(decisione A-D2 di Tid, 2026-10-07, brief-db-offerta-emissione-ed-erogazione):
il freeze lo rifiuta con `E_CONTRATTO_ATTIVAZIONE_SENZA_VERSIONE_LISTINO`
(409), e la capability spegne «Attiva» col motivo (`reason_key`
`vendite.contratti.azione_reason.listino_senza_versione_in_vigore`), dalla
stessa check `script.fn_check_listino_congelabile`. Fino a quel giorno il
contratto si attivava con la versione NULL e poi **galleggiava** sulla versione
in vigore di ogni giorno: l'opposto di «congela all'attivazione» (§4.4 del
2026-05-18, rovesciato). Una versione gia' fissata dal push dell'offerta resta,
anche se nel frattempo si e' chiusa. Il negoziato puro (`listino_id` NULL)
resta fuori.

Riferimento: [refactor-contratti-modalita.md](/dev/work-done/refactor-contratti-modalita) §3-bis-A/A-schema.

## Contesto

- Il **numero contratto** e' generato via `script.fn_generate_codice('contratto')`
  (prefix `CNT`, len 7, config in `config.sistema_codici`) **dentro la funzione madre**
  `vendite.fn_create_contratto` (fix analisi-fix-transazioni #2, 2026-07-08 — prima
  lato service, prima dell'INSERT). NON e' accettato in payload (lock via trigger
  `trgfn_lock_columns('numero', 'CODICE_NON_MODIFICABILE')`).
- Lo **stato iniziale** di ogni contratto e' `DRAFT` (risolto **dentro** la fn madre
  da `config.stati_doc_contratti.codice_interno`).
- **Atomicità creazione (#2):** generazione numero + INSERT testata + INSERT utility 1:1
  opzionale avvengono in **un'unica** `SELECT vendite.fn_create_contratto(...)`, atomica
  per costruzione: o tutto o rollback (contatore numero incluso). Prima erano
  `generate_numero()` + 2 INSERT separati in autocommit → un fallimento dell'INSERT
  utility lasciava un contratto orfano. NB: il numero viene da una **sequence** e un
  rollback lascia comunque un **gap** di numerazione (innocuo, gia' cosi' in precedenza).
- Le coerenze cross-table (tipo/classe utenza per ambito utility, no-overlap,
  coerenza tipo_eccezione/prezzo) sono enforced dai trigger DB e dal
  temporal UNIQUE PG18:
  - `trgfn_contratti_freeze_listino_versione_upd` — fissa
    `listino_versione_id` al passaggio DRAFT→ATTIVO
  - `trgfn_doc_testata_lock_fuori_bozza` (building block di testata, dal
    2026-10-10 al posto di `trgfn_contratti_lock_post_attivazione`) — quali
    colonne della testata si cambiano fuori bozza, colonna per colonna e per
    stato (vedi §PATCH testata)
  - `trgfn_doc_righe_lock_fuori_bozza` (building block, dal 2026-09-22, al
    posto di `trgfn_contratti_righe_lock_post_attivazione`) — eccezioni
    immutabili dopo l'attivazione del contratto padre: la stessa regola «le
    righe si toccano solo in bozza» dei DDT e degli ordini, un trigger per
    documento, codice `E_RIGA_DOC_NON_BOZZA` (409)
  - `script.trgfn_righe_guard_articolo_ammesso` — l'articolo della riga col
    primo motivo di `script.fn_check_articolo_riga` (AGGIUNTA gia' in listino,
    eccezione senza listino o fuori listino, figlio di bundle, solo componente,
    kit senza componenti, tipologia, erogazioni): la stessa check del picker
    `GET /catalogo/articoli/lookup/?documento=CONTRATTO`
  - `trgfn_contratti_utilities_guard_tipo_classe`
  - CHECK `chk_contrighe_prezzo_per_tipo_eccezione` — ESCLUSIONE ↔ prezzo NULL
  - EXCLUDE gist parziale `ex_contratti_no_overlap` su `(billing_account_id WITH =, istanza_utility_id WITH =, utility_id WITH =, ambito WITH =, validita WITH &&) WHERE (partecipa_overlap_snapshot)` (migration `20260521-03`; predicato DRAFT-escluso da `20260602-17..22`). I contratti DRAFT e quelli abortiti **non** partecipano al vincolo: l'esclusivita' scatta solo all'attivazione (vedi nota DRAFT-scope sotto). Governato dal framework `dbops.automazione_overlap` (re-apply notturno).
- Il service `ContrattiService` traduce gli errori `P0001` dei trigger nei
  codici applicativi documentati piu' sotto.

## Input

### Form-defaults `GET /api/v1/vendite/contratti/form-defaults/`

Endpoint sola lettura per pre-popolare il form CREATE contratto. Riusato
dal drawer FE all'apertura e al cambio `billing_account_id`. Simmetrico
a `vendite-offerta-form-defaults` e `vendite-preventivi-form-defaults`.

| Parametro             | Tipo  | Descrizione                                                                                |
| --------------------- | ----- | ------------------------------------------------------------------------------------------ |
| `billing_account_id`  | int   | Opzionale. Se presente, popola i campi BA-derived (categoria_cliente, utility, valuta).    |

Risposta `200`:

```json
{
  "data": {
    "billing_account_id": 10,
    "default_valido_dal": "2026-01-15",
    "default_data": "2026-01-15",
    "categoria_cliente_id_snapshot": 7,
    "categoria_cliente_codice": "STANDARD",
    "categoria_cliente_descrizione": "Standard",
    "utility_id": 3,
    "istanza_utility_id": 20,
    "utility_codice": "GAS",
    "utility_descrizione": "Gas",
    "valuta_id": 1,
    "valuta_codice": "EUR",
    "valuta_descrizione": "Euro"
  }
}
```

Risoluzione `valuta_id` (BB `resolve_valuta_default`, allineato a
`vendite.fn_get_valuta_id`): vedi
[api_vendite_form_defaults.md](api_vendite_form_defaults.md) per la
catena 5-livelli (BA → EF-BA → EF-utente → gestore → null).
`default_valido_dal` / `default_data` calcolati con lead_gg da parameter.

Errori: `E_VENDITE_NOT_FOUND` (404) se `billing_account_id` non esiste.

### Lista contratti `GET /api/v1/vendite/contratti/`

> **DEF-8 (2026-06-02)**: la lista legge dalla vista `vendite.vw_contratti_lista`
> (lista configurabile `vendite.contratti`, ritiro dinamico colonne lato FE).
> I campi display usano i **nomi canonici della vista** — cliente =
> `ragione_sociale_completa`, id. fiscale = `id_fiscale_univoco_cf_piva` (niente
> alias `ba_*`); stato = `stato_descrizione` (display) + `stato_codice` (codice
> **mutabile**, display) + `stato_codice_interno` (codice **immutabile**, per la logica —
> es. confronti `DRAFT`/`ATTIVO`/`CESSATO`; vedi linee-guida-sql.md §6c). Il **dettaglio**
> (`GET .../<id>/`) conserva invece i nomi storici (`ba_ragione_sociale`,
> `id_fiscale`): è una fonte diversa (JOIN su tabelle base, non la vista).

| Parametro | Tipo | Descrizione |
|---|---|---|
| `search` | string | ILIKE su `numero`, `ragione_sociale_completa`, `ba_codice` e `id_fiscale_univoco_cf_piva` (le colonne `ricercabile_full` a catalogo); sotto i 3 caratteri non filtra |
| `billing_account_id` | int | Filtro cliente |
| `stato_doc_contratto_id` | int | Filtro stato (FK `config.stati_doc_contratti`) |
| `utility_id` | int | Filtro utility |
| `ambito` | string | `COMMODITY` o `COMMERCIO` |
| `listino_id` | int | Filtro listino di pricing (debug forma con_listino vs senza_listino) |
| `data_da` | ISO date | Filtro periodo validità (overlap `valido_dal`/`valido_al`). **Nessun default backend**: il default anno-1 lo mette la UI |
| `data_a` | ISO date | Filtro periodo validità |
| `scadenza_mese` | string | `YYYY-MM`: contratti con `valido_al` (ultimo giorno di validità) nel mese indicato |
| `limit` | int | Default 25, max 200 |
| `offset` | int | Default 0 |
| `order_by` | string | Default `data`. Whitelist `_ORDER_COLS_CONTRATTI`: `numero` `data` `valido_dal` `valido_al` `ba_codice` `ragione_sociale_completa` `id_fiscale_univoco_cf_piva` `utility_codice` `utility_descrizione` `ambito` `listino_codice` `listino_versione_codice` `tipo_variazione_globale` `valore_variazione_globale` `valuta_codice` `stato_descrizione` `categoria_cliente_snapshot_codice` `data_insert` `data_update` `pratica_numero` `fase`. Fuori whitelist → `400 E_VENDITE_VALIDATION` (`stato_codice` non è ordinabile: si ordina per `stato_descrizione`) |
| `order_dir` | string | `asc` o `desc`. Assente: `desc` sulla colonna di default (`data`, «dal più recente») e sulle colonne data (`valido_dal`, `valido_al`, `data_insert`, `data_update`), `asc` sulle altre. `valido_al` vuoto ordina come `infinity` |

Scope emittente applicato a livello DB (RLS `security_invoker` sulla vista) +
filtro applicativo `fn_get_emittenti_scope_pk_ids` (defense-in-depth). Lista ed
export dichiarano `lista_codice = "vendite.contratti"`: il cancello di perimetro
emittente può rispondere `422 E_UI_LISTA_EMITTENTE_DA_SCEGLIERE`.

### Export lista `GET /api/v1/vendite/contratti/export/`

Genera un file **CSV** o **Excel** con i contratti filtrati (stessi parametri
della lista). Renderer generico DEF-1 (`ListaExportService`); le colonne sono
coerenti con la DataTable a video (config runtime: preferenza + preset +
permessi — colonne nascoste escluse, ordine utente rispettato).

| Parametro | Tipo | Descrizione |
|---|---|---|
| `formato` | string | `csv` (default) o `xlsx`. **NB**: parametro `formato` (italiano), NON `format` (magic param DRF) |
| `search`, `billing_account_id`, `stato_doc_contratto_id`, `utility_id`, `ambito`, `listino_id`, `data_da`, `data_a`, `scadenza_mese`, `order_by`, `order_dir` | — | stessi della lista |

- Hard cap **10.000 righe**: oltre → `422 E_UI_EXPORT_LIMIT_EXCEEDED`.
- `formato` non valido → `400 E_UI_EXPORT_FORMAT_INVALID`.
- Risposta binaria: `Content-Disposition: attachment; filename="contratti.csv|xlsx"`; i filtri attivi sono inclusi come metadato nel file.
- Coda condivisa: `apps.ui.api.export_helpers.{parse_export_format,build_export_response}` (building block DEF-1, gemello clienti/soggetti/fornitori).

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
  "valuta_id": 1,
  "emittente_fiscale_id": 2,
  "tipo_variazione_globale": "PERCENTUALE",
  "valore_variazione_globale": "10",
  "fatturazione_immediata": false,
  "codice_cig": "Z1234567890",
  "codice_cup": null,
  "codice_commessa": null,
  "meta": {"note": "Cliente Gold"},
  "utility": {
    "tipo_utenza_id": 2,
    "classe_utenza_id": 7,
    "param_2_txt": "POD-XYZ"
  }
}
```

Note (refactor 2026-05-15):

- Chiavi ammesse (`CREATE_KEYS_TESTATA`): `emittente_fiscale_id`,
  `billing_account_id`, `istanza_utility_id`, `utility_id`, `ambito`,
  `valido_dal`, `valido_al`, `parent_contratto_id`, `data`, `listino_id`,
  `tipo_variazione_globale`, `valore_variazione_globale`,
  `categoria_cliente_id_snapshot`, `fatturazione_immediata` (booleano JSON),
  `valuta_id`, i riferimenti dell'atto `codice_cig` / `codice_cup` (max 15) e
  `codice_commessa` (max 100), `meta`, `utility`. Ogni altra chiave → `400
  E_VENDITE_VALIDATION`. La risposta è il dettaglio completo.
- `tipo_variazione_globale` ammette solo `PERCENTUALE`: `VALORE_FISSO` → `400
  E_VENDITE_VALIDATION` (per un prezzo fisso su un articolo si usa una riga
  OVERRIDE).
- `valuta_id` opzionale (2026-05-29). Snapshot fissato al CREATE,
  immutabile in PATCH (non in `UPDATE_KEYS_TESTATA`). Se omesso, il
  trigger DB `_a*_set_valuta_default_ins` lo risolve via
  `vendite.fn_get_valuta_id` (catena BA → emittente → gestore). Il FE può
  pre-popolare via `GET /api/v1/vendite/contratti/form-defaults/?billing_account_id=...`.
- `numero` e `stato_doc_contratto_id` **NON vanno mai inviati** in
  payload (rifiutati con `E_VENDITE_VALIDATION`).
- `utility` (sub-payload opzionale): se presente, crea la riga utility 1:1
  nello stesso round-trip. `istanza_utility_id` e `utility_id` sono
  derivati dalla testata, NON dal sub-payload.
- **Il listino e' della utility e dell'emittente del contratto** (dal
  2026-10-08, F-2 di brief-db-offerta-emissione-ed-erogazione): uno di un'altra
  utility → `E_DOC_LISTINO_UTILITY_DIVERSA`, di un'altra azienda →
  `E_DOC_LISTINO_EMITTENTE_DIVERSO` (400, campo `listino_id`), all'INSERT e
  quando cambiano listino, utility o emittente (guard
  `script.trgfn_doc_guard_listino_documento`; i contratti gia' scritti restano
  come sono). Il form li sceglie da `GET /vendite/lookup/listini-selezionabili/`
  ([api_vendite_lookups](api_vendite_lookups.md)). Un listino **senza versione in
  vigore** si sceglie in DRAFT: lo rifiuta l'attivazione
  (`E_CONTRATTO_ATTIVAZIONE_SENZA_VERSIONE_LISTINO`).
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

Output: testata + `utility` + `righe[]` + **`capabilities`**
(Fase 1.B2 refactor frontend vendite, da `script.fn_available_actions_contratto`;
non fuse nella testata dal 2026-09-23, [api.md §«Il blob sta SOTTO `capabilities`»](../../../dev/api.md)).
`contatori` (dal 2026-10-25): `{"note": <n>}`, il numero sul pulsante «Gestisci note» del drawer, dal BB `contatori_documento` — contato **dopo** il cancello di testata, con lo stesso perimetro della lista note. Forma e ragioni in [api_fattura_dettaglio §`contatori`](/backend/vendite/manual/api_fattura_dettaglio).

Le chiavi di `capabilities`:

| Campo | Tipo | Significato |
| --- | --- | --- |
| `available_actions[]` | array | Azioni cambio stato disponibili. L'azione `cessa` e' arricchita runtime con `requires_date=true`, `default_date=today`, `min_date=valido_dal` |
| `can_change_state` | bool | `true` se almeno un'azione manuale disponibile |
| `can_edit_testata` | bool | `true` in DRAFT e in ATTIVO (`valido_al`, riferimenti dell'atto, `meta`); `false` in CESSATO e ANNULLATO |
| `can_edit_righe` | bool | `true` solo in DRAFT |
| `non_editable_fields[]` | string[] | Le colonne che il lock di testata DB (`trgfn_doc_testata_lock_fuori_bozza`) blocca nello stato corrente, calcolate da `script.fn_available_actions_contratto`. Il service non ne ha più una tabella sua (`_CONTRATTO_PATCH_ALLOWED_BY_STATE` ritirata il 2026-10-10) |

Il frontend (`ContrattoDrawer.vue`) usa `default_date`/`min_date` dell'azione
`cessa` per pre-popolare il dialog di cessazione: niente `new Date()` cablato.

### Update testata `PATCH /api/v1/vendite/contratti/<id>/`

Chiavi ammesse (`UPDATE_KEYS_CONTRATTO`): `billing_account_id`,
`istanza_utility_id`, `ambito`, `valido_dal`, `valido_al`,
`parent_contratto_id`, `data`, `listino_id`, `tipo_variazione_globale`,
`valore_variazione_globale`, `categoria_cliente_id_snapshot`,
`fatturazione_immediata` (booleano JSON), `codice_cig`, `codice_cup`,
`codice_commessa`, `meta` e la scheda `utility` inline. Ogni altra chiave →
`400 E_VENDITE_VALIDATION`; `numero`, `stato_doc_contratto_id`, `utility_id`,
`valuta_id`, `emittente_fiscale_id` non si cambiano. Corpo senza campi → 400.
Risposta: il dettaglio completo.

- **Cliente in bozza**: `billing_account_id` e `istanza_utility_id` si cambiano
  in DRAFT (coppia risolta e verificata contro la utility del contratto, BB
  `risolvi_cliente_coppia`; incoerente → 400). Fuori bozza li ferma il DB
  (`E_DOC_CLIENTE_FUORI_BOZZA`, 409).
- **Scheda utility inline** (`utility`: `tipo_utenza_id`, `classe_utenza_id`,
  `istanza_dati_precontrattuali_id`, `param_1_num`, `param_2_txt`, `meta`):
  la crea se manca, altrimenti la aggiorna, nella stessa transazione della
  testata. `istanza_utility_id`/`utility_id`/`contratto_id` dentro la scheda →
  400. ⚠️ Con un **cambio di cliente** la scheda del payload non si applica: la
  rifà il DB dal contatore nuovo (`trg_contratti_m50_fornitura_segue_cliente_upd`)
  e il dettaglio restituito porta quella.
**Fuori bozza decide il DB** (dal 2026-10-10,
[brief-db-testata-dopo-emissione](/dev/work-done/brief-db-testata-dopo-emissione)):
il service non ha piu' una tabella dei campi ammessi per stato. In ATTIVO
restano aperti `valido_al`, `codice_cig`/`codice_cup`/`codice_commessa` e
`meta`; il resto lo ferma il lock di testata con un 409 per famiglia —
`E_DOC_IDENTITA_FUORI_BOZZA` (data, valuta), `E_DOC_CONDIZIONI_FUORI_BOZZA`
(listino, versione, variazione globale, categoria, ambito, decorrenza, contratto
padre), `E_DOC_CLIENTE_FUORI_BOZZA`, `E_DOC_SORGENTE_FUORI_BOZZA`. In CESSATO e
ANNULLATO si ferma tutto (`E_DOC_CHIUSO`). Il form spegne i campi prima con
`can_edit_testata` e `non_editable_fields` della capability, letti dallo stesso
montaggio. `E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE` e' ritirato. Per cambi
sostanziali serve un nuovo contratto.

**Il listino sotto le righe** (dal 2026-10-11, brief-db-testata-dopo-emissione
§11, R-DB-4): lo giudica il DB, per contratto e offerta
(`script.trgfn_doc_guard_listino_con_righe`). Un listino messo o sostituito con
righe attive risponde 422 `E_DOC_LISTINO_CAMBIO_CON_RIGHE`; il listino tolto con
eccezioni OVERRIDE/ESCLUSIONE attive risponde 422
`E_DOC_LISTINO_RIMOZIONE_CON_ECCEZIONI` (AGGIUNTA non blocca). Campo `listino_id`.
Il service non ha piu' controlli suoi: `E_CONTRATTO_CAMPI_BLOCCATI_CON_RIGHE` ed
`E_CONTRATTO_LISTINO_RIMOZIONE_CON_ECCEZIONI` sono ritirati.

**Gate L2 sulla variazione globale** (refactor §3-bis-E): se il PATCH **o la
creazione** (`POST /contratti/`, dal 2026-10-21: prima la sola PATCH) porta
`valore_variazione_globale`, si applica il gate L2 sul cliente che il contratto
avrà — quello del payload, o quello che ha (cascata user →
categoria_cliente → group → emittente). Sconto/maggiorazione oltre soglia →
403 retryable con `E_PRICING_SCONTO_ECCESSIVO`/`E_PRICING_MAGGIORAZIONE_ECCESSIVA`.
Il tipo ammesso è solo `PERCENTUALE`: `VALORE_FISSO` è rifiutato prima (400
`E_VENDITE_VALIDATION`), non «saltato». Superuser bypass.

### Cambio stato `POST /api/v1/vendite/contratti/<id>/cambia-stato/`

```json
{"codice_interno": "CESSATO", "valido_al": "2026-12-31"}
```

- `codice_interno` (obbligatorio): stato di destinazione.
- `valido_al` (ISO date): la data di cessazione, **solo verso `CESSATO`**; con un
  altro stato è un `400 E_VENDITE_VALIDATION` col campo. La cessazione la decide
  il verbo `vendite.fn_cessa_contratto`: oggi → `CESSATO` subito; futura →
  **programmata** (si scrive solo la data, lo stato resta e lo porta a `CESSATO`
  il job alla scadenza); senza data → `E_CONTRATTO_CESSAZIONE_SENZA_DATA` (400,
  campo `valido_al`); passata → `E_CONTRATTO_VALIDO_AL_RETROATTIVO` (409).
- `legami_confermati` (int): solo verso `ANNULLATO`, vedi sotto.

Risposta `200`: il **dettaglio completo** del contratto (stessa forma del
`GET /<id>/`, `capabilities` comprese), anche sull'annullo. Verso `CESSATO` porta
anche `programmata` (bool): `true` se lo stato non è cambiato e lo chiuderà il job.

Permesso: l'azione la dice la riga del passaggio (`PassaggioDocumento`): la
cessazione chiede `emetti_contratto` (403 senza), l'annullo della bozza il solo
permesso sul documento. Uno stato che il vocabolario non ha →
`E_STATO_WORKFLOW_NON_TROVATO` (404); lo stato che il contratto ha già →
`E_DOC_GIA_NELLO_STATO` (409). Contratto inesistente o fuori perimetro →
`E_CONTRATTO_NON_TROVATO` (404), dal verbo: dal 2026-10-27 il service non lo
ridice (regola del 1, Tid).

Verso `ANNULLATO` passa sempre dal verbo `vendite.fn_annulla_contratto`: su un
contratto con legami (offerta d'origine, righe di commessa da emettere) risponde
`E_DOC_ANNULLO_CON_LEGAMI` (409, `confirm_and_retry`) finché il body non dichiara
`legami_confermati` (intero, letto da `…/legami/`). Confermato, l'offerta torna
trasformabile e le righe di commessa da emettere si annullano.

Legami `GET /<id>/legami/` (factory `build_legami_view`, BB
`_annullo_con_legami.legami_del_documento`): `{documento, id, legami, righe}`,
una riga per legame di `vendite.fn_documento_legami` con `origine` (codice di `config.sorgenti`), `natura`
(CONSUMO/PROVENIENZA), `origine_id` e il nome del documento dall'altra parte
dal lineage (`origine_tipo_codice_interno`, `origine_codice`). `legami` e' il
numero da dichiarare. Alimenta la finestra di conferma dell'annullo.

Stati ammessi via questo endpoint: `CESSATO` e `ANNULLATO`, più ciò che la
matrice `config.transizioni_stati_contratti` ammette in futuro (il verbo di
stato la legge). **`ATTIVO` non è ammesso da questo endpoint**: il service
risponde `E_VENDITE_VALIDATION` (400) e indirizza a `POST /<id>/emetti/`
(sezione seguente), perché l'attivazione deve orchestrare atomicamente cambio
stato + generazione documento + allegati ("stato ATTIVO ⇒ esiste un documento
PDF persistito").

### Attivazione DRAFT→ATTIVO `POST /api/v1/vendite/contratti/<id>/emetti/`

Nuovo endpoint multipart 2026-05-28. Mirror del flusso offerta/preventivo
(`ApiOffertaEmetti` / `ApiPreventivoEmetti`). Sostituisce la transizione
`DRAFT→ATTIVO` precedentemente esposta via `/cambia-stato/`.

- Metodo: `POST`
- Content-Type: `multipart/form-data`
- Parser: `MultiPartParser`, `FormParser`
- Auth: JWT, `area_funzionale = "vendite"`. L'azione la dice la riga del
  passaggio verso lo stato di emissione (`PassaggioDocumento`): chiede
  `emetti_contratto`, 403 senza. Lo stato lo scrive il verbo
  `vendite.fn_cambia_stato_contratto`; un secondo «Emetti» →
  `E_DOC_GIA_NELLO_STATO` (409), senza un secondo PDF
- Body multipart:
  - `template_documento_id` (int, opzionale)
  - `tipo_documento_output_id` (int, opzionale)
  - `allegati` (file ripetuto, opzionale) — file secondari da persistere
    assieme al PDF principale del contratto
- Output `200`:

```json
{
  "data": {
    "contratto": { "...": "testata aggiornata dopo cambio stato" },
    "documento": {
      "documento_generato_id": 42,
      "uid": "...",
      "progressivo_sorgente": 1,
      "nome_file": "CONTRATTO_CNT0000001_v1.pdf",
      "size_bytes": 34567,
      "allegati_count": 1
    }
  },
  "meta": { "request_id": "..." }
}
```

- Semantica transazionale: la view apre `transaction.atomic()` che
  racchiude (in ordine): `ContrattiService().emetti(contratto_id)`
  (cambio stato DRAFT→ATTIVO + freeze `listino_versione_id` via trigger
  `trgfn_contratti_freeze_listino_versione`) →
  `_resolve_contesto_contratto` → `DocumentGenerationService.genera_documento(allegati=...)`.
  Se il render fallisce o un allegato viola MIME/size, l'atomic esterno
  rollbacka tutto → il contratto resta DRAFT, nessun record orfano.
  **Invariante di dominio**: `stato='ATTIVO'` ⇒ esiste almeno un record
  `documenti_generati` con `sorgente_tipo=CONTRATTO,
  sorgente_id=contratto.id`.
- Regole pre-attivazione (validate dal trigger DB):
  - Con listino: una versione in vigore oggi da congelare
    (`script.fn_check_listino_congelabile`), altrimenti
    `E_CONTRATTO_ATTIVAZIONE_SENZA_VERSIONE_LISTINO` (409, dal 2026-10-07)
  - Forma "senza_listino" → almeno una riga AGGIUNTA con prezzo
    valorizzato, altrimenti `E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE`
    (422)
  - Template documento applicabile (`PUBBLICATA` valido alla data)
- Errori:
  - `E_CONTRATTO_NON_TROVATO` (404) — contratto inesistente o fuori perimetro, dal verbo
  - `E_VENDITE_VALIDATION` (400) — contratto non in DRAFT
  - `E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE` (422) — forma senza_listino
    senza righe valorizzate
  - `E_CONTRATTO_ATTIVAZIONE_SENZA_VERSIONE_LISTINO` (409) — il listino non ha
    una versione in vigore oggi
  - `E_DOCUMENTI_VALIDATION` (400/422) — emittente non risolto / sorgente
    CONTRATTO non attiva / template assente / MIME/size allegato non
    ammesso
  - `E_DOCUMENTI_NOT_FOUND` (404)

### Righe `POST /api/v1/vendite/contratti/<id>/righe/`

Refactor 2026-05-15: le righe sono **eccezioni tipizzate** del listino. Il
campo `tipo_eccezione` e' obbligatorio in CREATE e immutabile in UPDATE
(per cambiare tipo serve DELETE + INSERT).

```json
{
  "articolo_id": "00000000-0000-0000-0000-000000000001",
  "tipo_eccezione": "OVERRIDE",
  "tipo_erogazione": "CANONE",
  "fonte_quantita_attesa": "FISSA",
  "prezzo_unitario": "25.50",
  "qta_operativa": "1",
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

- **AGGIUNTA su articolo presente nel listino**: bloccata dal guard
  `script.trgfn_righe_guard_articolo_ammesso` (lo stesso dell'offerta) →
  `E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO` (422). L'operatore avrebbe dovuto
  usare OVERRIDE. Il picker lo mostra gia' spento, col motivo.
- **Coerenza prezzo/tipo**: ESCLUSIONE con prezzo NOT NULL o
  OVERRIDE/AGGIUNTA con prezzo NULL → `E_VENDITE_VALIDATION` (pre-DB) o
  CHECK violation (DB).
- **Un'ESCLUSIONE e' vuota** (decisione di Tid, 2026-10-04,
  brief-db-righe-esclusione-solo-non-si-vende): dice solo «non si vende», quindi
  `prezzo_unitario`, `quantita`, `qta_operativa`, `uom_operativa_id`,
  `factor_to_base`, `tipo_erogazione`, `fonte_quantita_attesa`, `periodicita`,
  `generazione_canone` e `competenza_canone` restano NULL. «Escludi» manda solo
  `articolo_id` e `tipo_eccezione`. Un dato valorizzato lo rifiuta il guard
  `script.trgfn_righe_guard_esclusione_senza_dati` → `E_RIGA_ESCLUSIONE_CON_DATI`
  (400, campo in `error.fields`); CHECK `chk_contrighe_esclusione_senza_dati` come rete.
- **Un'ESCLUSIONE non si modifica** (decisione di Tid, 2026-10-04): si crea
  («Escludi») e si cancella («Ripristina articolo», `DELETE`), e basta. Ogni
  `UPDATE` che cambia una colonna di contenuto — prezzo, quantita', `attivo`,
  FK — lo rifiuta il guard `trg_contratti_righe_a05_guard_esclusione_immutabile_upd`
  (funzione `script.trgfn_righe_guard_esclusione_immutabile`, la stessa dell'offerta)
  → `E_CONTRATTO_ESCLUSIONE_NON_MODIFICABILE` (409). La riga non porta il verbo
  `MODIFICA` (solo `RIPRISTINA_ARTICOLO`), quindi il drawer non apre il form.
- **`tipo_erogazione` obbligatoria sulle righe che si fatturano**: OVERRIDE e AGGIUNTA si fatturano e devono dire come si erogano
  (canone, una tantum, a ore, a consumo); l'ESCLUSIONE no. CHECK
  `chk_contrighe_erogazione_per_tipo_eccezione` + guard
  `script.trgfn_righe_guard_erogazione_obbligatoria` →
  `E_RIGA_EROGAZIONE_OBBLIGATORIA` (400, campo `tipo_erogazione` in
  `error.fields`) in un PATCH che la toglie; in create, dal 2026-10-07, la riga
  la eredita dall'articolo. Il service non la pre-valida: parla il DB
  (2026-10-04, brief-db-erogazione-obbligatoria-righe-fatturate).
- **Il tipo non si cambia**, per nessuna riga: lock di colonna su
  `tipo_eccezione` (`dbops.automation_lock_columns`) →
  `E_CONTRATTO_RIGA_TIPO_ECCEZIONE_IMMUTABILE` (409). Dall'API il service
  rifiuta la chiave per primo (`E_VENDITE_VALIDATION`, col campo): il lock e'
  la rete per chi scrive da un'altra strada.
- **Unicita' eccezione**: max 1 eccezione `OVERRIDE`/`ESCLUSIONE` per coppia
  `(contratto_id, articolo_id)`. Stessa univocita' per AGGIUNTA.
- **Post-attivazione**: tutte le eccezioni sono immutabili (INSERT/UPDATE/DELETE
  bloccati dal building block `trgfn_doc_righe_lock_fuori_bozza`, dal
  2026-09-22) → `E_RIGA_DOC_NON_BOZZA` (409).
  La testata ha il suo lock (`trgfn_doc_testata_lock_fuori_bozza`, §PATCH testata).

`PATCH /api/v1/vendite/contratti/<id>/righe/<riga_id>/` aggiorna i campi
mutabili di una riga OVERRIDE o AGGIUNTA; `articolo_id` e `tipo_eccezione`
immutabili. Cambio di `prezzo_unitario` validato in coerenza col
`tipo_eccezione` esistente (pre-DB con messaggio parlante: il prezzo resta
obbligatorio). Su una riga ESCLUSIONE il PATCH arriva al DB e risponde
`E_CONTRATTO_ESCLUSIONE_NON_MODIFICABILE` (409): fino al 2026-10-04 il service
pre-validava il prezzo di un'esclusione con un 400 suo, ritirato perche' la
regola e' una sola, a DB.

`DELETE /api/v1/vendite/contratti/<id>/righe/<riga_id>/` hard-delete
(bloccato dal trigger se note collegate o contratto ATTIVO).

Su PATCH e DELETE la riga deve essere **del contratto dell'URL**: una riga di
un altro contratto (o inesistente) → `404 E_VENDITE_NOT_FOUND`, prima di ogni
altro controllo (2026-10-20). Fuori bozza → `409 E_RIGA_DOC_NON_BOZZA`.

#### Campo `fonte_quantita_attesa` (refactor 2026-05-19)

`fonte_quantita_attesa` (obbligatoria su OVERRIDE/AGGIUNTA, NULL sull'ESCLUSIONE:
CHECK `chk_contrighe_fonte_per_tipo_eccezione`, dal 2026-10-04)
dichiara da dove arriva la quantita' che il motore di fatturazione applichera'
in fase di push periodico verso le commesse. 4 valori (vocabolario
`config.erogazioni_fonti`):

| Valore | Semantica | Quantita' sulla riga |
| --- | --- | --- |
| `FISSA` | Quantita' contrattualizzata, snapshot in riga | `qta_operativa` obbligatoria e diversa da zero (`E_QTA_MISSING`, `chk_contrighe_qta_operativa_nonzero`) |
| `MANUALE` | Definita di volta in volta sul documento downstream | Vuota: una `qta_operativa` valorizzata e' rifiutata |
| `TIMESHEET` | Da rendicontazione ore (modulo timesheet futuro) | Vuota, come sopra |
| `LETTURE` | Da letture utility | Vuota, come sopra |

⛔ `DERIVATA_COMPONENTI` non c'e' piu' (I-D1 di
brief-db-offerta-emissione-ed-erogazione, 2026-10-21): il modello andava in un
verso solo, dal padre ai componenti, quindi una riga «derivata» o non aveva
componenti o era una FISSA con un altro nome. La quantita' del kit la porta la
fonte (un kit si vende solo FISSA, I-D6), e i componenti la seguono.

⭐ **La quantita' per fonte la decide il DB** (dal 2026-10-08,
brief-db-offerta-emissione-ed-erogazione F-1). L'elenco delle fonti che portano
la quantita' sta in `script.fn_fonte_porta_quantita` (la sola FISSA, dal
2026-10-21). Con una fonte a valle:

- `quantita` e' **calcolata**: la svuota il DB (`script.trgfn_qta_from_operativa`),
  all'INSERT e a ogni UPDATE. Il client non la manda: dal 2026-10-21 e' una
  chiave fuori contratto del payload di riga (400 `E_VENDITE_VALIDATION`);
- una `qta_operativa` valorizzata e' rifiutata: `E_RIGA_QUANTITA_CON_FONTE_A_VALLE`
  (400, campo `qta_operativa` in `error.fields`), guard
  `script.trgfn_righe_guard_quantita_per_fonte`; rete `chk_contrighe_quantita_per_fonte`.

Il form, al passaggio a una fonte a valle, manda `qta_operativa = null`.
⛔ Il service non normalizza: fino al 2026-10-08 `_apply_fonte_quantita_logic`
azzerava in silenzio `quantita`/`qta_operativa` (e solo sul contratto),
ritirato con `_FONTI_QUANTITA_DOWNSTREAM`.

⭐ **Come si eroga una riga lo dice l'articolo, dal DB** (dal 2026-10-07,
brief-db-offerta-emissione-ed-erogazione B-R1…B-R4). Le combinazioni
`(tipo_erogazione, fonte_quantita_attesa)` ammesse e quella di default le
dichiara la **tipologia di listino** dell'articolo
(`config.listini_tipologie_erogazioni`), o la sua **natura di vendita** se non
ha tipologia (`config.nature_vendita_erogazioni`); un composito (kit) le sole
combinazioni `FISSA` (I-D6, 2026-10-21). Sede unica: `vendite.fn_articolo_erogazioni`.

- **Eredità** (solo INSERT): erogazione e fonte non indicate si ereditano dalla
  combinazione di default; `CANONE` porta anche la sua `generazione_canone`
  (`script.trgfn_righe_default_erogazione_da_articolo`). Su un UPDATE che cambia
  la sola erogazione, la fonte si riallinea a quella che l'articolo ammette.
- **Perimetro**: una combinazione che l'articolo non ammette →
  `E_RIGA_EROGAZIONE_FUORI_PERIMETRO` (400, campo `tipo_erogazione` o
  `fonte_quantita_attesa`); un articolo la cui tipologia la utility del contratto
  non prevede → `E_RIGA_TIPOLOGIA_FUORI_UTILITY` (400, campo `articolo_id`).
  Guard `script.trgfn_righe_guard_erogazione_perimetro`, su INSERT e quando
  cambiano articolo, erogazione o fonte: le righe già scritte restano come sono
  (B-D6).
- **Rete**: la FK composta `(tipo_erogazione, fonte_quantita_attesa)` sul
  vocabolario `config.erogazioni_fonti` (23503), che ha preso il posto dei CHECK
  della matrice.
- **Il form** legge le combinazioni da `GET …/righe/erogazioni/` (sotto) e
  preseleziona il default.

⛔ Il service **non ne tiene una copia**: fino al 2026-10-07 `contratti_service`
ricopiava la matrice (`_FONTE_VIETATE_PER_TIPO_EROGAZIONE`) e i default
(`_FONTE_DEFAULT_PER_TIPO_EROGAZIONE`), ritirati. Una combinazione vietata la
rifiuta il DB (`E_RIGA_EROGAZIONE_FUORI_PERIMETRO`, sopra).

Riferimento doc dominio:
[docs/it/dev/work-done/refactor-contratti-fonte-quantita.md](../../../dev/work-done/refactor-contratti-fonte-quantita.md).

#### Workflow autorizzazioni prezzo L1+L2+L3 (refactor 2026-05-19)

CREATE e UPDATE riga sono cablati al BB orchestratore
`_pricing_gate_helpers.resolve_or_check_override_prezzo`. Matrice
gate per `tipo_eccezione` (decisione Alternativa B 2026-05-18):

| `tipo_eccezione` | L1 permesso `prezzo_override_manuale` | L2 soglia % | L3 richiesta_approvazione |
| --- | --- | --- | --- |
| `OVERRIDE` | sempre | sempre (vs prezzo resolver) | opt-in via payload |
| `AGGIUNTA` | sempre | condizionale: solo se resolver trova base (stadio 3 categoria_cliente o stadio 0 promo) | condizionale, simmetrico a L2 |
| `ESCLUSIONE` | skip (prezzo NULL, niente gate) | skip | skip |

**L1 — permesso override**. Senza azione di processo `prezzo_override_manuale`
sull'utente, il prezzo non puo' essere salvato manualmente. Codice errore:
`E_PRICING_OVERRIDE_NON_AUTORIZZATO` (403, `retryable=false`: senza permesso
non c'e' nulla da ritentare).

**L2 — soglia variazione %**. Il prezzo manuale viene confrontato con il
prezzo del resolver (`contratti_suggerisci_prezzo_riga`). Il delta % deve
restare entro la soglia configurata via parameter
`VENDITE_MAX_SCONTO_PCT` / `VENDITE_MAX_MAGGIORAZIONE_PCT` con cascata
estesa user → categoria_cliente → group → emittente → default (refactor
2026-05-15 cascata BA-aware). Se viola: `E_PRICING_SCONTO_ECCESSIVO` o
`E_PRICING_MAGGIORAZIONE_ECCESSIVA` (403, `retryable=true`: il FE puo'
offrire la CTA "Richiedi approvazione"). Codici stabili per distinguere
direzione downstream (dashboard / log / pratiche); user_message generico
"Variazione prezzo oltre il limite consentito per il tuo ruolo" (refactor
2026-05-20) — il `detail` riporta direzione esplicita "in diminuzione" /
"in aumento" + percentuale + limite.

**Fast path resolver per contratti** (refactor 2026-05-20). Il pricing gate L2
invoca `fn_resolve_prezzo_listino_v2` passando come 9° argomento il
`listino_versione_id` letto da `vendite.fn_documento_listino_operativo`
(la fissata se ATTIVO, altrimenti quella in vigore oggi: la stessa delle righe a
video; dal 2026-10-07, prima una copia Python che la cercava a `valido_dal`).
Questo
attiva lo stadio `CONTRATTO_LISTINO` del resolver e impedisce il drift
verso lo stadio `CATEGORIA` (che pesca da `categorie_clienti_listini` un
listino diverso da quello del contratto). Senza fast path il check L2
confronterebbe il prezzo OVERRIDE con un prezzo categoria semanticamente
non pertinente. Quando il fast path attivo trova il prezzo, l'output del
resolver ha `contratto_id` / `tipo_eccezione` = NULL e
`tipo_variazione_applicata = 'NESSUNA'` (nessun lookup contratto).

**L3 — workflow approvazione**. Quando il payload include
`richiesta_approvazione=true` (booleano JSON: una stringa come `"true"` →
`400 E_VENDITE_VALIDATION`), una violazione L2 non solleva ma apre una
pratica `APPROVAZIONE_PREZZO` e salva la riga con
`stato_approvazione_prezzo='PENDING'` + `pratica_approvazione_prezzo_id`
valorizzato. Il trigger DB `trg_contratti_righe_a10_guard_pending_upd`
blocca modifiche struttura sulla riga finche' l'admin non chiude la
pratica via `POST /api/v1/vendite/righe-contratto/<riga_id>/approva-prezzo/`
o `POST /api/v1/vendite/righe-contratto/<riga_id>/rifiuta-prezzo/`
(simmetrici agli endpoint preventivi `/righe/<id>/...`).

Il meta della pratica include `sorgente='contratto'` + `riga_contratto_id`
per routing FE corretto degli endpoint approva/rifiuta. La coda
`GET /api/v1/vendite/approvazioni-prezzo/` espone item da entrambe le
sorgenti (preventivi + contratti); ogni item include `sorgente` per
permettere alla UI ApprovazioniPrezzoListView di dispatchare al path
corretto.

**Integrazione FE** (`ContrattoRigheDrawer.vue`, simmetrico a
`PreventiviRigaForm.vue`):

- Il save normale (`onSave`) intercetta specificamente i codici
  `E_PRICING_SCONTO_ECCESSIVO` / `E_PRICING_MAGGIORAZIONE_ECCESSIVA` e
  mostra un banner inline (no toast) con la CTA "Richiedi approvazione".
- Il click sulla CTA invoca `onRichiediApprovazione` che ri-tenta il save
  aggiungendo `richiesta_approvazione: true` al payload. In caso di
  riuscita la riga e' salvata in `PENDING` e l'operatore riceve un toast
  esplicito. Eventuali errori del retry tornano sul toast standard.
- Per le righe gia' in `PENDING` il trigger DB `_a10_guard_pending_upd`
  blocca ogni modifica struttura: la UI mostra la pratica nella coda
  approvazioni dell'admin (vedi sopra) — l'operatore deve attendere
  l'esito o chiedere all'approver di rifiutare per riprovare.

Per i 3 tipi `tipo_eccezione`:

- `OVERRIDE` su articolo del listino → workflow completo (L1+L2+L3)
- `AGGIUNTA` fuori-listino → workflow attivo solo se il resolver trova
  comunque una base prezzo (matrice categoria_cliente_listino o promo).
  Senza base, il prezzo manuale e' accettato sotto L1 senza confronto.
- `ESCLUSIONE` → workflow non applicabile (prezzo NULL per design).

### Contesto pricing `GET /api/v1/vendite/contratti/<id>/contesto-pricing/`

Endpoint readonly mutuato dal pattern preventivi (`/preventivi/<id>/contesto-pricing/`).
Ritorna la "forma" derivata e i riferimenti pricing per il banner FE:

```json
{
  "data": {
    "contratto_id": 42,
    "forma": "con_listino",
    "stato_codice_interno": "ATTIVO",
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

Campi di drift (sempre presenti):
`listino_versione_corrente_id` / `listino_versione_corrente_codice` — la
versione `ATTIVA` del listino in vigore oggi (`null` se non ce n'è);
`drift_versione_listino` — `true` quando il contratto ha una versione fissata
e quella in vigore oggi è un'altra (in DRAFT mai).

Contratto inesistente o fuori perimetro → `404 E_VENDITE_NOT_FOUND` (fino al
2026-10-20 rispondeva `200` con `{}`).

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

#### Come si eroga un articolo `GET /api/v1/vendite/contratti/<id>/righe/erogazioni/?articolo_id=<uuid>`

Le combinazioni (`tipo_erogazione`, `fonte_quantita_attesa`) che una riga con
l'articolo può avere sul contratto, col **default in testa** (`e_default`),
`generazione_canone` da proporre sulle `CANONE` e `origine`
(`TIPOLOGIA` | `NATURA` | `DISTINTA`). Envelope dei lookup:
`{"data": {"results": [...]}}`. Lettura del form delle righe, gemella
dell'offerta (base `RigaErogazioniView`, contratto completo in
[api_offerte.md](api_offerte.md) § «Come si eroga un articolo»): le righe di
`vendite.fn_documento_riga_erogazioni`, la stessa sede dell'eredità e del guard.
Lista vuota = l'articolo non si vende su questo contratto (tipologia fuori dalla
utility). Contratto che non si vede → 404; `articolo_id` assente o non UUID →
400 col campo.

#### Preview componenti `POST /api/v1/vendite/contratti/<id>/righe/preview-componenti/`

```json
{
  "articolo_id": "abc-uuid",
  "uom_operativa_id": 2,
  "quantita": "1"
}
```

> `quantita` qui è la **quantità padre transiente** per cui prezzare il bundle
> (il FE passa `form.qta_operativa`), non la colonna riga: il preview è read-only
> e non scrive nulla.

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
articolo/uom/iva + flag `obbligatorio` e modo `esposizione_in_fattura` (JOIN
runtime su `articoli_componenti`).

#### Update componente `PATCH /api/v1/vendite/contratti/<id>/righe/<rid>/componenti/<cid>/`

```json
{
  "prezzo_unitario": "12.50",
  "attivo": true,
  "meta": {}
}
```

Whitelist dell'operatore (`COMPONENTE_PATCH_OPERATORE`): `prezzo_unitario`,
`attivo`, `meta`. Ogni altra chiave → `400 E_VENDITE_VALIDATION`. Un
`prezzo_unitario` **non nullo** richiede l'azione `prezzo_override_manuale`
(`403 E_PRICING_OVERRIDE_NON_AUTORIZZATO`) e scrive `origine_prezzo =
MANUALE`; `null` non chiede il permesso e azzera l'origine.

Anti-tampering URL: `riga_id` URL deve matchare riga reale del
componente; mismatch → `E_VENDITE_NOT_FOUND`. Solo contratto in stato
DRAFT modificabile (altrimenti `E_RIGA_DOC_NON_BOZZA`, 409: dal 2026-09-22
il pre-check BE — BB `richiedi_righe_in_bozza` — usa lo stesso codice del
trigger su `contratti_righe`).

#### Delete componente `DELETE /api/v1/vendite/contratti/<id>/righe/<rid>/componenti/<cid>/`

Soft delete (`attivo=FALSE`). Il trigger DB di ricalcolo padre lo esclude
dalla SUM. Idempotente: se gia' soft-deleted ritorna `{deleted: false}`
senza errore. Stesso scope check anti-tampering di update.

### Lista righe `GET /api/v1/vendite/contratti/<id>/righe/lista/` (+ `export/`)

Le righe **operative** del contratto come lista configurabile
`vendite.contratto_righe` (103), paginata, con ricerca, ordinamento ed export,
sulla funzione `vendite.fn_contratto_righe_preview` (dal 2026-09-30, lotto D del
brief-db-liste-righe-documento). Contratto comune alle righe dei documenti di
vendita: [api_righe_documento.md](api_righe_documento.md).

### ~~Preview righe contratto `GET …/<id>/righe-preview/`~~ — ritirato il 2026-10-04

L'anteprima intera delle righe operative non esiste più come endpoint
(brief-db-liste-righe-documento §9.15): il suo solo consumatore, il drawer delle
righe, legge la lista `…/righe/lista/` qui sopra, sulla stessa funzione
`vendite.fn_contratto_righe_preview`. Il banner «listino senza versione oggi»
viene da `…/contesto-pricing/`. La lettura completa della funzione resta nel
backend (`ContrattiRepository.list_righe_preview`) per il contesto di stampa e
`righe_count` del dettaglio.

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

Endpoint del motore documentale parametrico per la sorgente `CONTRATTO`.
Risolvono il contesto comune (contratto + emittente fiscale + sorgente
attiva) via helper condiviso
`apps.documenti.api.contesto_helpers.resolve_contesto_documentale` (vedi
[api_documenti_helpers](../../documenti/manual/api_documenti_helpers.md)).

| Metodo | Path | Effetto |
| --- | --- | --- |
| `GET` | `/api/v1/vendite/contratti/<id>/documenti/` | Lista documenti generati dal contratto (paginata, scope emittente) — contratto di lista in [api_documenti_per_sorgente](../../documenti/manual/api_documenti_per_sorgente.md) §3.4 |
| `POST` | `/api/v1/vendite/contratti/<id>/documenti/anteprima/` | Render PDF temporaneo, non persistito |
| `POST` | `/api/v1/vendite/contratti/<id>/documenti/genera/` | Persiste PDF + record DB + evento `GENERATO` (per contratti già ATTIVI: ristampe successive all'attivazione) |
| `GET` | `/api/v1/vendite/contratti/<id>/documenti/<documento_id>/file/` | Download PDF principale + evento `SCARICATO` |
| `GET` | `/api/v1/vendite/contratti/<id>/documenti/<documento_id>/allegati/` | Lista files del documento (principale + allegati) |
| `POST` | `/api/v1/vendite/contratti/<id>/documenti/<documento_id>/allegati/` | Append allegati multipart su documento esistente |

> L'**attivazione iniziale** (DRAFT→ATTIVO con generazione del documento
> originale) passa per il nuovo endpoint `/emetti/` multipart (vedi
> sezione "Attivazione DRAFT→ATTIVO" sopra), non per `documenti/genera/`.
> Questo endpoint `genera/` resta per ristampe/varianti successive su
> contratti già ATTIVI.

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

**Endpoint `allegati/` (nuovi 2026-05-28)**:

- GET: ritorna `{"data": {"principale": {...}, "allegati": [{...}, {...}]}}`.
  Consumato dal row-expand di `DocumentiGeneratiSorgenteList` per popolare
  `filesPerDoc`
- POST: multipart con campo ripetuto `allegati`. Modalità append
  post-attivazione. Non rigenera il PDF principale, aggiunge solo file
  secondari al documento esistente. MIME/size validati dal service

### Regole stampa contratto

- In stato `DRAFT`, il frontend usa `anteprima/`: il PDF viene renderizzato ma
  non viene persistito in `documenti.documenti_generati`.
- La transizione `DRAFT → ATTIVO` passa ora per l'endpoint dedicato
  `POST /<id>/emetti/` (multipart), che in `transaction.atomic()` cambia
  stato (con freeze `listino_versione_id` via trigger) e persiste il PDF
  contrattuale + allegati come `documenti_generati` con
  `sorgente=CONTRATTO`. Invariante: `stato=ATTIVO` ⇒ almeno un record
  documentale generato.
- Dopo l'attivazione, ristampe/download usano il documento salvato; non viene
  rigenerato il layout storico. Nuove versioni esplicite si ottengono via
  `POST documenti/genera/`.
- Allegati post-attivazione: append via
  `POST documenti/<doc_id>/allegati/`. Non rigenera il principale.
- La lista `GET /documenti/` espone i documenti gia' generati per il contratto,
  ed e' la fonte usata dal drawer e dalla tabella ricerca per le ristampe.
- La generazione richiede un `emittente_fiscale_id` sul contratto e almeno una
  versione `PUBBLICATA` attiva del template applicabile alla data corrente.

### Indirizzi documento `GET/POST /<id>/indirizzi/` + `DELETE /<id>/indirizzi/<iid>/`

BB condiviso sui 5 domini vendite (ambito CONTRATTI (FATT, CON, FORNITURA); editabile solo DRAFT):
contratto completo in [api_indirizzi_documento.md](api_indirizzi_documento.md).


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
    "stato_codice_interno": "DRAFT", "stato_codice": "DRAFT", "stato_descrizione": "Bozza",
    "listino_id": 100, "listino_codice": "LST-GAS-2026",
    "tipo_variazione_globale": "PERCENTUALE", "valore_variazione_globale": "10",
    "categoria_cliente_id_snapshot": 3,
    "categoria_cliente_snapshot_codice": "GOLD",
    "categoria_cliente_snapshot_descrizione": "Cliente gold",
    "valuta_id": 1, "valuta_codice": "EUR", "valuta_descrizione": "Euro",
    "valido_dal": "2026-01-01", "valido_al": "2026-12-31",
    "utility": {"id": 5, "tipo_utenza_codice": "DOM", ...},
    "righe": [{"id": 99, "articolo_codice": "ART-001", "is_composito": false, "prezzo_unitario": "25.50"}, ...]
  }
}
```

Ogni riga espone `is_composito` denormalizzato (JOIN `catalogo.articoli`) sia
nel detail (`/righe` interne al contratto) sia nella lista delle righe
operative (`/righe/lista/`). Driver lato FE per detection auto-apertura
`ComponentiDialog` e visibilita' `ComponentiPanel` in EDIT senza round-trip
extra al catalogo.

## Note del contratto

| | |
|---|---|
| **Lista / creazione** | `GET` `POST` `/api/v1/vendite/contratti/{contratto_id}/note/` |
| **Dettaglio / modifica / cancellazione** | `GET` `PATCH` `DELETE` `/api/v1/vendite/contratti/{contratto_id}/note/{note_id}/` |

Contratto identico agli altri cinque domini — payload, filtri,
`Idempotency-Key` obbligatoria sulla creazione, codici errore: **una pagina
sola**, [api_note_documento](../../core/manual/api_note_documento.md). Qui sotto solo il delta: partizione
`vendite.note_contratto`, `target_tipo = 'CONTRATTO'`, note di riga ancorate
alle righe di contratto via `target_riga_id`.

## Regole

1. Numero contratto generato dalla funzione madre DB `vendite.fn_create_contratto` (mai in payload).
2. Stato iniziale DRAFT; transizioni via endpoint dedicato.
   La transizione `DRAFT -> ATTIVO` genera e salva il documento contratto +
   fissa `listino_versione_id` alla versione corrente del listino.
3. Cliente (`billing_account_id`, `istanza_utility_id`) modificabile solo in
   DRAFT; utility, numero e stato mai — fuori bozza per cambiare cliente si
   crea un nuovo contratto.
4. **Forma "senza_listino"** valida a livello DB solo se esistono righe
   AGGIUNTA con `prezzo_unitario` valorizzato. Il guard di attivazione
   solleva `E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE` (422). Sostituisce i
   vecchi guard di "modalita' C" rimossi col refactor 2026-05-15.
5. **Profilo A — congelamento post-attivazione**: dopo `DRAFT → ATTIVO`,
   tutti i campi pricing della testata (`listino_id`, `listino_versione_id`,
   `tipo_variazione_globale`, `valore_variazione_globale`) sono immutabili,
   cosi' come le eccezioni in `contratti_righe`. Tentativi di modifica
   sollevano `E_DOC_CONDIZIONI_FUORI_BOZZA` (409, lock di testata, dal
   2026-10-10) e `E_RIGA_DOC_NON_BOZZA` sulle righe. Per modifiche
   sostanziali serve un nuovo contratto.
6. **Coerenza coppia variazione globale**: `tipo_variazione_globale` e
   `valore_variazione_globale` entrambi NULL o entrambi NOT NULL
   (pre-validation `_validate_variazione_globale_coppia_coerente`).
7. **Coerenza prezzo/tipo_eccezione**: ESCLUSIONE ↔ prezzo NULL,
   OVERRIDE/AGGIUNTA ↔ prezzo NOT NULL. Validato in service (pre-DB con
   messaggio parlante; in UPDATE solo OVERRIDE/AGGIUNTA, perche' un'ESCLUSIONE
   non si modifica affatto) e in DB (`chk_contrighe_prezzo_per_tipo_eccezione`).
8. Tipo/classe utenza obbligatori per utility con dimensione (es. GAS,
   EE), vietati per utility commercio (Base). Coerenza
   `classi_utenze.tipo_utenza_id = contratti_utilities.tipo_utenza_id`
   imposta dal trigger DB.
9. EXCLUDE no-overlap: un solo contratto **attivo** per
   `(BA, istanza_utility, utility, ambito)` su validita' sovrapposta.
   **DRAFT-scope (2026-06-02)**: i contratti in DRAFT sono **esclusi** dal
   vincolo (colonna generata `partecipa_overlap_snapshot = NOT abortito AND
   NOT draft`). Conseguenze: due bozze sovrapposte sono ammesse, e una bozza
   puo' sovrapporsi a un contratto attivo (preparazione della successione);
   il blocco scatta **solo all'attivazione** (`POST .../emetti/`). La regola la
   dice il DB, in un posto solo (`script.fn_check_contratto_sovrapposto`,
   2026-10-19): la capability spegne «Attiva» col motivo che **nomina il
   contratto in conflitto** (`reason_key`
   `vendite.contratti.azione_reason.contratto_sovrapposto`), e il guard della
   transizione rifiuta con `E_CONTRATTO_OVERLAP_ESISTENTE`. Il backend non ha una
   copia della regola.
   ⭐ Prima del sovrapposto, dal 2026-10-21 (H-R4 di
   brief-db-offerta-emissione-ed-erogazione), le **righe**: una riga che la
   regola intera non ammette piu' (articolo, erogazione e fonte, giudicati sui
   dati di oggi: listino operativo, vocabolario del perimetro) spegne «Attiva»
   col motivo `RIGA_NON_AMMESSA` (`reason_key`
   `common.azione_reason.riga_non_ammessa`, valori: documento e articolo) e la
   transizione e' rifiutata con `E_DOC_RIGA_NON_AMMESSA` (400, campo
   `articolo_id`). Sede: `script.fn_check_righe_documento`, la stessa
   dell'emissione dell'offerta. In DRAFT le righe si correggono: nessuna uscita
   nuova.
10. `categoria_cliente_id_snapshot` e' congelato alla creazione del
    contratto (dal trigger DB, che lo popola dal BA). Rappresenta la
    categoria commerciale del cliente al momento della stipula. Non e'
    modificabile in update. In risposta vengono esposti anche
    `categoria_cliente_snapshot_codice` e
    `categoria_cliente_snapshot_descrizione` (JOIN display).

### Lineage / genealogia (brief-be-fe-lineage, 2026-07-15)

- **Colonne lineage in lista** (Fase B): la lista espone anche `fase`
  (proiezione normalizzata dallo stato), `pratica_id`/`pratica_numero`/
  `n_pratiche` (pratica collegata), `frontiera_tipo_id` +
  `frontiera_tipo_codice_interno` e `frontiera_natura_doc_codice_interno`
  (dalla vista, non piu' decodificati dal repository: changeSet `20260829-01/02`
  — ⛔ il nome e' cambiato, e con lui la sorgente),
  `frontiera_codice`/`frontiera_stato_codice_interno`/`frontiera_fase`,
  `n_discendenti_attivi`, `is_transitato` — dalla vista canonica estesa
  (LEFT JOIN `vendite.vw_documento_lineage`). Colonne configurabili
  `pratica`/`fase`/`transito` visibili di default (seed preset). `order_by`
  accetta anche `pratica_numero` e `fase` (la frontiera NON e' ordinabile).
- **Passaggi** `GET /api/v1/vendite/contratti/<id>/passaggi/` — genealogia del
  documento: pratica + frontiera + catena transiti in entrambe le direzioni.
  Contratto completo nel manuale del BB condiviso:
  [api_lineage_passaggi.md](api_lineage_passaggi.md).

## Codici errore

| Codice | HTTP | Origine | Trigger DB |
|---|---|---|---|
| `E_VENDITE_VALIDATION` | 400 | Service (struttura/coerenza coppia variazione globale, tipo_eccezione obbligatorio + coerenza prezzo, componenti_overrides non finito o non numerico, preview senza emittente/utility/valido_dal) | — |
| `E_VENDITE_NOT_FOUND` | 404 | Service (contratto/riga/componente; riga o componente non del contratto/riga dell'URL; contesto-pricing di contratto inesistente o fuori perimetro) | — |
| `E_PRICING_OVERRIDE_NON_AUTORIZZATO` | 403 | Service — prezzo manuale (riga o componente) senza l'azione `prezzo_override_manuale` | — |
| `E_VENDITE_DUPLICATO` | 400 | UNIQUE `uq_contratti_numero` o `uq_contratti_utilities_contratto_id` o `uq_contrighe_one_eccezione_per_articolo` o `uq_contrighe_one_aggiunta_per_articolo` | — |
| `E_VENDITE_FK` | 400 | FK su BA/istanza/utility/listino/listino_versione/parent/stato/articolo/UoM/tipo/classe utenza/categoria cliente snapshot | — |
| `E_CONTRATTO_OVERLAP_ESISTENTE` | 409 | Il guard della transizione verso ATTIVO (messaggio che nomina il contratto in conflitto) **oppure**, sulla corsa, l'EXCLUDE gist `ex_contratti_no_overlap` (testo del ripiego, senza il numero). Scatta all'**attivazione** (DRAFT esclusi dal vincolo, vedi Regole §9). Fino al 2026-10-19 era `E_VENDITE_CONTRATTO_OVERLAP` | `script.fn_check_contratto_sovrapposto` |
| `E_DOC_DATI_COLLEGATI_NON_BOZZA` | 409 | DB P0001 (2026-10-11) — **utility e indirizzi** su contratto fuori bozza (create/update utility, indirizzi). Al posto di `E_CONTRATTO_NON_MODIFICABILE`, che il service sollevava come copia della regola e non solleva piu' | `trgfn_doc_righe_lock_fuori_bozza` (montato sui satelliti) |
| `E_DOC_RIGA_NON_AMMESSA` | 400 | DB P0001 (2026-10-21) — attivazione con una riga che la regola intera non ammette piu'. Campo `articolo_id`; `motivo_riga` nel contesto | `vendite.trgfn_contratti_guard_transizione_stato` (`script.fn_check_righe_documento`) |
| `E_CONTRATTO_VALIDO_AL_RETROATTIVO` | 409 | DB P0001 (cessazione manuale con `valido_al < CURRENT_DATE`, bypass GUC per job notturno) | `trgfn_contratti_a10_guard_cessazione_no_retroattiva` |
| `E_DATA_AL_MINORE_DAL` | 400 | DB P0001, campo `valido_al` — `valido_al < valido_dal` in create, PATCH testata e cessazione. Il service non lo anticipa (dal 2026-09-23). Frase del catalogo con le due date, soluzione in `hint`: `raise_from_database_error` fa vincere il codice del DB anche fuori da `_KNOWN_DB_ERROR_MARKERS` | `script.trgfn_guard_date_validita` (automazione `DATE_VALIDITA`) |
| `E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE` | 422 | DB P0001 (refactor modalita 2026-05-15) — attivazione di contratto senza listino senza righe AGGIUNTA con prezzo valorizzato | `trgfn_contratti_freeze_listino_versione` (guard interno) |
| `E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO` | 422 | DB P0001 (refactor 2026-05-15) — INSERT/UPDATE riga `tipo_eccezione=AGGIUNTA` per articolo gia' presente nel listino di riferimento | `script.trgfn_righe_guard_articolo_ammesso` (dal 2026-10-13; prima `trgfn_righe_guard_aggiunta_fuori_listino`, ritirato) |
| `E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA` | 422 | DB P0001 (§6.1 2026-05-16) — INSERT/UPDATE riga `tipo_eccezione=ESCLUSIONE` per articolo che e' `articolo_figlio_id` in un bundle del listino del contratto. L'ESCLUSIONE si applica al padre bundle, non al singolo componente | `script.trgfn_righe_guard_articolo_ammesso` (dal 2026-10-13; prima `trgfn_righe_guard_esclusione_figlio_bundle`, ritirato) |
| `E_ARTICOLO_SENZA_EROGAZIONE` | 400 | DB P0001 (2026-10-13) — AGGIUNTA o OVERRIDE di un articolo che non si eroga in nessun modo. Campo `articolo_id`. Stesso codice sull'offerta | `script.trgfn_righe_guard_articolo_ammesso` |
| `E_RIGA_ECCEZIONE_SENZA_LISTINO` · `E_RIGA_ECCEZIONE_FUORI_LISTINO` | 400 | DB P0001 (2026-10-13) — OVERRIDE o ESCLUSIONE su un contratto senza listino operativo, o di un articolo che il listino non ha. Campo `articolo_id`. Stessi codici sull'offerta | `script.trgfn_righe_guard_articolo_ammesso` |
| `E_ARTICOLO_SOLO_COMPONENTE` · `E_ARTICOLO_KIT_SENZA_COMPONENTI` | 400 | DB P0001 (2026-10-13 / 2026-10-14) — AGGIUNTA o OVERRIDE di un articolo usabile solo dentro un kit, o di un kit senza componenti attivi. Campo `articolo_id`. Stessi codici sull'offerta e sulle righe di preventivo, ordine e bolla | `script.trgfn_righe_guard_articolo_ammesso` |
| `E_CONTRATTO_ESCLUSIONE_NON_MODIFICABILE` | 409 | DB P0001 (2026-10-04) — UPDATE di una riga ESCLUSIONE che cambia una colonna di contenuto (ammesse le sole tecniche). Parla prima dei guard `_a10_` e del CHECK sul prezzo. Nessun valore nel messaggio | `script.trgfn_righe_guard_esclusione_immutabile` (fascia `_a05_`) |
| `E_CONTRATTO_RIGA_TIPO_ECCEZIONE_IMMUTABILE` | 409 | DB P0001 (2026-10-04) — UPDATE che cambia `tipo_eccezione` di una riga qualunque. Dall'API non si raggiunge: il service rifiuta la chiave prima | lock di colonna generato (`trg_contratti_righe_a10_lock_columns_upd`) |
| `E_RIGA_EROGAZIONE_OBBLIGATORIA` | 400 | DB P0001 (2026-10-04) — PATCH che toglie `tipo_erogazione` a una riga OVERRIDE/AGGIUNTA (in create, dal 2026-10-07, la riga la eredita dall'articolo). Campo `tipo_erogazione` in `error.fields`. Stesso codice sulle eccezioni dell'offerta | `script.trgfn_righe_guard_erogazione_obbligatoria` |
| `E_RIGA_EROGAZIONE_FUORI_PERIMETRO` | 400 | DB P0001 (2026-10-07) — combinazione `(tipo_erogazione, fonte_quantita_attesa)` che l'articolo non ammette. Campo in `error.fields`. Stesso codice sull'offerta | `script.trgfn_righe_guard_erogazione_perimetro` |
| `E_RIGA_TIPOLOGIA_FUORI_UTILITY` | 400 | DB P0001 (2026-10-07) — articolo con una tipologia di listino che la utility del contratto non prevede. Campo `articolo_id`. Stesso codice sull'offerta | `script.trgfn_righe_guard_erogazione_perimetro` |
| `E_RIGA_QUANTITA_CON_FONTE_A_VALLE` | 400 | DB P0001 (2026-10-07, rivisto 2026-10-08) — `qta_operativa` valorizzata con una fonte a valle (MANUALE, LETTURE, TIMESHEET). Campo `qta_operativa`. `quantita` la svuota il DB, non e' materia del rifiuto. Stesso codice sull'offerta | `script.trgfn_righe_guard_quantita_per_fonte` |
| `E_DOC_LISTINO_UTILITY_DIVERSA` | 400 | DB P0001 (2026-10-08) — il listino e' di un'altra utility. Campo `listino_id`. Stesso codice sull'offerta | `script.trgfn_doc_guard_listino_documento` |
| `E_DOC_LISTINO_EMITTENTE_DIVERSO` | 400 | DB P0001 (2026-10-08) — il listino e' di un'altra azienda emittente (anche uno che chi agisce non legge, per RLS). Campo `listino_id`. Stesso codice sull'offerta | `script.trgfn_doc_guard_listino_documento` |
| `E_CONTRATTO_ATTIVAZIONE_SENZA_VERSIONE_LISTINO` | 409 | DB P0001 (2026-10-07, A-D2) — attivazione di un contratto con listino che non ha una versione in vigore oggi | `trgfn_contratti_freeze_listino_versione` |
| `E_RIGA_ESCLUSIONE_CON_DATI` | 400 | DB P0001 (2026-10-04) — INSERT di un'ESCLUSIONE con un dato di fatturazione valorizzato. Campo (il primo valorizzato) in `error.fields`. Stesso codice sull'offerta | `script.trgfn_righe_guard_esclusione_senza_dati` |
| `E_ARTICOLO_ESCLUSO_DA_CONTRATTO` | 422 | DB P0001 (resolver pricing) — tentativo di prezzare un articolo che ha eccezione ESCLUSIONE sul contratto attivo del cliente | `fn_resolve_prezzo_listino_v2` (STADIO 1 eccezioni) |
| `E_DOC_IDENTITA_FUORI_BOZZA` · `E_DOC_CONDIZIONI_FUORI_BOZZA` · `E_DOC_CLIENTE_FUORI_BOZZA` · `E_DOC_SORGENTE_FUORI_BOZZA` · `E_DOC_CHIUSO` | 409 | DB P0001 (2026-10-10, brief-db-testata-dopo-emissione) — PATCH testata su una colonna che lo stato non ammette, una famiglia per codice; `E_DOC_CHIUSO` a contratto cessato o annullato. Al posto di `E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE` (ritirato) e della tabella per stato del service | `trgfn_doc_testata_lock_fuori_bozza` |
| `E_RIGA_DOC_NON_BOZZA` | 409 | DB P0001 (building block, 2026-09-22 — D7 di brief-db-partita-merce-per-documento) — INSERT/UPDATE/DELETE di un'eccezione su contratto non più in bozza; stesso codice sulle righe di DDT e (DELETE) di ordine. Lo solleva **anche il pre-check BE** (BB `richiedi_righe_in_bozza`) su righe e componenti, con la frase a catalogo (etichetta «Contratto <numero>», stato, verbo) | `trgfn_doc_righe_lock_fuori_bozza` + service |
| `E_DOC_LISTINO_CAMBIO_CON_RIGHE` · `E_DOC_LISTINO_RIMOZIONE_CON_ECCEZIONI` | 422 | DB P0001 (2026-10-11) — PATCH testata che mette o sostituisce `listino_id` con righe attive, o lo toglie con eccezioni OVERRIDE/ESCLUSIONE attive. Campo `listino_id`. Stessi codici sull'offerta. Al posto di `E_CONTRATTO_CAMPI_BLOCCATI_CON_RIGHE` ed `E_CONTRATTO_LISTINO_RIMOZIONE_CON_ECCEZIONI` (ritirati, erano controlli del service) | `script.trgfn_doc_guard_listino_con_righe` |
| `E_PRICING_SCONTO_ECCESSIVO` / `E_PRICING_MAGGIORAZIONE_ECCESSIVA` | 403 (retryable=True) | Service (refactor §3-bis-E) — gate L2 sulla variazione globale del contratto al PATCH testata, e sul prezzo manuale di riga. Cascata user → categoria → group → emittente. `VALORE_FISSO` non è un tipo ammesso in testata (400) | — |
| `E_CONTRATTO_UTILITY_TIPO_CLASSE_OBBLIGATORI` | 400 | DB P0001 | `trgfn_contratti_utilities_guard_tipo_classe` |
| `E_CONTRATTO_CLASSE_TIPO_INCOERENTE` | 400 | DB P0001 | `trgfn_contratti_utilities_guard_tipo_classe` |
| `E_CONTRATTO_UTILITY_SENZA_DIMENSIONE_TIPO_CLASSE_VIETATI` | 400 | DB P0001 | `trgfn_contratti_utilities_guard_tipo_classe` |
| `E_DOC_COMPOSITO_BOM_VUOTA` | 400 | DB P0001 (auto-init componenti riga: articolo composito senza figli BoM validi alla data) | `fn_contratto_riga_componenti_init` |
| `E_DOC_COMPONENTE_OBBLIGATORIO` | 400 | DB P0001 (tentativo di disattivare un componente obbligatorio) | `trgfn_contratti_righe_componenti_guard_obbligatorio` |
| `E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO` | 400 | DB P0001 (override prezzo 0 su componente obbligatorio) | `trgfn_contratti_righe_componenti_guard_prezzo` |
| `E_BOM_IVA_DISCORDANTE` | 400 | DB P0001 (IVA componente diversa da padre — vincolo modello unificato) | trigger catalogo IVA coerenza |
| `E_DOCUMENTI_VALIDATION` | 400/422 | Endpoint `/emetti/` + sezione "Documenti contratto": emittente non risolto, sorgente CONTRATTO non attiva, template assente/non applicabile, MIME allegato non ammesso, size oltre limite. Sollevato da `apps.documenti.api.contesto_helpers.resolve_contesto_documentale` o da `DocumentGenerationService` | — |
| `E_DOCUMENTI_NOT_FOUND` | 404 | Endpoint `/emetti/` + sezione "Documenti contratto": contratto o documento atteso non trovato dal resolver di contesto | — |

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

- `trg_contratti_righe_z90_propaga_qta_componenti_upd` (su `contratti_righe`)
  → `script.trgfn_componenti_propaga_qta` — ricalcolo `quantita` componente
  al cambio `quantita` riga padre.
- `trg_contratti_righe_componenti_a10_guard_pending_upd`
  → `script.trgfn_componenti_guard_pending` — immutabilita' componenti
  quando `stato_approvazione_prezzo = PENDING` (L3 approvazioni prezzo).
  Generico dal 2026-05-26 (`20260526-23`): sostituisce il vecchio
  `trgfn_contratti_righe_componenti_guard_pending`, droppato il 2026-08-04.

**Stati** gestiti via `config.stati_doc_contratti`
(DRAFT/ATTIVO/CESSATO/ANNULLATO), scritti solo dai verbi: «Emetti» dal verbo di
stato `vendite.fn_cambia_stato_contratto`, la cessazione da
`vendite.fn_cessa_contratto` con la sua data (oggi = immediata, futura =
programmata, passata rifiutata), l'annullo da `vendite.fn_annulla_contratto`. Il
job `fn_apply_chiusura_scadenze` chiude i contratti scaduti col verbo
`vendite.fn_cessa_contratti_scaduti`.
