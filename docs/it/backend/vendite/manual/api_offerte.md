# API Offerte commerciali `vendite.offerte_commerciali`

## Scopo

CRUD operativo delle **offerte commerciali**, documento pre-contrattuale che
propone al cliente le condizioni quadro per una specifica utility prima della
formalizzazione in contratto. Espone sub-entita' **eccezioni** (mirror di
`contratti_righe`) e **utility 1:1** (estensione 1:1 con dati di utenza).

L'offerta e' specchio strutturale del contratto: stessa testata, stesso enum
`tipo_eccezione`, stessa cardinalita' utility. La fedelta' garantisce che il
push offerta -> contratto (in arrivo allo step DB 8) sia una copia 1:1 senza
conversioni semantiche.

### Modello (decisioni §5 chiuse 2026-05-23)

- **Mono-utility per offerta**: `istanza_utility_id` e `utility_id` NOT NULL
  sulla testata. Cliente con piu' utility → N offerte distinte (un eventuale
  raggruppamento "pacchetto commerciale" e' fuori dal v1).
- **Versione listino fissata all'emissione**: in `BOZZA` `listino_versione_id`
  puo' essere NULL; al passaggio `BOZZA -> EMESSA` il trigger guard rifiuta
  se NULL o versione non ATTIVA. Da `EMESSA` in poi e' immutabile.
- **Eccezioni come mirror di `contratti_righe`** con i 5 CHECK constraint
  replicati (`chk_offerte_eccezioni_*`) **e** i gate prezzo L1/L2/L3
  (refactor-prezzi 2026-06-01). Le colonne `stato_approvazione_prezzo` e
  `pratica_approvazione_prezzo_id` esistono su `offerte_commerciali_eccezioni`
  (migration `20260601-01`): la proposta ha lo stesso workflow di approvazione
  prezzo del contratto. Al push lo stato approvazione viene **copiato 1:1** sul
  contratto (non più NULL) — un override già autorizzato in offerta non va
  riapprovato. Vedi [API approvazioni prezzo](api_approvazioni_prezzo.md) e
  [refactor-prezzi](../../dev/work-in-progress/refactor-prezzi.md).
- **State machine asimmetrica** (decisione operativa): annullamento da noi
  solo prima dell'emissione; rifiuto cliente solo dopo l'emissione.

## Contesto

- Il **codice offerta** `OFC-*` e' generato dal trigger DB
  `trgfn_offerte_commerciali_gen_codice` (BEFORE INSERT, step 5 brief DB
  atterrato 2026-05-25). Il campo `codice` **non va nel payload** in
  creazione: se inviato viene rifiutato come `unknown_key`. Lookup
  `script.fn_generate_codice('offerta_commerciale')` con prefisso `OFC`
  e lunghezza 7.
- Lo **stato iniziale** di ogni offerta e' `BOZZA` (risolto dal service via
  `config.stati_doc_offerte.codice_interno`).
- La **state machine** e' autoritativa lato DB tramite il trigger
  `trgfn_offerte_commerciali_guard_transizione` che:
  - verifica che la transizione sia in `config.stati_doc_offerte_transizioni`
  - valorizza `data_emissione` / `data_accettazione` / `data_rifiuto` /
    `data_annullamento` al passaggio
  - rifiuta `BOZZA -> EMESSA` con `listino_versione_id` NULL o versione non
    ATTIVA (codici `E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO` /
    `E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA`)
- I codici errore `E_OFFERTA_*` sollevati dal trigger sono **estratti dal
  MESSAGE** del trigger via regex (`_DB_ERROR_CODE_RE`) e propagati al client
  come `ServiceError.code` originale, non come `E_VENDITE_VALIDATION` generico.
  Il FE puo' fare routing UI specifico per codice.

### State machine

| Da     | A         | Chi la innesca                | Effetto laterale                                                |
| ------ | --------- | ----------------------------- | --------------------------------------------------------------- |
| BOZZA  | EMESSA    | operatore (`/emetti/`)        | Congela versione listino; valorizza `data_emissione`            |
| BOZZA  | ANNULLATA | operatore (`/annulla/`)       | Valorizza `data_annullamento` + `motivazione_rifiuto`           |
| EMESSA | ACCETTATA | operatore (`/registra-esito/`) | Valorizza `data_accettazione`                                  |
| EMESSA | RIFIUTATA | operatore (`/registra-esito/`) | Valorizza `data_rifiuto` + `motivazione_rifiuto`               |
| EMESSA | SUPERATA  | trigger revisione (Step 7 DB) | Stato terminale tecnico; rev.N+1 diventa la nuova offerta corrente |

