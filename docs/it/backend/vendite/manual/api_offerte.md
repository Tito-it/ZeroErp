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
- **Versione listino fissata all'emissione, dal DB**: in `BOZZA`
  `listino_versione_id` e' NULL e l'offerta vive sulla versione **in vigore oggi**
  (`vendite.fn_documento_listino_operativo`, la stessa per righe, pricing e
  capability). Al passaggio `BOZZA -> EMESSA` il guard di transizione la
  **congela** nella stessa scrittura, dopo averla verificata con
  `script.fn_check_listino_congelabile`. Da `EMESSA` in poi e' immutabile
  (brief-db-offerta-emissione-ed-erogazione, 2026-10-07).
- **Eccezioni come mirror di `contratti_righe`** con i 5 CHECK constraint
  replicati (`chk_offerte_eccezioni_*`) **e** i gate prezzo L1/L2/L3
  (refactor-prezzi 2026-06-01). Le colonne `stato_approvazione_prezzo` e
  `pratica_approvazione_prezzo_id` esistono su `offerte_commerciali_eccezioni`
  (migration `20260601-01`): la proposta ha lo stesso workflow di approvazione
  prezzo del contratto. Al push lo stato approvazione viene **copiato 1:1** sul
  contratto (non più NULL) — un override già autorizzato in offerta non va
  riapprovato. Vedi [API approvazioni prezzo](api_approvazioni_prezzo.md) e
  [refactor-prezzi](../../../dev/work-done/refactor-prezzi.md).
- **State machine asimmetrica** (decisione operativa): annullamento da noi
  prima dell'emissione, o dopo l'accettazione se l'offerta non si trasforma
  (dal 2026-10-21); rifiuto cliente solo dopo l'emissione.

## Contesto

- Il **codice offerta** `OFC-*` e' generato dal trigger DB
  `trgfn_offerte_commerciali_gen_codice` (BEFORE INSERT, step 5 brief DB
  atterrato 2026-05-25). Il campo `codice` **non va nel payload** in
  creazione: se inviato viene rifiutato come `unknown_key`. Lookup
  `script.fn_generate_codice('offerta_commerciale')` con prefisso `OFC`
  e lunghezza 7.
- Lo **stato iniziale** di ogni offerta e' `BOZZA`: lo mette il DB alla nascita
  (`script.trgfn_doc_stato_iniziale`), il service non lo passa.
- ⭐ **Lo stato lo scrivono solo i verbi** (dal 2026-10-26,
  brief-modello-documento-vendita §13, giro 9): `vendite.fn_cambia_stato_offerta`
  per «Emetti» e l'esito, `vendite.fn_annulla_offerta` per l'annullo. Un `UPDATE`
  diretto della colonna di stato lo rifiuta la porta
  (`E_DOC_STATO_SOLO_DAL_VERBO`). Il verbo giudica, prima di scrivere: il
  perimetro (fuori perimetro = `E_OFFERTA_NON_TROVATA`), lo stato che l'offerta
  ha gia' (`E_DOC_GIA_NELLO_STATO`), l'azione dalla riga del passaggio e la
  motivazione dove la riga la chiede. Il service non ripete nessuno stato di
  partenza.
- **Permessi del passaggio** (O-1, guida del modello §6): la riga della matrice
  `config.stati_doc_offerte_transizioni` dichiara l'azione. `emetti_offerta` su
  `BOZZA -> EMESSA` («Emetti») e `ACCETTATA -> ANNULLATA` (l'annullo
  dell'accettata); accetta, rifiuta e l'annullo della bozza chiedono il solo
  livello sul documento. La view risponde 403 `E_PERMESSO_NEGATO` prima della
  transazione (`PassaggioDocumento`: `emetti_passaggio` della factory documenti,
  `post_passaggio` su `/registra-esito/` e `/annulla/`); la capability nasconde
  le azioni a chi non ha l'azione. ⚠️ `emetti_offerta` non la riceve nessun
  profilo dai seed: va concessa.
- La **state machine** e' autoritativa lato DB tramite il trigger
  `trgfn_offerte_commerciali_guard_transizione` che:
  - verifica che la transizione sia in `config.stati_doc_offerte_transizioni`
  - valorizza `data_emissione` / `data_accettazione` / `data_rifiuto` /
    `data_annullamento` al passaggio
  - su `BOZZA -> EMESSA` congela `listino_versione_id` sulla versione in vigore
    oggi, e rifiuta col primo motivo di `script.fn_check_listino_congelabile`:
    listino senza versione in vigore (`E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO`)
    o versione gia' fissata non piu' ATTIVA
    (`E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA`). La capability spegne
    «Emetti» con la stessa check (`reason_key`
    `vendite.offerte.azione_reason.listino_senza_versione_in_vigore` /
    `…listino_versione_non_attiva`): pulsante e guard non possono dissentire
  - su `BOZZA -> EMESSA`, per ultime, le **righe** che la regola intera non
    ammette piu' (`script.fn_check_righe_documento`: articolo, erogazione e
    fonte, giudicati sui dati di oggi) → `E_DOC_RIGA_NON_AMMESSA` col campo
    `articolo_id`; la capability spegne «Emetti» col motivo `RIGA_NON_AMMESSA`
    (dal 2026-10-21, H-R1 di brief-db-offerta-emissione-ed-erogazione)
  - verso `ANNULLATA` da `ACCETTATA`: rifiuta se dall'offerta vive un contratto
    o un ordine (`script.fn_check_offerta_annullabile` →
    `E_OFFERTA_ANNULLO_CON_DOCUMENTI_VIVI`, col bersaglio)
- I codici errore `E_OFFERTA_*` sollevati dal trigger sono **estratti dal
  MESSAGE** del trigger via regex (`_DB_ERROR_CODE_RE`) e propagati al client
  come `ServiceError.code` originale, non come `E_VENDITE_VALIDATION` generico.
  Il FE puo' fare routing UI specifico per codice.

### State machine

| Da     | A         | Chi la innesca                | Azione            | Effetto laterale                                                |
| ------ | --------- | ----------------------------- | ----------------- | --------------------------------------------------------------- |
| BOZZA  | EMESSA    | operatore (`/emetti/`)        | `emetti_offerta`  | Congela versione listino; valorizza `data_emissione`            |
| BOZZA  | ANNULLATA | operatore (`/annulla/`)       | —                 | Valorizza `data_annullamento` + `motivazione_rifiuto` (obbligatoria) |
| EMESSA | ACCETTATA | operatore (`/registra-esito/`) | —                | Valorizza `data_accettazione`                                  |
| EMESSA | RIFIUTATA | operatore (`/registra-esito/`) | —                | Valorizza `data_rifiuto` + `motivazione_rifiuto` (obbligatoria) |
| EMESSA | SUPERATA  | DB, alla revisione (processo) | —                 | Stato terminale tecnico; rev.N+1 diventa la nuova offerta corrente |
| ACCETTATA | ANNULLATA | operatore (`/annulla/`)    | `emetti_offerta`  | Solo senza contratti o ordini vivi a valle (dal 2026-10-21); valorizza `data_annullamento` + `motivazione_rifiuto` (obbligatoria) |
| SUPERATA | EMESSA   | DB, all'annullo dell'ultima revisione viva (processo) | — | Rientro del padre; l'annullo che lo causa si conferma (vedi `/annulla/`) |

