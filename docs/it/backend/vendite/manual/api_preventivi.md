# API Preventivi vendita (Django)

## Scopo

Esporre via HTTP la gestione completa dei preventivi di vendita: CRUD testata, righe, indirizzi, cambio stato, revisioni, integrazione con commesse/fatturazione e pratiche.

## Contesto

I preventivi vendita sono il punto d'ingresso del ciclo commerciale. Dopo accettazione, alimentano la pipeline commesse/attivita_fatturabili/fatturazione. Possono anche generare pratiche operative (installazione, sopralluogo, ecc.) via tabella ponte `pratiche.pratiche_sorgenti`.

Le tabelle DB esistono gia' (`vendite.preventivi`, `preventivi_righe`, `preventivi_indirizzi`, `note_preventivo`, `config.stati_doc_preventivi`). Alcune funzioni DB sono da creare (cambio stato, revisione, ricalcolo totali).

---

## Endpoint

### 1. Lista preventivi

> **DEF-8 (2026-06-03)**: la lista legge dalla vista canonica
> `vendite.vw_preventivi_lista` (`security_invoker=on`, sorgente `vw_preventivi`
> per `is_attiva` derivata) — lista configurabile `vendite.preventivi`, ritiro
> dinamico colonne lato FE. I campi display usano i **nomi canonici della
> vista**: cliente = `ragione_sociale_completa`, id. fiscale =
> `id_fiscale_univoco_cf_piva`, codice account = `ba_codice`, stato =
> `stato_descrizione` + `stato_codice_interno`. Il **dettaglio** (`GET .../<id>/`)
> conserva i nomi storici (`cliente_denominazione`): è una fonte diversa (JOIN
> diretto, non la vista). Anche `list_revisioni` legge dalla vista canonica.

- Metodo: `GET`
- Path: `/api/v1/vendite/preventivi/`
- Auth: JWT, `area_funzionale = "vendite"`, `is_search_endpoint = True`
- Query param (tutti opzionali):
  - `stato` (string) — `codice_interno` stato (es. `DRAFT`, `EMESSO`, `ACCETTATO`); filtro su `stato_codice_interno`. Fuori vocabolario `config.stati_doc_preventivi` → 400 `E_PREV_VALIDAZIONE` col campo `stato_codice_interno` (2026-10-20: prima lista vuota con 200)
  - `billing_account_id` (int) — filtro per BA/cliente
  - `utility_id` (int) — filtro per utility
  - `data_da` (date ISO) — data minima (su `data` preventivo). **Default: 1 gennaio anno-1** (regola standard liste con date, lato frontend)
  - `data_al` (date ISO) — data massima
  - `search` (string, min 3 char) — ILIKE su `numero`, `ragione_sociale_completa`, `ba_codice` e `id_fiscale_univoco_cf_piva`
  - `solo_ultima_revisione` (bool, default `true`) — solo l'ultima revisione per numero; `false` = storico revisioni completo (toggle "Mostra storico")
  - `limit` (int, default 25, max 200) / `offset` (int, default 0) — paginazione
  - `order_by` (string, default `data`) — `campo_sorgente` colonna catalogo `vendite.preventivi`: `numero` `data` `ragione_sociale_completa` `ba_codice` `id_fiscale_univoco_cf_piva` `utility_codice` `utility_descrizione` `istanza_utility_codice` `totale_documento` `totale_imponibile` `totale_iva` `validita_al` `validita_dal` `stato_descrizione` `valuta_codice` `competenza_mese` `data_insert` `pratica_numero` `fase`. `rev` **non ordinabile**
  - `order_dir` (string, default `desc`) — `asc` o `desc`; assente vale `desc` («dal più recente»)
- Output `200`:
```json
{
  "data": {
    "count": 42,
    "page": 1,
    "page_size": 25,
    "total_pages": 1,
    "results": [
      {
        "id": 1,
        "uid": "01970...",
        "numero": "P-0001",
        "rev": 0,
        "is_attiva": true,
        "data": "2026-04-03",
        "stato_codice_interno": "DRAFT",
        "stato_descrizione": "Bozza",
        "ragione_sociale_completa": "Azienda Esempio S.r.l.",
        "id_fiscale_univoco_cf_piva": "01234567890",
        "billing_account_id": 10,
        "ba_codice": "BA-0010",
        "utility_id": 1,
        "utility_codice": "EE",
        "utility_descrizione": "Energia elettrica",
        "istanza_utility_codice": "POD-0001",
        "totale_imponibile": "1000.00",
        "totale_iva": "220.00",
        "totale_documento": "1220.00",
        "validita_dal": "2026-04-01",
        "validita_al": "2026-06-30",
        "competenza_mese": "2026-04-01",
        "valuta_codice": "EUR",
        "emittente_fiscale_codice": "EF-01",
        "data_insert": "2026-04-03T10:00:00+02:00"
      }
    ]
  },
  "meta": { "request_id": "..." }
}
```
- Regole: scope emittente DB-first (RLS `security_invoker` sulla vista) + filtro
  applicativo `fn_get_emittenti_scope_pk_ids` (defense-in-depth); filtro data
  consigliato (default anno-1 nel frontend).

---

### 1b. Export lista preventivi `GET /api/v1/vendite/preventivi/export/`

Genera un file **CSV** o **Excel** con i preventivi filtrati (stessi parametri
della lista). Renderer generico DEF-1 (`ListaExportService`); le colonne sono
coerenti con la DataTable a video (config runtime: preferenza + preset +
permessi — colonne nascoste escluse, ordine utente rispettato).

| Parametro | Tipo | Descrizione |
|---|---|---|
| `formato` | string | `csv` (default) o `xlsx`. **NB**: parametro `formato` (italiano), NON `format` (magic param DRF) |
| `search`, `stato`, `billing_account_id`, `utility_id`, `data_da`, `data_al`, `solo_ultima_revisione`, `order_by`, `order_dir` | — | stessi della lista |

- Hard cap **10.000 righe**: oltre → `422 E_UI_EXPORT_LIMIT_EXCEEDED`.
- `formato` non valido → `400 E_UI_EXPORT_FORMAT_INVALID`.
- Risposta binaria: `Content-Disposition: attachment; filename="preventivi.csv|xlsx"`; i filtri attivi sono inclusi come metadato nel file.
- Coda condivisa: `apps.ui.api.export_helpers.{parse_export_format,build_export_response}` (building block DEF-1, gemello contratti/clienti/soggetti/fornitori).

---

### 2. Crea preventivo

- Metodo: `POST`
- Path: `/api/v1/vendite/preventivi/`
- Body JSON:
  - `utility_id` (int, **obbligatorio**)
  - `billing_account_id` (int, opzionale)
  - `istanza_utility_id` (int, opzionale)
  - `valuta_id` (int, opzionale)
  - `termine_pagamento_id` (int, opzionale)
  - `validita_dal` (date, opzionale)
  - `validita_al` (date, opzionale)
  - `competenza_mese` (date, opzionale — primo del mese)
  - `emittente_fiscale_id` (int, opzionale; fermo dopo la creazione)
  - `fatturazione_immediata` (bool, default false)
  - `meta` (object, opzionale)
- Una chiave fuori elenco (es. `iva_id`, `codice`) → 400 `E_PREV_VALIDAZIONE` (2026-10-20: prima scartata in silenzio)
- Output `200`: `{ "data": { "id": 1, "uid": "...", "numero": "P-0001" } }`
- Regole: crea sempre in stato BOZZA, numero generato da trigger `trgfn_preventivi_gen_codice`
- Errori: `E_PREV_VALIDAZIONE` (400), `E_CONFIG_MANCANTE` (500 se BOZZA non configurato)

---

### 3. Dettaglio preventivo

- Metodo: `GET`
- Path: `/api/v1/vendite/preventivi/{id}/`
- Output `200`: testata completa con decodifiche (stato, cliente, utility, valuta, termini) + `indirizzi[]` + `righe_count` (summary leggero) + **capabilities** (Fase 1 refactor frontend vendite)
- **Fase 3.F6 refactor frontend vendite** — il detail NON include piu' `righe[]` (decisione C2: detail = testata + summary, righe via endpoint autonomo `/righe/`). Il FE chiama `GET /righe/` separatamente. Vantaggi: payload detail piu' leggero su lista refresh, mai mismatch con totali ricalcolati dai trigger DB. `righe_count` resta disponibile come badge UX.
- Errori: `E_PREV_NOT_FOUND` (404)

**Capabilities** (da `script.fn_available_actions_preventivo`, nella chiave `capabilities` del detail, non fuse nella testata — dal 2026-09-23, [api.md §«Il blob sta SOTTO `capabilities`»](../../../dev/api.md)):

