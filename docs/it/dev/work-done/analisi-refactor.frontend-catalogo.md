# Analisi refactor frontend catalogo

<!-- markdownlint-disable MD036 MD031 -->

> **Stato: COMPLETATO (2026-04-28).** Tutte le 8 fasi pianificate sono
> chiuse end-to-end DB+BE+FE. Fase 8 (C4 detail aggregato) esplicitamente
> non implementata per regola YAGNI (nessun profilo perf evidenziava
> bottleneck). Test BE 83/83 verdi, vite build verde. Doc API
> aggiornata a "Fasi 1..8". Documento spostato in `work-done/`.
>
> Obiettivo: identificare cosa nei drawer/store catalogo e' logica di dominio
> mascherata da codice di presentazione, e quindi va spostata su backend/DB
> (filosofia DB-first: il frontend e' solo presentazione + UX).
>
> L'analisi distingue tre categorie:
>
> - **A.** Logica di business da spostare a backend/DB (priorita' alta)
> - **B.** Casi controversi (UX defense-in-depth, refactor cosmetici)
> - **C.** Bug logici di modello / falsi positivi del doc precedente
>
> Riferimenti vincolanti:
>
> - `docs/it/dev/api.md` — contratto API (envelope, command/read, idempotency, lookup vs parameters)
> - `docs/it/dev/backend/catalogo-building-block-backend.md` — building block BE
> - `docs/it/dev/frontend/catalogo-building-block-frontend.md` — building block FE
> - `docs/it/dev/frontend/frontend-standards.md` — pattern obbligatori (filtro data, immutabilita', cessazione data-driven, RowActionsMenu, readonly, ecc.)
>
> Riferimenti modello:
>
> - Pattern `classify EMPTY/PARTIAL/VALID` per payload inline opzionali (refactor anagrafiche Fase 5)
> - Pattern `non_editable_fields` esposto sul detail (refactor anagrafiche Fase 6, B4)
> - Pattern `evento_stato_corrente` data-driven (refactor anagrafiche Fase 4)
> - Pattern cessazione/chiusura data-driven (contratti, listini-versioni, promo articoli)
> - Pattern slot/override per matrici parametri (`feedback_slot_override_matrix`)

---

## Critica al documento precedente

Il documento iniziale individua 14 punti, ma confonde tre cose diverse:
**default UI di comodo**, **regole di dominio replicate in JS**, **standard
condivisi del progetto**. Sintesi della revisione:

| # | Punto originale | Diagnosi corretta |
| --- | --- | --- |
| 1 | `ArticoloDrawer:148` DEFAULT_IVA_ID lato FE | **Falso positivo.** Il valore arriva gia' da `config.parameters` via `useParameterDefaults(['DEFAULT_IVA_ID'])`. Il FE applica solo l'auto-propose nel form di create. Niente da spostare. |
| 2 | `ArticoloDrawer:160` whitelist PATCH (omissione `uom_id`) | **Reale ma cosmetico.** Backend gia' impone `uom_id` immutabile (`_extract_uom_operativa_payload` + DDL lock). Il FE ricalca la stessa regola. Soluzione: esporre `non_editable_fields` sul detail (pattern Fase 6 anagrafiche). |
| 3 | `ArticoliSearchTable:62` disable manage BoM se `!is_composito` | **UX legittima**, dato gia' data-driven (`is_composito` sulla riga). Eventualmente arricchire con `can_manage_bom` + `manage_bom_reason`, ma e' refactor cosmetico. |
| 4 | `ArticoloUomDrawer:46` `roundingOptions` hardcoded | **Vero**, ma c'e' sia un ENUM-like backend (`_ROUNDING_MODE_VALIDI`) sia regole di dominio (binding con `forbid_fraction`). Va esposto come lookup whitelisted (`config.uom_rounding_modes`) o come campo di un endpoint config-resolver dedicato al catalogo. |
| 5 | `ArticoloUomDrawer:54` defaults UoM operativa | **Vero, alta priorita'.** `factor_to_base=1`, `qty_step=1`, `rounding_mode=HALF_UP`, `max_decimals=6`, flags vendita/acquisto/logistica, ecc. sono **policy di dominio** scelte dall'admin, non default UI. Vanno parametrizzati (`config.parameters` con override per emittente) e restituiti dal BE come "form defaults". |
| 6 | `ArticoloUomDrawer:74` watcher `is_base ↔ factor=1` | **Defense-in-depth UX.** DB ha CHECK (vedi `articoli_uom_operativa.md` §1) e service controlla la stessa regola. Il watcher e' UX corretta. Da semplificare leggendo i defaults dal BE, non da rimuovere. |
| 7 | `ArticoloUomDrawer:198` nascondi delete se `is_base` | **Vero.** Va emesso dal BE come `can_delete`/`delete_reason` per riga, simmetrico al pattern azioni-da-API. |
| 8 | `ArticoloBomDrawer:4` pattern immutabilita' codificato in FE | **Vero ma sfumato.** L'immutabilita' e' garantita dal trigger DB `trgfn_articoli_componenti_block_modifica_struttura`. La UX "chiudi+duplica" e' legittima, ma le **azioni consentite** vanno viste dal BE come capability di riga. |
| 9 | `ArticoloBomDrawer:117` defaults BoM | **Vero, alta priorita'.** Come item 5, vanno spostati in `config.parameters` con scope override. |
| 10 | `ArticoloBomDrawer:198` duplica come nuova versione | **Vero, alta priorita'.** Operazione di dominio "versionamento componente": deve essere un **endpoint dedicato** atomico (`POST .../componenti/{id}/duplica-versione/`), non assemblato lato Vue. Riduce race condition tra "chiudi vecchia" + "crea nuova". |
| 11 | `ArticoloBomDrawer:279` default chiusura riga + min-date | **Vero.** Pattern simmetrico a `ChiudiVersioneDialog` listini-versioni: il BE deve esporre `min_close_date` (= `valido_dal`) e `default_close_date` (= oggi/`max(valido_dal, today)`) sul detail riga, oppure validarli a service. |
| 12 | `ConversioneUomDrawer:45` `valido_dal=oggi` di default | **Vero.** Default di processo, da applicare lato BE in create se non fornito. La FE deve solo *presentare* il valore. |
| 13 | `UomConversioniDrawer:82` `uom_from_id` forzato + edit inline solo `fattore` | **UX legittima.** Coerente con il modello di dominio (la conversione sorgente coincide con la UoM contesto). Refactor cosmetico opzionale via `editable_inline_fields` esposto dall'API. |
| 14 | `articoli.js:16` `data_da` default = anno-1 | **Falso positivo.** E' lo **standard di progetto** documentato in `frontend-standards.md` §"Filtro data standard": `default_data_da = ${year-1}-01-01`. Cambiarlo violerebbe l'omogeneita' UI con tutte le altre liste filtrate per data. Niente da spostare. |

In sintesi: 4 **falsi positivi o cosmetici** (1, 14 wholly; 3, 13 cosmetici),
4 **regole di dominio reali da spostare** (5, 9, 10, 12), 5 punti
di **metadata API mancanti** (2, 4, 7, 8, 11), 1 **defense-in-depth**
da preservare (6).

Il documento originale inoltre **non vede tre questioni piu' grosse**:

- **C1.** Whitelist PATCH articolo `ArticoloDrawer.handleSave` cablata (lista
  esplicita di chiavi). Se il modello articolo cambia o si rilascia un nuovo
  campo immutabile, l'UI drifta silenziosamente.
- **C2.** Pulsante **Disattiva articolo** non esiste in FE pur esistendo
  l'endpoint `POST /articoli/{id}/disattiva/`. Invece la "disattivazione" passa
  da `attivo` toggle in form, che bypassa il guard del trigger DB
  `trgfn_prevent_deactivate_if_children` (pattern AS/400-style: figli prima
  del padre). Bug logico potenziale.
- **C3.** Le note articolo + componente nel drawer parent caricano fino a 3
  endpoint in parallelo (`Promise.all` in `loadDetail`). Lecito per UX, ma il
  BE potrebbe esporre un `articolo/{id}/full` (pratica gia' citata in
  building-block-backend per altri domini) per ridurre N+1. Refactor cosmetico,
  bassa priorita'.

---

## A. Logica di business da spostare a backend/DB

> **Nota whitelist lookup**: la whitelist delle relazioni ammesse dal lookup
> generico (`/core/lookup/codici/?rel=...`) e' una **frozenset Python**
> `_REL_CONSENTITE` in `backend/apps/core/db/dbops_repository.py`, **non**
> una tabella DB. Per consentire una nuova `rel` lato API basta aggiungere
> la stringa schema-qualificata al frozenset (no migration DB).

### A1. Defaults di policy UoM operativa esposti come parameters (PRIORITA' ALTA)

- `frontend/src/catalogo/components/ArticoloUomDrawer.vue:54`

  ```js
  function defaultForm() {
    return {
      uom_id: null,
      is_base: false,
      factor_to_base: 1,
      is_sell_uom: false, is_purchase_uom: false, is_logistic_uom: false,
      qty_step: 1, rounding_mode: 'HALF_UP', max_decimals: 6,
      forbid_fraction: false, require_lot: false,
      gtin: '', valido_dal: null, valido_al: null, attivo: true,
    }
  }
  ```

Ogni valore qui dentro e' una **scelta di policy** (es. "di default qty_step
e' 1", "rounding HALF_UP", "max_decimals 6"). Non sono valori UI: se un
emittente vuole `rounding_mode='HALF_EVEN'` per default, l'attuale codice
costringe l'admin a editare ogni nuova UoM operativa.

**Pattern obbligatorio** (vedi `feedback_no_hardcoded_ids` +
pattern `config.parameters` con override per emittente/utente):

- Nuovi parametri seedati in `config.parameters`:
  - `CATALOGO_UOM_OP_DEFAULT_FACTOR_TO_BASE`
  - `CATALOGO_UOM_OP_DEFAULT_QTY_STEP`
  - `CATALOGO_UOM_OP_DEFAULT_ROUNDING_MODE`
  - `CATALOGO_UOM_OP_DEFAULT_MAX_DECIMALS`
  - `CATALOGO_UOM_OP_DEFAULT_FORBID_FRACTION`
- FE consuma via `useParameterDefaults([...])` (gia' building block); il default
  applicato vince override per emittente.
- Override gratuito per utente/gruppo via `config.parameter_overrides` (gia'
  esistente).

### A2. Defaults di policy BoM esposti come parameters (PRIORITA' ALTA)

- `frontend/src/catalogo/components/ArticoloBomDrawer.vue:117`

  ```js
  function defaultForm() {
    return {
      coeff_qta: 1,
      partecipa_qta: true, obbligatorio: true,
      determina_qta_padre: false, esposto_in_fattura: false,
      valido_dal: new Date(), valido_al: null,
    }
  }
  ```

Stessa logica di A1: `partecipa_qta=true`, `obbligatorio=true`, `coeff_qta=1`,
`esposto_in_fattura=false` sono regole operative. Ogni emittente potrebbe
volere defaults diversi (es. utility energia: `partecipa_qta=false` e
`esposto_in_fattura=true` di default per la voce consumo).

**Parametri proposti**:

- `CATALOGO_BOM_DEFAULT_COEFF_QTA`
- `CATALOGO_BOM_DEFAULT_PARTECIPA_QTA`
- `CATALOGO_BOM_DEFAULT_OBBLIGATORIO`
- `CATALOGO_BOM_DEFAULT_DETERMINA_QTA_PADRE`
- `CATALOGO_BOM_DEFAULT_ESPOSTO_IN_FATTURA`

`valido_dal=oggi` non e' un default di policy, e' **decisione di processo**
(qualsiasi nuova versione parte oggi); va applicato al BE in create se assente
(vedi A3).

### A3. Default di processo `valido_dal = oggi` applicato lato service (PRIORITA' MEDIA)

- `frontend/src/catalogo/components/ConversioneUomDrawer.vue:45`
- `frontend/src/catalogo/components/ArticoloBomDrawer.vue:127` (`valido_dal: new Date()`)
- `frontend/src/catalogo/components/UomConversioniDrawer.vue:37` (`valido_dal: new Date()`)

Pattern identico nei 3 punti: il FE prepara `valido_dal=oggi` perche' il BE
oggi non lo applica.

**Refactor**: i tre service `fn_create_componente`, `fn_create_conversione`,
`fn_create_uom_operativa` (per `valido_dal`) devono applicare
`COALESCE(valido_dal, CURRENT_DATE)` lato Python o, ancora meglio, via DDL
default sulla colonna (`DEFAULT CURRENT_DATE`) lato DB. Il FE smette di
toccarlo.

### A4. Endpoint dedicato per "duplica come nuova versione" BoM (PRIORITA' ALTA)

- `frontend/src/catalogo/components/ArticoloBomDrawer.vue:198`
  (funzione `startDuplicaComeNuovaVersione`)

Oggi la duplicazione e' assemblata lato Vue:

1. precompila componente_obj
2. copia coeff_qta/flags/esposto_in_fattura
3. setta `valido_dal = oggi`
4. lascia all'admin la scelta se chiudere la riga sorgente (race condition)

E' un'azione di dominio classica ("crea nuova versione di un componente
chiudendo eventualmente la precedente"). Va esposta come endpoint atomico:

```text
POST /api/v1/catalogo/articoli/{articolo_id}/componenti/{comp_id}/duplica-versione/
Body: { chiudi_precedente_al: <date|null> }
```

Service `fn_duplica_componente_versione`:

- legge la riga sorgente in `FOR UPDATE`,
- chiude la riga sorgente con `valido_al = chiudi_precedente_al` se passato
  (default: `CURRENT_DATE`),
- crea una nuova riga con `valido_dal = chiudi_precedente_al + 1` (no
  sovrapposizione daterange),
- tutto in transazione atomica + Idempotency-Key obbligatoria.

Il FE non riassembla piu' nulla: chiama l'endpoint e ricarica.

### A5. Default IVA e config form articolo via config-resolver (PRIORITA' MEDIA)

`ArticoloDrawer:148` applica `DEFAULT_IVA_ID` da parameters (gia' OK), ma se in
futuro emergono altri default (`tipo_voce_id`, `gruppo_voce_id`,
`listino_tipologia_id`, ecc. specifici per emittente o categoria) la pratica
deve essere coerente: **un solo punto** che restituisce tutti i defaults form.

**Proposta**: estendere il payload del create-form con un endpoint
config-resolver simile ad anagrafiche (`getConfigResolver(...)`). Per ora basta
preparare l'infrastruttura: aggiungere `articoli/form-defaults/` (lookup
dedicato, no paginazione) che ritorna `{default_iva_id, default_tipo_voce_id?,
default_gruppo_voce_id?, default_uom_id?}`.

**Non urgente**, ma il pattern e' stato gia' validato per anagrafiche (Fase 3).

---

## B. Metadata API mancanti — espone capability gia' applicate

Tutti i punti qui sotto sono casi in cui il **backend gia' applica** la regola
(via service, trigger, CHECK) ma il **FE replica la stessa regola** per
costruire l'UI. La fix e' esporre i metadata sull'endpoint detail/list e
consumarli dal FE come dati, non come `if` cablati.

Pattern di riferimento gia' in produzione: **Fase 6 anagrafiche** ha
introdotto `non_editable_fields: str[]` sul detail soggetto consumato dal
SoggettoForm.

### B1. `non_editable_fields` su detail articolo (PRIORITA' MEDIA)

- `frontend/src/catalogo/components/ArticoloDrawer.vue:160-176`

`fn_get_articolo` deve aggiungere `non_editable_fields: ["codice", "uom_id"]`.
Il FE costruisce la whitelist PATCH escludendo questi campi invece di cablarla.

Cosi' quando l'admin DB rilascia un nuovo lock_columns (es. `requires_serial`
post-prima-vendita), il FE si adatta automaticamente. Niente piu' deploy
frontend per allineare la whitelist.

### B2. `roundingOptions` da endpoint lookup (PRIORITA' MEDIA)

- `frontend/src/catalogo/components/ArticoloUomDrawer.vue:46`

L'enum `_ROUNDING_MODE_VALIDI = {UP, DOWN, HALF_UP, HALF_DOWN, HALF_EVEN}` vive
nel service backend (`backend/apps/catalogo/services/catalogo_service.py:67`).
Sono **valori tecnici fissi** (modi di arrotondamento matematici, IEEE 754):
non li gestisce l'admin, non hanno bisogno di audit/storico, non cambiano nel
tempo.

Per questo motivo **non conviene** creare una tabella config dedicata
(`config.uom_rounding_modes`) con tutto il boilerplate (lock_columns,
storicizzazione, seed, lookup whitelist Python). E' over-engineering rispetto
alla regola `feedback_lookup_whitelist_first`, che vale per **dati di config
operativi** (qualifiche, stati, tipi pratiche, ecc.).

**Soluzione preferita** — lookup dedicato statico:

- Endpoint `GET /api/v1/catalogo/lookup/rounding-modes/` (no paginazione).
- View `ApiUomRoundingModesLookup(DomainAPIView)` ritorna un payload statico
  costruito leggendo `_ROUNDING_MODE_VALIDI` come **single source of truth**.
- Risposta: `[{ "codice": "HALF_UP", "descrizione": "Arrotondamento metà su" }, ...]`,
  con descrizioni tradotte (i18n lato BE o codice + lookup i18n lato FE).
- FE consuma via `useGlobalLookup` (cache modulo-level) o un thin wrapper
  `lookupUomRoundingModes()` in `catalogo.js`.

Vantaggi rispetto alla tabella config: nessun migration DB, nessun lock_columns,
single source of truth in Python, nessun rischio di drift fra `_ROUNDING_MODE_VALIDI`
e tabella seedata.

Vedi Fase 1 per i dettagli implementativi.

### B3. `can_delete` + `delete_reason` su righe UoM operativa (PRIORITA' MEDIA)

- `frontend/src/catalogo/components/ArticoloUomDrawer.vue:198`

  ```js
  visible: !row.is_base
  ```

`row.is_base` arriva dal BE, ma la **regola** "is_base ⇒ no delete" e'
duplicata. Il view set `fn_list_uom_operative` deve emettere per ogni riga:

```json
{
  "id": ..., "is_base": true, "factor_to_base": 1.0,
  "can_delete": false, "delete_reason": "UOM_BASE_NON_ELIMINABILE"
}
```

Il FE legge `can_delete` per nascondere/disabilitare l'azione, e mostra
`delete_reason` come tooltip i18n. Stesso pattern per:

- `can_manage_bom` su righe articoli (`ArticoliSearchTable:62`)
- `can_modify_inline` per `valido_al` su righe BoM
- `can_close_riga` su righe BoM

### B4. Capability di riga BoM (`can_close_riga`, `min_close_date`, `default_close_date`)

- `frontend/src/catalogo/components/ArticoloBomDrawer.vue:91-99`, `:280-294`

`chiudiDialogMinDate = parseDate(row.valido_dal)` e
`chiudiDialogData = max(today, valido_dal)` sono regole di policy (la riga
"chiudi" non puo' essere antecedente all'apertura).

`fn_get_componente` (e quindi anche `fn_list_componenti`) deve emettere:

```json
{
  ...,
  "can_close": true,
  "min_close_date": "2026-04-01",
  "default_close_date": "2026-04-28",
  "close_reason": null
}
```

FE rimuove i computed ridondanti e si limita a costruire il dialog dai dati.

### B5. Esponi `non_editable_fields` su conversione UoM (PRIORITA' BASSA)

- `frontend/src/catalogo/components/ConversioneUomDrawer.vue:139,144`,
  `frontend/src/catalogo/components/UomConversioniDrawer.vue:202`

Il drawer disabilita `uom_from_id`/`uom_to_id` in edit (immutabilita'). Stesso
trattamento di B1: il FE deve leggere `non_editable_fields` dal detail
conversione invece di cablare la regola.

---

## C. Bug, falsi positivi del doc, semplificazioni

### C1. Whitelist PATCH articolo cablata — copre B1 (PRIORITA' ALTA)

Vedi B1: e' la stessa cosa, conviene contarli come un'unica fase.

### C2. Toggle `attivo` in form bypassa flusso disattiva/riattiva (PRIORITA' ALTA, bug logico)

- `frontend/src/catalogo/components/ArticoloDrawer.vue:175,294-300`

In edit, l'utente puo' settare `attivo=false` direttamente nel form e salvare.
Il PATCH passa per `fn_update_articolo`, che lo aggiorna sulla colonna
`attivo`. Se l'articolo ha **figli attivi** (`articoli_uom_operativa`,
`articoli_componenti`, righe listino, ecc.), il trigger
`trgfn_prevent_deactivate_if_children` blocca. Ma:

1. L'errore arriva senza messaggio coerente, perche' il PATCH non e'
   l'azione semantica corretta;
2. Esiste `POST /articoli/{id}/disattiva/` (vedi `ApiArticoloDisattiva`) che
   e' la **vera** azione di dominio, ma il drawer non la usa;
3. La riattivazione richiede l'**ordine inverso** (padre poi figli, vedi
   `feedback_disattiva_ordine`), non e' chiaro nel form.

**Refactor**:

- Rimuovere `attivo` come ToggleSwitch dal form articolo.
- Aggiungere pulsante "Disattiva" / "Riattiva" nel header del drawer
  (pattern stato terminale data-driven, vedi `feedback_stato_terminale_con_data`).
- Pulsante chiama `POST /articoli/{id}/disattiva/` o
  `POST /articoli/{id}/riattiva/` (da creare). Stesso schema gia' esistente
  per `ApiUnitaMisuraDisattiva`.
- L'azione cascading (disattiva figli prima) la fa il **service backend**, non
  il FE: stesso pattern del refactor anagrafiche (operatori `disattiva` con
  ordine deterministico).

### C3. Falso positivo del doc precedente — `articoli.js:16` (data_da default) e `ArticoliSearchTable:62` (manage BoM)

Da rimuovere dalla lista degli interventi. Il primo e' lo standard
di progetto, il secondo e' UX legittima. Documentati qui per chiarezza.

### C4. Ridondanza `loadDetail` + 3 chiamate parallele riepilogo (PRIORITA' BASSA)

- `frontend/src/catalogo/components/ArticoloDrawer.vue:113-137`

```js
await Promise.all([loadUomRiepilogo(), loadBomRiepilogo(), loadNoteRiepilogo()])
```

4 round-trip per aprire un articolo in edit. Si potrebbe esporre
`GET /articoli/{id}/full/` che ritorna `articolo + uom + componenti + note`
in un'unica response. Cosmetico, da fare solo se diventa un problema reale.

### C5. Sync `is_base ↔ factor_to_base=1` come watcher FE — preservare

- `frontend/src/catalogo/components/ArticoloUomDrawer.vue:74`

```js
watch(() => form.value.factor_to_base, (val) => {
  form.value.is_base = val === 1
})
```

DB ha CHECK + service controlla. Il watcher e' **defense-in-depth UX**:
nasconde l'errore di submit prevenendolo a digitazione. **Da non rimuovere**.
La stessa filosofia adottata per `B2 canSave` di anagrafiche.

---

## D. Piano di sviluppo

> Ordine di esecuzione concentrico (DB → Backend → Frontend).
> Ogni fase produce un brief in `docs/it/dev/work-in-progress/`
> che migra a `work-done/` al landing.

### Fase 1 — Defaults UoM operativa via parameters (A1) + B2 lookup rounding

**Team DB**

- Migration `80_data` con seed in `config.parameters` (file
  `db/changelog/migrations_v2/80_data/sql/config/parameters.csv`,
  pattern simmetrico a `DEFAULT_IVA_ID` riga 11):
  - `CATALOGO_UOM_OP_DEFAULT_FACTOR_TO_BASE = 1`
  - `CATALOGO_UOM_OP_DEFAULT_QTY_STEP = 1`
  - `CATALOGO_UOM_OP_DEFAULT_ROUNDING_MODE = HALF_UP`
  - `CATALOGO_UOM_OP_DEFAULT_MAX_DECIMALS = 6`
  - `CATALOGO_UOM_OP_DEFAULT_FORBID_FRACTION = false`
- pgTAP: scenario read parametro con cascata override
  (user → group → emittente → default).

**Nessuna tabella `config.uom_rounding_modes`**: come spiegato in B2, i modi
arrotondamento sono enum tecnici fissi (Python `_ROUNDING_MODE_VALIDI` resta
single source of truth).

**Team Backend**

- Lookup dedicato per i rounding modes:
  - Nuova view `ApiUomRoundingModesLookup(DomainAPIView)` con
    `area_funzionale = "catalogo"` (sola lettura, niente scope emittente).
  - URL `catalogo/lookup/rounding-modes/` in `apps/catalogo/api/urls.py`.
  - Handler ritorna lista statica `[{codice, descrizione, ordering}]` costruita
    dalla costante `_ROUNDING_MODE_DESCRIZIONI` (single source of truth col
    set di validazione `_ROUNDING_MODE_VALIDI` — invariante coperta da test
    `test_fn_list_uom_rounding_modes_coverage`). Descrizioni in italiano
    hardcoded nel BE, coerentemente con `note_stili`/`qualifiche`/altri config
    (lingua del progetto = it-IT, descrizioni cfg sempre dal BE).
- Whitelist FE no-op (lookup dedicato non passa dal frozenset
  `_REL_CONSENTITE`).
- Defaults parameters: nessuna modifica al service, il FE legge i parametri
  via `fetchParameterDefaults` (gia' building block in `apiCore.js`). Eventuale
  test smoke che verifica che i 5 nuovi codici arrivano dall'endpoint
  `/core/parameters/defaults/?codes=CATALOGO_UOM_OP_DEFAULT_FACTOR_TO_BASE,...`.

**Team Frontend**

- `frontend/src/catalogo/api/catalogo.js`: aggiungere
  `lookupUomRoundingModes()` che chiama `/catalogo/lookup/rounding-modes/`.
- Nuovo wrapper `frontend/src/catalogo/components/RoundingModeSelect.vue`
  che incapsula `useGlobalLookup` con chiave `catalogo.uom_rounding_modes`
  e usa `lookupUomRoundingModes`. Display `"descrizione (codice)"`. Transform
  custom `(r) => r.data.data` perche' l'endpoint ritorna lista nuda (non
  envelope paginato).
- Nuovo modulo `frontend/src/core/utils/parameterCast.js` con helper
  `paramBool` / `paramNumber` / `paramInt` / `paramString`. Centralizzano il
  cast da `dict[str, str]` (envelope `ParameterService.get_defaults`) ai tipi
  attesi dal form, con fallback resiliente. Riusabile da Fasi successive.
- `ArticoloUomDrawer.vue`: rimosso `roundingOptions` hardcoded; sostituito
  con `<RoundingModeSelect v-model="form.rounding_mode" />`. `defaultForm()`
  legge i defaults da `useParameterDefaults([...5 codici...])` con cast via
  `paramBool` / `paramNumber`. Race-fix: `watch(props.visible)` await-a
  `loadDefaults()` prima di costruire il form (evita form costruito con
  fallback hardcoded mentre la fetch e' in volo).
- Chiave i18n `catalogo.select_rounding_mode` aggiunta a `it.json`/`en.json`.

**Dipendenze**: DB indipendente (solo seed). BE indipendente (lookup view +
URL). FE attende sia il merge BE (lookup endpoint) sia il merge DB (parametri
seedati visibili da `/core/parameters/defaults/`). **Fallback FE**: se i
parametri sono assenti, gli helper `paramBool`/`paramNumber` cadono sui
fallback hardcoded che replicano il comportamento pre-refactor (zero
regressione fino al merge DB).

---

### Fase 2 — Defaults BoM via parameters (A2) + capability di riga (B4)

**Team DB** — landed 2026-04-28 (branch `dev/db-tid`, pre-push):

- 5 seed `config.parameters` id 22-26:
  `CATALOGO_BOM_DEFAULT_COEFF_QTA=1`, `CATALOGO_BOM_DEFAULT_PARTECIPA_QTA=true`,
  `CATALOGO_BOM_DEFAULT_OBBLIGATORIO=true`, `CATALOGO_BOM_DEFAULT_DETERMINA_QTA_PADRE=false`,
  `CATALOGO_BOM_DEFAULT_ESPOSTO_IN_FATTURA=false`.
- Migration `20260428-02`: ALTER COLUMN `articoli_componenti.partecipa_qta SET
  DEFAULT true` (allinea il default DDL al parameter, cosi' insert SQL diretti
  da admin/cron/fixture pgTAP rispettano la stessa policy del backend service).
  Nessun backfill — solo INSERT futuri.
- Migration `20260428-03`: estensione `catalogo.vw_articoli_componenti_dettaglio`
  con 4 campi calcolati (**naming italiano**, coerente coi campi esistenti
  della vista `prodotto_codice`, `valido_dal`, ecc.):
  - `puo_chiudersi BOOLEAN` (= `valido_al IS NULL`)
  - `data_min_chiusura DATE` (= `valido_dal` se `puo_chiudersi`, altrimenti `NULL`)
  - `data_default_chiusura DATE` (= `GREATEST(valido_dal, CURRENT_DATE)` se
    `puo_chiudersi`, altrimenti `NULL`)
  - `motivo_non_chiudibile TEXT` (oggi unico codice: `RIGA_GIA_CHIUSA`,
    snake-upper senza prefisso `E_*`)
- Su righe **non chiudibili** i campi `data_*_chiusura` sono **NULL** (scelta
  autodocumentante: il FE non puo' aprire dialog di chiusura su valori NULL).
- `attivo` ortogonale a `puo_chiudersi`: una riga `attivo=false` con
  `valido_al IS NULL` resta temporalmente chiudibile. Il FE puo' filtrare le
  inattive a livello di lista, ma non tramite `puo_chiudersi`.
- pgTAP: 13 test parameters cascade + 12 test capability vista (3 scenari × 4 campi).

**Team Backend** — landed 2026-04-28 (branch `dev/backend-tid`):

- `CatalogoBomRepository.COMPONENTE_DETAIL_COLUMNS` (`db/catalogo_bom_repository.py`)
  estesa con i 4 campi calcolati **inline** via SQL `CASE WHEN ac.valido_al IS NULL ...`.
  Stessa logica della vista DB (single source of truth lato dominio); duplicazione
  controllata e documentata in commento (drift visibile, vista DB resta valida
  per tool/report manuali). Non e' stato migrato il repository alla vista perche'
  questa post-19-01-2026 non include `determina_qta_padre`/`esposto_in_fattura`,
  letti dalla tabella; mantenere il JOIN diretto evita di perdere quei campi.
- Test API `test_get_articolo_componenti_capability_ok`: verifica pass-through
  dei 4 campi su scenario riga aperta + riga chiusa.

**Team Frontend** — landed 2026-04-28 (branch `dev/backend-tid`):

- `ArticoloBomDrawer.vue:defaultForm()` legge i 5 defaults via
  `useParameterDefaults([...])` con cast `paramBool` / `paramNumber` (helper
  centrali in `core/utils/parameterCast.js`). Race-fix: `watch(props.visible)`
  await-a `loadDefaults()` prima di costruire il form.
- `valido_dal: new Date()` resta lato FE: e' un default di **processo** (la
  nuova versione parte da oggi), non di policy. Sara' delegato al BE in Fase 4.
- Dialog "chiudi riga": `chiudiDialogMinDate` letto da `row.data_min_chiusura`,
  `chiudiDialogData` inizializzato da `row.data_default_chiusura`. Eliminato
  ricalcolo client-side `dal && dal > today ? dal : today`.
- `buildRigaActions`: voce `chiudi-riga` ha `visible: row.puo_chiudersi === true`
  (autodocumentante, niente ricorso a `valido_al`). Visibilita' guidata dalla
  capability BE.
- Edit inline `valido_al` (cella DataTable): clic abilitato solo se
  `data.puo_chiudersi`, altrimenti sola visualizzazione. Coerente con
  l'azione "chiudi riga".
- Nessuna chiave i18n nuova: il `motivo_non_chiudibile` non e' mostrato in UI
  (l'azione sparisce, autodocumentante perche' `valido_al` e' valorizzato).
  Eventuale tooltip esplicito potra' arrivare se nascono nuovi codici motivo
  non self-evident come `RIGA_GIA_CHIUSA`.

**Dipendenze**: DB indipendente (seed parameters + estensione vista). BE
indipendente (proiezione SQL inline replicata, niente attesa migration vista).
FE attende solo BE (proiezione campi + endpoint parameters disponibile).
Fallback hardcoded preserva il comportamento pre-refactor finche' il merge DB
non e' applicato.

---

### Fase 3 — Endpoint atomico "duplica versione componente" (A4)

**Team DB** — landed 2026-04-28 (commit `90b4609f`):

- Funzione `catalogo.fn_duplica_componente_versione(p_articolo_id UUID,
  p_componente_row_id UUID, p_chiudi_al DATE DEFAULT NULL) RETURNS UUID`:
  - `pg_advisory_xact_lock(hashtext('catalogo.articoli_componenti.duplica:'||p_articolo_id))`
    serializza duplicazioni concorrenti sullo stesso articolo,
  - `SELECT FOR UPDATE` riga sorgente,
  - guard ordinati: `E_BOM_RIGA_NOT_FOUND` → `E_BOM_PRODOTTO_MISMATCH` →
    `E_BOM_SORGENTE_GIA_CHIUSA`,
  - UPDATE `valido_al = COALESCE(p_chiudi_al, CURRENT_DATE)` sulla sorgente
    (edge case `chiudi_al < valido_dal` → `E_BOM_VALIDO_AL_INVALIDO`
    propagato dal trigger esistente `block_modifica_struttura`),
  - INSERT nuova riga con `valido_dal = COALESCE(p_chiudi_al, CURRENT_DATE) + 1`,
    copia verbatim di `componente_id`+struttura+`meta`+`note_*`, `attivo=true` forzato,
  - `EXCEPTION WHEN exclusion_violation` → `E_BOM_VERSIONE_OVERLAP`.
- 4 nuovi codici in `config.messaggi_errore` (id 400-403):
  - `E_BOM_VERSIONE_OVERLAP` (400) — overlap su EXCLUDE GIST
  - `E_BOM_SORGENTE_GIA_CHIUSA` (401)
  - `E_BOM_RIGA_NOT_FOUND` (402)
  - `E_BOM_PRODOTTO_MISMATCH` (403)
  - Riusato: `E_BOM_VALIDO_AL_INVALIDO` (388, propagato dal trigger).
- pgTAP: 9 test (6 happy + sorgente_chiusa + non_esistente + prodotto_mismatch).
  Scenario `E_BOM_VERSIONE_OVERLAP` non riproducibile in pgTAP single-session:
  path `EXCEPTION` verificato via code-review.
- Doc concettuale completa: `docs/it/dbzero/catalogo/manual/fn_duplica_componente_versione.md`.

**Team Backend** — landed 2026-04-28 (branch `dev/backend-tid`):

- Registrate 5 policy errore in `core/services/error_policies.py`
  (`E_BOM_VERSIONE_OVERLAP`/`SORGENTE_GIA_CHIUSA`/`RIGA_NOT_FOUND`/`PRODOTTO_MISMATCH`/`VALIDO_AL_INVALIDO`)
  con HTTP coerente (409/409/404/400/400) e `ui_action` parlante.
- `CatalogoBomRepository.duplica_versione(articolo_id, comp_id, chiudi_al)`:
  wrapper `SELECT catalogo.fn_duplica_componente_versione(...)`. Ritorna l'UUID
  della nuova riga.
- `catalogo_service.fn_duplica_componente_versione(articolo_id, comp_id, payload)`:
  whitelist payload `{chiudi_al?}`, parsing ISO date, chiama repository,
  ritorna `get_componente()` della NUOVA riga (UI: focus + reload).
  Errori P0001 tradotti via `_DUPLICA_DB_ERROR_MARKERS` con marker
  multi-substring (pattern simmetrico a `pricing_service`): codice di dominio
  preservato; fallback `E_CATALOGO_VALIDATION` per P0001 sconosciuti.
- View `ApiArticoloComponenteDuplicaVersione(DomainAPIView)`:
  - URL `articoli/<uuid:articolo_id>/componenti/<uuid:comp_id>/duplica-versione/`,
  - `handle_post_json(require_idempotency_key=True)`,
  - schema OpenAPI inline.
- 8 test mock-only: 1 happy + 1 chiudi_al passed + 1 chiave non whitelisted +
  4 traduzioni P0001 noti + 1 fallback P0001 sconosciuto + 3 API
  (happy/idempotency-required/db-error). Tutti verdi (catalogo: 68/68).

**Team Frontend** — landed 2026-04-28 (branch `dev/backend-tid`):

- `catalogo.js`: nuova `duplicaComponenteVersione(articoloId, compId, payload)`
  con header `Idempotency-Key: crypto.randomUUID()` (UUID v4 nativo browser).
- `ArticoloBomDrawer.vue` refactor sostanziale:
  - **Rimosso** `startDuplicaComeNuovaVersione` (pre-fill form race-prone).
  - **Rimosso** `formMode` ref (`'new' | 'duplicate'` non piu' necessario).
  - **Aggiunto** dialog dedicato "Duplica versione" con DatePicker `chiudi_al`
    (default oggi, min-date = `data_min_chiusura` dal BE), info esplicita
    sul comportamento atomico, conferma chiama `duplicaComponenteVersione`
    e ricarica.
  - `buildRigaActions`: voce `duplica-nuova-versione` rinominata
    `duplica-versione`, `visible: !!row.puo_chiudersi` (coerente con
    `chiudi-riga` e inline edit `valido_al`).
- 7 nuove chiavi i18n (`catalogo.duplica_versione_*`) in `it.json`/`en.json`.
  Rimosse `nuova_versione_componente`/`nuova_versione_hint` non piu' usate.

**Decisioni divergenti dal brief originale**

- **No edit dei valori durante la duplica**: il pre-fill+edit FE era
  race-prone; l'endpoint atomico DB copia verbatim. Per cambiare valori,
  il pattern e' `chiudi-riga + Aggiungi componente` (azioni intenzionali,
  gia' supportato).
- **Codici errore esposti distintamente** (E_BOM_*) invece di tradurre tutto
  in `E_CATALOGO_VALIDATION`: il FE puo' mostrare messaggi specifici
  (sorgente chiusa, overlap, prodotto mismatch).

**Dipendenze**: DB → BE → FE in serie. Tutto landed.

---

### Fase 4 — Default `valido_dal` lato service (A3) — landed 2026-04-28 BE-only

**Team DB** — declined:

Scelta di team: **non** modificare il DDL `DEFAULT CURRENT_DATE`. L'onere
del fallback resta nel service Python (single source of truth). Coerente con
filosofia "regole di processo nel service, regole di integrita' nel DB":
"valido_dal di una riga BoM/UoM/Conversione e' obbligatorio nel modello"
resta una regola di processo, non un'integrita' DB.

**Team Backend** — landed 2026-04-28 (branch `dev/backend-tid`):

- `_extract_componente_payload` (per_create): `valido_dal` declassato da
  `nullable=False` a `nullable=True`; se omesso o `None`, applica
  `date.today()` **prima** di `_validate_date_interval` (cosi' la coerenza
  con `valido_al` e' verificata sul valore effettivo, non `_MISSING`).
- `_extract_uom_operativa_payload` (per_create): stesso pattern.
- `fn_create_conversione`: stesso pattern (qui il payload non passa per un
  helper extract dedicato, fallback applicato inline).
- Pattern unificato: `if not for_update and (valido_dal is _MISSING or valido_dal is None): valido_dal = date.today()`.
- Whitelist payload create componente non cambia: `valido_dal` resta una
  chiave ammessa ma non obbligatoria.
- 3 test mock-only: `test_fn_create_componente_valido_dal_fallback_today`,
  `test_fn_create_uom_operativa_valido_dal_fallback_today`,
  `test_fn_create_conversione_valido_dal_fallback_today`.

**Team Frontend** — landed 2026-04-28:

- `ArticoloBomDrawer.vue:defaultForm()`: `valido_dal: null` (era `new Date()`).
- `ConversioneUomDrawer.vue:resetForm`: `valido_dal: null` (era `new Date()`).
- `UomConversioniDrawer.vue`: estratto helper `defaultForm()` per eliminare
  4 occorrenze duplicate dello stato iniziale `{uom_to_id, fattore, valido_dal}`,
  centralizzando `valido_dal: null` in un unico posto.
- DatePicker mostra placeholder vuoto se `null`: l'utente sa che il default
  arriva dal server (UX piu' onesta del pre-fill cliente).

**Decisioni divergenti dal brief originale**

- **DB declined il DDL change**: il fallback vive solo lato service, non in
  DDL. Implicazione: insert SQL diretti (cron, fixture pgTAP, manutenzione
  admin) richiedono ancora `valido_dal` esplicito — il service e' l'unica
  via "magica". Decisione consapevole: tutti i path di scrittura per
  catalogo passano dal service Django, no SQL diretti in produzione.
- **Fallback dentro l'extract, non nella fn_create**: il guard
  `valido_dal obbligatorio` originale impediva al fallback nella fn_create
  di attivarsi. Spostarlo dentro l'extract risolve sia il guard che la
  validazione coerenza con `valido_al` in un singolo posto.

**Dipendenze**: BE indipendente (DB declined). FE solo dopo merge BE.

---

### Fase 5 — `non_editable_fields` cross-entita' catalogo (B1, B5, C1) — landed 2026-04-28

**Team DB** — landed 2026-04-28:

- Nuova vista `dbops.vw_non_editable_fields` come alias semantico su
  `dbops.automation_lock_columns` filtrata `enabled=true`. Espone
  `(target_schema, target_table, column_name, error_code, exec_mode, note)`.
  Filtro su flag attivo; **non copre i lock condizionali stato-dipendenti**
  gestiti da trigger custom (gap noto, vedi sotto).

**Team Backend** — landed 2026-04-28 (branch `dev/backend-tid`):

- Nuovo `apps/core/db/lock_columns_repository.py`:
  `LockColumnsRepository.list_non_editable(schema, table) -> tuple[str, ...]`,
  cache `lru_cache(128)` (la vista cambia solo con migrazioni Liquibase, niente
  mutazioni runtime). Riusabile cross-dominio.
- `catalogo_service._NON_EDITABLE_DB_GAPS`: dict che documenta esplicitamente
  le colonne immutabili **non coperte** dalla vista DB ma richieste dal FE
  (lock condizionali / non ancora registrati nel CSV `automation_lock_columns`):
  - `("catalogo", "articoli")`: `("codice",)` — gestito dal trigger
    `trgfn_articoli_protect_codice`, non in CSV.
  - `("catalogo", "articoli_uom_operativa")`: `("uom_id",)`.
  - `("catalogo", "unita_misura_conversioni")`: `("uom_from_id", "uom_to_id")`.
  - **Drift visibile**: quando il team DB completera' il registro, le entries
    qui andranno rimosse. Self-documenting nel codice.
- `_compute_non_editable_fields(schema, table) -> list[str]`: helper centrale
  che unisce lista DB + gap Python e restituisce la lista ordinata.
- `fn_get_articolo`: detail arricchito con `non_editable_fields` (auto
  propagato da `fn_create_articolo`/`fn_update_articolo`/`fn_disattiva_articolo`
  che gia' richiamano `fn_get_articolo`).
- `fn_list_uom_operative`: envelope arricchito con `non_editable_fields`
  (envelope-level: il FE costruisce il form di edit da una riga della lista,
  ha bisogno dei metadata appena dopo la chiamata lista).
- `fn_create_uom_operativa` / `fn_update_uom_operativa`: response singola riga
  arricchita anche, per consistenza.
- `fn_get_conversione`: detail arricchito (auto propagato da create/update).
- 3 test mock-only: articolo / lista UoM operativa / conversione, mockando
  `LockColumnsRepository.list_non_editable` per evitare query DB nel testbed.

**Team Frontend** — landed 2026-04-28 (branch `dev/backend-tid`):

- `ArticoloDrawer.vue`:
  - `nonEditableFields` computed da `detail.non_editable_fields`.
  - `isFieldLocked(name)` helper: `isEdit && nonEditableFields.includes(name)`.
  - `:disabled="isFieldLocked('codice')"` e `:disabled="isFieldLocked('uom_id')"`
    sostituiscono il `:disabled="isEdit"` cablato per campi specifici.
- `ArticoloUomDrawer.vue`:
  - `nonEditableFields` ref popolato da `payload.non_editable_fields`
    nell'envelope di `listArticoloUom`.
  - `isFieldLocked(name)`: `formMode === 'edit' && nonEditableFields.includes(name)`.
  - `:disabled="isFieldLocked('uom_id')"` sulla LookupSelect UoM.
- `ConversioneUomDrawer.vue`:
  - `nonEditableFields` popolato in `loadDetail` da `data.non_editable_fields`.
  - `:disabled="isFieldLocked('uom_from_id')"` / `'uom_to_id'`.
- Whitelist payload PATCH lascia esplicita la lista di campi (codice/uom_id
  esclusi a mano): rimangono coerenti con `non_editable_fields` ma il drift
  e' enforced anche dal BE (`_extract_*_payload` rifiuta chiavi non
  whitelisted). Il vero source of truth e' BE; il FE usa
  `non_editable_fields` per UX (`:disabled`), non per filtraggio payload.

**Decisioni divergenti dal brief originale**

- **Vista DB invece di whitelist Python**: il team DB ha preferito esporre
  i lock_columns come vista DB (single source of truth dal CSV). Il pattern
  e' piu' robusto a lungo termine (registro DB cresce naturalmente con le
  migrazioni). Lo svantaggio e' il gap noto (lock condizionali) che richiede
  il fallback Python.
- **Envelope-level su lista UoM operative**: `non_editable_fields` come
  metadata della collezione, non per ogni riga. La regola e' la stessa per
  tutte le righe della stessa entita': duplicarla per riga e' rumore.
- **Whitelist payload non auto-derivata**: il FE mantiene la lista esplicita
  dei campi PATCH, il BE rifiuta i campi non whitelisted. Doppio enforcement
  e' difese-in-depth, non duplicazione di logica.

**Gap aperti (non bloccanti)**

- Il registro DB `dbops.automation_lock_columns` non copre i lock
  condizionali (es. `catalogo.articoli.codice`). Quando il team DB completera'
  il registro, le entries in `_NON_EDITABLE_DB_GAPS` vanno rimosse.
- Eventuale arricchimento futuro: aggiungere `non_editable_reason` per riga
  (utile per tooltip i18n). Out-of-scope per Fase 5.

**Dipendenze**: DB → BE → FE in serie. Tutto landed.

---

### Fase 6 — Capability di riga `puo_eliminarsi`/`puo_gestire_bom` (B3) — landed 2026-04-28

**Team DB (consegnato)**

- `vw_articoli_uom_operativa_dettaglio` aggiornata: aggiunge denormalizzazioni
  `uom_codice`/`uom_descrizione`, `articolo_codice`/`articolo_descrizione` +
  capability di riga
  - `puo_eliminarsi BOOLEAN` (= `NOT is_base`)
  - `motivo_non_eliminabile TEXT` (`'UOM_BASE_NON_ELIMINABILE'` quando
    `is_base`, altrimenti `NULL`)
- `vw_articoli_dettaglio` estesa con capability BoM:
  - `puo_gestire_bom BOOLEAN` (= `is_composito AND NOT is_solo_componente`)
  - `motivo_non_gestibile_bom TEXT` (`'ARTICOLO_SOLO_COMPONENTE'` se
    `is_solo_componente`, `'ARTICOLO_NON_COMPOSITO'` se `NOT is_composito`,
    altrimenti `NULL`)

**Naming italiano vs brief inglese.** Il brief proponeva `can_delete`/
`delete_reason`/`can_manage_bom`/`manage_bom_reason`. Il team DB ha
consegnato in italiano, coerente con il pattern Fase 2 BoM
(`puo_chiudersi`/`motivo_non_chiudibile`). Naming uniforme: tutto il
catalogo usa la convenzione italiana per le capability.

**Chiarificazione "figli" nel brief originale.** Il primo brief
proponeva `can_delete = NOT is_base AND NOT EXISTS (figli...)`. Verifica
sul modello: `articoli_uom_operativa.id` non e' referenziato da FK
reverse. Le righe listino/magazzino/documenti tengono `uom_id` su
`catalogo.unita_misura` (anagrafica), non sulla mappatura operativa per
articolo. "Figli" era un'astrazione preventiva, rimossa dal brief.
Eventuali guard cross-dominio si aggiungono in iterate successive se
emerge un caso d'uso concreto.

**Team Backend (landed)**

- `CatalogoRepository.list_articoli` e `get_articolo` proiettano
  `puo_gestire_bom`/`motivo_non_gestibile_bom` da `vw_articoli_dettaglio`
  (aggiunti a `ARTICOLI_DETAIL_COLUMNS`, propagati in automatico).
- `CatalogoUomRepository.list_uom_operative` e `get_uom_operativa`
  passano a leggere da `vw_articoli_uom_operativa_dettaglio` (single
  source of truth per join + capability), proiettano `puo_eliminarsi`/
  `motivo_non_eliminabile`.
- 2 nuovi test in `test_catalogo_service.py` (#45, #46): coverage
  propagazione capability via service.

**Team Frontend (landed)**

- `RowActionsMenu.vue` esteso: campo opzionale `tooltip` per azione
  (sovrascrive `label` come tooltip del bottone inline). Retrocompatibile,
  utile per spiegare il motivo di un disabled.
- `ArticoliSearchTable.vue:64`: action manage-bom con `disabled:
  !data.puo_gestire_bom` + `tooltip: manageBomTooltip(data)` derivato da
  `motivo_non_gestibile_bom`.
- `ArticoloUomDrawer.vue:225`: action delete con `disabled:
  !row.puo_eliminarsi` + `tooltip: deleteUomTooltip(row)` derivato da
  `motivo_non_eliminabile`. Cambio UX rispetto al brief: l'azione resta
  visibile (non nascosta su `is_base`) per mantenere l'affordance e
  mostrare il motivo via tooltip — coerente con pattern Fase 2 di
  capability di chiusura riga BoM.
- 3 chiavi i18n nuove in `it.json`/`en.json`:
  `catalogo.motivo_uom_base_non_eliminabile`,
  `catalogo.motivo_articolo_solo_componente`,
  `catalogo.motivo_articolo_non_composito`.

**Esiti.** 76/76 test catalogo verdi (74 + 2 nuovi). Vite build verde
925ms. Naming italiano consolidato cross-vista.

**Dipendenze**: DB ↔ BE ↔ FE in serie. Tutte chiuse.

---

### Fase 7 — Disattiva/Riattiva articolo come azione di dominio (C2) — landed 2026-04-28

**Team DB**

- Verifica `trgfn_prevent_deactivate_if_children` su `catalogo.articoli`
  (probabile gia' presente per pattern AS/400). Se manca, aggiungerlo.
- Nuova fn `catalogo.fn_riattiva_articolo(p_articolo_id UUID)` che fa solo
  `UPDATE attivo=TRUE WHERE id=...` (i figli rimangono inattivi: il padre
  prima, i figli poi, in azioni separate, come da pattern operatori).
- pgTAP: disattiva → trigger blocca se figli attivi; riattiva → padre torna
  attivo, i figli no.

**Team Backend**

- `fn_riattiva_articolo(articolo_id)` simmetrico a `fn_disattiva_articolo`.
- Nuova view `ApiArticoloRiattiva` registrata in `urls.py`:
  - `articoli/<uuid:articolo_id>/riattiva/`
- `fn_update_articolo` rimuove `attivo` dalla whitelist (la disattivazione
  passa solo dall'endpoint dedicato). Aggiornare test articolo update per
  rispondere `E_CATALOGO_VALIDATION` se `attivo` arriva nel payload.

**Team Frontend**

- `ArticoloDrawer.vue:295-300`: rimuovere ToggleSwitch `attivo`.
- Aggiungere pulsanti header `Disattiva` / `Riattiva` con classe `app-escape`
  (pattern `feedback_stato_terminale_con_data`). I pulsanti mostrano un
  dialog di conferma (`useConfirmAction`).
- Pulsante chiama lo store: `store.disattiva(id)` (gia' esiste) o
  `store.riattiva(id)` (da aggiungere).

**Esiti.**

- DB: `catalogo.fn_riattiva_articolo(uuid)` consegnata, idempotente, raise
  `E_ARTICOLO_NOT_FOUND` se id NULL/inesistente. Disattivazione resta UPDATE
  diretto coperto da `trgfn_prevent_deactivate_if_children`.
- BE:
  - `CatalogoRepository.reactivate_articolo` chiama la fn DB.
  - `fn_riattiva_articolo(articolo_id)` simmetrico a disattiva: pre-flight
    `fn_get_articolo` (uniforma il NOT_FOUND con `E_CATALOGO_ARTICOLO_NOT_FOUND`),
    short-circuit se gia' attivo.
  - `ApiArticoloRiattiva` su `POST .../articoli/{id}/riattiva/`.
  - Whitelist update articolo: rimosso `attivo`. Guard esplicita in
    `_extract_articolo_payload(for_update=True)`: PATCH con `attivo` →
    `E_CATALOGO_VALIDATION` con detail "usa /disattiva/ o /riattiva/".
  - 4 nuovi test (#47-#50) — riattiva ok/already_active/not_found + update
    rifiuta attivo.
- FE:
  - `riattivaArticolo` in `api/catalogo.js`, `riattiva` action nello
    store articoli.
  - `ArticoloDrawer`: rimosso `ToggleSwitch attivo` e `attivo` da defaultForm/
    loadDetail/payload PATCH. Sezione "Stato articolo" con `Tag` + pulsante
    contestuale (Disattiva se attivo, Riattiva se inattivo) gated su
    `!isReadonly`. `useConfirmAction.confirmAction` con messaggio dedicato
    che spiega il pattern "padre prima, figli poi".
  - 9 chiavi i18n nuove (it/en) per stato, label, dialog title/message,
    toast success.

**Dipendenze**: DB → BE → FE. Breaking lato API: PATCH con `attivo` rifiutato.
In ZeroErp non in produzione, breaking ammessi.

---

### Fase 8 — Refactor opzionali (C4, A5, B5 cosmetico) — landed 2026-04-28 (A5 only)

**Team DB**: nessuna modifica.

**Team Backend (landed A5)**

- `fn_get_articolo_form_defaults(*, django_user_id, group_ids,
  emittente_fiscale_id)` in `catalogo_service.py`: chiama
  `ParameterService.get_defaults(["DEFAULT_IVA_ID"])`, casta a `int`,
  ritorna `{"default_iva_id": int | None}`. Best-effort: parametro
  malformato → `None` (no raise).
- `ApiArticoliFormDefaults` su `GET .../articoli/form-defaults/`. Riusa
  `get_user_context(request, ParameterService())` (rinominato da
  `_get_user_context` a pubblico per riuso cross-modulo) per superuser
  bypass + override emittente/utente.
- 3 nuovi test (#51-#53) — ok / param mancante / param malformato.

**Team Frontend (landed)**

- `getArticoloFormDefaults()` in `api/catalogo.js`.
- `ArticoloDrawer`: rimosso `useParameterDefaults(['DEFAULT_IVA_ID'])` +
  `loadDefaults()` + cast `Number(paramDefaults.value.DEFAULT_IVA_ID)`.
  `applyFormDefaults()` chiama l'endpoint dedicato e applica
  `form.value.iva_id = defaults.default_iva_id` (gia' int). Best-effort
  su errore di rete.

**(C4) — non implementata.** Brief: "solo se profilo perf evidenzia
bottleneck". Nessun profilo, nessun fix: regola progetto YAGNI applicata.

**Dipendenze**: indipendente, basso rischio. Chiusa.

---

## E. Sintesi tabellare per priorita' e team

| Fase | Punti coperti | Team DB | Team Backend | Team Frontend | Priorita' |
| --- | --- | --- | --- | --- | --- |
| 1 | A1 + B2 | seed parametri UoM in `config.parameters` | view lookup dedicato rounding-modes + URL | wrapper `RoundingModeSelect` + `useParameterDefaults` | ALTA |
| 2 | A2 + B4 | seed parametri BoM + estensione vista (`can_close`, `min_close_date`) | proiezione campi + defaults service | rimozione computed + uso campi BE | ALTA |
| 3 | A4 | `fn_duplica_componente_versione` + pgTAP | repository + service + view + Idempotency | dialog minimale + chiamata API | ALTA |
| 4 | A3 | DDL DEFAULT CURRENT_DATE (opzionale) | service applica fallback `today` | rimozione `new Date()` nei 3 drawer | MEDIA |
| 5 | B1 + B5 + C1 | nessuna | helper `compute_non_editable_fields` + arricchimento detail | uso `non_editable_fields` da response | MEDIA |
| 6 | B3 | estensione viste (`can_delete`, `can_manage_bom`) | proiezione campi | uso capability nelle row actions | MEDIA |
| 7 | C2 | guard trigger + `fn_riattiva_articolo` | view + service + breaking PATCH | rimuovi toggle + pulsanti dedicati | ALTA (bug logico) |
| 8 | A5 + C4 | nessuna | endpoint form-defaults + detail aggregato | uso endpoint nuovi | BASSA (cosmetica) |

**Da NON toccare** (falsi positivi del documento originale):

- `ArticoloDrawer:148` DEFAULT_IVA_ID lato FE (gia' parameters-driven)
- `ArticoliSearchTable:62` disable manage BoM se `!is_composito` (UX, dato data-driven; eventualmente rifinito in Fase 6)
- `ArticoloUomDrawer:74` watcher `is_base ↔ factor=1` (defense-in-depth UX corretta)
- `articoli.js:16` `data_da` default = anno-1 (standard di progetto, vedi `frontend-standards.md`)
- `UomConversioniDrawer:82` `uom_from_id` forzato (UX corretta, coerente col modello di dominio)

---

## F. Pattern emersi dal refactor

I pattern riusabili in futuri refactor di altri domini:

- **Defaults di policy via `config.parameters`**: ogni valore "default per
  l'admin" appartiene a un parametro con override per emittente (Fase 1, 2).
  Mai hardcodare nei `defaultForm()` di Vue.
- **`non_editable_fields` esposto sul detail** (B1, B5, C1): i drawer
  costruiscono whitelist PATCH dai metadata, non da `if` cablati.
  Stesso pattern adottato in Fase 6 anagrafiche.
- **Capability di riga (`can_*` / `*_reason`)**: il BE risolve `can_delete`,
  `can_close`, `can_manage_bom`, ecc. e il FE le applica come dati.
- **Endpoint atomico per azioni di versionamento**: la duplica BoM (A4)
  diventa azione di dominio backend, non orchestrazione FE. Simmetrica al
  pattern listini-versioni v3 (rettifica controllata).
- **Disattiva/Riattiva come azioni dedicate** (C2): mai dentro PATCH, sempre
  endpoint POST dedicato che rispetta l'ordine padre/figli.

Tutti questi pattern sono gia' documentati nella memoria progetto:

- `feedback_no_hardcoded_ids` — Fase 1, 2
- `feedback_slot_override_matrix` — Fase 1, 2 (pattern parametri-per-entita')
- `feedback_stato_terminale_con_data` — Fase 7
- `feedback_disattiva_ordine` — Fase 7
- `feedback_classify_payload_three_state` — non applicabile qui (no payload inline opzionale)
- `feedback_payload_helpers_duplicati` — Fase 5

Nessuna nuova memoria pattern necessaria: il refactor consolida pattern gia'
emersi su altri domini.