Stati terminali: **RIFIUTATA**, **ANNULLATA**. **ACCETTATA** si chiude
trasformandola (contratto o ordine) o, quando non si puo' trasformare,
annullandola (H-R3 di brief-db-offerta-emissione-ed-erogazione: prima del
2026-10-21 un'offerta accettata che non si trasformava restava bloccata).
**SUPERATA** non ha uscite manuali. Transizioni *NON* ammesse (documentate per
evitare ambiguita'):

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
- `GET/POST /<id>/note/` + `GET/PATCH/DELETE /<id>/note/<note_id>/` —
  cablaggio building block `PartitionedNoteRepository` per
  `target_tipo='OFFERTA'` (2026-05-26; `'OFFERTA_COMMERCIALE'` dal 2026-10-25). Contratto comune in
  [api_note_documento](../../core/manual/api_note_documento.md)

### Perimetro D7 — capability layer + refactor atomico (2026-05-26)

Step migliorativo data-driven applicato dopo la consegna della fn DB
`script.fn_available_actions_offerta` (migration `20260526-01`):

- **Capability blob** nel detail: `get_offerta` ora include
  `available_actions[]`, `can_edit_*`, `can_push_contratto`,
  `non_editable_fields`, `stato_codice` letti da `script.fn_available_actions_offerta`,
  nella chiave `capabilities` (dal 2026-09-23; vuota, mai assente, se la
  funzione fallisce).
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
    "valuta_descrizione": "Euro",
    "fornitura": {
      "istanza_dati_precontrattuali_id": 88, "classe_utenza_id": 7,
      "tipo_utenza_id": 2, "param_1_num": "1500", "param_2_txt": "POD-XYZ",
      "meta": {}
    }
  }
}
```

`fornitura`: la scheda di fornitura che l'anagrafica dà alla coppia (istanza,
utility) del BA (`vendite.fn_get_fornitura_da_anagrafica`), con cui il drawer
precompila il sotto-oggetto `utility`. `null` senza BA o se la coppia non ha dati
precontrattuali.

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
> `listino_versione_codice`, `valuta_codice`) e **materializza `is_scaduta`**:
> la regola intera, validita' passata (`script.fn_data_operativa`) **e** nessun
> esito del cliente (`esito IS NULL` sullo stato). ⛔ Fino al 2026-11-13 la
> vista diceva solo la validita' e il FE completava con
> `STATI_OFFERTA_SEGNALA_SCADENZA` (D-SCAD,
> brief-db-stati-documento-dal-vocabolario §6.8): ritirata. Campi display con i **nomi
> canonici**: cliente = `ragione_sociale_completa`, id. fiscale =
> `id_fiscale_univoco_cf_piva`, codice account = `ba_codice`, stato =
> `stato_descrizione` + `stato_codice_interno`. Il **dettaglio** (`GET .../<id>/`)
> conserva i nomi storici (`billing_account_display`, `utility_display`): fonte
> diversa (JOIN su tabelle base). `vw_offerte_commerciali_list` deprecata (drop
> differito post-BE).

| Parametro              | Tipo     | Descrizione                                                                                |
| ---------------------- | -------- | ------------------------------------------------------------------------------------------ |
| `search`               | string   | ILIKE su `codice` offerta, `ragione_sociale_completa`, `ba_codice` e `id_fiscale_univoco_cf_piva`. Sotto 3 caratteri il termine **non filtra** (nessun errore) |
| `billing_account_id`   | int      | Filtro cliente                                                                              |
| `stato_codice_interno` | string   | `BOZZA` \| `EMESSA` \| `ACCETTATA` \| `RIFIUTATA` \| `ANNULLATA` \| `SUPERATA`. Fuori vocabolario `config.stati_doc_offerte` → 400 `E_VENDITE_VALIDATION` col campo (2026-10-20: prima lista vuota con 200) |
| `utility_id`           | int      | Filtro utility                                                                              |
| `listino_id`           | int      | Filtro listino di riferimento                                                               |
| `validita_dal_min`     | ISO date | Filtro su `validita_dal` (range minimo). Nessun default backend                             |
| `validita_dal_max`     | ISO date | Filtro su `validita_dal` (range massimo)                                                    |
| `solo_ultima_revisione` | bool    | Default `true`: solo la revisione non rimpiazzata per lineage (`vw_offerte_commerciali_lista.is_superata IS FALSE`). Filtra sulla posizione nella catena, non sullo stato: le ANNULLATE restano visibili. `false` = storico revisioni completo |
| `limit`                | int      | Default 25                                                                                  |
| `offset`               | int      | Default 0                                                                                   |
| `order_by`             | string   | `campo_sorgente` catalogo `vendite.offerte`: `codice` \| `ragione_sociale_completa` \| `ba_codice` \| `id_fiscale_univoco_cf_piva` \| `utility_codice` \| `utility_descrizione` \| `listino_codice` \| `validita_dal` \| `validita_al` \| `data_emissione` \| `data_accettazione` \| `data_rifiuto` \| `data_annullamento` \| `stato_descrizione` \| `data_insert` \| `pratica_numero` \| `fase` (default `data_insert`). Fuori whitelist → 400. `revisione_numero` **non ordinabile** |
| `order_dir`            | string   | `asc` \| `desc`. Assente: `desc` sulle colonne data e sul default `data_insert`, `asc` sulle altre |

> **`search` corto o vuoto**: vuoto, whitespace-only o sotto 3 caratteri →
> nessun filtro, nessun errore (BB `add_ricerca_full_condition`, soglia unica
> delle liste). Fino al 2026-09-23 sotto i 3 caratteri rispondeva 400
> `E_VENDITE_VALIDATION`.

> **Scope emittente** (dal 2026-09-21): lista **ed export** applicano il filtro
> applicativo `v.emittente_fiscale_id = ANY(<whitelist>)` risolto da
> `get_scope_user_id(request)` → `add_emittente_scope_condition` (convenzione
> `pk`), lo stesso calco di preventivi e contratti; `None` = nessuna
> restrizione, whitelist vuota = **fail-closed**. Si **somma** alla RLS della
> vista (`security_invoker=on`), non la sostituisce (api.md §«Scope emittente»).
> Fino a quel giorno la lista offerte era l'unica di testata del dominio senza
> — il «B1» dell'analisi RLS. Presidio:
> `apps/vendite/tests/db/test_offerte_scope_emittente.py`.

### Export lista offerte `GET /api/v1/vendite/offerte/export/`

Genera un file **CSV** o **Excel** con le offerte filtrate (stessi parametri
della lista). Renderer generico DEF-1 (`ListaExportService`); colonne coerenti
con la DataTable a video (config runtime: preferenza + preset + permessi).

| Parametro | Tipo | Descrizione |
|---|---|---|
| `formato` | string | `csv` (default) o `xlsx`. **NB**: `formato` (italiano), NON `format` (magic param DRF) |
| `search`, `billing_account_id`, `stato_codice_interno`, `utility_id`, `listino_id`, `validita_dal_min`, `validita_dal_max`, `solo_ultima_revisione`, `order_by`, `order_dir` | — | stessi della lista |

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
- **I canoni della testata** (dal 2026-10-29, F-2 e F-7 di
  brief-db-contratto-righe-periodiche-in-commessa), in creazione e in PATCH:
  `generazione_canone` (`INIZIO_PERIODO` = anticipati, il default;
  `FINE_PERIODO` = normali) e `mese_partenza_canone` (1-12, default 1: il mese da
  cui si contano i periodi). NOT NULL: si omettono o si mandano valorizzati, mai
  `null`. Il dominio lo dicono i CHECK `chk_offerte_commerciali_*`, tradotti sul
  campo (400). Fuori bozza li ferma il lock di testata
  (`E_DOC_CONDIZIONI_FUORI_BOZZA`, 409). Il passaggio a contratto li copia. Una
  riga a canone con `generazione_canone` vuota segue la testata.
- Coerenza coppia variazione globale: `tipo_variazione_globale` +
  `valore_variazione_globale` entrambi NULL o entrambi NOT NULL (CHECK DB
  `chk_offerte_variazione_globale_coerenza`).

### Detail `GET /api/v1/vendite/offerte/<id>/`

Output: testata + display fields + `eccezioni[]` + `utility` (1:1, null se
non ancora compilato) + `capabilities` (con `stato_terminale`, la colonna
`terminale` del vocabolario: il banner del drawer la legge invece di un elenco
di stati). `is_scaduta` (dal 2026-11-13) è letto dalla vista della lista, la
sede della regola (D-SCAD): dettaglio e lista dicono la stessa cosa. `contatori` (dal 2026-10-25): `{"note": <n>}`, il numero sul pulsante «Gestisci note» del drawer, dal BB `contatori_documento` — contato **dopo** il cancello di testata, con lo stesso perimetro della lista note. Forma e ragioni in [api_fattura_dettaglio §`contatori`](/backend/vendite/manual/api_fattura_dettaglio).

```json
{
  "data": {
    "id": 1, "uid": "...", "codice": "OFC-0000001",
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
    "is_scaduta": false,
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
    "capabilities": {
      "available_actions": [
        {
          "key": "emetti", "target_state": "EMESSA",
          "label_key": "vendite.offerte.azione_emetti",
          "requires_confirm": true, "requires_motivazione": false
        },
        {
          "key": "annulla", "target_state": "ANNULLATA",
          "label_key": "vendite.offerte.azione_annulla",
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
      "can_genera_ordine": false,
      "can_genera_ordine_reason": "OFFERTA_NON_ACCETTATA",
      "can_genera_ordine_reason_key": "vendite.offerte.push_reason.non_accettata",
      "non_editable_fields": [
        "codice", "uid", "revisione_numero", "revisione_padre_id",
        "stato_doc_offerta_id", "data_emissione", "data_accettazione",
        "data_rifiuto", "data_annullamento", "motivazione_rifiuto"
      ],
      "stato_codice": "BOZZA"
    },
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
- **Capability blob** (da `script.fn_available_actions_offerta`, sotto
  `capabilities`): `available_actions[]` lista azioni ammesse nello stato
  corrente (mappabili 1:1 a `DrawerActionsBar` via
  `mapAvailableActionsToDrawerActions`); `can_edit_testata` /
  `can_edit_eccezioni` / `can_edit_utility` flag editabilita';
  `can_change_state` true se almeno un'azione disponibile;
  `can_create_revisione` / `can_push_contratto` / `can_genera_ordine`
  flag per azioni speciali non-cambio-stato. Le due materializzazioni sono
  **mutuamente esclusive** (XOR): ognuna è abilitata solo se non esiste né un
  contratto né un ordine generati dall'offerta. `can_push_contratto_reason` +
  `can_push_contratto_reason_key` coppia stabile reason-code +
  chiave i18n quando il push non e' ammesso (`OFFERTA_NON_ACCETTATA`,
  `OFFERTA_CONTRATTO_GIA_GENERATO` o `OFFERTA_ORDINE_GIA_GENERATO`); analoga coppia
  `can_genera_ordine_reason` + `can_genera_ordine_reason_key` per la
  generazione ordine (`OFFERTA_NON_ACCETTATA`, `OFFERTA_ORDINE_GIA_GENERATO` o
  `OFFERTA_CONTRATTO_GIA_GENERATO`). ⭐ Dal 2026-10-21 da `ACCETTATA` senza
  documenti vivi le azioni `push_contratto` e `genera_ordine` sono **proposte**
  in `available_actions` anche spente (`enabled:false` + `reasons`), col motivo
  `RIGA_NON_AMMESSA` se una riga non puo' andare nel documento da generare; il
  flag e la coppia reason seguono il primo motivo. Fuori da quel caso le due
  azioni non compaiono e il motivo sta solo nella coppia reason;
  `non_editable_fields[]` lista
  immutabili (sempre + workflow-dipendenti, lista lunga fuori BOZZA);
  `stato_codice` discriminante macchina (equivalente a
  `stato_codice_interno`, esposto anche dalla fn DB).

### Update testata `PATCH /api/v1/vendite/offerte/<id>/`

Nessun guard di stato nel service: quali colonne si cambiano in quale stato lo
decide il lock di testata del DB (`trgfn_doc_testata_lock_fuori_bozza`, il 409
`E_DOC_*` passa com'e'; vedi §Regole 3). Offerta inesistente o fuori perimetro →
404. Whitelist campi mutabili: `emittente_fiscale_id`,
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

Solo la bozza vuota: la regola «si cancella solo la bozza vuota» la giudica **solo il DB** (`vendite.trgfn_doc_guard_delete_solo_bozza`, dal 2026-11-08: il service non la ripete, brief-db-sorgente-documento-e-riga §8.21 BE-Z.2-a): fuori bozza 409 `E_DELETE_DOC_NON_BOZZA`, bozza con contenuto 409 `E_DELETE_DOC_CON_RIGHE`, documento citato come origine da un altro 409 `E_SORG_ORIGINE_REFERENZIATA`; il service legge solo l'esito del `DELETE`. Per l'offerta il contenuto sono le
eccezioni attive. Il pre-check di stato del service (400 `E_VENDITE_VALIDATION`)
è ritirato, e con lui `_STATI_EDITABILI`. L'offerta che non c'è è un 404
`E_VENDITE_NOT_FOUND`. Hard delete dell'offerta + cascade su
`offerte_commerciali_eccezioni` e `offerte_commerciali_utilities` via FK.
Il FE non offre l'eliminazione (UI-Z.2-a): l'azione `elimina` dello store e
`deleteOfferta` sono ritirate il 2026-11-08.

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

⭐ **Permesso e stato dal modello** (dal 2026-10-26, brief-modello-documento-vendita
§13.6): la view chiede `emetti_offerta` dalla riga del passaggio verso lo stato
di emissione, letto dal vocabolario a ogni richiesta (403 `E_PERMESSO_NEGATO`
prima della transazione); `OfferteService.emetti` chiama il verbo
`vendite.fn_cambia_stato_offerta` con lo stato di emissione del vocabolario. Un
secondo «Emetti» e' il 409 `E_DOC_GIA_NELLO_STATO` del verbo, e il PDF non nasce.
⛔ Fino al 2026-10-26: un pre-check Python «solo da BOZZA» e un `UPDATE` diretto
dello stato.

⭐ **La versione di listino la congela il DB** (dal 2026-10-07,
brief-db-offerta-emissione-ed-erogazione A-R1/A-R2). `OfferteService.emetti` fa
solo il cambio stato; il guard `trgfn_offerte_commerciali_guard_transizione`, su
`BOZZA -> EMESSA`:

1. verifica la versione che verrebbe congelata con
   `script.fn_check_listino_congelabile` — la fissata, altrimenti quella in
   vigore oggi — e solleva il primo motivo:
   `E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO` (409, il listino non ha una
   versione in vigore oggi) o `E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA`
   (409, la versione gia' fissata si e' chiusa);
2. congela `listino_versione_id` se e' vuota, nella stessa scrittura;
3. valorizza `data_emissione = now()`.

⛔ Fino al 2026-10-07 il congelamento lo faceva il service, in Python, prima del
cambio stato (`_fissa_versione_listino_se_necessario`, ritirato): la capability
leggeva la colonna nuda e spegneva «Emetti» proprio perche' quel passo non
c'era ancora stato — un'offerta nuova non si emetteva.

Da questo momento la versione del listino è "congelata": modifiche al
listino sottostante non si propagano all'offerta.

Semantica transazionale (refactor 2026-05-28): la view apre
`transaction.atomic()` esterno che racchiude (in ordine):
`OfferteService().emetti(offerta_id)` (cambio stato, che congela la versione) →
`_resolve_contesto_offerta` →
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
[api_documenti_helpers](../../documenti/manual/api_documenti_helpers.md).

### Cambio stato EMESSA -> ACCETTATA/RIFIUTATA `POST /api/v1/vendite/offerte/<id>/registra-esito/`

```json
{"esito": "ACCETTATA"}
```

oppure

```json
{"esito": "RIFIUTATA", "motivazione": "Cliente preferisce concorrente X."}
```

- `esito = "ACCETTATA"`: valorizza `data_accettazione`. **Nessuna
  motivazione**: una `motivazione` non vuota e' un 400 `E_VENDITE_VALIDATION`
  col campo `motivazione` (l'accettazione non ha una colonna che la tenga);
  assente, `null` o vuota passa. ⛔ Fino al 2026-10-26 era scartata in
  silenzio.
- ⭐ `ACCETTATA` e `RIFIUTATA` sono **parole dell'API**: lo stato che l'esito
  scrive lo dice il vocabolario, colonne `accettazione` e `rifiuto`
  (`script.fn_stato_accettazione_id` / `script.fn_stato_rifiuto_id`, dal BB
  `stato_di_accettazione` / `stato_di_rifiuto`); un vocabolario che non lo
  marca è `E_CONFIG_MANCANTE`.
- `esito = "RIFIUTATA"`: valorizza `data_rifiuto` +
  `motivazione_rifiuto`. **Motivazione obbligatoria**: lo dice la riga del
  passaggio (`requires_motivazione` nel `meta`), e la fa rispettare il verbo →
  400 `E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA` col campo `motivazione` (il verbo
  nomina la colonna `motivazione_rifiuto`, il service la traduce nel campo
  della richiesta). Vuota
  o di soli spazi vale assente. Una `motivazione` che non e' una stringa e' un
  400 `E_VENDITE_VALIDATION` col campo. ⛔ Fino al 2026-10-26 l'obbligo era una
  copia Python (`guard_non_empty_string`, `E_VENDITE_VALIDATION`).
- `esito` non valido → `E_VENDITE_VALIDATION` col campo `esito` e detail
  "Atteso uno tra ['ACCETTATA', 'RIFIUTATA']": e' la validazione del campo in
  ingresso, non lo stato di partenza.
- Da quale stato si registra un esito lo dice la matrice: da uno stato diverso
  da EMESSA e' il 409 `E_OFFERTA_TRANSIZIONE_NON_AMMESSA` (⛔ fino al
  2026-10-26 un pre-check Python, 400).

Permesso: il livello sul documento (accetta e rifiuta non hanno un'azione
sulla riga del passaggio); la view lo legge comunque dalla riga
(`post_passaggio`, campo `esito`), cosi' un'azione aggiunta domani alla matrice
vale senza toccare il codice. ⭐ La riga che legge e' quella verso lo stato che
il verbo scrive: la parola dell'esito nomina un ruolo (`RUOLO_DEGLI_ESITI`:
`ACCETTATA` → `accettazione`, `RIFIUTATA` → `rifiuto`) e lo stato si chiede
al vocabolario (`stato_del_campo`). ⛔ Fino al 2026-11-14 cercava la riga
verso la parola, che coincide con lo stato solo finche' il vocabolario lo
chiama cosi'. Routing per esito nel service (`registra_esito`),
la view e' sottile.

### Cambio stato -> ANNULLATA `POST /api/v1/vendite/offerte/<id>/annulla/`

```json
{"motivazione": "Riscontrato errore nel listino di riferimento.", "legami_confermati": 1}
```

Dal verbo `vendite.fn_annulla_offerta(id, motivazione, legami_confermati)` (dal
2026-10-26, O-4). Motivazione obbligatoria, dal verbo:
`E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA` (400, campo `motivazione`; ⛔ fino
al 2026-10-26 una copia Python). Salvata in `motivazione_rifiuto` (colonna
condivisa con RIFIUTATA). Il trigger DB valorizza `data_annullamento`. Lo stato
d'annullo lo sceglie il verbo dal vocabolario (`is_abortito`).

Permesso: l'annullo dell'accettata chiede `emetti_offerta` dalla riga del
passaggio (403 prima della transazione), quello della bozza il solo livello sul
documento.

⭐ **L'annullo di una revisione si conferma** (Regola 6 della guida del
modello): annullare l'ultima revisione viva fa tornare EMESSA la revisione
precedente (superata), e non in silenzio. Il primo tentativo, senza
`legami_confermati`, risponde 409 `E_DOC_ANNULLO_CON_LEGAMI`
(`ui_action: confirm_and_retry`); la finestra legge i legami da
`GET /<id>/legami/` (sotto) e la conferma ripete la richiesta dichiarando
`legami_confermati` = il numero letto. Se nel frattempo i legami sono cambiati,
il DB chiede di nuovo. Una revisione il cui padre non torna emesso (un'altra
revisione viva lo tiene superato, o non c'e' padre) si annulla al primo colpo.
`legami_confermati` non intero → 400 `E_VENDITE_VALIDATION` col campo.

Annullamento ammesso da **BOZZA** e da **ACCETTATA** (dal 2026-10-21, H-R3):
da ACCETTATA solo se l'offerta non ha generato un contratto o un ordine ancora
vivo, altrimenti `E_OFFERTA_ANNULLO_CON_DOCUMENTI_VIVI` (409, col bersaglio).
⛔ Il service **non** ha uno stato di partenza suo: da quali stati si annulla lo
dicono le transizioni del DB, e un tentativo da un altro stato e' il 409
`E_OFFERTA_TRANSIZIONE_NON_AMMESSA` del guard. Fino al 2026-10-21 c'era un
pre-check «solo da BOZZA» (400 `E_VENDITE_VALIDATION`), che avrebbe rifiutato
l'annullo da ACCETTATA. Offerta inesistente o fuori perimetro → 404
`E_OFFERTA_NON_TROVATA`, dal verbo, come su `/emetti/`, `/registra-esito/` e
`/push-contratto/`: dal 2026-10-27 il service non lo ridice col suo codice
(regola del 1, Tid: i verbi prendono la testata nel perimetro). `/legami/` legge
ancora prima la testata (404 `E_VENDITE_NOT_FOUND`: il lettore dei legami non
applica il perimetro), e così `/crea-revisione/` finché la sua fn risponde
all'offerta che non c'è con un 400 `E_PARAMETRO_INVALIDO` (richiesta al team DB). ⛔ Dal 2026-10-26 nessun pre-check di stato nemmeno su
`/emetti/`, `/registra-esito/`, `/crea-revisione/` e `/push-contratto/`: li
giudicano verbi e funzioni del DB.

### Legami dell'annullo `GET /api/v1/vendite/offerte/<id>/legami/`

La finestra di conferma dell'annullo (factory `build_legami_view`, BB
`legami_del_documento`, lettore `vendite.fn_documento_legami('OFFERTA_COMMERCIALE', id)`).
Prima la testata: offerta inesistente o fuori perimetro → 404
`E_VENDITE_NOT_FOUND`.