| Campo | Tipo | Significato |
| --- | --- | --- |
| `available_actions[]` | array | Azioni cambio stato disponibili: `{key, target_state, label_key (i18n), requires_confirm}` — Icona e colore non viaggiano: li sceglie il frontend dal `key` (`frontend/src/core/aspettoAzioni.js`; l'icona dal 2026-09-27, il colore dal 2026-09-28). Non include transizioni automatiche (job notturno SCADUTO) |
| `can_edit_testata` | bool | `true` se nello stato almeno una colonna della testata si cambia, letto dal montaggio del lock di testata (dal 2026-10-10: DRAFT, ed EMESSO/ACCETTATO per note e competenza). Quali no lo dice `non_editable_fields`; `PATCH /<id>/` non ha piu' un guard di stato, decide il DB |
| `can_edit_righe` | bool | `true` solo in DRAFT |
| `can_create_revisione` | bool | `true` per ACCETTATO (revisione = nuova rev del preventivo) |
| `can_push_commessa` | bool | `true` per ACCETTATO (push verso commesse) |
| `can_push_commessa_reason` | string\|null | Codice tecnico ostativo (es. `PREVENTIVO_NON_ACCETTATO`) |
| `can_push_commessa_reason_key` | string\|null | Chiave i18n pronta da tradurre, es. `preventivi.push_commessa_reason.non_accettato` |
| `non_editable_fields[]` | string[] | Whitelist campi immutabili nello stato corrente. **`utility_id` sempre incluso** (regola di dominio: utility immutabile post-create) |

Il frontend (`PreventiviDrawer.vue`) consuma questi metadata direttamente: niente `if (stato === 'DRAFT')` cablato.

⭐ **Il blob arriva intatto** (dal 2026-09-24). Un prezzo non autorizzato —
riga o componente BoM attivo `PENDING` o `REJECTED` — spegne «Emetti» e
«Accetta» **a DB**: l'azione ha `enabled: false` e i motivi in `reasons[]`
(`PREZZO_PENDENTE` / `PREZZO_RIFIUTATO`, `dettaglio.n_prezzi`), dallo stesso
building block con cui il guard solleva (`script.fn_check_prezzi_autorizzati`).
«Annulla» resta acceso e testata e righe restano modificabili in BOZZA: il
blocco sta sulla sola riga in attesa, dal suo guard per riga. Il drawer mostra
i motivi nel tooltip del pulsante spento, col conteggio (`valori`). ⛔ Fino a quella data il service riscriveva
`available_actions`/`can_edit_*` in Python e aggiungeva sulla testata quattro
riepiloghi (`frozen_for_*`, `*_pricing_count`) che contavano le sole righe:
tutti ritirati
([brief-db-preventivi-congelamento-pricing §6.1](../../../dev/work-done/brief-db-preventivi-congelamento-pricing.md)).

---

### 4. Aggiorna preventivo

- Metodo: `PATCH`
- Path: `/api/v1/vendite/preventivi/{id}/`
- Body JSON: campi modificabili — **`billing_account_id`**, `istanza_utility_id`, `valuta_id`, `termine_pagamento_id`, `validita_dal`, `validita_al`, `competenza_mese`, `fatturazione_immediata`, `meta`. Passare `null` per azzerare campi nullable. **`utility_id` non e' aggiornabile** (regola di dominio, vedi `non_editable_fields` nel detail).
- Regole: **nessun guard di stato nel service**: quali colonne si cambiano in quale stato lo decide il lock di testata del DB (`trgfn_doc_testata_lock_fuori_bozza`: in bozza tutto, in EMESSO/ACCETTATO note e competenza), il cui 409 `E_DOC_*` passa com'è. `utility_id` ed `emittente_fiscale_id` → 400 `E_PREV_VALIDAZIONE` sul campo (colonne ferme); ogni altra chiave ignota → 400. BA e istanza si cambiano per coppia
- Output `200`: `{ "data": { "status": "ok", "preventivo_id": 1 } }`
- Errori: `E_PREV_NOT_FOUND` (404), `E_PREV_VALIDAZIONE` (400), `E_DOC_*` (409, lock di testata)

---

### 4b. Elimina bozza orfana

- Metodo: `DELETE`
- Path: `/api/v1/vendite/preventivi/{id}/`
- Scopo: pulizia della bozza abbandonata dal drawer (pattern «abbandono bozza»). Un preventivo reale non si cancella, si annulla (`POST /{id}/stato/` con `ANNULLATO`)
- Regole: stato BOZZA, zero righe, zero pratiche collegate; altrimenti 409 `E_PREV_STATO_NON_MODIFICABILE` (messaggio dedicato per ciascun caso)
- Output `200`: `{ "data": { "status": "ok" | "noop", "preventivo_id": 1 } }`
- Errori: `E_PREV_NOT_FOUND` (404), `E_PREV_STATO_NON_MODIFICABILE` (409)

---

### 5. Cambio stato

- Metodo: `POST`
- Path: `/api/v1/vendite/preventivi/{id}/stato/`
- Auth: JWT, `model_permission = ("vendite", "preventivo")`, `post_passaggio` (BB `PassaggioDocumento`, modello del documento): l'azione la dice la **riga del passaggio** (stato corrente → `nuovo_stato`), la stessa che legge il verbo. Oggi l'annullo di un preventivo emesso o accettato chiede `emetti_preventivo`; gli altri passaggi il solo livello sul preventivo. Senza l'azione: 403 prima della transazione
- Body JSON: `{ "nuovo_stato": "ACCETTATO", "fatturazione_immediata": false, "competenza_mese": "2026-11-01", "legami_confermati": 2 }`
- Regole: delega al verbo `vendite.fn_cambia_stato_preventivo(id, stato)`; matrice, righe, prezzi e annullabilità li giudicano i guard della tabella
- **Verso ACCETTATO** (da EMESSO, o su un ACCETTATO per correggere la modalità): `fatturazione_immediata` (booleano JSON) è **obbligatorio**, altrimenti 400 `E_PREV_VALIDAZIONE`; con `false` serve anche `competenza_mese` (data ISO, primo del mese), altrimenti 400; con `true` la competenza è forzata al mese corrente. I due campi si scrivono sulla testata nella stessa transazione del cambio stato. Su un preventivo **già ACCETTATO** si aggiornano solo i due campi: lo stato non cambia e il verbo non si chiama (risposta con `stato_precedente` = `stato_nuovo` = `ACCETTATO`). Sulle altre transizioni sono ignorati
- Transizioni: EMESSO→ACCETTATO/RIFIUTATO/SCADUTO/ANNULLATO, BOZZA→ANNULLATO
- **Lo stato di emissione non si raggiunge da questo endpoint** (refactor 2026-05-28, M-2 del modello del documento): 400 `E_PREV_VALIDAZIONE` col campo `nuovo_stato`; si emette dall'endpoint dedicato `POST /<id>/emetti/` (§5b). Quale stato sia l'emissione lo dice il vocabolario (colonna `emissione` di `config.stati_doc_preventivi`), non il backend. Motivo: l'emissione deve orchestrare atomicamente cambio stato + generazione documento + allegati per garantire l'invariante "stato EMESSO ⇒ esiste un documento PDF persistito".
- **Prezzi non autorizzati verso ACCETTATO**: la Regola 3 di `vendite.trgfn_preventivi_guard_transizione` rifiuta la transizione se una riga o un componente BoM attivo ha il prezzo `PENDING` o `REJECTED` (building block `script.fn_check_prezzi_autorizzati`, vedi `api_approvazioni_prezzo.md`): si attende l'esito, si corregge il prezzo o si toglie la riga. Annulla resta sempre ammesso.
- **Verso ANNULLATO** passa sempre dal verbo `vendite.fn_annulla_preventivo`: con righe di commessa da emettere risponde `E_DOC_ANNULLO_CON_LEGAMI` (409, `confirm_and_retry`) finché il body non dichiara `legami_confermati` (intero, letto da `GET /{id}/legami/`). Risposta con la stessa forma di `fn_cambia_stato_preventivo` (`preventivo_id`, `stato_precedente`, `stato_nuovo`).
- Errori: `E_PREV_STATO_TRANSIZIONE` (409), `E_PREV_NESSUNA_RIGA` (400), `E_DOC_PREZZO_PENDENTE` (409), `E_DOC_PREZZO_RIFIUTATO` (409), `E_PREV_VALIDAZIONE` (400: lo stato di emissione, modalità di fatturazione mancante verso ACCETTATO), `E_DOC_ANNULLO_CON_LEGAMI` (409, conferma), `E_DOC_PASSAGGIO_DI_PROCESSO` (un passaggio che non si chiede a mano: ACCETTATO → EVASO, EMESSO → SCADUTO), `E_PREV_NOT_FOUND` (404, anche un preventivo fuori perimetro), 403 senza l'azione del passaggio

### 5-bis. Cambio stato dalla pratica `POST /api/v1/vendite/preventivi/da-pratica/{pratica_id}/stato/`

«Accetta/Rifiuta» dentro la pratica: cambia lo stato del preventivo **ROOT** della
pratica. Stesso permesso (la riga del passaggio, sul preventivo ROOT: `post_passaggio`
con `risolvi_documento`), stesso corpo (`nuovo_stato`, `fatturazione_immediata`,
`competenza_mese`) e stesse regole e risposta di §5; il preventivo lo risolve il
backend dal `pratica_id`. Pratica
senza preventivo ROOT → 422 `E_VENDITA_PREVENTIVO_NON_COLLEGATO`. Il milestone
della pratica avanza da sé (trigger DB `fn_reconcile_sorgente`).

### 5a. Legami `GET /<id>/legami/` (factory `build_legami_view`, BB
`_annullo_con_legami.legami_del_documento`): `{documento, id, legami, righe}`,
una riga per legame di `vendite.fn_documento_legami` con `origine` (codice di `config.sorgenti`), `natura`
(CONSUMO/PROVENIENZA), `origine_id` e il nome del documento dall'altra parte
dal lineage (`origine_tipo_codice_interno`, `origine_codice`). `legami` e' il
numero da dichiarare. Alimenta la finestra di conferma dell'annullo.

---

### 5b. Emissione BOZZA→EMESSO `POST /api/v1/vendite/preventivi/{id}/emetti/`

Nuovo endpoint multipart 2026-05-28. Mirror del flusso offerta `POST /api/v1/vendite/offerte/<id>/emetti/`. Sostituisce la transizione `BOZZA→EMESSO` precedentemente esposta via `/stato/`.

- Metodo: `POST`
- Path: `/api/v1/vendite/preventivi/{id}/emetti/`
- Content-Type: `multipart/form-data`
- Parser: `MultiPartParser`, `FormParser` (override del default DRF JSON-only)
- Auth: JWT, `area_funzionale = "vendite"`, livello sul preventivo, e l'azione dalla riga del passaggio DRAFT → EMESSO (`emetti_passaggio` della factory; oggi `emetti_preventivo`): 403 prima della transazione a chi non ce l'ha. Fino al 2026-10-25 `cambia_stato_preventivi`, spenta
- Body multipart:
  - `template_documento_id` (int, opzionale) — id template documentale da usare. Se omesso, il motore documentale seleziona il template `is_default=true` per `(sorgente=PREVENTIVO, emittente_fiscale_id, tipo_documento_output_id)`
  - `tipo_documento_output_id` (int, opzionale) — id tipo output (PDF, ecc.). Se omesso, default del template
  - `allegati` (file ripetuto, opzionale) — file secondari da persistere assieme al PDF principale. MIME/size validati dal `DocumentGenerationService`
