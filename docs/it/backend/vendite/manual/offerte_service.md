# `OfferteService` (Django)

## Scopo

Facade applicativa CRUD per `vendite.offerte_commerciali` + eccezioni
(mirror di `contratti_righe`) + utility 1:1 (estensione `contratti_utilities`),
con gestione della state machine di processo (BOZZA / EMESSA / ACCETTATA /
RIFIUTATA / ANNULLATA / SUPERATA) e propagazione fedele dei codici errore
`E_OFFERTA_*` sollevati dai trigger DB.

## Contesto

L'offerta commerciale e' lo specchio strutturale del contratto: stessa
forma di testata (mono-utility, listino + versione, variazione globale),
stesso enum `tipo_eccezione`, stessa cardinalita' utility (1:1). La
fedelta' garantisce che il push offerta -> contratto in DRAFT sia copia
1:1 senza conversioni (step 8 brief DB, non ancora cablato).

La logica di business autoritativa vive in DB:

- **State machine**: trigger `trgfn_offerte_commerciali_guard_transizione`
  verifica le transizioni contro `config.stati_doc_offerte_transizioni` e
  valorizza i timestamp di transizione + `motivazione_rifiuto`.
- **5 CHECK eccezioni**: replicati con nomi `chk_offerte_eccezioni_*`,
  identici alla logica `contratti_righe`.
- **UNIQUE**: codice offerta, uid, utility 1:1 per offerta, eccezione
  unica per (offerta, articolo, tipo).

Il service e' **sottile**: applica solo pre-condizioni applicative
(stato corrente, payload non vuoto, motivazione obbligatoria su transizioni
negative) e traduce gli errori DB in `ServiceError` con codice originale.

### Perimetro D4 (rev. 2026-05-24d)

Cablati i metodi coerenti con quanto consegnato dal team DB negli step 1-4
+ addendum del brief. **Non** cablati (in attesa step 5-8):

- generazione automatica codice `OFC-*` via `sistema_codici` (step 5)
- `crea_revisione`, `push_a_contratto`, `list_revisioni` (step 7-8)

## Input

### Lookup e dettaglio

- `list_offerte(*, search, billing_account_id, stato_codice_interno,
  utility_id, listino_id, validita_dal_min, validita_dal_max, limit,
  offset, order_by, order_dir) -> (list[OffertaRow], int)`
  - `search` opzionale; vuoto/whitespace-only -> nessun filtro; non vuoto -> min 3 char
  - `order_by` whitelist: vedi `_ORDER_BY_OFFERTE`
- `get_offerta(offerta_id) -> OffertaRow` — arricchito con `eccezioni[]`
  e `utility` (1:1, None se non ancora creato)

### Mutazione testata

- `crea_offerta(payload) -> OffertaRow` — payload richiede `codice`,
  `emittente_fiscale_id`, `billing_account_id`, `istanza_utility_id`,
  `utility_id`, `listino_id`, `validita_dal`. Stato iniziale BOZZA
  risolto via `repo.get_stato_id_by_codice(StatoOfferta.BOZZA)`.
- `aggiorna_offerta(offerta_id, payload) -> OffertaRow` — solo in BOZZA;
  payload `{}` rifiutato.
- `elimina_offerta(offerta_id) -> None` — solo in BOZZA. Pulizia
  tecnica; l'annullamento di processo passa da `annulla`.

### Transizioni di stato

- `emetti(offerta_id) -> OffertaRow` — BOZZA -> EMESSA
- `registra_accettazione(offerta_id) -> OffertaRow` — EMESSA -> ACCETTATA
- `registra_rifiuto(offerta_id, *, motivazione) -> OffertaRow` —
  EMESSA -> RIFIUTATA + motivazione obbligatoria
- `registra_esito(offerta_id, *, esito, motivazione=None) -> OffertaRow` —
  routing unificato per la view: `esito IN ('ACCETTATA', 'RIFIUTATA')`
  delega al metodo specifico
- `annulla(offerta_id, *, motivazione) -> OffertaRow` —
  BOZZA -> ANNULLATA + motivazione obbligatoria

### Mutazione sub-resource

- Eccezioni: `list_eccezioni` (libera), `crea_eccezione` / `aggiorna_eccezione`
  / `elimina_eccezione` (solo BOZZA + ownership URL)
- Utility 1:1: `get_utility` (libera), `crea_utility` / `aggiorna_utility`
  (solo BOZZA + UNIQUE su offerta_id)

## Output

Tutti i metodi di mutazione restituiscono la versione aggiornata della
testata via `get_offerta(offerta_id)` (read-after-write). I metodi
sub-resource restituiscono il record creato/aggiornato (con display
fields da JOIN backend).

Errori sono `ServiceError` con `code` semantico:

- `E_VENDITE_VALIDATION` — struttura payload, payload vuoto, esito non
  valido, motivazione mancante, search < 3 char, order_by fuori whitelist
- `E_VENDITE_NOT_FOUND` — offerta/eccezione/utility non trovata; mismatch
  ownership URL
- `E_VENDITE_DUPLICATO` — UNIQUE violations
- `E_VENDITE_FK` — FK violations
- `E_OFFERTA_*` — codici sollevati dai trigger DB, propagati come `code`
  originale via regex `_DB_ERROR_CODE_RE` sul MESSAGE del trigger