```json
{"data": {"documento": "OFFERTA_COMMERCIALE", "id": 42, "legami": 1, "righe": [
  {"riga_id": null, "riga_nr": null, "origine": "OFFERTA_COMMERCIALE", "natura": "PROVENIENZA",
   "origine_id": 41, "origine_riga_id": null, "qta": null,
   "origine_tipo_codice_interno": "OFFERTA_COMMERCIALE", "origine_codice": null}
]}}
```

Il legame dell'offerta e' la revisione precedente (`origine_id`) che torna
emessa. ⚠️ La revisione precedente non e' un nodo del lineage (nessun arco
offerta → offerta): `origine_codice` resta `null`, e la finestra mostra il solo
tipo, senza link. `legami` e' il numero da dichiarare in `legami_confermati`.

### Crea revisione `POST /api/v1/vendite/offerte/<id>/crea-revisione/`

Body vuoto. Crea rev.N+1 in stato `BOZZA` a partire dall'offerta corrente
(che deve essere in stato `EMESSA`). Effetti:

1. Invoca `vendite.fn_crea_revisione_offerta(offerta_id, user)` (step 7
   brief DB).
2. La fn DB copia testata + eccezioni attive + utility 1:1 nella nuova
   revisione, con `revisione_numero = N+1` e `revisione_padre_id = <id>`.
   ⭐ **Tranne la versione di listino**: la revisione nasce con
   `listino_versione_id` NULL e congela alla **sua** emissione (decisione A-D3
   di Tid, 2026-10-07). Una revisione è una proposta nuova, mandata in un giorno
   nuovo; con la copia, una versione chiusa nel frattempo l'avrebbe resa non
   emettibile.