- Output `200`:

```json
{
  "data": {
    "preventivo": { "...": "testata aggiornata dopo cambio stato" },
    "documento": {
      "documento_generato_id": 42,
      "uid": "...",
      "progressivo_sorgente": 1,
      "nome_file": "PREVENTIVO_P-0001_v1.pdf",
      "size_bytes": 23456,
      "allegati_count": 2
    }
  },
  "meta": { "request_id": "..." }
}
```

- Semantica transazionale: la view apre `transaction.atomic()` che racchiude (in ordine): `preventivi_service.emetti(preventivo_id)` (cambio stato + valorizza `data_emissione = now()`) → `_resolve_contesto_preventivo` (entity + sorgente_tipo) → `DocumentGenerationService.genera_documento(allegati=...)` (render + persist su `documenti.documenti_generati` + evento `GENERATO`). Se il render fallisce o uno qualsiasi degli allegati viola MIME/size, l'eccezione propaga e l'`atomic` esterno fa rollback completo → il preventivo resta BOZZA, nessun record orfano. **Invariante di dominio**: `stato='EMESSO'` ⇒ esiste almeno un record `documenti_generati` con `sorgente_tipo=PREVENTIVO, sorgente_id=preventivo.id`.
- Regole pre-emissione (validate dal service + trigger DB):
  - Preventivo in stato BOZZA con almeno una riga attiva
  - Nessun prezzo non autorizzato (`PENDING` o `REJECTED`, righe e componenti BoM attivi): motivo 2 di `script.fn_check_preventivo_emettibile`, vedi §5
  - Template documento applicabile (`PUBBLICATA` valido alla data)
- Errori:
  - `E_PREV_NOT_FOUND` (404) — preventivo inesistente
  - `E_PREV_STATO_TRANSIZIONE` (409) — preventivo non in BOZZA
  - `E_PREV_NESSUNA_RIGA` (400) — nessuna riga attiva
  - `E_DOC_PREZZO_PENDENTE` / `E_DOC_PREZZO_RIFIUTATO` (409) — prezzi in attesa di approvazione o rifiutati
  - `E_DOCUMENTI_VALIDATION` (400) — emittente non risolto / sorgente PREVENTIVO non attiva / template non trovato / MIME allegato non ammesso / size oltre limite
  - `E_DOCUMENTI_NOT_FOUND` (404) — entity attesa non trovata dal resolver di contesto

---

### 6. Nuova revisione

- Metodo: `POST`
- Path: `/api/v1/vendite/preventivi/{id}/revisione/`
- Regole: delega a `vendite.fn_crea_revisione_preventivo()` — copia testata+righe, rev+1, nuova rev in BOZZA, disattiva precedente
- Errori: `E_PREV_REVISIONE_ATTIVA` (409)

---

### 6b. Lista catena revisioni `GET /api/v1/vendite/preventivi/{id}/revisioni/`

Nuovo endpoint 2026-05-28. Mirror di `GET /api/v1/vendite/offerte/<id>/revisioni/`.

- Metodo: `GET`
- Path: `/api/v1/vendite/preventivi/{id}/revisioni/`
- Auth: JWT, `area_funzionale = "vendite"`. Lettura libera in ogni stato (utile per timeline UI revisioni anche su preventivi annullati/scaduti)
- Scopo: ritorna, **paginate**, le revisioni che condividono lo stesso `numero` del preventivo passato (lista configurabile `vendite.preventivo_revisioni`, tab "Revisioni" del drawer)
- Query param: `limit` (default 25) / `offset`; `order_by` = `rev` (default) | `numero` | `data` | `stato_descrizione` | `totale_documento`; `order_dir` assente = `asc`, `desc` su `data`; `emittente_fiscale_id` (PK) letto solo dal cancello di perimetro per chi vede più emittenti
- Output `200` (righe della vista `vw_preventivi_lista`):

```json
{
  "data": {
    "count": 3, "page": 1, "page_size": 25, "total_pages": 1,
    "results": [
      {"id": 1, "numero": "P-0001", "rev": 1,
       "stato_codice_interno": "SUPERATO", "stato_descrizione": "Superato",
       "data": "2026-04-10", "totale_documento": "1220.00", "...": "..."},
      {"id": 42, "numero": "P-0001", "rev": 3,
       "stato_codice_interno": "EMESSO", "stato_descrizione": "Emesso",
       "data": "2026-05-25", "totale_documento": "1300.00", "...": "..."}
    ]
  }
}
```

- Errori: `E_PREV_NOT_FOUND` (404) se l'id passato non esiste o è fuori perimetro

---

### 6c. Genera ordine da preventivo (smistamento MERCE) `POST /api/v1/vendite/preventivi/{id}/genera-ordine/`

**Modello split per natura** (brief [brief-preventivi-ordini.md](../../../dev/work-done/brief-preventivi-ordini.md) D8 — sostituisce il vecchio copia-tutto 1:1).
Smista a un **ordine di vendita DRAFT** **solo le righe MERCE** del preventivo
(natura con `destinazione_tipo='ORDINE_VENDITA'`), valorizzando `documento_origine =
('PREVENTIVO', preventivo_id)` sull'ordine.

- View `ApiPreventivoGeneraOrdine` (area `vendite`) → delega a
  `ordini_service.crea_ordine_da_preventivo(preventivo_id, righe_ids)`, che a sua
  volta delega alla **primitiva DB** `vendite.fn_push_preventivo_a_ordine`.
- **Body JSON** (opzionale): `{ "righe_ids": [int, ...] }` — sottoinsieme di
  righe da smistare (smistamento selettivo). **Assente/null** = tutte le righe
  MERCE residue; **lista vuota** = `E_PREV_VALIDAZIONE` (non degrada a "tutte").
- **Cosa fa la fn DB** (non più orchestrazione Python):
  - copia **solo** le righe natura `ORDINE_VENDITA` (i **servizi una-tantum** vanno a
    commessa via push commessa; il **ricorrente** è bloccato a monte, D9);
  - **snapshot prezzi** + componenti BoM (`fn_ordine_riga_componenti_init`);
  - scrive il **link di riga** `ordini_righe.preventivo_riga_id` → **idempotenza
    di riga**: una riga merce finisce su **al massimo un** ordine (le righe già
    allocate sono **saltate**, D5). Niente più doppio-ordine del vecchio copia-tutto.
- **Precondizione / guard** (validati **dalla fn DB**, non più in Python):
  stato `ACCETTATO` → altrimenti `E_VENDITA_PREVENTIVO_PUSH_STATO_NON_AMMESSO`;
  almeno una riga merce residua → altrimenti `E_VENDITA_PREVENTIVO_NESSUNA_RIGA_ORDINE`.
- Output `200`: `{ "ordine_id": int, "numero": str,
  "documento_origine": {"tipo": "PREVENTIVO", "id": int} }`.
  (Il campo `righe_create` non è più ritornato: il conteggio vive a DB.)
- FE: il ramo merce vive nel **Pannello Smistamento**
  (`PreventiviSmistamentoPanel`, sostituisce il `GeneraOrdineDialog` dal
  2026-06-12): l'operatore seleziona le righe residue (preselezionate tutte) e
  «Smista selezionate» instrada per natura — le righe merce finiscono su questo
  endpoint con `righe_ids`. La capability `genera_ordine` di
  `script.fn_available_actions_preventivo` (gate su **residuo merce**) resta
  esposta dal BE ma è filtrata dalla barra azioni del drawer.
- **Gate EVASO bi-ramo** (§5b brief smistamento): dopo il push, se non resta
  residuo su **nessun** ramo, il preventivo passa ACCETTATO→EVASO **dentro**
  `vendite.fn_push_preventivo_a_ordine`, dal BB DB
  `vendite.fn_preventivo_proietta_stato_smistamento` (lo stesso del ramo commessa,
  §13).
- **Percorso pratica (bivio-per-esito rev.3)**: lo smistamento merce si esegue da
  qui (Pannello Smistamento); quando il preventivo è in una pratica, **l'aggancio
  dell'ordine** come `pratiche_sorgenti` `COLLEGATO` avviene alla chiusura di
  SMISTAMENTO via l'handler **merce-only** `post_smistamento` (esito
  `MERCE_PRESENTE`), non da un orchestratore monolitico. Il vecchio
  `CONFERMA_VENDITA` / `vendita.push_preventivo` è **deprecato** (solo tipi legacy
  9002/9003). Vedi §14b (completa smistamento).

> **Offerta → ordine**: non disponibile (l'offerta non ha righe materializzate,
> solo eccezioni su listino). Prerequisito DB: brief
> [db-brief-offerta-righe-espanse.md](../../../dev/work-done/db-brief-offerta-righe-espanse.md).

---

### 6d. Righe merce smistabili a ordine `GET /api/v1/vendite/preventivi/{id}/righe-smistabili-ordine/`

Alimenta il dialog di smistamento riga-per-riga (§6c): ritorna **solo** le righe
**merce** del preventivo ancora da ordinare.

- View `ApiPreventivoRigheSmistabiliOrdine` (area `vendite`, sola lettura) →
  `preventivi_service.list_righe_smistabili_ordine` →
  `PreventiviRepository.list_righe_smistabili_ordine`.
- **Criterio**: legge dalla **vista** `vendite.vw_preventivi_righe_smistabili_ordine`
  — la **fonte unica** del predicato (natura `destinazione_tipo='ORDINE_VENDITA'`, riga
  attiva, **non ancora allocata** a un ordine), consumata anche da
  `fn_preventivo_ha_residuo_ordine` e `fn_push_preventivo_a_ordine`
  (consolidamento DB 2026-06-10). Le righe restituite sono quindi **esattamente**
  quelle che lo smistamento copierebbe → niente sorprese tra anteprima e push, e
  nessuna regola duplicata lato BE.
- Output `200`: `{ "data": [ { id, ordine, articolo_id, articolo_codice,
  articolo_descrizione, descrizione, qta_operativa, uom_operativa_id, uom_codice,
  prezzo_unitario, sconto_percentuale } ] }` (campi display via JOIN, no lookup
  client-side). Lista **vuota** se non resta merce da ordinare.
