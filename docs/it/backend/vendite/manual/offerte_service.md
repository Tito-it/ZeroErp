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
1:1 senza conversioni (`push_a_contratto`, step 8 brief DB).

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

### Perimetro D6 (rev. 2026-05-25 PM) — completo

Tutti i metodi cablati. Step DB 1-9 atterrati:

- step 1-4 + addendum (commit 2026-05-24): testata, eccezioni, utility 1:1,
  state machine, `motivazione_rifiuto`
- step 5-7 (commit 2026-05-25 AM): codice automatico `OFC-*` via trigger,
  `crea_revisione`, `list_revisioni`
- step 8-9 (commit 2026-05-25 PM): `push_a_contratto` + suite pgTAP
  completa lato DB

Il dominio offerta commerciale lato BE e' **funzionalmente completo**:
restano solo cantieri FE (drawer, dialog, lista) e l'eventuale cablaggio
del building block note partizionate sul nuovo target `OFFERTA`.

## Input

### Lookup e dettaglio

- `list_offerte(*, search, billing_account_id, stato_codice_interno,
  utility_id, listino_id, validita_dal_min, validita_dal_max,
  solo_ultima_revisione=True, limit, offset, order_by, order_dir,
  auth_user_id) -> (list[OffertaRow], int)`
  - `search` opzionale; vuoto, whitespace-only o sotto 3 caratteri -> nessun
    filtro (soglia del BB `add_ricerca_full_condition`)
  - `stato_codice_interno` fuori vocabolario `config.stati_doc_offerte` ->
    `E_VENDITE_VALIDATION` col campo (2026-10-20)
  - `order_by` whitelist: `_ORDER_BY_OFFERTE`, derivata da `_ORDER_COLS_OFFERTE`
    del repository; senza `order_dir` le colonne data e il default `data_insert`
    vanno DESC
  - `auth_user_id`: scope emittente (`None` = nessuna restrizione)
- `get_offerta(offerta_id) -> OffertaRow` — arricchito con `eccezioni[]`,
  `utility` (1:1, None se non ancora creato) e **capability blob**
  (`available_actions[]`, `can_edit_*`, `can_push_contratto*`,
  `non_editable_fields[]`, `stato_codice`) letto da
  `repo.get_available_actions` (wrapper su `script.fn_available_actions_offerta`,
  D7 2026-05-26) e posato **intatto sotto `capabilities`** (dal 2026-09-23:
  fino ad allora era fuso nella testata con `row.update(...)`). Se la funzione
  fallisce, `capabilities` e' `{}`, mai assente. Il FE consuma il blob con `useEntityCapabilities` +
  `mapAvailableActionsToDrawerActions`, eliminando ogni state-machine
  hardcoded lato client.

### Mutazione testata

- `crea_offerta(payload) -> OffertaRow` — payload richiede
  `emittente_fiscale_id`, `billing_account_id`, `istanza_utility_id`,
  `utility_id`, `listino_id`, `validita_dal`. Il `codice` **non va nel
  payload** (rifiutato come unknown_key): lo genera il trigger DB
  `trgfn_offerte_commerciali_gen_codice` (BEFORE INSERT). Stato iniziale
  BOZZA risolto via `repo.get_stato_id_by_codice(StatoOfferta.BOZZA)`.
  **Sub-oggetto opzionale `utility`** (D7, 2026-05-26): se valorizzato,
  `_add_utility_inline` esegue `create_utility` nella stessa
  `transaction.atomic()` della testata, ereditando
  `istanza_utility_id`/`utility_id` dalla testata se non specificati nel
  sub-payload. Niente piu' rischio di "offerta orfana di utility" del
  flusso a 2 round-trip.
- `aggiorna_offerta(offerta_id, payload) -> OffertaRow` — nessun guard di
  stato: quali colonne si cambiano in quale stato lo decide il lock di testata
  del DB (`trgfn_doc_testata_lock_fuori_bozza`, 409 `E_DOC_*` propagato); la
  scheda utility la ferma fuori bozza il lock dei satelliti
  (`E_DOC_DATI_COLLEGATI_NON_BOZZA`). Chiavi fuori `UPDATE_KEYS_OFFERTA` -> 400.
  **Sub-oggetto opzionale `utility`** (D7, simmetria col create):
  `_upsert_utility_inline` distingue create vs update via
  `repo.get_utility(offerta_id)`. Ramo update: chiave fuori
  `CREATE_KEYS_UTILITY` -> 400; poi tiene le sole `UPDATE_KEYS_UTILITY`
  (immutabili `istanza_utility_id`/`utility_id`). Con un cambio di coppia
  cliente la scheda del payload non si applica (la rifà il DB).
  Ramo create: stesso `_add_utility_inline` di sopra. Payload `{}`
  rifiutato; payload con SOLO `utility` (zero campi testata) ammesso ed
  esegue solo l'upsert utility.
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