3. Il codice `OFC-*` della nuova rev e' generato ex novo dal trigger
   `gen_codice` (uid e timestamp di transizione restano NULL).
4. Il trigger `trg_offerte_commerciali_z90_revisione_ins` (step 6,
   AFTER INSERT) marca **automaticamente** la rev.N come `SUPERATA`
   (transizione `EMESSA -> SUPERATA` ammessa nel seed).
5. Ritorna il dettaglio della nuova rev.N+1 (testata + eccezioni + utility).

Guard:

- Stato corrente diverso da `EMESSA` → 409
  `E_OFFERTA_REVISIONE_STATO_NON_AMMESSO` dalla fn DB. ⛔ Fino al 2026-10-26 lo
  anticipava un pre-check del service (400 `E_VENDITE_VALIDATION`).
- Offerta inesistente → 404.

`user` di audit: il service prende `request.user.username` se autenticato
(la fn DB ha `COALESCE(p_user, CURRENT_USER)` come fallback).

### Push a contratto `POST /api/v1/vendite/offerte/<id>/push-contratto/`

```json
{"pratica_id": 7, "chiudi_esistente": false}
```

Entrambi i campi opzionali (body vuoto `{}` = push senza pratica e senza
successione):

- `pratica_id` (int, anche `"7"` stringa): collega il contratto alla pratica.
- `chiudi_esistente` (booleano JSON, default `false`): se esiste un contratto
  attivo sovrapposto, `false` fa fallire il push con
  `E_CONTRATTO_OVERLAP_ESISTENTE` (409), `true` lo chiude per successione e crea
  il nuovo. Un valore non booleano (anche `"false"` stringa) → 400
  `E_VALIDATION_INPUT` col campo (2026-10-20: prima `"false"` valeva `true` e
  chiudeva il contratto esistente).

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