- Errori: `E_PREV_NOT_FOUND` (404) se il preventivo non esiste.
- FE: storicamente alimentava il `GeneraOrdineDialog`; dal 2026-06-12 il
  pannello (`PreventiviSmistamentoPanel`) legge da `GET /smistamento/` (§14),
  che copre **entrambi** i rami con lo stato per riga. L'endpoint resta per
  usi mirati al solo ramo merce (stessa vista, stessa verità).

---

### 7. Lista righe

- Metodo: `GET`
- Path: `/api/v1/vendite/preventivi/{id}/righe/`
- Output `200`: TUTTE le righe attive, nell'ordine del documento, dalla vista `vw_preventivi_righe_dettaglio`
- La **lista configurabile** delle righe (pagina ed export, `…/righe/lista/`) è il BB condiviso: vedi [api_righe_documento.md](api_righe_documento.md).

---

### 8. Aggiungi riga

- Metodo: `POST`
- Path: `/api/v1/vendite/preventivi/{id}/righe/`
- Body JSON:
  - `articolo_id` (uuid string, **obbligatorio**)
  - `descrizione` (string, opzionale — override descrizione articolo)
  - `qta_operativa` (decimal, **obbligatorio**, `<> 0`) — quantità nell'UoM operativa scelta (sorgente). La colonna base `quantita` è **derivata dal trigger DB** `trgfn_qta_from_operativa` (`quantita = qta_operativa × factor_to_base`) e **non va inviata** (refactor 2026-05-31, allineamento a contratti/offerte). Zero vietato, negativi ammessi (es. resi/note credito)
  - `prezzo_unitario` (decimal, opzionale — **auto-fill dal resolver pricing v5 se omesso**; per articoli **compositi** non va inviato: il padre e' SUM(figli × coeff_qta) calcolato dai trigger DB)
  - `sconto_percentuale` (decimal, opzionale, default 0)
  - `uom_operativa_id` (int, opzionale); `factor_to_base` (decimal, opzionale)
  - `ordine` (int, opzionale)
  - `meta` (object, opzionale)
  - ⛔ `iva_id` **non c'è** (dal 2026-08-31 l'aliquota la decide il risolutore): inviato, come ogni chiave fuori contratto, è un 400 `E_PREV_VALIDAZIONE` (2026-10-20: prima scartato in silenzio)
  - `data_consegna_richiesta_cliente` (date ISO, opzionale, nullable — 2026-09-14, Blocco A di `brief-db-modifiche-certe-ciclo-vendita-e-articolo`): quando il cliente vuole la merce. Sul preventivo c'è **solo la richiesta** (non c'è ancora niente da confermare); `fn_push_preventivo_a_ordine` la porta avanti sulla riga d'ordine. Anche in `PATCH` (`null` esplicito azzera); malformata → `400` `E_PREV_VALIDAZIONE` col campo. Esce da `list_righe`/`get_riga`
  - `richiesta_approvazione` (booleano JSON, opzionale, default `false`; un altro tipo → 400) — **L3 workflow Sprint E**: se `true` e il prezzo viola L2, invece di sollevare `E_PRICING_SCONTO_ECCESSIVO`/`E_PRICING_MAGGIORAZIONE_ECCESSIVA` la riga viene salvata con `stato_approvazione_prezzo='PENDING'` collegata a una pratica `APPROVAZIONE_PREZZO` aperta automaticamente
  - `componenti_overrides` (object `{componente_id: prezzo_string}`, opzionale) — **modello unificato componenti BoM 2026-05-13**: mappa di prezzi manuali per i figli del padre composito. Solo se l'articolo `is_composito=TRUE`. Richiede l'azione `prezzo_override_manuale` come per il prezzo padre; altrimenti `E_PRICING_OVERRIDE_NON_AUTORIZZATO` (403). Per i componenti senza entry, il backend invoca il resolver bundle-aware (STADIO 0 listino bundle del padre, fallback STADIO 1 standalone). Vedi `modello-componenti-bom.md`.
  - `componenti_attivazioni` (object `{componente_id: bool}`, opzionale) — **modello unificato**: mappa per attivare/disattivare componenti opzionali. Default DB: obbligatori `attivo=TRUE`, opzionali `attivo=FALSE`. Inviare solo i delta. Disattivare componenti `obbligatorio=TRUE` e' bloccato dal trigger DB con `E_DOC_COMPONENTE_OBBLIGATORIO` (400). Nessun gate L1 dedicato — decisione operativa, non economica
- Regole:
  - Ammesso solo in stato BOZZA
  - **Auto-fill prezzo**: se `prezzo_unitario` non e' nel payload e la testata ha BA+utility+data validi, il service chiama `PricingService.resolve_prezzo` e popola il prezzo dal resolver v5 (3 stadi: promo/contratto/categoria)
  - **L1 override**: se `prezzo_unitario` e' passato e differisce dal resolver, serve l'azione di processo `prezzo_override_manuale`; altrimenti `E_PRICING_OVERRIDE_NON_AUTORIZZATO` (403). Stessa autorizzazione per `componenti_overrides` non vuoto. Superuser bypassato
  - **L2 limite variazione (Sprint D)**: dopo L1, se `prezzo_resolver` e' noto e non zero, calcola `delta_pct` firmato; sconto > `VENDITE_MAX_SCONTO_PCT` o maggiorazione > `VENDITE_MAX_MAGGIORAZIONE_PCT` -> `E_PRICING_SCONTO_ECCESSIVO`/`E_PRICING_MAGGIORAZIONE_ECCESSIVA` (403, **`retryable=True`** dopo Fase 5.B2: il FE puo' offrire CTA "richiedi approvazione" e ri-tentare con `richiesta_approvazione=true`). Parametri risolti via `ParameterService` con **cascata estesa (refactor 2026-05-15)**: `user → categoria_cliente → group → emittente → session → function → default`. La `categoria_cliente_id` viene recuperata dal BA della testata preventivo (`BillingAccountRepository.get_categoria_cliente_id`) e propagata al risolutore: cosi' un'azienda puo' configurare soglie commerciali per categoria cliente (es. PREMIUM max sconto 5% indipendentemente dal seniority dell'operatore). Superuser bypass.
  - **L3 workflow approvazione (Sprint E)**: se `richiesta_approvazione=true` e L2 viola, l'errore L2 viene catturato, viene creata pratica `APPROVAZIONE_PREZZO` (stato APERTA) e la riga inserita con `stato_approvazione_prezzo='PENDING'` + `pratica_approvazione_prezzo_id`. Email best-effort al recipient configurato in parameter `VENDITE_APPROVAZIONE_PREZZO_RECIPIENT_EMAIL`. La pratica e' visibile nella coda approver via `GET /vendite/approvazioni-prezzo/`.
  - **Componenti BoM CASO composito**: dopo `create_riga`, se l'articolo e' `is_composito=TRUE`, il service invoca `fn_preventivo_riga_componenti_init` che popola `preventivi_righe_componenti` per tutti i figli BoM validi alla data. Errori bloccanti: `E_DOC_COMPOSITO_BOM_VUOTA` (422) se la BoM e' vuota/scaduta alla data del documento; `E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO` (400) se un override mette prezzo 0 su un obbligatorio; `E_DOC_COMPONENTE_LISTINO_MANCANTE` (422) se il resolver fallisce per un componente senza override. Tutta la transazione e' atomica (init + UPDATE attivazioni avvengono in `@transaction.atomic`).
  - **Meta audit**: popolato sempre con `origine_prezzo` (PROMO/CONTRATTO_OVERRIDE/CONTRATTO_LISTINO/CATEGORIA/MANUALE/LISTINO_BUNDLE) + `prezzo_resolver_context` (listino/contratto/promo + variazione). Se override manuale: anche `prezzo_base_resolver`, `delta_override`, `delta_override_pct`, `override_user_id`. Se workflow L3: anche `richiesta_approvazione_pending=true` + `violazione_l2` (tipo, variazione_abs_pct, limite_pct).
  - Ricalcolo totali automatico dopo insert (trigger DB). Per padri compositi il prezzo unitario padre viene **immediatamente sovrascritto** dal trigger `_z90_ricalcola_padre` come SUM(figli × coeff_qta_snapshot).
- Errori: `E_PREV_VALIDAZIONE` (400), `E_RIGA_DOC_NON_BOZZA` (409), `E_PRICING_OVERRIDE_NON_AUTORIZZATO` (403), `E_PRICING_SCONTO_ECCESSIVO` (403), `E_PRICING_MAGGIORAZIONE_ECCESSIVA` (403), `E_DOC_COMPOSITO_BOM_VUOTA` (422), `E_DOC_COMPONENTE_OBBLIGATORIO` (400), `E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO` (400), `E_DOC_COMPONENTE_LISTINO_MANCANTE` (422)

---

### 8a-bis. Date di consegna in blocco