## Regole

1. **Stato BOZZA = unico stato editabile** per testata, eccezioni, utility.
   Defense-in-depth applicativa via `_assert_stato_corrente(expected=_STATI_EDITABILI)`;
   il trigger DB e' guard finale.
2. **Annullamento solo da BOZZA, rifiuto solo da EMESSA**. State machine
   asimmetrica: niente `BOZZA -> RIFIUTATA` (non esiste un "no del cliente"
   prima dell'emissione) ne' `EMESSA -> ANNULLATA` (correzioni
   post-emissione passano da revisione che genera SUPERATA, step 7 DB).
3. **Motivazione obbligatoria** per `registra_rifiuto` e `annulla`:
   stringa non vuota post-strip; whitespace-only rifiutato.
4. **Payload `{}` rifiutato** in tutti i PATCH/UPDATE
   (`_guard_payload_non_vuoto`): niente no-op silenziosi.
5. **Anti-tampering URL** su sub-resource: il service verifica
   `eccezione.offerta_id == offerta_id` (e analogo per utility) prima
   di mutare. Mismatch -> 404 esplicito.
6. **Codici errore DB propagati come `code` originale** (fix critico
   rev. 2026-05-25 analisi codice): senza propagazione il FE non puo'
   discriminare per codice (es. mostrare dialog "versione listino non
   ATTIVA" diverso da "transizione non ammessa"). Estrazione via regex
   `\b(E_[A-Z][A-Z0-9_]+)\b` sul MESSAGE del trigger.
7. **Codice offerta dal payload finche' step 5 DB non chiude**. Dopo
   diventera' generato e immutabile (lock_columns).
8. **Costanti di stato** in `StatoOfferta` (BOZZA/EMESSA/ACCETTATA/
   RIFIUTATA/ANNULLATA/SUPERATA); niente stringhe magiche sparse.

## Dipendenze DB

**Tabelle**:

- `vendite.offerte_commerciali`
- `vendite.offerte_commerciali_eccezioni`
- `vendite.offerte_commerciali_utilities`
- `config.stati_doc_offerte` (lookup id stato per codice_interno)
- `config.stati_doc_offerte_transizioni` (autoritativa per state machine)

**Trigger autoritativi**:

- `trgfn_offerte_commerciali_guard_transizione` — state machine + guard
  versione listino + valorizzazione `data_*` di transizione

**Funzioni** (riservate, non ancora cablate):

- `script.fn_generate_codice('offerta_commerciale')` — step 5 DB
- `vendite.fn_crea_revisione_offerta` — step 7 DB
- `vendite.fn_push_offerta_a_contratto` — step 8 DB

**Helper applicativi** (`apps.core`):

- `apps.core.services.payload_helpers.PayloadValidator` — guard payload
- `apps.core.services.payload_helpers.map_integrity_error` — UNIQUE/FK mapping
- `apps.core.services.error_manager.ErrorManager` — raise/require coerente

## Note di migrazione

- **2026-05-24** — atterraggio step DB 1-4 + addendum (commit `2000d8261`):
  service inizialmente scritto contro questo perimetro (D4 piano BE/FE
  rev. d).
- **2026-05-25 — Analisi critica + ottimizzazioni**:
  - Codici errore `E_OFFERTA_*` del trigger DB ora estratti dal MESSAGE
    e propagati come `code` originale (fix #1 analisi)
  - `_guard_payload_non_vuoto` per evitare no-op silenziosi (fix #3)
  - Helper `_build_insert` / `_build_update` modulo-level in repository:
    6 metodi CRUD ridotti da ~25 righe ciascuno a 3-4 (fix #5)
  - Routing `ACCETTATA`/`RIFIUTATA` spostato in `registra_esito` (fix #6)
  - Costanti `StatoOfferta` + `_STATI_EDITABILI` + `_ESITI_AMMESSI_DA_EMESSA`
    (fix #7: niente stringhe magiche sparse)
  - Suite test 16 -> 26 casi con happy path + propagazione codice DB +
    ownership eccezioni
- **In attesa team DB** (sblocca cantiere BE residuo):
  - Step 5 — `sistema_codici` `OFC-*`: il service generera' il codice e
    rifiutera' il campo dal payload; lo schema OpenAPI cambia di conseguenza.
  - Step 6-7 — trigger revisione + `fn_crea_revisione_offerta`: si
    aggiungeranno `crea_revisione(offerta_id)` (guard EMESSA) e
    `list_revisioni(offerta_padre_id)`.
  - Step 8 — `fn_push_offerta_a_contratto` + ALTER `contratti.offerta_id`:
    si aggiungera' `push_a_contratto(offerta_id, pratica_id?)` con
    idempotenza pattern A.

## Riferimenti

- API: [api_offerte](api_offerte.md)
- Modello: [analisi-offerta-commerciale](/dev/work-in-progress/analisi-offerta-commerciale)
- Brief DB: [analisi-offerta-commerciale-db](/dev/work-in-progress/analisi-offerta-commerciale-db)
- Piano BE+FE: [analisi-offerta-commerciale-be-fe](/dev/work-in-progress/analisi-offerta-commerciale-be-fe)
- Service contratto (specchio strutturale): [contratti_service.py](../../../../backend/apps/vendite/services/contratti_service.py)