### Push a contratto (step 8, 2026-05-25 PM)

- `push_a_contratto(offerta_id, *, pratica_id=None, chiudi_esistente=False)
  -> OffertaPushResult` — invoca
  `vendite.fn_push_offerta_a_contratto(p_offerta_id, p_pratica_id,
  p_chiudi_contratto_esistente)`. Guard applicativo `ACCETTATA` (400
  `E_VENDITE_VALIDATION`; il DB e' la rete con
  `E_OFFERTA_PUSH_STATO_NON_AMMESSO`, 409). Con contratto attivo sovrapposto:
  `chiudi_esistente=False` -> `E_CONTRATTO_OVERLAP_ESISTENTE`, `True` -> chiude
  il vecchio per successione. Dopo il push riempie lo slot indirizzo di default
  del contratto se rimasto vuoto.
- `get_contratto_sovrapposto(offerta_id) -> dict | None` — contratto attivo
  sovrapposto (`fn_contratto_sovrapposto`), sola lettura. Pattern A idempotenza:
  doppia chiamata su stessa offerta → `E_OFFERTA_CONTRATTO_GIA_GENERATO`
  propagato come `code` originale. Ritorna `{contratto_id,
  contratto_codice, sorgente_uid}` letto via
  `repo.get_contratto_minimal` (no coupling cross-service).

### Revisioni (step 6-7, 2026-05-25)

- `crea_revisione(offerta_id, *, user=None) -> OffertaRow` — invoca
  `vendite.fn_crea_revisione_offerta(p_offerta_id, p_user)`. Guard
  applicativo `EMESSA` (400 `E_VENDITE_VALIDATION`); il DB e' la rete con
  `E_OFFERTA_REVISIONE_STATO_NON_AMMESSO` (409).
  Ritorna la nuova rev.N+1 (dettaglio completo via `get_offerta`).
- `list_revisioni(offerta_id, *, limit, offset, order_by, order_dir)
  -> (list[OffertaRow], int)` — una **pagina** della catena di revisioni con la
  stessa radice (`revisione_radice_id`), col totale per `paginated_envelope`.
  Ordine di default `revisione_numero` ASC (whitelist
  `OFFERTA_REVISIONI_ORDER_COLUMNS`). Offerta inesistente -> 404. Lettura libera
  in ogni stato.

### Mutazione sub-resource

- Eccezioni: `list_eccezioni` (libera), `crea_eccezione` / `aggiorna_eccezione`
  / `elimina_eccezione` (ownership URL; «solo in bozza» lo dice il lock righe
  del DB, `E_RIGA_DOC_NON_BOZZA`)
- Componenti BoM: `preview_componenti_eccezione`, `list_componenti_eccezione`,
  `update_componente_eccezione` (whitelist operatore `prezzo_unitario`,
  `attivo`, `meta`; prezzo manuale -> gate `prezzo_override_manuale`),
  `delete_componente_eccezione` (soft delete)
- Utility 1:1: `get_utility` (libera), `crea_utility` / `aggiorna_utility`
  (UNIQUE su offerta_id; fuori bozza il lock satelliti del DB)

## Output

Tutti i metodi di mutazione restituiscono la versione aggiornata della
testata via `get_offerta(offerta_id)` (read-after-write). I metodi
sub-resource restituiscono il record creato/aggiornato (con display
fields da JOIN backend).

Errori sono `ServiceError` con `code` semantico:

- `E_VENDITE_VALIDATION` (400) — struttura payload, payload vuoto, esito non
  valido, motivazione mancante, stato errato nei pre-check, filtro di stato
  fuori vocabolario, order_by fuori whitelist
- `E_VENDITE_NOT_FOUND` — offerta/eccezione/utility non trovata; mismatch
  ownership URL
- `E_VENDITE_DUPLICATO` — UNIQUE violations
- `E_VENDITE_FK` — FK violations
- `E_OFFERTA_*` — codici sollevati dai trigger DB, propagati come `code`
  originale via regex `_DB_ERROR_CODE_RE` sul MESSAGE del trigger

## Regole

1. **Chi è editabile in quale stato lo dicono i lock del DB**: testata
   (`trgfn_doc_testata_lock_fuori_bozza`), eccezioni e componenti
   (`trgfn_doc_righe_lock_fuori_bozza`), utility (lock satelliti).
   `_assert_stato_corrente(expected=_STATI_EDITABILI)` resta solo su
   `elimina_offerta` e sulle transizioni che partono da BOZZA.
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
7. **Codice offerta generato dal DB** (trigger `gen_codice`, `OFC-NNNNNNN`):
   nel payload e' rifiutato come chiave sconosciuta.
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