- Metodo: `POST`
- Path: `/api/v1/vendite/preventivi/{id}/righe/date-consegna/`
- Body JSON: `colonna` (`data_consegna_richiesta_cliente`, l'unica data della riga di preventivo), `data` (`AAAA-MM-GG`, **obbligatoria**), `modalita` (`TUTTE` | `SOLO_VUOTE`), `anteprima` (bool, opzionale: esegue lo stesso UPDATE e lo annulla — i numeri della scrittura, il rifiuto del DB già qui, niente resta scritto)
- Scopo: scrive la stessa data richiesta su più righe attive, in un solo UPDATE ([brief-db-date-consegna-righe-in-blocco](/dev/work-done/brief-db-date-consegna-righe-in-blocco) §5, §8). La giudica il lock delle righe: solo in `DRAFT`. Nessun pre-check di stato nel backend
- Output `200`: `{ "data": { "documento_id": 9, "colonna": "data_consegna_richiesta_cliente", "data": "2026-11-20", "modalita": "SOLO_VUOTE", "anteprima": false, "aggiornate": 3, "saltate_spedite": 0 } }`
- Errori: `E_PREV_NOT_FOUND` (404), `E_PREV_VALIDAZIONE` (400, col campo), `E_RIGA_DOC_NON_BOZZA` (409), `E_RIGA_PREZZO_PENDENTE` (409: una riga col prezzo in attesa di approvazione ferma il gesto per intero)

---

### 8b. Suggerisci prezzo riga

- Metodo: `POST`
- Path: `/api/v1/vendite/preventivi/{id}/righe/suggerisci-prezzo/`
- Body JSON:
  - `articolo_id` (uuid string, **obbligatorio**)
  - `uom_id` (int, **obbligatorio**)
- Scopo: calcola il prezzo suggerito dal resolver v5 senza creare la riga. Usato dal FE per pre-compilare il campo prezzo all'apertura del drawer. Nessun side-effect
- Output `200`: `{ "data": { "prezzo_finale": "50.00", "prezzo_base_snapshot": "52.50", "origine": "CATEGORIA", "listino_id": 100, "contratto_id": null, "promo_id": null, "tipo_variazione_applicata": "PERCENTUALE", "valore_variazione_applicata": "-5.00" } }`
- Contesto derivato: BA, utility, data dalla testata preventivo; emittente dal JWT operatore
- Permesso: oggetto `("vendite", "preventivo")` livello **TUTTO** — è un `POST`, e i POST non di ricerca chiedono il livello pieno anche se non scrivono
- Errori: `E_PREV_NOT_FOUND` (404), `E_PREV_VALIDAZIONE` (400 — testata senza BA/utility/data o utente senza emittenti autorizzati), errori applicativi del resolver (es. `E_CATEGORIA_LISTINO_NON_MAPPATA`)

---

### 8c. Preview componenti riga (modello unificato BoM)

- Metodo: `POST`
- Path: `/api/v1/vendite/preventivi/{id}/righe/preview-componenti/`
- Body JSON:
  - `articolo_id` (uuid string, **obbligatorio**) — articolo composito padre
  - `uom_operativa_id` (int, opzionale)
  - `quantita` (decimal, **obbligatorio**)
- Scopo: ritorna i componenti BoM validi alla data del preventivo con prezzo suggerito dal resolver bundle-aware. Consumato dal `ComponentiDialog` FE (building block riusabile in `vendite/_shared/componenti/`) per la valorizzazione pre-save dei componenti del padre composito. Read-only, nessun side-effect (fn DB `STABLE`)
- Output `200`: `{ "data": [ { "articolo_componente_id": "...", "componente_id": "...", "componente_codice": "...", "componente_descrizione": "...", "coeff_qta_snapshot": "1.5", "quantita_componente": "3.0", "uom_id": 1, "uom_codice": "PZ", "iva_id": 1, "prezzo_suggerito": "10.00", "origine_prezzo": "LISTINO_BUNDLE", "resolver_error_reason": null, "obbligatorio": true, "esposizione_in_fattura": "DESCRITTIVO" }, ... ] }` — `esposizione_in_fattura` è un codice di `config.esposizioni_componente` (`NASCOSTO` / `DESCRITTIVO` / `VALORIZZATO`)
- Comportamento per componente:
  - Resolver invocato in modalita' **bundle-aware**: STADIO 0 cerca prezzo in `vendite.listini_righe_componenti` (bundle del padre, origine `LISTINO_BUNDLE`); fallback STADIO 1 standalone (origine `CATEGORIA`/`PROMO`/`CONTRATTO_LISTINO`/`CONTRATTO_OVERRIDE`)
  - Resolver fallito su un componente → `prezzo_suggerito: null` + `resolver_error_reason: "messaggio"`; l'operatore deve inserire prezzo manuale via `componenti_overrides` al save riga
- Contesto derivato: BA, utility, data, emittente dalla testata preventivo (precedenza `emittente_fiscale_id` esplicito > operatore JWT)
- Permesso: oggetto `("vendite", "preventivo")` livello **TUTTO** (`POST`, come §8b)
- Errori:
  - `E_PREV_NOT_FOUND` (404) — preventivo inesistente
  - `E_PREV_VALIDAZIONE` (400) — data preventivo NULL, utility NULL, emittente non risolvibile
- Vedi anche: [`modello-componenti-bom.md`](../../../dev/manual/modello-componenti-bom.md)

---

### 8d. Lista componenti riga padre

- Metodo: `GET`
- Path: `/api/v1/vendite/preventivi/{id}/righe/{rid}/componenti/`
- Query params:
  - `solo_attivi` (bool, opzionale, default `true`) — `true`: solo componenti `attivo=TRUE` (vista compatta retro-compatibile, expander tabella righe). `false`: include anche opzionali disattivati — usato dall'EDIT panel FE per consentire riattivazione via toggle. Accetta `"false"`/`"0"`/`"no"`/`"off"` come falsy
- Scopo: lista i componenti BoM persistiti su `preventivi_righe_componenti` per la riga padre composita, con denormalizzazioni catalogo/uom/iva + flag `obbligatorio` e modo `esposizione_in_fattura` (JOIN runtime su `articoli_componenti` — BoM immutabile per design)
- Output `200`: `{ "data": [ { "id": 1, "riga_preventivo_id": 10, "articolo_componente_id": "...", "componente_id": "...", "componente_codice": "...", "componente_descrizione": "...", "coeff_qta_snapshot": "1.5", "quantita": "3.0", "uom_operativa_id": 1, "uom_codice": "PZ", "factor_to_base": "1.0", "qta_operativa": "3.0", "prezzo_unitario": "10.00", "iva_id": 1, "iva_codice": "22", "iva_aliquota": "22.00", "origine_prezzo": "LISTINO_BUNDLE", "prezzo_resolver_context": {...}, "stato_approvazione_prezzo": null, "pratica_approvazione_prezzo_id": null, "meta": {}, "ordine": 1, "attivo": true, "obbligatorio": true, "esposizione_in_fattura": "DESCRITTIVO" } ] }`
- Area: `vendite` livello LETTURA sufficiente (`GET`)
- Errori: `E_PREV_RIGA_NOT_FOUND` (404 — riga inesistente o non appartenente al preventivo)

---

### 8e. Aggiorna componente singolo

- Metodo: `PATCH`
- Path: `/api/v1/vendite/preventivi/{id}/righe/{rid}/componenti/{cid}/`
- Body JSON (contratto dell'operatore, BB `COMPONENTE_PATCH_OPERATORE`, uguale sui cinque documenti):
  - `prezzo_unitario` (decimal o `null`, opzionale) — non nullo richiede l'azione `prezzo_override_manuale` (403 `E_PRICING_OVERRIDE_NON_AUTORIZZATO`)
  - `attivo` (bool, opzionale)
  - `meta` (object, opzionale)
  - Ogni altra chiave (anche `origine_prezzo`, `iva_id`, `ordine`) → 400 `E_PREV_VALIDAZIONE`; `{}` → 400. `origine_prezzo` la calcola il server (`MANUALE` col prezzo, `null` senza)
- Output `200`: `{ "data": { "status": "ok", "componente_id": 1 } }`
- Regole:
  - Ammesso solo se il preventivo e' in stato BOZZA (`E_RIGA_DOC_NON_BOZZA`)
  - Anti-tampering URL: il componente deve esistere ed essere della `riga_id` e del preventivo dell'URL, altrimenti 404 `E_PREV_COMPONENTE_NOT_FOUND`
  - Trigger DB `_z90_ricalcola_padre` aggiorna il `prezzo_unitario` della riga padre come SUM(figli × coeff_qta) post-update
  - **Guard prezzo zero**: `prezzo_unitario=0` su componente obbligatorio rejected dal trigger `script.trgfn_componenti_check_prezzo_obbligatorio` con `E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO` (400)
- Area: `vendite` livello TUTTO + azione `prezzo_override_manuale` per un `prezzo_unitario` non nullo
- Errori: `E_PREV_COMPONENTE_NOT_FOUND` (404), `E_PREV_VALIDAZIONE` (400), `E_RIGA_DOC_NON_BOZZA` (409), `E_PRICING_OVERRIDE_NON_AUTORIZZATO` (403), `E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO` (400)

---

### 8f. Elimina componente singolo

- Metodo: `DELETE`
- Path: `/api/v1/vendite/preventivi/{id}/righe/{rid}/componenti/{cid}/`
- Regole:
  - Soft delete (`attivo=FALSE`), ammesso solo in stato BOZZA
  - Anti-tampering URL come §8e
  - **Guard componente obbligatorio**: tentativo di disattivare un componente `obbligatorio=TRUE` rejected dal trigger `script.trgfn_componenti_guard_obbligatorio` con `E_DOC_COMPONENTE_OBBLIGATORIO` (400)
  - Trigger DB `_z90_ricalcola_padre` aggiorna il `prezzo_unitario` della riga padre post-delete
- Output `200`: `{ "data": { "status": "ok", "componente_id": 1, "deleted": true } }` (`deleted: false` se era già disattivato: non è un errore)
- Errori: `E_PREV_COMPONENTE_NOT_FOUND` (404), `E_RIGA_DOC_NON_BOZZA` (409), `E_DOC_COMPONENTE_OBBLIGATORIO` (400)

---

### 9. Aggiorna riga

- Metodo: `PATCH`
- Path: `/api/v1/vendite/preventivi/{id}/righe/{rid}/`
- Body JSON: campi modificabili (`qta_operativa`, `prezzo_unitario`, `sconto_percentuale`, `descrizione`, `uom_operativa_id`, `factor_to_base`, `ordine`, `meta`, `data_consegna_richiesta_cliente`, `richiesta_approvazione`). `quantita` (base) è derivata dal trigger e **non aggiornabile dal client**: la sorgente è `qta_operativa`. `iva_id` non c'è: come ogni chiave ignota è un 400 `E_PREV_VALIDAZIONE` (2026-10-20: prima scartata)
- Regole: ammesso solo in stato BOZZA, ricalcolo totali dopo update. La riga deve essere del preventivo dell'URL, altrimenti 404 `E_PREV_RIGA_NOT_FOUND` (2026-10-20: prima si modificava una riga di un altro preventivo)
- Output `200`: `{ "data": { "status": "ok", "riga_id": 10 } }`
- **L1+L2+L3 su PATCH**: se il payload tocca `prezzo_unitario`, scattano gli stessi check dell'insert (autorizzazione + audit meta + L2 limite + L3 workflow opzionale via flag `richiesta_approvazione=true`). L'articolo/UoM della riga esistente sono usati come contesto resolver
- **Trigger DB guard riga PENDING**: se la riga ha `stato_approvazione_prezzo='PENDING'`, il trigger `trg_preventivi_righe_a10_guard_pending_upd` (Sprint E) blocca modifica di campi struttura (prezzo, qta, articolo, sconto, ecc.) con `E_RIGA_PREZZO_PENDENTE` (409). Solo `stato_approvazione_prezzo`, `pratica_approvazione_prezzo_id` e `meta` sono ammessi. Per modificare prezzo: prima chiudere il workflow (approva/rifiuta) o annullare la pratica.
- **Guard componenti via PATCH riga**: payload con `componenti_overrides` o `componenti_attivazioni` viene rifiutato con `E_PREV_VALIDAZIONE` (400). La PATCH riga e' solo testata; per modificare i componenti BoM usare gli endpoint dedicati §8e (PATCH componente) / §8f (DELETE componente).
- Errori: `E_PREV_RIGA_NOT_FOUND` (404), `E_RIGA_DOC_NON_BOZZA` (409), `E_PRICING_OVERRIDE_NON_AUTORIZZATO` (403), `E_PRICING_SCONTO_ECCESSIVO` (403), `E_PRICING_MAGGIORAZIONE_ECCESSIVA` (403), `E_RIGA_PREZZO_PENDENTE` (409), `E_PREV_VALIDAZIONE` (400 — chiave ignota o campi componenti)

---

### 10. Elimina riga

- Metodo: `DELETE`
- Path: `/api/v1/vendite/preventivi/{id}/righe/{rid}/`
- Regole: **hard delete** (i componenti BoM vanno via per `ON DELETE CASCADE`), ammesso solo in stato BOZZA, ricalcolo totali da trigger. La riga deve essere del preventivo dell'URL, altrimenti 404 `E_PREV_RIGA_NOT_FOUND`
- Output `200`: `{ "data": { "status": "ok", "riga_id": 10 } }`
- Errori: `E_PREV_RIGA_NOT_FOUND` (404), `E_RIGA_DOC_NON_BOZZA` (409)

---

### 10b. Riepilogo IVA `GET /api/v1/vendite/preventivi/{id}/riepilogo-iva/`

Una riga per aliquota (`imponibile`, `imposta`, `arrotondamento`, `totale_riga` e le
decodifiche `iva_*`), letta dalla vista derivata del DB (IVA per gruppo aliquota,
DPR 633/72 art. 21): nessun calcolo Python. Stessa view factory
(`build_riepilogo_iva_view`) di ordini e DDT. Prima la testata: preventivo
inesistente o fuori perimetro → 404 `E_PREV_NOT_FOUND`. Usato dal pannello
«Riepilogo IVA» del drawer e dal context builder PDF.

---

### 11. Indirizzi documento (BB condiviso, contratto 2026-07-12)

- `GET /api/v1/vendite/preventivi/{id}/indirizzi/` → `{tipi_ammessi[], indirizzi[]}`
- `POST /api/v1/vendite/preventivi/{id}/indirizzi/` — upsert uno-per-tipo:
  flusso PICKER `{tipo_indirizzo_id, origine_indirizzo_id}` (snapshot composto
  server-side; dal payload solo i contatti) o UNA-TANTUM `{tipo_indirizzo_id, snapshot,
  origine_soggetto_ruolo_id?}`. Nel picker `origine_soggetto_ruolo_id` lo deriva il
  backend dall'indirizzo; nell'una-tantum il client può dichiararlo (provenienza
  «anagrafica soggetto»). Che l'indirizzo sia del cliente lo giudica il guard DB
  `vendite.trgfn_doc_indirizzi_guard_cliente` (`E_INDIRIZZO_DOC_NON_DEL_CLIENTE`, 400);
  lo stato il lock dei satelliti a DB (`E_DOC_DATI_COLLEGATI_NON_BOZZA`, 409: in
  pratica solo BOZZA). Il service non ha guard di stato né di proprietà suoi.
- `DELETE /api/v1/vendite/preventivi/{id}/indirizzi/{indirizzo_id}/` — rimozione slot (stesso lock DB).
- Dettagli completi (shape, errori, whitelist ambito PREVENTIVI):
  [api_indirizzi_documento.md](api_indirizzi_documento.md)

---

### 13. Push in commessa (fatturazione)

- Metodo: `POST`
- Path: `/api/v1/vendite/preventivi/{id}/push-commessa/`
- Auth: `post_permission = "push_commessa_preventivi"`, `Idempotency-Key` obbligatoria
- Body JSON (opzionale): `{ "righe_ids": [int, ...] }` — sottoinsieme di righe
  **servizio** da pushare (smistamento selettivo dal Pannello Smistamento,
  [brief-db-smistamento-preventivi.md](../../../dev/work-done/brief-db-smistamento-preventivi.md) C).
  **Assente/null** = tutte le righe servizio eleggibili; **lista vuota** =
  `E_PREV_VALIDAZIONE` (non degrada a "tutte" — stessa regola su
  `/genera-ordine/`, helper `_parse_righe_ids`). Il filtro arriva alla fn DB
  `fn_list_preventivi_da_pushare(p_righe_ids)` attraverso la catena
  `push_a_commessa → pr_run_commesse_push_one → CommessaPushOrchestrator →
  handler → CommesseRepository.fetch_pushable_rows` (5° parametro, supportato
  dalla sola sorgente `PREVENTIVO` — whitelist `_SORGENTE_SUPPORTA_RIGHE_IDS`).
- Regole: ammesso solo in stato ACCETTATO, verifica righe eleggibili via `fn_list_preventivi_da_pushare`
- **Gate EVASO bi-ramo** (D6 + brief smistamento §5b): il preventivo passa
  ACCETTATO→EVASO **solo** se non resta residuo su **nessun** ramo (merce da
  ordinare, servizi da mandare in commessa). ⭐ Dal 2026-10-12 lo fa il **DB**
  (D-10 / R-8 di brief-db-annullo-a-valle-riapre-a-monte): il trigger delle righe
  di commessa riproietta il preventivo col BB
  `vendite.fn_preventivo_proietta_stato_smistamento`, nella stessa transazione
  dell'invio — lo stesso BB che lo riporta ad ACCETTATO quando la commessa si
  annulla, e che usa il ramo ordine (`vendite.fn_push_preventivo_a_ordine`). Il
  backend non tocca lo stato: `transiziona_a_evaso_se_smistato` (e il modulo
  `_smistamento_gate_helpers.py`) è ritirato.
- **Aggancio pratica (ramo servizi dello split, bivio rev.3)**: se il preventivo
  appartiene a una pratica, a push `COMPLETATO` la commessa-servizi viene legata
  alla pratica come `pratiche_sorgenti` **COLLEGATO** (idempotente). È il punto
  d'aggancio del ramo servizi: l'handler `post_smistamento` è **merce-only**, quindi
  la commessa-servizi non passa da lì. No-op per i push standalone (preventivo non
  in pratica).
- **Semantica transazionale (fix analisi-fix-transazioni #5, 2026-07-08)**: push +
  aggancio commessa-servizi alla pratica avvengono in un **unico**
  `transaction.atomic()`. Un fallimento dell'**aggancio-pratica** rolla l'**intero
  push** (commesse + ponte emittibilità, e con loro lo stato proiettato dal DB): non
  resta mai una commessa-servizi orfana senza link pratica. Il push è
  idempotente/ri-eseguibile (advisory lock + dedup `segment_key`) → retry sicuro.
- Output `200`: report orchestrator `{ stato, push_log_id, durata_ms, handlers,
  commesse_ids, righe_pushable, fatturazione_immediata }`
- Errori: `E_PREV_STATO_TRANSIZIONE` (409), `E_PREV_NESSUNA_RIGA` (400)

---

### 14. Smistamento (Pannello Smistamento)

Sostituisce il vecchio `GET /stato-fatturazione/` (viste DB rinominate e rifatte
natura-aware il 2026-06-12: `vw_preventivi_smistamento` + `_righe`, le vecchie
`vw_preventivi_stato_fatturazione*` sono droppate).

- Metodo: `GET`
- Path: `/api/v1/vendite/preventivi/{id}/smistamento/`
- View `ApiPreventivoSmistamento` → `preventivi_service.smistamento` →
  `PreventiviRepository.stato_smistamento` + `list_righe_smistamento`
- Output `200` (`aggregato` è **null** per preventivo senza righe attive — la
  vista GROUP BY non produce la riga e il BE non fabbrica fallback):

```json
{
  "data": {
    "aggregato": {
      "preventivo_id": 1, "righe_totali": 5, "righe_merce": 3,
      "righe_servizi": 2, "righe_a_ordine": 2, "righe_in_commessa": 1,
      "righe_emesse_af": 0, "righe_fatturate": 0, "righe_residue": 2
    },
    "righe": [
      { "riga_id": 10, "riga_descrizione": "...", "articolo_codice": "ART1",
        "qta_operativa": "2", "uom_codice": "PZ", "natura_vendita_codice": "MERCE",
        "destinazione_tipo": "ORDINE_VENDITA", "stato_smistamento": "A_ORDINE",
        "ordine_id": 7, "ordine_numero": "ORD-0007" }
    ]
  }
}
```

- Regole: `stato_smistamento` è la **colonna autorevole** per la UI
  (`RESIDUA` / `A_ORDINE` / `IN_COMMESSA` / `EMESSA_AF` / `FATTURATA`); il
  predicato `IN_COMMESSA` conta solo attività `stato_emissione='EMESSA'`
  (allineato a capability e list-fn — fix della divergenza preesistente).
  `righe_residue` alimenta il progress X/Y verso EVASO del pannello.
- Errori: `E_PREV_NOT_FOUND` (404)

---

### 14b. Completa smistamento (percorso pratica — bivio-per-esito)

Completa lo step **SMISTAMENTO** della pratica con un **esito di RAMO calcolato dal
dominio** (`MERCE_PRESENTE` / `SOLO_SERVIZI`), **non scelto dall'operatore**. È il
fix di PRA-0000225 (bivio-per-esito rev.3,
[brief-db-chiusura-pratica-nessun-lavoro-pendente.md](../../../dev/work-done/brief-db-chiusura-pratica-nessun-lavoro-pendente.md)):
l'esito viene scritto nella **stessa UPDATE** che completa il flusso, così il check
di chiusura template-based lo legge subito.

- Metodo: `POST`
- Path: `/api/v1/vendite/preventivi/{id}/completa-smistamento/`
- Auth: area `vendite`, `Idempotency-Key` obbligatoria
- Body JSON: **nessuno** (l'esito NON è un input: il FE **sopprime il picker esiti**
  per SMISTAMENTO — `modalita_esito=MANUALE` a livello motore).
- View `ApiPreventivoCompletaSmistamento` → `preventivi_service.completa_smistamento`.
- Comportamento:
  1. risolve la pratica del preventivo (ROOT per-flusso) → `E_VENDITA_PREVENTIVO_NON_COLLEGATO` (422) se il preventivo non nasce da una pratica;
  2. **guard bi-ramo**: nessun residuo su ORDINE né COMMESSA (`fn_preventivo_ha_residuo_ordine` / `_commessa`) → `E_VENDITA_SMISTAMENTO_NON_ESEGUITO` (422) se resta merce/servizi da smistare;
  3. **esito di ramo**: `MERCE_PRESENTE` se dal preventivo è nato un ordine
     (stesso lookup `documento_origine` dell'handler `post_smistamento`, così
     l'handler troverà l'ordine da agganciare), altrimenti `SOLO_SERVIZI` — copre
     anche il caso **misto** (c'è merce → `MERCE_PRESENTE`);
  4. completa (o avvia+completa se lo step è ancora `DA_ESEGUIRE`) delegando al BB
     motore `pratiche_service.completa_step_pratica`.
- Effetto sul percorso pratica:
  - **`MERCE_PRESENTE`** → i flussi ordine `CONFERMA_ORDINE` (9013) e `INVIO_COMMESSA`
    (9014) sono percorribili+obbligatori → la pratica **resta APERTA** finché non
    completati; nasce anche il retro-aggancio dell'ordine (handler `post_smistamento`);
  - **`SOLO_SERVIZI`** → 9013/9014 sono **ramo morto** (non bloccano) → la pratica
    **si chiude subito** (nessun lavoro pendente).
- Idempotente: se lo step è già terminale → no-op, `gia_completato=true`.
- Output `200`:

```json
{ "data": { "preventivo_id": 1, "pratica_id": 42, "flusso_id": 500,
            "esito": "MERCE_PRESENTE", "gia_completato": false } }
```

- Errori: `E_VENDITA_PREVENTIVO_NON_COLLEGATO` (422), `E_VENDITA_SMISTAMENTO_NON_ESEGUITO` (422), `E_PREV_VALIDAZIONE` (400, flusso SMISTAMENTO non istanziato).

---

### 15. Genera pratica

- Metodo: `POST`
- Path: `/api/v1/vendite/preventivi/{id}/genera-pratica/`
- Auth: `post_permission = "genera_pratica_preventivi"`, `Idempotency-Key` obbligatoria
- Body JSON:
  - `tipo_prestazione_id` (int positivo, **obbligatorio**)
  - `priorita_id` (int positivo, **obbligatorio**) — assenti o non validi → 400 `E_PREV_VALIDAZIONE` col campo (2026-10-20: prima un 500)
  - `descrizione` (string, opzionale)
- Regole:
  - Ammesso solo in stato ACCETTATO con `billing_account_id` valorizzato
  - Risolve contesto anagrafico dal BA (emittente default, soggetto, ruolo)
  - Crea pratica via BB `pratiche_service.crea_pratica` (riutilizzabile cross-dominio)
  - Crea link `pratiche.pratiche_sorgenti` con `sorgente_tipo = 'PREVENTIVO_VENDITA'`
- Output `200`: `{ "data": { "pratica_id": 42, "preventivo_id": 1 } }`
- Errori: `E_PREV_PRATICA_STATO` (409), `E_PREV_VALIDAZIONE` (400), `E_CONFIG_MANCANTE` (500)

---

### 16. Pratiche collegate — RIMOSSO (2026-07-15)

L'endpoint `GET /{id}/pratiche/` è stato rimosso: la pratica collegata vive nel
pannello Passaggi (lineage, `GET /{id}/passaggi/` — vedi
[api_lineage_passaggi.md](api_lineage_passaggi.md)), che espone il link
cliccabile al `PraticaDrawer`. Il vincolo "zero pratiche collegate" del
hard-delete resta (guard nel service via `repo.list_pratiche`).

---

### 16b. Risoluzione preventivo ROOT (percorso pratica)

Due endpoint di lettura che risolvono il preventivo ROOT agganciato a una pratica
(`pratiche_sorgenti`, ruolo_link `ROOT`). Alimentano gli step del percorso che
aprono lo stesso `PreventiviDrawer`. Ritornano `{"preventivo_id": <id|null>}`.

- **Per flusso**: `GET /api/v1/vendite/preventivi/root-per-flusso/?flusso_id=<id>`
  — ROOT agganciato a **quel flusso** (aggancio per-flusso). Usato dalla
  riapertura del flusso PREVENTIVAZIONE (`azione_ui` APRI_PREVENTIVO): se il ROOT
  esiste apre in EDIT, altrimenti CREATE. `flusso_id` obbligatorio
  (`E_FLUSSO_ID_OBBLIGATORIO`).
- **Per pratica**: `GET /api/v1/vendite/preventivi/root-per-pratica/?pratica_id=<id>`
  — ROOT della **pratica** (non del flusso corrente). Usato dagli step **a valle**
  (es. `azione_ui` SMISTAMENTO, flusso che non possiede il ROOT: agganciato a
  monte da PREVENTIVAZIONE). `pratica_id` obbligatorio
  (`E_PRATICA_ID_OBBLIGATORIO`). Il FE non apre in CREATE se ritorna `null`
  (`requiresExisting`): lo step a valle richiede un preventivo già esistente.
- Lettura libera (area `vendite`); l'apertura del documento applica comunque RLS
  sull'emittente.

---

### 17. Contesto pricing

- Metodo: `GET`
- Path: `/api/v1/vendite/preventivi/{id}/contesto-pricing/`
- Scopo: Restituisce il **path di risoluzione prezzi** applicato al preventivo (contratto attivo o listino categoria fallback). Lettura puramente informativa per l'header del drawer FE — audit visivo di quale listino verra' usato dal resolver al calcolo prezzi riga. Stessa logica applicata da `fn_resolve_prezzo_listino_v2` (STADIO 1 contratto / STADIO 2 categoria).
- Output `200`:
  ```json
  {
    "data": {
      "preventivo_id": 53,
      "data_riferimento": "2026-05-14",
      "fonte": "CONTRATTO",
      "contratto_id": 23,
      "contratto_numero": "CNT0000023",
      "listino_id": 85,
      "listino_codice": "com-002",
      "listino_descrizione": "...",
      "categoria_cliente_id": null,
      "categoria_cliente_codice": null,
      "categoria_cliente_descrizione": null
    }
  }
  ```
- Campo `fonte`:
  - `"CONTRATTO"`: contratto attivo trovato per (BA, utility, data). I prezzi vengono dal listino del contratto (`contratto_*` valorizzati, `categoria_*` NULL).
  - `"CATEGORIA"`: nessun contratto attivo, listino mappato in `categorie_clienti_listini` per la categoria cliente + utility, classe NULL (`categoria_*` e `listino_*` valorizzati, `contratto_*` NULL).
  - `"NONE"`: nessuna config (no contratto, no mapping categoria-listino). Il FE mostra warning all'admin. Resolver fallira' al calcolo prezzi riga.
- Pattern lookup: replica intenzionalmente STADIO 1+2 del resolver per coerenza UI (vedi `feedback_db_actions_passaggio_team` — refactor a fn DB `fn_get_contesto_pricing` rimandato).
- Area: `vendite` livello LETTURA sufficiente.
- Errori: preventivo inesistente o fuori perimetro → 404 `E_PREV_NOT_FOUND` (2026-10-20: prima `200 {}`).

---

### 18. Documenti preventivo

Endpoint del motore documentale parametrico per la sorgente `PREVENTIVO`.
Risolvono il contesto comune (preventivo + emittente fiscale + sorgente
attiva) via helper condiviso `apps.documenti.api.contesto_helpers.resolve_contesto_documentale`
(vedi [api_documenti_helpers](../../documenti/manual/api_documenti_helpers.md)).

| Metodo | Path | Effetto |
| --- | --- | --- |
| `GET` | `/api/v1/vendite/preventivi/<id>/documenti/` | Lista documenti generati per il preventivo (paginata, scope emittente) — contratto di lista in [api_documenti_per_sorgente](../../documenti/manual/api_documenti_per_sorgente.md) §3.4 |
| `POST` | `/api/v1/vendite/preventivi/<id>/documenti/anteprima/` | Render PDF temporaneo, no persist (Decisione 30) |
| `POST` | `/api/v1/vendite/preventivi/<id>/documenti/genera/` | Persiste PDF + record DB + evento `GENERATO` (per preventivi già EMESSI: ristampe successive all'emissione iniziale) |
| `GET` | `/api/v1/vendite/preventivi/<id>/documenti/<doc_id>/file/` | Download PDF principale + evento `SCARICATO` (Decisione 31) |
| `GET` | `/api/v1/vendite/preventivi/<id>/documenti/<doc_id>/allegati/` | Lista files del documento (principale + allegati) |
| `POST` | `/api/v1/vendite/preventivi/<id>/documenti/<doc_id>/allegati/` | Append allegati multipart su documento esistente |

Payload `genera/` e `anteprima/` (JSON):

```json
{
  "template_documento_id": 123,
  "tipo_documento_output_id": 2
}
```

Entrambi opzionali; selezione default come §5b. Permessi: oggetto `("vendite", "preventivo")`; i `GET` con LETTURA, i `POST` (`genera`, `anteprima`, append allegati) con **TUTTO**, come ogni POST non di ricerca. `genera/` risponde `200`.

**Endpoint `allegati/` (nuovi 2026-05-28)**:

- GET: ritorna `{"data": {"principale": {...}, "allegati": [{...}, {...}]}}`. Consumato dal row-expand di `DocumentiGeneratiSorgenteList` per popolare `filesPerDoc`
- POST: multipart con campo ripetuto `allegati`. Modalità append post-emissione. Non rigenera il PDF principale, aggiunge solo file secondari al documento esistente

Errori comuni di tutta la sezione: `E_DOCUMENTI_VALIDATION` (400), `E_DOCUMENTI_NOT_FOUND` (404).

---

## Note del preventivo

| | |
|---|---|
| **Lista / creazione** | `GET` `POST` `/api/v1/vendite/preventivi/{preventivo_id}/note/` |
| **Dettaglio / modifica / cancellazione** | `GET` `PATCH` `DELETE` `/api/v1/vendite/preventivi/{preventivo_id}/note/{note_id}/` |

Building block note partizionate: il contratto completo sta in
[api_note_documento](../../core/manual/api_note_documento.md). Delta del dominio: partizione
`vendite.note_preventivo`, `target_tipo = 'PREVENTIVO'`, note di riga sulle
righe di preventivo.

## Dipendenze DB

| Tabella/funzione | Ruolo |
|---|---|
| `vendite.preventivi` | Testata preventivo |
| `vendite.preventivi_righe` | Righe articoli |
| `vendite.preventivi_indirizzi` | Indirizzi snapshot |
| `config.stati_doc_preventivi` | Macchina a stati |
| `catalogo.articoli` | JOIN decodifica articolo |
| `catalogo.unita_misura` | JOIN decodifica UoM |
| `config.iva` | JOIN decodifica IVA |
| `anagrafiche.billing_account` → `soggetti_ruoli` → `soggetti` | JOIN cliente |
| `config.utilita` | JOIN utility |
| `config.valute` | JOIN valuta |
| `config.termini_pagamento` | JOIN termini |
| `vendite.fn_cambia_stato_preventivo()` | Transizione stato (da creare) |
| `vendite.fn_crea_revisione_preventivo()` | Copia revisione (da creare) |
| `vendite.fn_ricalcola_totali_preventivo()` | Ricalcolo totali (da creare) |
| `vendite.fn_list_preventivi_da_pushare()` | Discovery righe per commessa (esiste) |
| `vendite.commesse_sorgenti` | Link preventivo → commessa |
| `vendite.commesse_attivita` | Stato emissione righe |
| `vendite.attivita_fatturabili` | Stato fatturazione |
| `pratiche.pratiche_sorgenti` | Link preventivo → pratica (da creare) |
| `config.sorgenti` | Dizionario tipi sorgente |
| `pratiche_service.crea_pratica` | BB creazione pratica |

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
- **Passaggi** `GET /api/v1/vendite/preventivi/<id>/passaggi/` — genealogia del
  documento: pratica + frontiera + catena transiti in entrambe le direzioni.
  Contratto completo nel manuale del BB condiviso:
  [api_lineage_passaggi.md](api_lineage_passaggi.md).

## Codici errore

| Codice | HTTP | Descrizione |
|---|---|---|
| `E_PREV_NOT_FOUND` | 404 | Preventivo non trovato |
| `E_PREV_VALIDAZIONE` | 400 | Validazione input fallita (incluse chiavi fuori contratto, filtro di stato fuori vocabolario, booleani non JSON) |
| `E_PREV_STATO_TRANSIZIONE` | 409 | Transizione stato non ammessa |
| `E_PREV_STATO_NON_MODIFICABILE` | 409 | DELETE di un preventivo non BOZZA, con righe o con pratiche collegate (§4b) |
| `E_PREV_RIGA_NOT_FOUND` | 404 | Riga non trovata, o non del preventivo dell'URL |
| `E_PREV_COMPONENTE_NOT_FOUND` | 404 | Componente inesistente o non della riga/preventivo dell'URL |
| `E_PREV_NESSUNA_RIGA` | 400 | Nessuna riga attiva/eleggibile |
| `E_PREV_REVISIONE_ATTIVA` | 409 | Revisione attiva esistente |
| `E_PREV_PRATICA_STATO` | 409 | Stato non ammette generazione pratica |
| `E_PRICING_OVERRIDE_NON_AUTORIZZATO` | 403 | Modifica manuale del prezzo riga non autorizzata (serve azione `prezzo_override_manuale`). L1 del sistema autorizzazioni prezzi. **`retryable=False`**: senza permesso non c'e' nulla da ritentare. Vedi [sviluppo-autorizzazioni-prezzi](../../../dev/work-in-progress/sviluppo-autorizzazioni-prezzi) |
| `E_PRICING_SCONTO_ECCESSIVO` | 403 | Sconto > `VENDITE_MAX_SCONTO_PCT`. **`retryable=True`** (Fase 5.B2): il FE puo' offrire CTA "richiedi approvazione" e ritentare con `richiesta_approvazione=true` (workflow L3) |
| `E_PRICING_MAGGIORAZIONE_ECCESSIVA` | 403 | Maggiorazione > `VENDITE_MAX_MAGGIORAZIONE_PCT`. **`retryable=True`** come sconto eccessivo |
| `E_RIGA_PREZZO_PENDENTE` | 409 | Riga con prezzo in approvazione PENDING: modifica campi struttura bloccata dal trigger DB `trg_preventivi_righe_a10_guard_pending_upd` |
| `E_DOC_COMPOSITO_BOM_VUOTA` | 422 | Articolo composito senza componenti BoM validi alla data del documento. Sollevato da `fn_preventivo_riga_componenti_init` al primo init. **Bloccante**: la riga padre non viene creata (rollback transazionale via `@transaction.atomic`) |
| `E_DOC_COMPONENTE_OBBLIGATORIO` | 400 | Tentativo di disattivare un componente `obbligatorio=TRUE` via `componenti_attivazioni` o DELETE componente. Sollevato dal trigger DB `script.trgfn_componenti_guard_obbligatorio` |
| `E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO` | 400 | Prezzo 0 su componente `obbligatorio=TRUE`. Sollevato da `fn_preventivo_riga_componenti_init` (su `componenti_overrides`) o dal trigger DB `script.trgfn_componenti_check_prezzo_obbligatorio` (su PATCH componente). Componenti opzionali ammettono prezzo 0 |
| `E_DOC_COMPONENTE_LISTINO_MANCANTE` | 422 | Resolver fallito per un componente senza override esplicito. L'operatore deve aggiungere il prezzo manuale in `componenti_overrides` (richiede `prezzo_override_manuale`) o l'admin deve configurare il listino bundle/standalone per quel componente |
| `E_DOCUMENTI_VALIDATION` | 400 | Endpoint §5b + §18: emittente non risolto, sorgente PREVENTIVO non attiva, template assente/non applicabile, MIME allegato non ammesso, size oltre limite. Sollevato da `apps.documenti.api.contesto_helpers.resolve_contesto_documentale` o da `DocumentGenerationService` |
| `E_DOCUMENTI_NOT_FOUND` | 404 | Endpoint §5b + §18: preventivo o documento atteso non trovato dal resolver di contesto |
| `E_VENDITA_PREVENTIVO_PUSH_STATO_NON_AMMESSO` | 409 | §6c genera-ordine: preventivo non `ACCETTATO`. Sollevato dalla fn DB `fn_push_preventivo_a_ordine` |
| `E_VENDITA_PREVENTIVO_NESSUNA_RIGA_ORDINE` | 409 | §6c genera-ordine: nessuna riga **merce** residua da smistare (nessuna riga natura `ORDINE_VENDITA`, o tutte già allocate a un ordine — idempotenza di riga). Sollevato dalla fn DB `fn_push_preventivo_a_ordine` |

> Codici ritirati, non più sollevati: `E_PREV_GIA_IN_COMMESSA` (2026-08-26: annullare
> un preventivo in commessa ora ritira le righe non emesse) ed
> `E_PREZZO_LISTINO_NON_TROVATO` (2026-08-19).

## Integrazione pricing v5

Le righe preventivo usano il building block centralizzato `PricingService.resolve_prezzo` ([catalogo backend §Vendite Pricing v5](../../../dev/backend/catalogo-building-block-backend)) per:

- **Auto-fill** del prezzo quando il payload lo omette (endpoint 8) — resolver 3 stadi: PROMO → CONTRATTO → CATEGORIA
- **Suggerimento diagnostico** pre-compilazione (endpoint 8b) — nessun side-effect
- **Audit override** (endpoint 8/9) — meta JSONB popolato con origine del prezzo, contesto resolver e delta override manuale

Il resolver risolve il prezzo usando BA, utility, data della testata preventivo + emittente derivato dal JWT operatore. Se la testata manca di uno di questi campi (caso legacy), il wiring e' skippato: il prezzo passa come da payload senza check ne' audit.

Per la roadmap L2 (limite sconto via parametri) e L3 (approvazione out-of-policy via pratiche), vedi [sviluppo-autorizzazioni-prezzi](../../../dev/work-in-progress/sviluppo-autorizzazioni-prezzi).

## Form-defaults BA-aware (Fase 2.B4)

Il drawer FE preventivi popola valuta_id/termine_pagamento_id/iva_id automaticamente al cambio BA via `GET /api/v1/vendite/preventivi/form-defaults/?billing_account_id=...`. Risolve dal cliente associato al BA tramite tripletta `(istanza_utility_id, soggetto_ruolo_id, utility_id)`. `valuta_id` segue la catena del BB `resolve_valuta_default` (BA → EF del BA → EF utente → fallback gestore globale), allineata 2026-05-29 alla fn DB `vendite.fn_get_valuta_id`. Vedi [api_vendite_form_defaults.md](api_vendite_form_defaults.md).