Stati terminali immutabili: **ACCETTATA**, **RIFIUTATA**, **SUPERATA**,
**ANNULLATA**. Transizioni *NON* ammesse (documentate per evitare
ambiguita'):

- `BOZZA -> RIFIUTATA` non esiste: RIFIUTATA e' il "no del cliente" e dal
  cliente non si arriva mai con un'offerta ancora in bozza.
- `EMESSA -> ANNULLATA` non e' ammessa: una volta emessa, o accetta o
  rifiuta il cliente. Per correzioni interne dopo l'emissione si crea una
  revisione (che marcera' la corrente SUPERATA).

### Perimetro D6 (BE completo, step DB 1-9 + addendum)

Tutti gli endpoint cablati:

- testata + state machine + eccezioni + utility 1:1 (step 1-4)
- `motivazione_rifiuto` (addendum 2026-05-24)
- numerazione automatica `OFC-*` via trigger DB (step 5, 2026-05-25 AM)
- `POST /<id>/crea-revisione/` + `GET /<id>/revisioni/` (step 6-7, 2026-05-25 AM)
- `POST /<id>/push-contratto/` (step 8, 2026-05-25 PM)
- Suite pgTAP (step 9) confermata da team DB
- `POST /<id>/note/` + `GET/PATCH/DELETE /<id>/note/<note_id>/` —
  cablaggio building block `PartitionedNoteRepository` per
  `target_tipo='OFFERTA'` (2026-05-26)

### Perimetro D7 — capability layer + refactor atomico (2026-05-26)

Step migliorativo data-driven applicato dopo la consegna della fn DB
`script.fn_available_actions_offerta` (migration `20260526-01`):

- **Capability blob** nel detail: `get_offerta` ora include
  `available_actions[]`, `can_edit_*`, `can_push_contratto`,
  `non_editable_fields`, `stato_codice` letti da `script.fn_available_actions_offerta`.
  Il FE consuma con `useEntityCapabilities` + `mapAvailableActionsToDrawerActions`,
  rimuovendo lo state-machine FE hardcoded.
- **Contratto collegato**: `contratto_id` + `contratto_numero` esposti
  via LEFT JOIN `vendite.contratti.offerta_id`. Il FE li usa per il
  dialog parlante post-`E_OFFERTA_CONTRATTO_GIA_GENERATO` (link al
  ContrattoDrawer) e per il deep-link `?open=<id>` post-push.
- **Atomicita' utility 1:1 inline**: `crea_offerta` (POST) e
  `aggiorna_offerta` (PATCH) accettano un sub-oggetto opzionale `utility`.
  Se valorizzato, il service esegue il `create/update_utility` nella
  stessa `transaction.atomic()` (eredita `istanza_utility_id`/`utility_id`
  dalla testata se non specificati). Mirror del pattern `ContrattoDrawer`,
  elimina il rischio "offerta orfana di utility" del flusso a 2 round-trip.
- **Alias display fields**: il SELECT testata ora espone
  `billing_account_display` + `utility_display` (allineamento al piano
  FE+BE rev. f), evitando ricodifiche client-side.

## Input

### Form-defaults `GET /api/v1/vendite/offerte/form-defaults/`

Endpoint sola lettura per pre-popolare il form CREATE offerta. Riusato
dal drawer FE all'apertura e al cambio `billing_account_id`. Simmetrico
a `vendite-contratto-form-defaults` e `vendite-preventivi-form-defaults`.

| Parametro             | Tipo  | Descrizione                                                                                |
| --------------------- | ----- | ------------------------------------------------------------------------------------------ |
| `billing_account_id`  | int   | Opzionale. Se presente, popola i campi BA-derived (categoria_cliente, utility, valuta).    |

Risposta `200`:

```json
{
  "data": {
    "billing_account_id": 100,
    "categoria_cliente_id_snapshot": 7,
    "categoria_cliente_codice": "STANDARD",
    "categoria_cliente_descrizione": "Standard",
    "utility_id": 3,
    "istanza_utility_id": 200,
    "utility_codice": "GAS",
    "utility_descrizione": "Gas",
    "valuta_id": 1,
    "valuta_codice": "EUR",
    "valuta_descrizione": "Euro"
  }
}
```

Risoluzione `valuta_id` (BB `resolve_valuta_default`, allineato a
`vendite.fn_get_valuta_id`):

1. `billing_account.valuta_id` se valorizzato
2. EF del BA via `fn_get_emittente_fiscale_pk`
3. EF dell'utente loggato (con fallback gestore globale)
4. `anagrafiche.gestori.valuta_id` (primo per id)
5. `null` se nessuna sorgente

Senza `billing_account_id` i campi BA-derived restano `null` ma la
catena valuta parte comunque dal livello 3.

Errori: `E_VENDITE_NOT_FOUND` (404) se `billing_account_id` non esiste.

### Lista offerte `GET /api/v1/vendite/offerte/`

> **DEF-8 (2026-06-03)**: la lista legge dalla vista canonica self-contained
> `vendite.vw_offerte_commerciali_lista` (`security_invoker=on`) — lista
> configurabile `vendite.offerte`, ritiro dinamico colonne lato FE. La vista
> **assorbe** i JOIN prima nel repository (`listino_codice`,
> `listino_versione_codice`, `valuta_codice`) e **materializza `is_scaduta`**
> (`validita_al < CURRENT_DATE`; il gating per stato
> `STATI_OFFERTA_SEGNALA_SCADENZA` resta lato FE). Campi display con i **nomi
> canonici**: cliente = `ragione_sociale_completa`, id. fiscale =
> `id_fiscale_univoco_cf_piva`, codice account = `ba_codice`, stato =
> `stato_descrizione` + `stato_codice_interno`. Il **dettaglio** (`GET .../<id>/`)
> conserva i nomi storici (`billing_account_display`, `utility_display`): fonte
> diversa (JOIN su tabelle base). `vw_offerte_commerciali_list` deprecata (drop
> differito post-BE).

| Parametro              | Tipo     | Descrizione                                                                                |
| ---------------------- | -------- | ------------------------------------------------------------------------------------------ |
| `search`               | string   | ILIKE su `codice` offerta e `ragione_sociale_completa` BA (minimo 3 char se valorizzato)    |
| `billing_account_id`   | int      | Filtro cliente                                                                              |
| `stato_codice_interno` | string   | `BOZZA` \| `EMESSA` \| `ACCETTATA` \| `RIFIUTATA` \| `ANNULLATA` \| `SUPERATA`               |
| `utility_id`           | int      | Filtro utility                                                                              |
| `listino_id`           | int      | Filtro listino di riferimento                                                               |
| `validita_dal_min`     | ISO date | Filtro su `validita_dal` (range minimo). Nessun default backend                             |
| `validita_dal_max`     | ISO date | Filtro su `validita_dal` (range massimo)                                                    |
| `solo_attiva`          | bool     | Default `true`: solo l'ultima revisione viva per lineage (`vw_offerte_commerciali_lista.is_attiva`). `false` = storico revisioni completo (2026-05-28) |
| `limit`                | int      | Default 25                                                                                  |
| `offset`               | int      | Default 0                                                                                   |
| `order_by`             | string   | `campo_sorgente` catalogo `vendite.offerte`: `codice` \| `ragione_sociale_completa` \| `ba_codice` \| `id_fiscale_univoco_cf_piva` \| `utility_codice` \| `utility_descrizione` \| `listino_codice` \| `validita_dal` \| `validita_al` \| `data_emissione` \| `stato_descrizione` \| `stato_codice_interno` \| `data_insert`. `revisione_numero` **non ordinabile** |
| `order_dir`            | string   | `asc` o `desc` (default)                                                                    |

> **`search` vuoto**: stringa vuota o whitespace-only trattato come "no filter"
> (non solleva 422). Il minimo 3 char si applica solo a `search` non-vuota.

### Export lista offerte `GET /api/v1/vendite/offerte/export/`

Genera un file **CSV** o **Excel** con le offerte filtrate (stessi parametri
della lista). Renderer generico DEF-1 (`ListaExportService`); colonne coerenti
con la DataTable a video (config runtime: preferenza + preset + permessi).

| Parametro | Tipo | Descrizione |
|---|---|---|
| `formato` | string | `csv` (default) o `xlsx`. **NB**: `formato` (italiano), NON `format` (magic param DRF) |
| `search`, `billing_account_id`, `stato_codice_interno`, `utility_id`, `listino_id`, `validita_dal_min`, `validita_dal_max`, `solo_attiva`, `order_by`, `order_dir` | — | stessi della lista |

- Hard cap **10.000 righe**: oltre → `422 E_UI_EXPORT_LIMIT_EXCEEDED`.
- `formato` non valido → `400 E_UI_EXPORT_FORMAT_INVALID`.
- Risposta binaria: `Content-Disposition: attachment; filename="offerte.csv|xlsx"`; i filtri attivi sono metadato nel file.
- Coda condivisa: `apps.ui.api.export_helpers.{parse_export_format,build_export_response}` (building block DEF-1).

### Create testata `POST /api/v1/vendite/offerte/`

```json
{
  "emittente_fiscale_id": 10,
  "billing_account_id": 100,
  "istanza_utility_id": 200,
  "utility_id": 3,
  "listino_id": 50,
  "listino_versione_id": 5,
  "valuta_id": 1,
  "tipo_variazione_globale": "PERCENTUALE",
  "valore_variazione_globale": "-5.00",
  "validita_dal": "2026-06-01",
  "validita_al": "2026-12-31",
  "meta": {"campagna": "estate26"},
  "utility": {
    "tipo_utenza_id": 7,
    "classe_utenza_id": 4,
    "param_1_num": "12.5"
  }
}
```

Note:

- `valuta_id` opzionale (2026-05-29). Snapshot fissato al CREATE,
  immutabile in PATCH (simmetrico a preventivi). Se omesso, il trigger DB
  `_a*_set_valuta_default_ins` lo risolve via `vendite.fn_get_valuta_id`
  (catena BA → emittente → gestore). Il FE può pre-popolare il valore
  via `GET /api/v1/vendite/offerte/form-defaults/?billing_account_id=...`
  che usa il BB `resolve_valuta_default`.
- `codice` **non va nel payload** (step 5 atterrato 2026-05-25): generato
  dal trigger DB `trgfn_offerte_commerciali_gen_codice` come
  `OFC-NNNNNNN`. Se inviato, rifiutato come `unknown_key` con
  `E_VENDITE_VALIDATION`.
- `stato_doc_offerta_id` / `uid` / `revisione_*` / `data_*` di transizione
  **NON vanno mai inviati** (rifiutati come unknown_keys con
  `E_VENDITE_VALIDATION`).
- `istanza_utility_id` e `utility_id` sono il riferimento "anagrafico"
  della utility (mono-utility per offerta). I campi business
  (tipo/classe utenza, parametri) vivono nel sub-record utility 1:1.
- **`utility` (sub-oggetto opzionale, atomicita' inline 2026-05-26)**:
  se valorizzato, il service crea il record utility 1:1 nella stessa
  `transaction.atomic()` della testata (mirror `ContrattoDrawer` pattern).
  `istanza_utility_id`/`utility_id` interni al sub-oggetto sono opzionali:
  vengono ereditati dalla testata se omessi (coerenza FK col BA scelto).
  Whitelist sub-payload: `istanza_utility_id`, `utility_id`,
  `istanza_dati_precontrattuali_id`, `tipo_utenza_id`, `classe_utenza_id`,
  `param_1_num`, `param_2_txt`, `meta`. Alternativa: chiamare
  `POST /utility/` separato dopo (vedi §Utility 1:1) — sconsigliato
  perche' non atomico col create testata.
- `validita_dal` obbligatorio; `validita_al` opzionale.
- Coerenza coppia variazione globale: `tipo_variazione_globale` +
  `valore_variazione_globale` entrambi NULL o entrambi NOT NULL (CHECK DB
  `chk_offerte_variazione_globale_coerenza`).

### Detail `GET /api/v1/vendite/offerte/<id>/`

Output: testata + display fields + `eccezioni[]` + `utility` (1:1, null se
non ancora compilato).

```json
{
  "data": {
    "id": 1, "uid": "...", "codice": "OFC-2026-0001",
    "emittente_fiscale_id": 10,
    "billing_account_id": 100,
    "ba_codice": "BA-0123", "billing_account_display": "Acme S.p.A.",
    "istanza_utility_id": 200, "utility_id": 3,
    "utility_codice": "GAS", "utility_display": "Gas naturale",
    "listino_id": 50, "listino_versione_id": 5,
    "listino_codice": "LST-GAS-2026", "listino_descrizione": "Listino gas 2026",
    "listino_versione_codice": "V5",
    "valuta_id": 1,
    "valuta_codice": "EUR",
    "valuta_descrizione": "Euro",
    "tipo_variazione_globale": "PERCENTUALE",
    "valore_variazione_globale": "-5.00",
    "validita_dal": "2026-06-01", "validita_al": "2026-12-31",
    "stato_doc_offerta_id": 1,
    "stato_codice_interno": "BOZZA", "stato_descrizione": "Bozza",
    "revisione_numero": 1, "revisione_padre_id": null,
    "data_emissione": null, "data_accettazione": null,
    "data_rifiuto": null, "data_annullamento": null,
    "motivazione_rifiuto": null,
    "meta": {"campagna": "estate26"},
    "contratto_id": null, "contratto_numero": null,
    "eccezioni": [
      {
        "id": 7, "offerta_id": 1, "articolo_id": "uuid-articolo",
        "articolo_codice": "GAS-STD", "articolo_descrizione": "Gas Standard",
        "tipo_eccezione": "OVERRIDE", "tipo_erogazione": "CONSUMO",
        "fonte_quantita_attesa": "LETTURE",
        "prezzo_unitario": "0.42", "quantita": null,
        "qta_operativa": null, "uom_operativa_id": 5, "uom_codice": "MWh",
        "factor_to_base": "1", "ordine": 10, "attivo": true, "meta": {}
      }
    ],
    "utility": {
      "id": 99, "offerta_id": 1,
      "istanza_utility_id": 200, "utility_id": 3,
      "utility_codice": "GAS", "utility_descrizione": "Gas naturale",
      "tipo_utenza_id": 2, "tipo_utenza_codice": "DOM",
      "classe_utenza_descrizione": "Domestico",
      "classe_utenza_id": 7, "classe_utenza_codice": "RES",
      "tipo_utenza_descrizione": "Residenziale",
      "param_1_num": "1500", "param_2_txt": "POD-XYZ",
      "istanza_dati_precontrattuali_id": null, "meta": {}
    },
    "available_actions": [
      {
        "key": "emetti", "target_state": "EMESSA",
        "label_key": "vendite.offerte.azione_emetti",
        "severity": "success", "icon": "pi pi-send",
        "requires_confirm": true, "requires_motivazione": false
      },
      {
        "key": "annulla", "target_state": "ANNULLATA",
        "label_key": "vendite.offerte.azione_annulla",
        "severity": "danger", "icon": "pi pi-ban",
        "requires_confirm": true, "requires_motivazione": true
      }
    ],
    "can_change_state": true,
    "can_edit_testata": true,
    "can_edit_eccezioni": true,
    "can_edit_utility": true,
    "can_create_revisione": false,
    "can_push_contratto": false,
    "can_push_contratto_reason": "OFFERTA_NON_ACCETTATA",
    "can_push_contratto_reason_key": "vendite.offerte.push_reason.non_accettata",
    "non_editable_fields": [
      "codice", "uid", "revisione_numero", "revisione_padre_id",
      "stato_doc_offerta_id", "data_emissione", "data_accettazione",
      "data_rifiuto", "data_annullamento", "motivazione_rifiuto"
    ],
    "stato_codice": "BOZZA",
    "data_insert": "2026-05-24T18:30:00Z", "user_insert": "mctit",
    "data_update": null, "user_update": null
  }
}
```

**Campi di output chiave**:

- **Display fields da JOIN backend** (no lookup client-side):
  `billing_account_display`, `utility_display`, `listino_codice/descrizione`,
  `listino_versione_codice`, `stato_codice_interno`, `stato_descrizione`,
  `ba_codice`.
- **Contratto collegato** (LEFT JOIN `vendite.contratti.offerta_id`):
  `contratto_id` + `contratto_numero` NULL se l'offerta non e' ancora
  stata pushata. Idempotenza Pattern A (UNIQUE
  `uq_contratti_offerta_id`): max 1 contratto per offerta. Il FE usa
  questi campi per il dialog "gia' generato" e per il deep-link
  `/vendite/contratti?open=<id>` post-push.
- **Capability blob** (da `script.fn_available_actions_offerta`, mergiato
  nel dict): `available_actions[]` lista azioni ammesse nello stato
  corrente (mappabili 1:1 a `DrawerActionsBar` via
  `mapAvailableActionsToDrawerActions`); `can_edit_testata` /
  `can_edit_eccezioni` / `can_edit_utility` flag editabilita';
  `can_change_state` true se almeno un'azione disponibile;
  `can_create_revisione` / `can_push_contratto` flag per azioni
  speciali non-cambio-stato; `can_push_contratto_reason` +
  `can_push_contratto_reason_key` coppia stabile reason-code +
  chiave i18n quando il push non e' ammesso (`OFFERTA_NON_ACCETTATA`
  o `OFFERTA_CONTRATTO_GIA_GENERATO`); `non_editable_fields[]` lista
  immutabili (sempre + workflow-dipendenti, lista lunga fuori BOZZA);
  `stato_codice` discriminante macchina (equivalente a
  `stato_codice_interno`, esposto anche dalla fn DB).

### Update testata `PATCH /api/v1/vendite/offerte/<id>/`

Solo in stato **BOZZA**. Whitelist campi mutabili: `emittente_fiscale_id`,
`billing_account_id`, `istanza_utility_id`, `utility_id`, `listino_id`,
`listino_versione_id`, `valore_variazione_globale`,
`tipo_variazione_globale`, `validita_dal`, `validita_al`, `meta`,
`utility` (sub-oggetto opzionale).

Immutabili (lock applicativo + DB):

- `codice`, `uid`, `stato_doc_offerta_id` — per il cambio stato c'e'
  l'endpoint dedicato `/emetti/` / `/registra-esito/` / `/annulla/`.
- `revisione_*` — gestiti dal flusso revisione (step 7 brief DB).
- `data_*` di transizione + `motivazione_rifiuto` — valorizzati dal
  trigger DB al cambio stato.

**Sub-oggetto `utility` (atomico, 2026-05-26)**: simmetria col create
(POST). Se valorizzato:

- se l'offerta NON ha ancora un record utility 1:1 → `create_utility`
  nella stessa transazione (eredita `istanza_utility_id`/`utility_id`
  dalla testata se non specificati nel sub-payload);
- se l'offerta ha gia' un record utility → `update_utility` filtrando il
  sub-payload sulla whitelist `_UPDATE_KEYS_UTILITY` (immutabili gli id
  derivati dal BA, modificabili: `tipo_utenza_id`, `classe_utenza_id`,
  `param_1_num`, `param_2_txt`, `istanza_dati_precontrattuali_id`,
  `meta`).

**Payload `{}` rifiutato** con `E_VENDITE_VALIDATION` (no-op evitato:
l'operatore non puo' premere "Salva" e vedere `200 OK` senza che nulla
sia stato scritto in DB). Payload con SOLO `utility` (senza campi
testata) e' ammesso ed esegue solo l'upsert utility.

### Delete `DELETE /api/v1/vendite/offerte/<id>/`

Solo in stato BOZZA. Hard delete dell'offerta + cascade su
`offerte_commerciali_eccezioni` e `offerte_commerciali_utilities` via FK.

**Annullamento di processo**: per "ritirare" un'offerta gia' presentata
internamente si usa `POST /<id>/annulla/` (stato ANNULLATA), non DELETE.
Il delete e' una pulizia tecnica di bozze "vuote".

### Cambio stato BOZZA -> EMESSA `POST /api/v1/vendite/offerte/<id>/emetti/`

Endpoint **multipart** (Content-Type: `multipart/form-data`). Mirror del
flusso preventivo/contratto `emetti` (refactor 2026-05-28: pattern
unificato cross-dominio).

- Parser: `MultiPartParser`, `FormParser`
- Body multipart:
  - `template_documento_id` (int, opzionale) — id template da usare. Se
    omesso, selezione default per
    `(sorgente=OFFERTA_COMMERCIALE, emittente_fiscale_id, tipo_documento_output_id)`
  - `tipo_documento_output_id` (int, opzionale)
  - `allegati` (file ripetuto, opzionale) — file secondari persistiti
    assieme al PDF principale

Pre-step (refactor 2026-05-28): `OfferteService.emetti` esegue il
**freeze at emission** della versione listino prima della transizione.
Se `listino_versione_id` non è già fissata, il service cerca la versione
del listino in stato `ATTIVA` (fallback `CHIUSA`) alla data odierna e la
persiste con UPDATE atomico. Motivazione: il form CREATE offerta espone
solo `listino_id` (non la versione); senza pre-fill il trigger DB
`trgfn_offerte_commerciali_guard_transizione` rifiuterebbe la transizione
con `E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO`. Errore parlante
`E_VENDITE_VALIDATION` (422) se il listino selezionato non ha versioni
operative valide oggi.

Trigger DB (post pre-fill):

1. verifica `listino_versione_id` NOT NULL → altrimenti
   `E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO` (422)
2. verifica versione listino in stato `ATTIVA` → altrimenti
   `E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA` (422)
3. valorizza `data_emissione = now()`

Da questo momento la versione del listino è "congelata": modifiche al
listino sottostante non si propagano all'offerta.

Semantica transazionale (refactor 2026-05-28): la view apre
`transaction.atomic()` esterno che racchiude (in ordine):
`OfferteService().emetti(offerta_id)` (con `atomic` nested per pre-fill +
cambio stato) → `_resolve_contesto_offerta` →
`DocumentGenerationService.genera_documento(allegati=...)` (render +
persist su `documenti.documenti_generati` + evento `GENERATO`). Se il
render fallisce o un allegato viola MIME/size, l'atomic esterno rollbacka
tutto → l'offerta resta BOZZA e `listino_versione_id` resta NULL
(nessun side-effect parziale). **Invariante di dominio**:
`stato='EMESSA'` ⇒ esiste almeno un record `documenti_generati` con
`sorgente_tipo=OFFERTA_COMMERCIALE, sorgente_id=offerta.id`.

Output `200`:

```json
{
  "data": {
    "offerta": { "...": "testata aggiornata dopo cambio stato" },
    "documento": {
      "documento_generato_id": 42,
      "uid": "...",
      "progressivo_sorgente": 1,
      "nome_file": "OFFERTA_OFC-0000001_v1.pdf",
      "size_bytes": 23456,
      "allegati_count": 0
    }
  }
}
```

Helper condivisi: `apps.documenti.api.contesto_helpers.resolve_contesto_documentale`
(resolve entity + emittente + sorgente_tipo) e
`apps.documenti.api.multipart_helpers.extract_allegati` (estrazione files
multipart neutra). Vedi
[api_documenti_helpers](../../../documenti/manual/api_documenti_helpers.md).

### Cambio stato EMESSA -> ACCETTATA/RIFIUTATA `POST /api/v1/vendite/offerte/<id>/registra-esito/`

```json
{"esito": "ACCETTATA"}
```

oppure

```json
{"esito": "RIFIUTATA", "motivazione": "Cliente preferisce concorrente X."}
```

- `esito = "ACCETTATA"`: valorizza `data_accettazione`. `motivazione`
  opzionale.
- `esito = "RIFIUTATA"`: valorizza `data_rifiuto` +
  `motivazione_rifiuto`. **Motivazione obbligatoria** (stringa non
  vuota): assenza solleva `E_VENDITE_VALIDATION` pre-DB.
- `esito` non valido → `E_VENDITE_VALIDATION` con detail "Atteso uno tra
  ['ACCETTATA', 'RIFIUTATA']".

Routing per esito implementato nel service (`registra_esito`), la view e'
sottile.

### Cambio stato BOZZA -> ANNULLATA `POST /api/v1/vendite/offerte/<id>/annulla/`

```json
{"motivazione": "Riscontrato errore nel listino di riferimento."}
```

Motivazione obbligatoria. Salvata in `motivazione_rifiuto` (colonna
condivisa con RIFIUTATA). Il trigger DB valorizza `data_annullamento`.

Annullamento ammesso **solo da BOZZA**. Pattern simmetrico ai contratti
`DRAFT -> ANNULLATO`. Tentativo da EMESSA → 422 con
`E_OFFERTA_TRANSIZIONE_NON_AMMESSA` propagato dal trigger DB.

### Crea revisione `POST /api/v1/vendite/offerte/<id>/crea-revisione/`

Body vuoto. Crea rev.N+1 in stato `BOZZA` a partire dall'offerta corrente
(che deve essere in stato `EMESSA`). Effetti:

1. Invoca `vendite.fn_crea_revisione_offerta(offerta_id, user)` (step 7
   brief DB).
2. La fn DB copia testata + eccezioni attive + utility 1:1 nella nuova
   revisione, con `revisione_numero = N+1` e `revisione_padre_id = <id>`.
3. Il codice `OFC-*` della nuova rev e' generato ex novo dal trigger
   `gen_codice` (uid e timestamp di transizione restano NULL).
4. Il trigger `trg_offerte_commerciali_z90_revisione_ins` (step 6,
   AFTER INSERT) marca **automaticamente** la rev.N come `SUPERATA`
   (transizione `EMESSA -> SUPERATA` ammessa nel seed).
5. Ritorna il dettaglio della nuova rev.N+1 (testata + eccezioni + utility).

Guard:

- Stato corrente diverso da `EMESSA` → 422
  `E_OFFERTA_REVISIONE_STATO_NON_AMMESSO`. La fn DB e' guard finale; il
  service applica anche un pre-check applicativo che ritorna
  `E_VENDITE_VALIDATION` parlante in caso di stato fuori scope.
- Offerta inesistente → 404.

`user` di audit: il service prende `request.user.username` se autenticato
(la fn DB ha `COALESCE(p_user, CURRENT_USER)` come fallback).

### Push a contratto `POST /api/v1/vendite/offerte/<id>/push-contratto/`

```json
{"pratica_id": 7}
```

oppure body vuoto `{}` per push senza collegamento a pratica.

Genera un **contratto DRAFT** a partire dall'offerta corrente (che deve
essere in stato `ACCETTATA`). Effetti:

1. Invoca `vendite.fn_push_offerta_a_contratto(offerta_id, pratica_id)`
   (step 8 brief DB).
2. La fn DB applica guard ACCETTATA + idempotenza UNIQUE su
   `vendite.contratti.offerta_id` e copia 1:1:
   - testata (`billing_account_id`, `istanza_utility_id`, `utility_id`,
     `listino_id`, `listino_versione_id`, variazione globale,
     `valido_dal/al` da `validita_dal/al`, `meta`)
   - eccezioni → `contratti_righe`, con `stato_approvazione_prezzo` e
     `pratica_approvazione_prezzo_id` **copiati 1:1** dall'eccezione offerta
     (migration `20260601-04`: prima erano forzati a `NULL`). Un override già
     autorizzato in offerta non va riapprovato sul contratto.
   - utility 1:1 → `contratti_utilities` (`INSERT ... ON CONFLICT DO UPDATE`
     sovrascrive il record creato dal trigger snapshot precontrattuali
     con i dati negoziati dell'offerta)
3. Sul contratto generato: `sorgente_tipo_id = OFFERTA_COMMERCIALE`,
   `sorgente_uid = offerta.uid`, `offerta_id = <id>` (UNIQUE).
4. Se `pratica_id` valorizzato: inserisce in `pratiche.pratiche_sorgenti`
   il contratto come sorgente `CONTRATTO` con ruolo `COLLEGATO`.

Ritorna gli identificativi minimi del nuovo contratto (il FE naviga al
`ContrattoDrawer` per il dettaglio completo):

```json
{
  "data": {
    "contratto_id": 101,
    "contratto_codice": "CNT0000045",
    "sorgente_uid": "11111111-2222-3333-4444-555555555555"
  }
}
```

Guard:

- Stato corrente ≠ `ACCETTATA` → 422 `E_OFFERTA_PUSH_STATO_NON_AMMESSO`.
  Il service applica anche pre-check applicativo che ritorna
  `E_VENDITE_VALIDATION` parlante in caso di stato fuori scope.
- Doppia invocazione su stessa offerta → 422
  `E_OFFERTA_CONTRATTO_GIA_GENERATO` (idempotenza pattern A §6.9.3).
- `pratica_id` non-positivo o non-int → `E_VENDITE_VALIDATION`.

### Lista revisioni `GET /api/v1/vendite/offerte/<id>/revisioni/`

Ritorna la **catena di revisioni** che condivide il root (rev.1) con
l'offerta passata. Output ordinato per `revisione_numero` ASC. Lettura
libera in ogni stato (utile per il drawer FE che vuole mostrare la
timeline rev.1 SUPERATA → rev.2 SUPERATA → rev.3 EMESSA → ecc.).

```json
{
  "data": [
    {"id": 1,  "codice": "OFC-0000001", "revisione_numero": 1,
     "stato_codice_interno": "SUPERATA", "revisione_padre_id": null,
     "data_emissione": "2026-04-10T09:15:00Z"},
    {"id": 7,  "codice": "OFC-0000003", "revisione_numero": 2,
     "stato_codice_interno": "SUPERATA", "revisione_padre_id": 1,
     "data_emissione": "2026-05-02T16:40:00Z"},
    {"id": 42, "codice": "OFC-0000019", "revisione_numero": 3,
     "stato_codice_interno": "EMESSA", "revisione_padre_id": 7,
     "data_emissione": "2026-05-25T11:00:00Z"}
  ]
}
```

Implementazione: CTE ricorsiva in due passi (risale via `revisione_padre_id`
fino al root, poi ridiscende a tutti i discendenti). Una query, indici
gia' presenti su `revisione_padre_id`.

### Eccezioni

#### Lista `GET /api/v1/vendite/offerte/<id>/eccezioni/`

Lettura libera in ogni stato. Output: array di eccezioni ordinate per
`ordine` poi `id`. Include display fields da JOIN (`articolo_codice`,
`articolo_descrizione`, `uom_codice`).

#### Create `POST /api/v1/vendite/offerte/<id>/eccezioni/`

Solo in BOZZA. Mirror del payload `vendite.contratti_righe` (eccezione
tipizzata):

```json
{
  "articolo_id": "00000000-0000-0000-0000-000000000001",
  "tipo_eccezione": "OVERRIDE",
  "tipo_erogazione": "CONSUMO",
  "fonte_quantita_attesa": "LETTURE",
  "prezzo_unitario": "0.42",
  "uom_operativa_id": 5,
  "factor_to_base": "1",
  "ordine": 10,
  "attivo": true,
  "richiesta_approvazione": false
}
```

Campo opzionale `richiesta_approvazione` (default `false`): flag opt-in del
workflow L3 (vedi gate prezzo sotto). Non è una colonna DB — viene estratto dal
service. `componenti_overrides` (override prezzi figli BoM su articolo
composito) è anch'esso accettato e non persiste come colonna (alimenta
`fn_offerta_eccezione_componenti_init`).

Tipi ammessi (enum DB `vendite.tipo_eccezione_contratto`, identico al
contratto — riuso intenzionale per push 1:1 senza conversioni):

| `tipo_eccezione` | Significato                                            | `prezzo_unitario` |
| ---------------- | ------------------------------------------------------ | ----------------- |
| `OVERRIDE`       | Prezzo personalizzato per articolo del listino         | NOT NULL          |
| `ESCLUSIONE`     | Articolo del listino non disponibile per il cliente    | NULL              |
| `AGGIUNTA`       | Articolo fuori-listino aggiunto all'offerta            | NOT NULL          |

Vincoli (CHECK DB `chk_offerte_eccezioni_*` + UNIQUE):

- ESCLUSIONE ↔ prezzo NULL; OVERRIDE/AGGIUNTA ↔ prezzo NOT NULL
  (`chk_offerte_eccezioni_prezzo_per_tipo_eccezione`)
- Coerenza `(tipo_erogazione, fonte_quantita_attesa)`
  (`chk_offerte_eccezioni_coerenza_fonte_erogazione`)
- `fonte_quantita_attesa` NOT NULL
  (`chk_offerte_eccezioni_fonte_qta`)
- **Quantità**: la sorgente è `qta_operativa` (UoM operativa). La colonna base
  `quantita` è **derivata dal trigger** `trgfn_qta_from_operativa`
  (`quantita = qta_operativa × factor_to_base`) e non va inviata. `qta_operativa`
  obbligatoria per `fonte = FISSA` (CHECK `qta_operativa <> 0`: zero vietato,
  negativi ammessi); ammessa NULL per le altre fonti (la qta arriva downstream).
  Allineato a contratti/preventivi (refactor 2026-05-31)
- `tipo_erogazione` ammesso (`chk_offerte_eccezioni_tipo_erog`)
- Coerenza canone (`chk_offerte_eccezioni_coerenza_canone`)
- UNIQUE: max 1 `OVERRIDE`/`ESCLUSIONE` per `(offerta_id, articolo_id)`
  e max 1 `AGGIUNTA` per stessa coppia.

I 5 CHECK sono **stessa logica** di `contratti_righe` (nomi `chk_offerte_eccezioni_*`),
quindi un'eccezione valida sull'offerta sara' accettata anche al push.

##### Gate prezzo L1/L2/L3 (su create ed update di OVERRIDE/AGGIUNTA)

Quando un'eccezione OVERRIDE/AGGIUNTA **non composita** porta un prezzo manuale,
il service applica gli stessi tre gate del contratto/preventivo (BB condiviso
`_pricing_gate_helpers`, mirror `contratti_service`):

- **L1 — permesso**: l'override del prezzo richiede l'azione di processo
  `prezzo_override_manuale`; in assenza → `403 E_PRICING_OVERRIDE_NON_AUTORIZZATO`.
  Lo stesso gate L1 si applica agli **override dei prezzi componenti**
  (`componenti_overrides`) — allineamento a preventivi.
- **L2 — soglia**: il delta % rispetto al prezzo suggerito (resolver pricing
  sul listino fissato/operativo dell'offerta) non può eccedere le soglie
  `max_sconto_pct` / `max_maggiorazione_pct` (cascata `user → categoria_cliente →
  group → emittente → default`). Oltre soglia, senza `richiesta_approvazione`
  → `422 E_PRICING_SCONTO_ECCESSIVO` / `E_PRICING_MAGGIORAZIONE_ECCESSIVA`
  (`retryable=true`).
- **L3 — escalation**: con `richiesta_approvazione: true`, una violazione L2
  **non solleva**: crea una pratica `APPROVAZIONE_PREZZO` (sorgente `offerta`) e
  salva l'eccezione con `stato_approvazione_prezzo = PENDING` +
  `pratica_approvazione_prezzo_id`. L'eccezione PENDING è bloccata in modifica
  dal trigger DB `trgfn_righe_guard_pending` finché l'approver non risolve
  (vedi [API approvazioni prezzo](api_approvazioni_prezzo.md)).

Note:
- gate **saltato** per `ESCLUSIONE` (prezzo NULL) e per i **compositi** (il
  prezzo padre è la somma derivata dei figli; i componenti hanno il proprio
  audit). Saltato anche se l'offerta è senza `listino_id` (caso non standard:
  per le offerte è obbligatorio).
- l'output dell'eccezione (su `GET`/detail) include ora
  `stato_approvazione_prezzo` e `pratica_approvazione_prezzo_id`
  (NULL = nessuna approvazione richiesta).

#### Update `PATCH /api/v1/vendite/offerte/<id>/eccezioni/<eid>/`

Solo in BOZZA. `articolo_id` e `tipo_eccezione` immutabili (cambio = DELETE
+ INSERT). Payload `{}` rifiutato (no-op evitato). Se il PATCH tocca
`prezzo_unitario` su una eccezione OVERRIDE/AGGIUNTA non composita, **riapplica
il gate L1/L2/L3** (stesso comportamento del create, incluso il flag opzionale
`richiesta_approvazione`). Il `meta` persistito dell'eccezione è preservato
(l'audit pricing viene mergiato, non sovrascritto).

Difesa anti-tampering URL: il service verifica
`eccezione.offerta_id == <id>` e ritorna 404 in caso di mismatch (per
evitare PATCH `/offerte/1/eccezioni/99/` se l'eccezione 99 appartiene
all'offerta 42).

#### Delete `DELETE /api/v1/vendite/offerte/<id>/eccezioni/<eid>/`

Solo in BOZZA. Hard delete. Stessa difesa ownership di update.

### Utility 1:1

La utility e' un record di **estensione** 1:1 con i dati business della
fornitura (tipo/classe utenza, parametri specifici per ambito). Mirror di
`contratti_utilities`.

#### Get `GET /api/v1/vendite/offerte/<id>/utility/`

Ritorna il record utility 1:1 (null se non ancora creato). Lettura libera.

#### Create `POST /api/v1/vendite/offerte/<id>/utility/`

```json
{
  "istanza_utility_id": 200,
  "utility_id": 3,
  "tipo_utenza_id": 2,
  "classe_utenza_id": 7,
  "param_1_num": "1500",
  "param_2_txt": "POD-XYZ",
  "istanza_dati_precontrattuali_id": 88,
  "meta": {}
}
```

Vincoli:

- `istanza_utility_id` + `utility_id` obbligatori; coerenti con la testata
  dell'offerta.
- UNIQUE `uq_offerte_commerciali_utilities_offerta_id`: un solo record per
  offerta. Doppio create → 409 `E_VENDITE_DUPLICATO`.
- Trigger `trgfn_offerte_utilities_guard_tipo_classe` (analogo a
  contratti) valida la coerenza `(tipo_utenza, classe_utenza)` per
  ambito utility.

Solo in BOZZA.

#### Update `PATCH /api/v1/vendite/offerte/<id>/utility/<utility_id>/`

Solo in BOZZA. `istanza_utility_id` e `utility_id` immutabili (cambio =
DELETE offerta + creazione nuova). Payload `{}` rifiutato. Anti-tampering:
verifica `utility.id == <utility_id>` e `utility.offerta_id == <id>`.

## Output

Tutte le risposte usano l'envelope `success_response`:

```json
{"data": { ... }, "meta": {"timestamp": "2026-05-25T10:00:00Z"}}
```

Per il dettaglio vedi §Detail; per la lista paginata l'envelope contiene
`{data: [...], pagination: {total, page, limit}}`.

## Regole

1. **Codice offerta** generato dal trigger DB
   `trgfn_offerte_commerciali_gen_codice` (BEFORE INSERT) via
   `script.fn_generate_codice('offerta_commerciale')`. Rifiutato in
   payload come `unknown_key`.
2. **Stato iniziale BOZZA**; transizioni via endpoint dedicato.
3. **Editabilita' solo in BOZZA** per testata, eccezioni e utility.
   Defense-in-depth applicativa; il trigger DB blocca comunque cambi su
   stati terminali.
4. **Annullamento solo da BOZZA, rifiuto solo da EMESSA**: state machine
   asimmetrica analoga ai contratti DRAFT/ATTIVO.
5. **Versione listino congelata all'emissione** (Profilo A); da EMESSA
   in poi `listino_versione_id` immutabile.
6. **Mirror del contratto**: enum `tipo_eccezione`, VARCHAR
   `tipo_variazione_globale`, cardinalita' utility 1:1, 5 CHECK su
   eccezioni — tutto identico a `vendite.contratti_*` per garantire push
   1:1 senza conversioni (step 8 DB).
7. **Anti-tampering URL** su sub-resource (`eccezioni/<eid>/`,
   `utility/<uid>/`): verifica ownership prima di ogni mutazione.
8. **Payload `{}` in PATCH rifiutato**: niente no-op silenziosi.
9. **Motivazione obbligatoria** per RIFIUTATA e ANNULLATA. Trim
   applicato; stringa whitespace-only rifiutata.

## Codici errore

| Codice                                              | HTTP                | Origine                                                                                                | Trigger DB                                          |
| --------------------------------------------------- | ------------------- | ------------------------------------------------------------------------------------------------------ | --------------------------------------------------- |
| `E_VENDITE_VALIDATION`                              | 400 / 422           | Service: struttura payload, payload vuoto in PATCH, motivazione obbligatoria, esito non valido          | —                                                   |
| `E_VENDITE_NOT_FOUND`                               | 404                 | Service: offerta/eccezione/utility non trovata; ownership URL                                          | —                                                   |
| `E_VENDITE_DUPLICATO`                               | 409                 | UNIQUE `uq_offerte_commerciali_codice` / `uq_offerte_commerciali_uid` / `uq_offerte_commerciali_utilities_offerta_id` / `uq_offerte_eccezioni_one_eccezione_per_articolo` / `uq_offerte_eccezioni_one_aggiunta_per_articolo` | —                                                   |
| `E_VENDITE_FK`                                      | 400                 | FK su BA/emittente/istanza/utility/listino/articolo/uom/tipo/classe utenza                              | —                                                   |
| `E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO`        | 422                 | DB P0001 — `BOZZA -> EMESSA` con `listino_versione_id` NULL                                            | `trgfn_offerte_commerciali_guard_transizione`        |
| `E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA`   | 422                 | DB P0001 — `BOZZA -> EMESSA` con versione listino non in stato `ATTIVA`                                 | `trgfn_offerte_commerciali_guard_transizione`        |
| `E_OFFERTA_TRANSIZIONE_NON_AMMESSA`                 | 422                 | DB P0001 — transizione non presente in `config.stati_doc_offerte_transizioni` (es. EMESSA -> ANNULLATA, EMESSA -> BOZZA, qualsiasi uscita da stato terminale) | `trgfn_offerte_commerciali_guard_transizione`        |
| `E_OFFERTA_REVISIONE_STATO_NON_AMMESSO`             | 422                 | DB P0001 — `crea_revisione` da stato != EMESSA. Il service applica anche pre-check applicativo (`E_VENDITE_VALIDATION`) | `fn_crea_revisione_offerta`                          |
| `E_OFFERTA_PUSH_STATO_NON_AMMESSO`                  | 422                 | DB P0001 — `push_a_contratto` da stato ≠ ACCETTATA. Il service applica anche pre-check applicativo (`E_VENDITE_VALIDATION`) | `fn_push_offerta_a_contratto`                        |
| `E_OFFERTA_CONTRATTO_GIA_GENERATO`                  | 422                 | DB P0001 — push idempotente (pattern A): doppia invocazione su stessa offerta. UNIQUE `uq_contratti_offerta_id` garantisce protezione strutturale | `fn_push_offerta_a_contratto`                        |
| `E_CONFIG_MANCANTE`                                 | 422                 | DB P0001 — `OFFERTA_COMMERCIALE` o `CONTRATTO` non trovati in `config.sorgenti`; stato `DRAFT` non in `config.stati_doc_contratti`. Errore di configurazione sistema | `fn_push_offerta_a_contratto`                        |
| `E_CONTRATTO_OVERLAP_ESISTENTE`                     | 422                 | DB P0001 — push con contratto attivo sovrapposto e `chiudi_esistente=false`. Il FE legge il conflitto via `contratto-sovrapposto/` e richiama con `chiudi_esistente=true` | `fn_push_offerta_a_contratto` / `fn_contratto_sovrapposto` |
| `E_CONTRATTO_SUCCESSIONE_DATA_INVALIDA`             | 422                 | DB P0001 — successione con date incoerenti: il contratto esistente inizia dopo la decorrenza del nuovo (chiusura produrrebbe `valido_al < valido_dal`) | `fn_chiudi_contratto_per_successione`                |

I codici `E_OFFERTA_*` sollevati dai trigger sono **propagati al client come
`ServiceError.code` originale** (non rimpiazzati da `E_VENDITE_VALIDATION`),
estratti via regex dal MESSAGE del trigger. Questo permette al FE di fare
routing UI specifico per codice (es. dialog "versione listino non ATTIVA"
diverso da "transizione non ammessa generica").

## Dipendenze DB

**Tabelle**:

- `vendite.offerte_commerciali` — testata
- `vendite.offerte_commerciali_eccezioni` — mirror di `contratti_righe`
- `vendite.offerte_commerciali_utilities` — estensione 1:1 (UNIQUE `offerta_id`)
- `vendite.note_offerte_commerciali` — partizione del sistema note generico
  (`target_tipo = 'OFFERTA'`), cablata via building block
  `apps.core.db.PartitionedNoteRepository` (cablaggio differito, vedi piano BE/FE)

**Funzioni**:

- `script.fn_generate_codice('offerta_commerciale')` — generazione codice
  `OFC-*` (step 5 atterrato 2026-05-25, invocata dal trigger BEFORE INSERT).
- `vendite.fn_crea_revisione_offerta(p_offerta_id, p_user)` — step 7
  atterrato 2026-05-25. Crea rev.N+1 da offerta EMESSA copiando testata +
  eccezioni attive + utility 1:1. Ritorna `BIGINT` (id nuova rev).
- `vendite.fn_push_offerta_a_contratto(p_offerta_id, p_pratica_id, p_chiudi_contratto_esistente)` —
  step 8 atterrato 2026-05-25 PM, esteso 2026-05-31 con la successione su
  overlap. Crea contratto DRAFT da offerta ACCETTATA, copia 1:1 eccezioni e
  UPSERT utility (sovrascrive il record creato dal trigger snapshot
  precontrattuali). Idempotente per costruzione (UNIQUE
  `uq_contratti_offerta_id`). Pratica opzionale (collega via
  `pratiche.pratiche_sorgenti`). 3° param `p_chiudi_contratto_esistente`
  (default false): su contratto attivo sovrapposto solleva
  `E_CONTRATTO_OVERLAP_ESISTENTE` se false, esegue la successione se true.
  Ritorna `BIGINT` (id nuovo contratto).
- `vendite.fn_contratto_sovrapposto(...)` — rilevamento read-only (`STABLE`)
  del contratto attivo sovrapposto sulla quintupla `ex_contratti_no_overlap`.
  Meccanismo generico di dominio contratti (riusabile da ogni percorso di
  creazione). Esposto via `OfferteRepository.get_contratto_sovrapposto` per
  l'endpoint `GET /<id>/contratto-sovrapposto/`.
- `vendite.fn_chiudi_contratto_per_successione(p_contratto_id, p_nuovo_valido_dal)` —
  accorcia il contratto esistente (`valido_al = nuovo valido_dal − 1`); nessun
  cambio di stato (lo allinea il job notturno `chiusura_scadenze_daily`).
  Guard `E_CONTRATTO_SUCCESSIONE_DATA_INVALIDA` su date incoerenti.
- `script.fn_available_actions_offerta(p_offerta_id)` — D7 atterrata
  2026-05-26 (migration `20260526-01`). Capability layer pure-read:
  ritorna `jsonb` con `available_actions[]` dalla matrice
  `config.stati_doc_offerte_transizioni.meta` (azioni manuali) + hardcode
  di `crea_revisione` (EMESSA) e `push_contratto` (ACCETTATA con check
  cross-dominio `EXISTS vendite.contratti.offerta_id`), oltre a
  `can_edit_*`, `can_push_contratto_reason`, `non_editable_fields`,
  `stato_codice`. Mergeata nel detail `get_offerta` per il FE
  data-driven.

**Trigger autoritativi**:

- `trgfn_offerte_commerciali_guard_transizione` — state machine + guard
  versione listino + valorizzazione timestamp transizione.
- `trgfn_offerte_commerciali_gen_codice` — generazione codice
  `OFC-NNNNNNN` (BEFORE INSERT) se `codice IS NULL` o vuoto.
- `trgfn_offerte_commerciali_revisione` — AFTER INSERT: marca la
  rev.N come SUPERATA quando si inserisce la rev.N+1 (cascata sicura
  perche' la transizione `EMESSA -> SUPERATA` e' ammessa nel seed).

**Stati** gestiti via `config.stati_doc_offerte`
(BOZZA / EMESSA / ACCETTATA / RIFIUTATA / ANNULLATA / SUPERATA).

## Note di migrazione

- **Step DB 1-4 + addendum atterrati 2026-05-24** (commit `2000d8261`).
  Cablato lato BE: testata + eccezioni + utility 1:1 + state machine
  asimmetrica + 6 codici errore.
- **Step DB 5-7 atterrati 2026-05-25 AM** (commit `13d57a846`). Cablato
  lato BE: codice automatico `OFC-*` via trigger, `crea-revisione/` end-to-end,
  `revisioni/` (lista catena via CTE ricorsiva).
- **Step DB 8-9 atterrati 2026-05-25 PM** (commit `906720ac5`). Cablato
  lato BE: `push-contratto/` end-to-end con pattern A idempotenza (UNIQUE
  `uq_contratti_offerta_id`); suite pgTAP completa (revisione, push,
  codice, struttura, end-to-end, state machine).
- **Bonus dal team DB**: messaggio errore `E_OFFERTA_TRANSIZIONE_NON_AMMESSA`
  refuso corretto allineato alla state machine reale; potenziamento sync
  `sistema_codici` (creazione sequenze automatica); guard transizione
  in forma `VARIADIC`.
- **Step DB D7 atterrato 2026-05-26** (`20260526-01-create-fn-available-actions-offerta-mctit.yaml`
  + seed `stati_doc_offerte_transizioni.csv` aggiornato con
  `requires_motivazione` per transizioni manuali). Cablato lato BE in
  giornata: capability blob mergeato in `get_offerta`, atomicita' utility
  inline su `crea_offerta` + `aggiorna_offerta`, LEFT JOIN `contratti`
  per `contratto_id`/`contratto_numero`, alias display fields
  `billing_account_display` + `utility_display`, cablaggio note partizionate
  `target_tipo='OFFERTA'` con factory in `note_views.py`. Test BE 42/42.
- **FE cantiere completato 2026-05-26**: `OffertaDrawer.vue` data-driven
  (`useEntityCapabilities` + `mapAvailableActionsToDrawerActions`,
  dispatch unico `onActionDispatch(action.key)`), drawer eccezioni
  master-detail inline, drawer note thin wrapper, deep-link contratto
  post-push (`?open=<id>` su `ContrattiListView`), dialog parlante
  `E_OFFERTA_CONTRATTO_GIA_GENERATO` con link al contratto esistente.
- **Successione contratti su overlap atterrata 2026-05-31** (DB su
  `dev/db-tid` + BE/FE). Meccanismo generico DB (`fn_contratto_sovrapposto`
  read-only + `fn_chiudi_contratto_per_successione`), push a 3 parametri,
  endpoint `GET /<id>/contratto-sovrapposto/`, codici
  `E_CONTRATTO_OVERLAP_ESISTENTE` / `E_CONTRATTO_SUCCESSIONE_DATA_INVALIDA`.
  FE: `OffertaSuccessioneDialog` con conferma esplicita; il push si re-invoca
  con `chiudi_esistente=true`. Vedi
  [brief](../../../dev/work-done/brief-db-offerta-push-successione-contratto-overlap.md).

Dominio offerta commerciale: **completo lato BE + FE**. Niente cantieri
aperti.

## Riferimenti

- Modello: [analisi-offerta-commerciale](/dev/work-in-progress/analisi-offerta-commerciale)
- Brief DB: [analisi-offerta-commerciale-db](/dev/work-done/analisi-offerta-commerciale-db)
- Piano BE+FE: [analisi-offerta-commerciale-be-fe](/dev/work-in-progress/analisi-offerta-commerciale-be-fe)
- Manuale service: [offerte_service](/backend/vendite/manual/offerte_service)
- API contratto (specchio strutturale): [api_contratti](/backend/vendite/manual/api_contratti)