- Stato corrente ≠ `ACCETTATA` → 400 `E_VENDITE_VALIDATION` dal pre-check del
  service; la fn DB resta la rete (`E_OFFERTA_PUSH_STATO_NON_AMMESSO`, 409).
- Doppia invocazione su stessa offerta → 409
  `E_OFFERTA_CONTRATTO_GIA_GENERATO` (idempotenza pattern A §6.9.3); offerta
  che ha già generato un ordine → 409 `E_OFFERTA_ORDINE_GIA_GENERATO`.
- `pratica_id` non-positivo o non-int → 400 `E_VENDITE_VALIDATION`.

### Contratto sovrapposto `GET /api/v1/vendite/offerte/<id>/contratto-sovrapposto/`

Sola lettura: il contratto attivo la cui validità si sovrappone a quella che il
push genererebbe (`vendite.fn_contratto_sovrapposto` sulla coppia BA/istanza,
utility e `validita_dal/al` dell'offerta). Alimenta il dialog di successione dopo
un `E_CONTRATTO_OVERLAP_ESISTENTE`.

```json
{"data": {"contratto": {"id": 55, "numero": "CNT0000031",
  "valido_dal": "2026-01-01", "valido_al": null}}}
```

`contratto: null` se non c'è sovrapposizione. Offerta inesistente o fuori
perimetro → 404 `E_VENDITE_NOT_FOUND`.

### Lista revisioni `GET /api/v1/vendite/offerte/<id>/revisioni/`

Ritorna, **paginata**, la catena di revisioni che condivide la radice (rev.1)
con l'offerta passata (lista configurabile `vendite.offerta_revisioni`, tab del
drawer). Lettura libera in ogni stato.

| Parametro | Tipo | Descrizione |
| --- | --- | --- |
| `limit` / `offset` | int | Default 25 / 0 |
| `order_by` | string | `revisione_numero` (default) \| `codice` \| `data_emissione` \| `stato_descrizione` |
| `order_dir` | string | `asc` \| `desc`. Assente: `asc`, `desc` su `data_emissione` (le bozze, senza data, in coda) |
| `emittente_fiscale_id` | int | Emittente del documento (PK). Lo legge solo il cancello di perimetro, per chi vede più emittenti: non filtra le righe |

```json
{
  "data": {
    "count": 3, "page": 1, "page_size": 25, "total_pages": 1,
    "results": [
      {"id": 1,  "codice": "OFC-0000001", "revisione_numero": 1,
       "stato_codice_interno": "SUPERATA", "data_emissione": "2026-04-10T09:15:00Z", "...": "..."},
      {"id": 42, "codice": "OFC-0000019", "revisione_numero": 3,
       "stato_codice_interno": "EMESSA", "data_emissione": "2026-05-25T11:00:00Z", "...": "..."}
    ]
  }
}
```

Le righe sono quelle della vista lista `vw_offerte_commerciali_lista` filtrate
su `revisione_radice_id`. Offerta inesistente o fuori perimetro → 404
`E_VENDITE_NOT_FOUND`.

### Genera ordine `POST /api/v1/vendite/offerte/<id>/genera-ordine/`

Conversione upstream (§7.4 analisi-ordini-vendita, 2026-06-04): crea un **ordine
di vendita DRAFT** dall'offerta ACCETTATA. ⭐ Dal 2026-10-21 lo fa il **verbo DB**
`vendite.fn_genera_ordine_da_offerta` (I-D2 di
brief-db-offerta-emissione-ed-erogazione), gemello del push al contratto, in una
transazione: offerta bloccata `FOR UPDATE`, stato, documenti vivi, righe, testata
con la provenienza `('OFFERTA_COMMERCIALE', offerta_id)`, indirizzo di default,
righe espanse coi prezzi negoziati e componenti BoM. Ritorna l'id dell'ordine.
⛔ Fino a quel giorno l'orchestrazione era in Python
(`ordini_service.crea_ordine_da_offerta`), con gli specchi di stato e documenti
vivi, e le righe dell'ordine non le giudicava nessuno prima di scriverle.

- View `ApiOffertaGeneraOrdine` (area `vendite`) → `ordini_service.crea_ordine_da_offerta`
  → `OfferteRepository.genera_ordine` → il verbo. Il service non legge l'offerta:
  traduce i rifiuti (`_db_errors`) e legge il numero dell'ordine nato.
- **Righe**: quelle «effettive» di `vendite.fn_offerta_righe_espanse` (listino
  base + variazione globale + eccezioni, con BoM, IVA/uom risolte). **Prezzi
  negoziati preservati**: non-composito = prezzo dell'offerta; composito = prezzo
  ricalcolato dai componenti, che nascono coi prezzi dell'offerta come override
  (un componente negoziato a 0 ricade sul resolver). Prima di scrivere il verbo
  le giudica come righe d'ordine (`script.fn_check_righe_offerta_in_ordine`: solo
  beni, niente solo-componente, niente kit senza componenti), la stessa check che
  spegne «Genera ordine» nella capability.
- **Univocità 1:1** e **mutua esclusività `contratto` XOR `ordine`**: contano i
  soli documenti **vivi** (`vendite.fn_offerta_documenti_vivi`); annullato il
  documento a valle, l'offerta torna trasformabile. Rete sulla corsa: UNIQUE
  parziale `uq_ordini_v_documento_origine_offerta` (mappata allo stesso codice).
- Output `200`: `{ "ordine_id": int, "numero": str,
  "documento_origine": {"tipo": "OFFERTA_COMMERCIALE", "id": int} }`. ⚠️
  `righe_create` non c'e' piu' (dal 2026-10-21): il conteggio era del Python.
- Errori, tutti dal verbo: `E_OFFERTA_NON_TROVATA` (404); `E_ORD_ORIGINE_NON_CONVERTIBILE`
  (409) se non `ACCETTATA`; `E_ORD_OFFERTA_GIA_CONVERTITA` (409) se un ordine vivo
  e' gia' nato dall'offerta; `E_OFFERTA_CONTRATTO_GIA_GENERATO` (409) se ne e' nato
  un contratto vivo (col bersaglio); `E_DOC_RIGA_NON_AMMESSA` (400, campo
  `articolo_id`) se una riga non puo' stare in un ordine.
- FE: azione «Genera ordine» **data-driven** da `available_actions` (key
  `genera_ordine`): da `ACCETTATA` senza documenti vivi e' **proposta**, spenta
  col motivo (tooltip) se una riga non va in un ordine; sparisce a conversione
  avvenuta. Confirm prima della generazione (`requires_confirm`).
- Prerequisiti DB: brief
  [db-brief-offerta-righe-espanse.md](../../../dev/work-done/db-brief-offerta-righe-espanse.md)
  (righe espanse),
  [brief-db-univocita-offerta-ordine.md](../../../dev/work-done/brief-db-univocita-offerta-ordine.md)
  (univocità 1:1) e brief-db-offerta-emissione-ed-erogazione §I (il verbo).

### Lista righe `GET /api/v1/vendite/offerte/<id>/righe/lista/` (+ `export/`)

Le righe **operative** dell'offerta come lista configurabile
`vendite.offerta_righe` (106), paginata, con ricerca, ordinamento ed export,
sulla funzione `vendite.fn_offerta_righe_preview`: le righe della versione
operativa del listino con l'overlay delle eccezioni `OVERRIDE` / `ESCLUSIONE`,
più le `AGGIUNTA`, ciascuna coi verbi che il DB ammette (`azioni`) e il motivo
che spegne «Escludi» (`escludi_blocco_codice`). Gemella della lista righe del
contratto, dal 2026-10-05 (brief-db-righe-esclusione-solo-non-si-vende §8.1).
Contratto comune alle righe dei documenti di vendita:
[api_righe_documento.md](api_righe_documento.md). È la lettura del drawer delle
righe; il dettaglio dell'offerta porta ancora `eccezioni` (conteggio, note di riga).

### Come si eroga un articolo `GET /api/v1/vendite/offerte/<id>/righe/erogazioni/?articolo_id=<uuid>`