**Funzioni**:

- `script.fn_generate_codice('offerta_commerciale')` — step 5 DB
  (invocata dal trigger BEFORE INSERT, non chiamata direttamente dal service)
- `vendite.fn_crea_revisione_offerta(p_offerta_id, p_user)` — step 7 DB,
  invocata da `repo.crea_revisione`
- `vendite.fn_push_offerta_a_contratto(p_offerta_id, p_pratica_id, p_chiudi_contratto_esistente)` —
  step 8 DB, invocata da `repo.push_a_contratto`

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
- **2026-05-25 AM — Step DB 5-7 atterrati** (commit `13d57a846`):
  - `codice` rimosso dalla whitelist `_CREATE_KEYS_OFFERTA` e da
    `_OFFERTA_CREATE_COLS` (generato dal trigger DB)
  - `crea_revisione(offerta_id, *, user=None)` + `list_revisioni(offerta_id)`
    aggiunti a service e repository, esposti via `POST .../crea-revisione/`
    e `GET .../revisioni/`
  - 6 test happy/fail aggiunti (suite 26 → 32)
- **2026-05-25 PM — Step DB 8-9 atterrati** (commit `906720ac5`):
  - `push_a_contratto(offerta_id, *, pratica_id=None) -> OffertaPushResult`
    aggiunto a service e repository
  - `repo.get_contratto_minimal(contratto_id)` helper per leggere
    `id`/`numero`/`uid` del nuovo contratto senza accoppiare a `ContrattiService`
  - Endpoint `POST .../push-contratto/` con `pratica_id` opzionale nel body
  - Costante `_STATI_PUSHABILI = frozenset({ACCETTATA})`
  - 6 test happy/fail aggiunti (suite 32 → 38) — incluso il caso
    obbligatorio "idempotenza pattern A: doppia invocazione fallisce con
    `E_OFFERTA_CONTRATTO_GIA_GENERATO`" (§6.9.5 pratiche)
- **2026-05-26 — D7 capability layer + atomicita' utility + display fields**
  (consegna DB `20260526-01-create-fn-available-actions-offerta-mctit.yaml`
  e seed `stati_doc_offerte_transizioni.csv` aggiornato con `requires_motivazione`):
  - `repo.get_available_actions(offerta_id)` wrapper su
    `script.fn_available_actions_offerta` (helper `call_jsonb_fn`)
  - `get_offerta` ora include il blob capability (`row.update(...)`):
    pattern speculare a `contratti_service.get_contratto` post Fase 1.B2
  - `crea_offerta` accetta sub-oggetto `utility` opzionale -> nuovo helper
    privato `_add_utility_inline` (atomicita' garantita dalla
    `transaction.atomic()` che incapsula entrambe le scritture). FE
    refactor: rimosso il flusso a 2 round-trip + `.catch(() => null)`
    silenzioso.
  - `aggiorna_offerta` simmetrico: sub-oggetto `utility` opzionale ->
    `_upsert_utility_inline` (create se utility assente, update con
    whitelist `_UPDATE_KEYS_UTILITY` altrimenti). Atomicita' col PATCH
    testata garantita dalla stessa `transaction.atomic()`. Test:
    `test_aggiorna_offerta_con_utility_inline_update_atomico` +
    `test_aggiorna_offerta_con_utility_inline_create_atomico`.
  - SELECT testata: alias rinominati `ba_ragione_sociale -> billing_account_display`,
    `utility_descrizione -> utility_display` (allineamento al piano FE+BE),
    con LEFT JOIN `vendite.contratti.offerta_id` per esporre `contratto_id` /
    `contratto_numero` (idempotenza Pattern A, max 1 contratto per offerta).
  - Cablate note partizionate `target_tipo='OFFERTA'` via
    `apps.core.db.partitioned_note_repository.PartitionedNoteRepository`
    (whitelist `TARGET_TIPI_AMMESSI` + factory `_OFFERTA_REPO` + views).
  - 4 test BE aggiunti (suite 38 → 42).

Dominio offerta commerciale lato BE+FE **completo**.

## Riferimenti

- API: [api_offerte](api_offerte.md)
- Modello: [analisi-offerta-commerciale](/dev/work-done/analisi-offerta-commerciale)
- Brief DB: [analisi-offerta-commerciale-db](/dev/work-done/analisi-offerta-commerciale-db)
- Piano BE+FE: [analisi-offerta-commerciale-be-fe](/dev/work-done/analisi-offerta-commerciale-be-fe)
- Service contratto (specchio strutturale): [contratti_service.py](../../../../backend/apps/vendite/services/contratti_service.py)