Le combinazioni (`tipo_erogazione`, `fonte_quantita_attesa`) che una riga con
l'articolo può avere sull'offerta, col **default in testa** (`e_default`: quello
che la riga erediterebbe senza indicarle). Lettura del form delle righe (B-R4 di
brief-db-offerta-emissione-ed-erogazione, 2026-10-07), gemella del contratto
(base `RigaErogazioniView`). ⛔ Il backend le trasporta, non le deduce: sono le
righe di `vendite.fn_documento_riga_erogazioni`, la stessa sede che il DB legge
per l'eredità e per il guard del perimetro.

```json
{ "data": { "results": [
  { "tipo_erogazione": "UNA_TANTUM", "fonte_quantita_attesa": "FISSA",
    "e_default": true, "origine": "TIPOLOGIA" },
  { "tipo_erogazione": "UNA_TANTUM", "fonte_quantita_attesa": "MANUALE",
    "e_default": false, "origine": "TIPOLOGIA" }
] } }
```

- `origine`: `TIPOLOGIA` (la tipologia di listino dell'articolo) o `NATURA` (la
  natura di vendita, se l'articolo non ha tipologia). Sul **kit** (composito) le
  sole combinazioni con fonte `FISSA` (I-D6, 2026-10-21): un kit si vende a
  quantità fissa. ⛔ `DERIVATA_COMPONENTI` e l'origine `DISTINTA` non ci sono
  piu' (I-D1, 2026-10-21): la quantità del kit la porta la fonte, i componenti
  la seguono.
- **Lista vuota** = la tipologia dell'articolo non è fra quelle della utility
  dell'offerta: lì l'articolo non si vende (`E_RIGA_TIPOLOGIA_FUORI_UTILITY` in
  scrittura).
- Prima la testata: offerta che non si vede → 404 `E_VENDITE_NOT_FOUND`, non una
  lista vuota. `articolo_id` assente o non UUID → 400 `E_VENDITE_VALIDATION`
  col campo `articolo_id`.

### Eccezioni

#### Lista `GET /api/v1/vendite/offerte/<id>/eccezioni/`

Lettura libera in ogni stato. Output: array delle eccezioni **scritte**,
ordinate per `ordine` poi `id`. Include display fields da JOIN
(`articolo_codice`, `articolo_descrizione`, `uom_codice`). ⚠️ Dal 2026-10-05 il
frontend non la legge più: il drawer delle righe legge `…/righe/lista/`.

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
| `ADESIONE`       | Articolo del listino al prezzo del listino (G-0-ter, dal 2026-10-29): sulla riga solo quantita' e periodicita' | NULL |

Vincoli (CHECK DB `chk_offerte_eccezioni_*` + UNIQUE):

- ESCLUSIONE ↔ prezzo NULL; OVERRIDE/AGGIUNTA ↔ prezzo NOT NULL
  (`chk_offerte_eccezioni_prezzo_per_tipo_eccezione`)
- **Come si eroga lo dice l'articolo** (dal 2026-10-07,
  brief-db-offerta-emissione-ed-erogazione B-R2/B-R3): `tipo_erogazione` e
  `fonte_quantita_attesa` **non indicati si ereditano** dall'articolo (trigger
  `script.trgfn_righe_default_erogazione_da_articolo`, solo in INSERT: la
  combinazione di default della sua tipologia, altrimenti della natura di
  vendita). La scelta dell'operatore vince, dentro il **perimetro**
  dell'articolo: una combinazione che non ammette →
  `E_RIGA_EROGAZIONE_FUORI_PERIMETRO` (400, campo `tipo_erogazione` o
  `fonte_quantita_attesa`); un articolo la cui tipologia la utility non prevede
  → `E_RIGA_TIPOLOGIA_FUORI_UTILITY` (400, campo `articolo_id`). Guard
  `script.trgfn_righe_guard_erogazione_perimetro`; le combinazioni ammesse le
  legge il form da `…/righe/erogazioni/`. Rete: la FK composta
  `fk_offerte_commerciali_eccezioni_erogazione_fonte` sul vocabolario
  `config.erogazioni_fonti` (ha preso il posto dei CHECK della matrice)
- `fonte_quantita_attesa` obbligatoria su OVERRIDE/AGGIUNTA, NULL sull'ESCLUSIONE
  (`chk_offerte_eccezioni_fonte_per_tipo_eccezione`, dal 2026-10-04); in create
  non si pretende: la eredita dall'articolo
- **Un'ESCLUSIONE e' vuota** (decisione di Tid, 2026-10-04,
  brief-db-righe-esclusione-solo-non-si-vende): dice solo «non si vende», quindi
  `prezzo_unitario`, `quantita`, `qta_operativa`, `uom_operativa_id`,
  `factor_to_base`, `tipo_erogazione`, `fonte_quantita_attesa`, `periodicita` e
  `generazione_canone` restano NULL (`competenza_canone` ritirata il 2026-10-29). «Escludi» manda solo
  `articolo_id` e `tipo_eccezione`. Un dato valorizzato lo rifiuta il guard
  `script.trgfn_righe_guard_esclusione_senza_dati` → `E_RIGA_ESCLUSIONE_CON_DATI`
  (400, campo in `error.fields`); CHECK `chk_offerte_eccezioni_esclusione_senza_dati` come rete.
- **Le stesse regole del contratto** (2026-10-04): righe solo in bozza
  (`trgfn_doc_righe_lock_fuori_bozza` → `E_RIGA_DOC_NON_BOZZA`), l'esclusione non si
  modifica (`E_CONTRATTO_ESCLUSIONE_NON_MODIFICABILE`), AGGIUNTA fuori listino
  (`E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO`), esclusione del componente di un bundle
  vietata, tipo immutabile (lock di colonna). I codici dicono «CONTRATTO» per storia,
  i messaggi sono neutri
- **Quantità**: la sorgente è `qta_operativa` (UoM operativa). La colonna base
  `quantita` è **calcolata** dal trigger `trgfn_qta_from_operativa`
  (`quantita = qta_operativa × factor_to_base`): nel payload e' una chiave fuori
  contratto (400, dal 2026-10-21, ritiro della DERIVATA_COMPONENTI). `qta_operativa`
  obbligatoria per `fonte = FISSA` (CHECK `qta_operativa <> 0`: zero vietato,
  negativi ammessi). Con una fonte a valle (MANUALE, LETTURE, TIMESHEET) la
  quantità arriva downstream: `quantita` la svuota il DB, una `qta_operativa`
  valorizzata è rifiutata con
  `E_RIGA_QUANTITA_CON_FONTE_A_VALLE` (400, campo `qta_operativa`). Le stesse
  regole del contratto (dal 2026-10-08, F-1 di
  brief-db-offerta-emissione-ed-erogazione: prima il solo backend del contratto
  azzerava, in silenzio)
- **`tipo_erogazione` obbligatoria sulle righe che si fatturano**: OVERRIDE e AGGIUNTA si fatturano e devono dire come si erogano
  (canone, una tantum, a ore, a consumo); l'ESCLUSIONE no. CHECK
  `chk_offerte_eccezioni_erogazione_per_tipo_eccezione` + guard
  `script.trgfn_righe_guard_erogazione_obbligatoria` →
  `E_RIGA_EROGAZIONE_OBBLIGATORIA` (400, campo `tipo_erogazione` in
  `error.fields`) in un PATCH che la toglie; in create, dal 2026-10-07, la riga
  la eredita dall'articolo. Il service non la pre-valida: parla il DB
  (2026-10-04, brief-db-erogazione-obbligatoria-righe-fatturate)
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
  → `403 E_PRICING_SCONTO_ECCESSIVO` / `E_PRICING_MAGGIORAZIONE_ECCESSIVA`
  (`retryable=true`). `richiesta_approvazione` è un booleano JSON: un altro tipo
  → 400 `E_VENDITE_VALIDATION`.
- **L3 — escalation**: con `richiesta_approvazione: true`, una violazione L2
  **non solleva**: crea una pratica `APPROVAZIONE_PREZZO` (sorgente `offerta`) e
  salva l'eccezione con `stato_approvazione_prezzo = PENDING` +
  `pratica_approvazione_prezzo_id`. L'eccezione PENDING è bloccata in modifica
  dal trigger DB `trgfn_righe_guard_pending` finché l'approver non risolve
  (vedi [API approvazioni prezzo](api_approvazioni_prezzo.md)). Approva/rifiuta
  chiedono l'azione `approva_prezzo_override`: senza → 403
  `E_PERMISSION_DENIED` dal cancello della view.

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

#### Componenti BoM dell'eccezione composita

Mirror dei componenti di riga del contratto. «Solo in bozza» lo dice il DB
(`trgfn_doc_righe_lock_fuori_bozza` → `E_RIGA_DOC_NON_BOZZA`, 409).

- `POST /<id>/eccezioni/preview-componenti/` — sola lettura, prima del save di
  un'eccezione composita: componenti BoM col prezzo suggerito dal resolver
  bundle-aware. Body `{articolo_id, quantita, uom_operativa_id?}`; risposta
  `{"data": [ ... ]}`. Offerta inesistente → 404 `E_VENDITE_NOT_FOUND`.
- `GET /<id>/eccezioni/<eid>/componenti/?solo_attivi=true|false` — componenti
  persistiti (default solo attivi; `false` include gli opzionali disattivati).
  Eccezione non dell'offerta dell'URL → 404 `E_VENDITE_NOT_FOUND`.
- `PATCH /<id>/eccezioni/<eid>/componenti/<cid>/` — whitelist `prezzo_unitario`,
  `attivo`, `meta` (chiave fuori → 400 `E_VENDITE_VALIDATION`; `{}` → 400).
  `prezzo_unitario` non nullo richiede `prezzo_override_manuale` (403
  `E_PRICING_OVERRIDE_NON_AUTORIZZATO`); `origine_prezzo` la calcola il server
  (`MANUALE`, o `null` se il prezzo si azzera). Risposta
  `{"status": "ok", "componente_id": <cid>}`.
- `DELETE /<id>/eccezioni/<eid>/componenti/<cid>/` — soft delete
  (`attivo = false`); risposta `{"status": "ok", "componente_id", "deleted"}`.

Su PATCH/DELETE `<eid>` deve essere dell'offerta e `<cid>` dell'eccezione,
altrimenti 404 `E_VENDITE_NOT_FOUND`.

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

### Indirizzi documento `GET/POST /<id>/indirizzi/` + `DELETE /<id>/indirizzi/<iid>/`

BB condiviso sui 5 domini vendite (ambito OFFERTE (FATT, CON, FORNITURA, RES); editabile solo BOZZA):
contratto completo in [api_indirizzi_documento.md](api_indirizzi_documento.md).


## Output

Tutte le risposte usano l'envelope `success_response`:

```json
{"data": { ... }, "meta": {"timestamp": "2026-05-25T10:00:00Z"}}
```

Per il dettaglio vedi §Detail; le liste paginate (offerte, revisioni) hanno
`{"data": {"count", "page", "page_size", "total_pages", "results": [...]}}`
(BB `paginated_envelope`).

## Regole

1. **Codice offerta** generato dal trigger DB
   `trgfn_offerte_commerciali_gen_codice` (BEFORE INSERT) via
   `script.fn_generate_codice('offerta_commerciale')`. Rifiutato in
   payload come `unknown_key`.
2. **Stato iniziale BOZZA**; transizioni via endpoint dedicato.
3. **Testata**: quali colonne si cambiano fuori bozza lo dice il lock di testata del DB (`trgfn_doc_testata_lock_fuori_bozza`, dal 2026-10-10, [brief-db-testata-dopo-emissione](/dev/work-done/brief-db-testata-dopo-emissione)); il 409 del lock (`E_DOC_*`) passa com'e' (in EMESSA e ACCETTATA le note). **Eccezioni e
   utility** solo in BOZZA: per la utility lo dice il lock «solo in bozza» dei
   satelliti a DB (dal 2026-10-11, `E_DOC_DATI_COLLEGATI_NON_BOZZA`, 409, che passa
   com'e'), specchiato dalla capability `can_edit_utility`. Il listino sotto le
   righe lo giudica il DB come sul contratto (`E_DOC_LISTINO_CAMBIO_CON_RIGHE`,
   `E_DOC_LISTINO_RIMOZIONE_CON_ECCEZIONI`, 422, campo `listino_id`).
4. **Annullamento da BOZZA o da ACCETTATA (senza documenti vivi a valle),
   rifiuto solo da EMESSA**: lo stato di partenza dell'annullo lo dice il DB.
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
- **Passaggi** `GET /api/v1/vendite/offerte/<id>/passaggi/` — genealogia del
  documento: pratica + frontiera + catena transiti in entrambe le direzioni.
  Contratto completo nel manuale del BB condiviso:
  [api_lineage_passaggi.md](api_lineage_passaggi.md).

## Codici errore

| Codice                                              | HTTP                | Origine                                                                                                | Trigger DB                                          |
| --------------------------------------------------- | ------------------- | ------------------------------------------------------------------------------------------------------ | --------------------------------------------------- |
| `E_VENDITE_VALIDATION`                              | 400                 | Service: struttura payload, chiave fuori contratto (anche `quantita` sulle eccezioni, dal 2026-10-21), payload vuoto in PATCH, motivazione non stringa, `legami_confermati` non intero, esito non valido, filtro di stato fuori vocabolario, stato errato per il delete (pre-check: l'unico rimasto dal 2026-10-26) | —                                                   |
| `E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA`                | 400                 | DB P0001 (2026-10-26, O-3) — rifiuto o annullo senza motivazione (vuota = assente): lo chiede la riga del passaggio (`requires_motivazione`). Il DB nomina la colonna `motivazione_rifiuto`, al client esce il campo della richiesta `motivazione` (`OfferteService._db_errors`); valori: codice dell'offerta, stato chiesto | `vendite.fn_cambia_stato_offerta` |
| `E_PERMESSO_NEGATO`                                 | 403                 | «Emetti» o l'annullo dell'accettata senza `emetti_offerta` (dalla riga del passaggio: view, poi verbo) | `script.fn_guard_passaggio` |
| `E_DOC_GIA_NELLO_STATO`                             | 409                 | DB P0001 — il passaggio allo stato che l'offerta ha gia' (un secondo «Emetti») | `vendite.fn_cambia_stato_offerta` |
| `E_DOC_ANNULLO_CON_LEGAMI`                          | 409 (`confirm_and_retry`) | DB P0001 (2026-10-26, O-4) — annullo di una revisione che fa tornare emessa la precedente, senza conferma o con una conferma che non corrisponde | `vendite.trgfn_doc_guard_annullo_con_legami` / `vendite.fn_documento_ritira_legami` |
| `E_VALIDATION_INPUT`                                | 400                 | `chiudi_esistente` del push non booleano JSON                                                           | —                                                   |
| `E_PRICING_OVERRIDE_NON_AUTORIZZATO`                | 403                 | Prezzo manuale (eccezione o componente) senza `prezzo_override_manuale`                                  | —                                                   |
| `E_PRICING_SCONTO_ECCESSIVO` / `E_PRICING_MAGGIORAZIONE_ECCESSIVA` | 403  | Gate L2 oltre soglia senza `richiesta_approvazione` (`retryable=true`)                                  | —                                                   |
| `E_VENDITE_NOT_FOUND`                               | 404                 | Service: offerta/eccezione/utility non trovata; ownership URL                                          | —                                                   |
| `E_VENDITE_DUPLICATO`                               | 409                 | UNIQUE `uq_offerte_commerciali_codice` / `uq_offerte_commerciali_uid` / `uq_offerte_commerciali_utilities_offerta_id` / `uq_offerte_eccezioni_one_eccezione_per_articolo` / `uq_offerte_eccezioni_one_aggiunta_per_articolo` | —                                                   |
| `E_VENDITE_FK`                                      | 400                 | FK su BA/emittente/istanza/utility/listino/articolo/uom/tipo/classe utenza                              | —                                                   |
| `E_RIGA_EROGAZIONE_OBBLIGATORIA`                    | 400                 | DB P0001 (2026-10-04) — PATCH che toglie `tipo_erogazione` a un'eccezione OVERRIDE/AGGIUNTA (in create, dal 2026-10-07, la riga la eredita). Campo `tipo_erogazione` in `error.fields`. Stesso codice sulle righe di contratto | `script.trgfn_righe_guard_erogazione_obbligatoria` |
| `E_RIGA_EROGAZIONE_FUORI_PERIMETRO`                 | 400                 | DB P0001 (2026-10-07) — combinazione `(tipo_erogazione, fonte_quantita_attesa)` che l'articolo non ammette. Campo `tipo_erogazione` o `fonte_quantita_attesa` in `error.fields`. Stesso codice sul contratto | `script.trgfn_righe_guard_erogazione_perimetro` |
| `E_RIGA_TIPOLOGIA_FUORI_UTILITY`                    | 400                 | DB P0001 (2026-10-07) — articolo con una tipologia di listino che la utility dell'offerta non prevede. Campo `articolo_id`. Stesso codice sul contratto | `script.trgfn_righe_guard_erogazione_perimetro` |
| `E_RIGA_ESCLUSIONE_CON_DATI`                        | 400                 | DB P0001 (2026-10-04) — INSERT di un'ESCLUSIONE con un dato di fatturazione. Campo in `error.fields`. Stesso codice sul contratto | `script.trgfn_righe_guard_esclusione_senza_dati` |
| `E_RIGA_QUANTITA_CON_FONTE_A_VALLE`                 | 400                 | DB P0001 (2026-10-07, rivisto 2026-10-08) — `qta_operativa` valorizzata con una fonte a valle. Campo `qta_operativa`. Stesso codice sul contratto | `script.trgfn_righe_guard_quantita_per_fonte` |
| `E_DOC_LISTINO_UTILITY_DIVERSA`                     | 400                 | DB P0001 (2026-10-08) — il listino è di un'altra utility. Campo `listino_id`. Stesso codice sul contratto | `script.trgfn_doc_guard_listino_documento` |
| `E_DOC_LISTINO_EMITTENTE_DIVERSO`                   | 400                 | DB P0001 (2026-10-08) — il listino è di un'altra azienda emittente. Campo `listino_id`. Stesso codice sul contratto | `script.trgfn_doc_guard_listino_documento` |
| `E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO`        | 409                 | DB P0001 — `BOZZA -> EMESSA` su un listino che non ha una versione in vigore oggi (dal 2026-10-07: prima «versione NULL», che il guard ora congela da sé) | `trgfn_offerte_commerciali_guard_transizione`        |
| `E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA`   | 409                 | DB P0001 — `BOZZA -> EMESSA` con una versione già fissata che non è più `ATTIVA`                         | `trgfn_offerte_commerciali_guard_transizione`        |
| `E_OFFERTA_TRANSIZIONE_NON_AMMESSA`                 | 409                 | DB P0001 — transizione non presente in `config.stati_doc_offerte_transizioni` (es. EMESSA -> ANNULLATA, EMESSA -> BOZZA, qualsiasi uscita da stato terminale) | `trgfn_offerte_commerciali_guard_transizione`        |
| `E_OFFERTA_REVISIONE_STATO_NON_AMMESSO`             | 409                 | DB P0001 — `crea_revisione` da stato != EMESSA (dal 2026-10-26 senza pre-check del service) | `fn_crea_revisione_offerta`                          |
| `E_OFFERTA_PUSH_STATO_NON_AMMESSO`                  | 409                 | DB P0001 — `push_a_contratto` da stato ≠ ACCETTATA (dal 2026-10-26 senza pre-check del service) | `fn_push_offerta_a_contratto`                        |
| `E_OFFERTA_CONTRATTO_GIA_GENERATO`                  | 409                 | Conflitto "già materializzato" (registrato in `error_policies`): push idempotente (pattern A, UNIQUE `uq_contratti_offerta_id`) **e** mutua esclusività XOR — blocca la generazione ordine se l'offerta ha già un contratto vivo | `fn_push_offerta_a_contratto` / `fn_genera_ordine_da_offerta` |
| `E_OFFERTA_NON_TROVATA`                             | 404                 | DB P0001 — offerta inesistente o fuori perimetro per il push, la generazione dell'ordine o un verbo di stato (il service legge prima la testata: di norma esce il suo 404 `E_VENDITE_NOT_FOUND`) | `fn_push_offerta_a_contratto` / `fn_genera_ordine_da_offerta` / `fn_cambia_stato_offerta` / `fn_annulla_offerta` |
| `E_ORD_ORIGINE_NON_CONVERTIBILE`                    | 409                 | DB P0001 — genera ordine da un'offerta non `ACCETTATA` | `fn_genera_ordine_da_offerta` |
| `E_ORD_OFFERTA_GIA_CONVERTITA`                      | 409                 | DB P0001 — genera ordine quando un ordine vivo è già nato dall'offerta (rete: UNIQUE `uq_ordini_v_documento_origine_offerta`) | `fn_genera_ordine_da_offerta` |
| `E_DOC_RIGA_NON_AMMESSA`                            | 400                 | DB P0001 (2026-10-21) — una riga che la regola intera non ammette più: all'emissione (articolo, erogazione, fonte) o nella generazione dell'ordine (riga d'ordine). Campo `articolo_id`; valori: documento, articolo; `motivo_riga` nel contesto | `trgfn_offerte_commerciali_guard_transizione` / `fn_genera_ordine_da_offerta` |
| `E_OFFERTA_ANNULLO_CON_DOCUMENTI_VIVI`              | 409                 | DB P0001 (2026-10-21) — annullo da `ACCETTATA` con un contratto o un ordine vivo nato dall'offerta; bersaglio nel contesto | `trgfn_offerte_commerciali_guard_transizione` |
| `E_OFFERTA_ORDINE_GIA_GENERATO`                     | 409                 | Mutua esclusività XOR (registrato in `error_policies`): blocca il push a contratto se l'offerta ha già generato un ordine | `fn_push_offerta_a_contratto` (guard DB)             |
| `E_CONFIG_MANCANTE`                                 | 500                 | DB P0001 — `OFFERTA_COMMERCIALE` o `CONTRATTO` non trovati in `config.sorgenti`; stato `DRAFT` non in `config.stati_doc_contratti`. Errore di configurazione sistema | `fn_push_offerta_a_contratto`                        |
| `E_CONTRATTO_OVERLAP_ESISTENTE`                     | 409                 | DB P0001 — push con contratto attivo sovrapposto e `chiudi_esistente=false`. Il FE legge il conflitto via `contratto-sovrapposto/` e richiama con `chiudi_esistente=true` | `fn_push_offerta_a_contratto` / `fn_contratto_sovrapposto` |
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
  (`target_tipo = 'OFFERTA_COMMERCIALE'`, fino al 2026-10-25 `'OFFERTA'`), cablata via building block
  `apps.core.db.PartitionedNoteRepository` (cablaggio differito, vedi piano BE/FE)

**Funzioni**:

- `script.fn_generate_codice('offerta_commerciale')` — generazione codice
  `OFC-*` (step 5 atterrato 2026-05-25, invocata dal trigger BEFORE INSERT).
- `vendite.fn_cambia_stato_offerta(p_offerta_id, p_stato, p_motivazione)` — il
  verbo di ogni cambio di stato manuale (dal 2026-10-26): «Emetti» e l'esito.
  SECURITY DEFINER col predicato del perimetro; azione dalla riga del passaggio,
  motivazione dove la riga la chiede, scrittura attraverso la porta. Ritorna
  `offerta_id, stato_precedente, stato_nuovo`. Repository: `cambia_stato`.
- `vendite.fn_annulla_offerta(p_offerta_id, p_motivazione, p_legami_confermati)` —
  il verbo d'annullo (dal 2026-10-26, O-4): prima cio' che vieta, poi la
  conferma dei legami (la revisione precedente), poi lo stato dal verbo di
  stato. Ritorna i legami confermati. Repository: `annulla`.
- `vendite.fn_documento_legami('OFFERTA_COMMERCIALE', id)` — i legami per la
  finestra di conferma (`GET /<id>/legami/`).
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

- Modello: [analisi-offerta-commerciale](/dev/work-done/analisi-offerta-commerciale)
- Brief DB: [analisi-offerta-commerciale-db](/dev/work-done/analisi-offerta-commerciale-db)
- Piano BE+FE: [analisi-offerta-commerciale-be-fe](/dev/work-done/analisi-offerta-commerciale-be-fe)
- Manuale service: [offerte_service](/backend/vendite/manual/offerte_service)
- API contratto (specchio strutturale): [api_contratti](/backend/vendite/manual/api_contratti)
