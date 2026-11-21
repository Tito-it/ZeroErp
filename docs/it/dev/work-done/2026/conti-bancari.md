# Conti Bancari — Piano di Sviluppo

> Documento di lavoro per implementazione end-to-end della gestione conti bancari.
> Riferimento principale: `docs/it/guide/gestione-conti-bancari.md`
>
> Area: anagrafiche (soggetti → conti bancari → ruoli)
>
> Data inizio: 20 marzo 2026
> **Stato: CHIUSO** — sviluppo completato end-to-end (DB, backend, frontend, test, doc) — 27 marzo 2026

---

## ✅ Recap stato

- [x] DB — Tabelle: `conti_bancari`, `soggetti_conti_bancari`, `soggetti_ruoli_conti_bancari`, `bank_branches`
- [x] DB — View: `vw_conti_bancari_per_ruolo`
- [x] DB — Funzione: `script.fn_get_conto_bancario_predefinito`
- [x] DB — Trigger: normalizzazione IBAN/BIC, guard, prevent deactivate
- [x] DB — Vincoli: IBAN unico, predefinito parziale, check uso/date
- [x] DB — SEPA: `pagamenti.sepa_mandati` (struttura pronta)
- [x] Backend — Repository conti bancari
- [x] Backend — Service conti bancari
- [x] Backend — API endpoints (views + urls)
- [x] Backend — Test unitari (21 service + 11 API = 32 test OK)
- [x] Frontend — Composable `useContoBancarioForm`
- [x] Frontend — Componente `ContoBancarioForm.vue`
- [x] Frontend — Drawer `ContiBancariDrawer.vue` (soggetto + ruolo)
- [x] Frontend — Integrazione in `SoggettoDrawer` (sezione riepilogo + gestisci)
- [x] Frontend — Stringhe i18n (`it.json`, `en.json`)
- [x] Documentazione — api.md (tabella endpoint completa), frontend-standards.md (catalogo componenti + composable)

---

## Architettura di riferimento

### Modello DB (implementato)

```
conti_bancari (registro unico IBAN — nessuna duplicazione)
    │
    ├── soggetti_conti_bancari       → livello SOGGETTO (fallback)
    │     soggetto_id + conto + uso + predefinito + validita + bloccato
    │
    └── soggetti_ruoli_conti_bancari → livello RUOLO (override, priorita)
          soggetto_ruolo_id + conto + uso + predefinito + validita + bloccato

Uso: INCASSO | PAGAMENTO | RIMBORSO | GENERICO
Predefinito: max 1 per (soggetto/ruolo, uso) — vincolo UNIQUE parziale
Risoluzione: RUOLO > SOGGETTO > fallback GENERICO
```

### Flusso UI previsto

```
SoggettoDrawer (edit mode)
  │
  ├── Sezione "Conti bancari" — riepilogo card (IBAN mascherato, uso, banca)
  │     [Gestisci conti bancari] → apre ContiBancariDrawer
  │
  └── ContiBancariDrawer
        ├── Lista card conti esistenti (soggetti_conti_bancari)
        │     click modifica → form inline
        │     [+ Aggiungi conto] → form inline
        │
        └── Form inline (ContoBancarioForm)
              IBAN (AutoComplete su registro) → auto-fill BIC, banca
              Banca/Filiale (AutoComplete bank_branches)
              Uso (Dropdown)
              ☐ Predefinito
              Valido dal / Valido al (DatePicker)
              Intestazione dichiarata
              ☐ Verificato  ☐ Bloccato
```

In futuro, lo stesso drawer sara riutilizzato nella gestione ruoli con `context: 'ruolo'`,
dove mostrera anche i conti ereditati dal soggetto (sola lettura, tag "Ereditato").

---

## Piano di sviluppo — ordine logico

### Fase 1 — Backend: Repository

**File:** `backend/apps/anagrafiche/db/conti_bancari_repository.py`

Pattern: come `soggetti_repository.py` — raw SQL con cursor, helper `rows_to_list`.

Metodi da implementare:

#### 1.1 Registro IBAN (`conti_bancari`)

| Metodo | SQL | Note |
|--------|-----|------|
| `search_conti_bancari(search, limit)` | SELECT su `conti_bancari` con ILIKE su iban | Per AutoComplete frontend — restituisce id, iban, bic_swift, intestatario, bank_branch (join), attivo |
| `get_conto_bancario(conto_id)` | SELECT singolo con join bank_branches | Dettaglio per pre-fill form |
| `get_or_create_conto_bancario(iban, bic_swift, bank_branch_id, intestatario)` | SELECT per iban; se non esiste INSERT | Il trigger normalizza IBAN. Ritorna id + created (bool) |

#### 1.2 Legame soggetto (`soggetti_conti_bancari`)

| Metodo | SQL | Note |
|--------|-----|------|
| `list_conti_soggetto(soggetto_id)` | SELECT con join conti_bancari + bank_branches | Lista per drawer. Campi: id, iban, bic, banca, uso, predefinito, valido_dal/al, bloccato, verificato, intestazione |
| `create_conto_soggetto(soggetto_id, payload)` | INSERT | payload: conto_bancario_id, uso, predefinito, valido_dal, valido_al, intestazione_dichiarata |
| `update_conto_soggetto(id, soggetto_id, payload)` | UPDATE con ownership check | Delta-only: solo campi presenti nel payload |
| `delete_conto_soggetto(id, soggetto_id)` | DELETE con ownership check | Verifica soggetto_id prima di eliminare |

#### 1.3 Legame ruolo (`soggetti_ruoli_conti_bancari`) — stessa struttura

| Metodo | SQL | Note |
|--------|-----|------|
| `list_conti_ruolo(soggetto_ruolo_id)` | SELECT con join | Stessa struttura di list_conti_soggetto |
| `list_conti_ereditati_ruolo(soggetto_ruolo_id)` | Query su soggetti_conti_bancari via soggetti_ruoli.soggetto_id | Per mostrare conti ereditati (sola lettura, tag "Ereditato") |
| `create_conto_ruolo(soggetto_ruolo_id, payload)` | INSERT | Stessa struttura di create_conto_soggetto |
| `update_conto_ruolo(id, soggetto_ruolo_id, payload)` | UPDATE con ownership | Stessa struttura |
| `delete_conto_ruolo(id, soggetto_ruolo_id)` | DELETE con ownership | Stessa struttura |

#### 1.4 Lookup filiali bancarie

| Metodo | SQL | Note |
|--------|-----|------|
| `search_bank_branches(search, limit)` | SELECT su bank_branches con join soggetti (nome banca) | Per AutoComplete filiale. Campi: id, name, bank_code, branch_code, bic_swift, banca_nome (da soggetto ruolo) |

**Error codes** da aggiungere in `error_codes.py`:

```python
E_ANAG_CONTO_NOT_FOUND = "E_ANAG_CONTO_NOT_FOUND"
E_ANAG_CONTO_SOGGETTO_NOT_FOUND = "E_ANAG_CONTO_SOGGETTO_NOT_FOUND"
```

---

### Fase 2 — Backend: Service

**File:** `backend/apps/anagrafiche/services/conti_bancari_service.py`

Pattern: come `soggetti_service.py` — orchestrazione con `ErrorManager.require`, `transaction.atomic`.

| Metodo | Logica |
|--------|--------|
| `search_conti_bancari(search, limit)` | Delega a repo, validazione input |
| `list_conti_soggetto(soggetto_id)` | Verifica soggetto esiste, delega a repo |
| `create_conto_soggetto(soggetto_id, payload)` | 1. `get_or_create` registro IBAN → conto_bancario_id; 2. INSERT legame soggetto. Transazione atomica |
| `update_conto_soggetto(soggetto_id, conto_soggetto_id, payload)` | Delega a repo con ownership |
| `delete_conto_soggetto(soggetto_id, conto_soggetto_id)` | Delega a repo con ownership |
| `list_conti_ruolo(soggetto_ruolo_id)` | Lista conti ruolo + conti ereditati (con flag fonte) |
| `create_conto_ruolo(soggetto_ruolo_id, payload)` | Stessa logica di create_conto_soggetto |
| `update_conto_ruolo(soggetto_ruolo_id, conto_ruolo_id, payload)` | Stessa logica |
| `delete_conto_ruolo(soggetto_ruolo_id, conto_ruolo_id)` | Stessa logica |
| `search_bank_branches(search, limit)` | Delega a repo |

**Nota**: il service gestisce la logica "get or create" del registro IBAN.
L'utente inserisce un IBAN nel form, il service cerca nel registro:
- Se esiste → usa quel `conto_bancario_id`
- Se non esiste → crea il record in `conti_bancari`, poi usa l'id

Questo mantiene il principio "registro unico IBAN" trasparente per il frontend.

---

### Fase 3 — Backend: API (Views + URLs)

**File views:** `backend/apps/anagrafiche/api/views_conti_bancari.py`

Pattern: `DomainAPIView` con `area_funzionale = "anagrafiche"`, `@extend_schema`.

| Endpoint | Metodo | View | Descrizione |
|----------|--------|------|-------------|
| `GET /anagrafiche/conti-bancari/lookup/` | GET | `ContiBancariLookupView` | AutoComplete registro IBAN (?search=) |
| `GET /anagrafiche/bank-branches/lookup/` | GET | `BankBranchesLookupView` | AutoComplete filiali (?search=) |
| `GET /anagrafiche/soggetti/{id}/conti-bancari/` | GET | `SoggettoContiBancariView` | Lista conti del soggetto |
| `POST /anagrafiche/soggetti/{id}/conti-bancari/` | POST | `SoggettoContiBancariView` | Crea legame soggetto ↔ conto |
| `PATCH /anagrafiche/soggetti/{id}/conti-bancari/{cb_id}/` | PATCH | `SoggettoContiBancariDetailView` | Aggiorna legame |
| `DELETE /anagrafiche/soggetti/{id}/conti-bancari/{cb_id}/` | DELETE | `SoggettoContiBancariDetailView` | Elimina legame |
| `GET /anagrafiche/ruoli/{id}/conti-bancari/` | GET | `RuoloContiBancariView` | Lista conti del ruolo (+ ereditati) |
| `POST /anagrafiche/ruoli/{id}/conti-bancari/` | POST | `RuoloContiBancariView` | Crea legame ruolo ↔ conto |
| `PATCH /anagrafiche/ruoli/{id}/conti-bancari/{cb_id}/` | PATCH | `RuoloContiBancariDetailView` | Aggiorna legame |
| `DELETE /anagrafiche/ruoli/{id}/conti-bancari/{cb_id}/` | DELETE | `RuoloContiBancariDetailView` | Elimina legame |

**File urls:** aggiornare `backend/apps/anagrafiche/api/urls.py` con le nuove rotte.

**Payload POST soggetto** (esempio):

```json
{
  "iban": "IT60 X054 2811 1010 0000 0123 456",
  "bic_swift": "BPPIITRRXXX",
  "bank_branch_id": 1,
  "intestatario_predefinito": "Mario Rossi",
  "uso": "INCASSO",
  "predefinito": true,
  "valido_dal": "2026-01-01",
  "valido_al": null,
  "intestazione_dichiarata": "Mario Rossi",
  "verificato": false,
  "bloccato": false
}
```

Il backend separa: primi 4 campi → registro (`get_or_create`), resto → legame.

---

### Fase 4 — Backend: Test

**Directory:** `backend/apps/anagrafiche/tests/`

| File | Contenuto |
|------|-----------|
| `services/test_conti_bancari_service.py` | Test service con mock del repository. Casi: create con IBAN nuovo, create con IBAN esistente, update, delete, ownership check |
| `api/test_conti_bancari_api.py` | Test endpoint con mock del service. Casi: lista, create, update, delete per soggetto e ruolo. Verifica envelope, status code, @extend_schema |

Pattern: `unittest.TestCase` con mock (no DB reale, compatibilita CI).

---

### Fase 5 — Frontend: Composable

**File:** `frontend/src/core/composables/useContoBancarioForm.js`

Pattern: come `useContattoForm.js` — reactive form + validate + reset + populate + toPayload.

```
Campi form:
  iban: ''              ← input/autocomplete
  iban_obj: null        ← oggetto dal registro (per restore autocomplete)
  bic_swift: ''         ← auto-fill da registro, editabile
  bank_branch_id: null  ← autocomplete filiali
  bank_branch_obj: null ← oggetto per restore autocomplete
  intestatario_predefinito: ''
  uso: 'GENERICO'       ← dropdown
  predefinito: false     ← checkbox
  valido_dal: null       ← datepicker
  valido_al: null        ← datepicker
  intestazione_dichiarata: ''
  verificato: false      ← checkbox
  bloccato: false        ← checkbox

Metodi:
  validate()  → errori: iban obbligatorio, uso obbligatorio, date coerenti
  reset()     → azzera tutti i campi
  populate(data) → popola da dati API (edit mode)
  toPayload() → costruisce payload per POST/PATCH
```

---

### Fase 6 — Frontend: Componente Form

**File:** `frontend/src/core/components/ContoBancarioForm.vue`

Building block riutilizzabile — riceve props dal composable, emette eventi.

Layout form (classi standard `form-grid`, `form-field`, `form-grid-2col`):

```
┌────────────────────────────────────────────┐
│ IBAN: [AutoComplete_____________________]  │  ← server-side su registro
│ BIC:  [_______________]                    │  ← auto-fill, editabile
│                                            │
│ Banca/Filiale: [AutoComplete____________]  │  ← server-side su bank_branches
│ Intestatario:  [________________________]  │
│                                            │
│ ┌─ 2 colonne ───────────────────────────┐  │
│ │ Uso: [Dropdown ▼]  ☐ Predefinito      │  │
│ │ Dal: [__/__/____]  Al: [__/__/____]   │  │
│ └───────────────────────────────────────┘  │
│                                            │
│ Intestazione dichiarata: [______________]  │
│ ☐ Verificato    ☐ Bloccato                 │
└────────────────────────────────────────────┘
```

**AutoComplete IBAN**: usa `useServerAutocomplete` con endpoint `/anagrafiche/conti-bancari/lookup/`.
Quando l'utente seleziona un IBAN esistente, auto-fill BIC, banca, intestatario dal registro.
Se digita un IBAN nuovo (non trovato), il form resta libero — il backend creera il record.

**AutoComplete Banca/Filiale**: usa `useServerAutocomplete` con endpoint `/anagrafiche/bank-branches/lookup/`.
Mostra: nome filiale + nome banca + codice. Salva `bank_branch_id`.

**Dropdown Uso**: valori fissi da i18n: `INCASSO`, `PAGAMENTO`, `RIMBORSO`, `GENERICO`.

---

### Fase 7 — Frontend: Drawer

**File:** `frontend/src/core/components/ContiBancariDrawer.vue`

Pattern: come `ContattiSoggettoDrawer.vue` — drawer con lista card + form inline.

Props:

| Prop | Tipo | Descrizione |
|------|------|-------------|
| `visible` | Boolean | Visibilita drawer |
| `ownerId` | String/Number | `soggetto_id` (UUID) o `soggetto_ruolo_id` (BIGINT) |
| `context` | String | `'soggetto'` o `'ruolo'` — determina API da chiamare |

Comportamento:

1. **Apertura** → carica lista conti dal backend (API soggetto o ruolo)
2. **Lista card** — per ogni conto:
   - Tag uso (`INCASSO`, `PAGAMENTO`, etc.) con severity per tipo
   - IBAN (parzialmente mascherato: `IT60****...3456`)
   - BIC + nome banca/filiale
   - Stella se predefinito
   - Badge "Bloccato" (severity warn) se `bloccato=true`
   - Badge "Ereditato" (severity secondary) se `context='ruolo'` e fonte=SOGGETTO
   - Pulsanti modifica/elimina (solo se non ereditato, non readonly)
3. **State machine**: `formMode: null | 'new' | 'edit'`
4. **Form inline** → `ContoBancarioForm` + `DrawerFooter`
5. **Larghezza**: `DRAWER_WIDTH.STANDARD` (640px)
6. **Conti ereditati** (solo context ruolo): sezione separata in fondo, sola lettura, stile attenuato

---

### Fase 8 — Frontend: Integrazione SoggettoDrawer

**File da modificare:** `frontend/src/anagrafiche/components/SoggettoDrawer.vue`

Aggiungere sezione "Conti bancari" in edit mode, come gia fatto per contatti e indirizzi:

1. Nuove ref: `contiBancariDrawerVisible`, `contiBancariRiepilogo`
2. Nel `populateFromDetail`: caricare `data.conti_bancari || []` nel riepilogo
3. Template: sezione con header, lista card riepilogo, bottone "Gestisci conti bancari"
4. Dichiarare `<ContiBancariDrawer>` fuori dal drawer principale

**Nota**: il backend `SoggettiService.get_soggetto()` dovra essere esteso
per includere `conti_bancari` nel dettaglio soggetto (come gia fa per contatti e indirizzi).

---

### Fase 9 — Frontend: i18n

**File:** `frontend/src/locales/it.json` e `en.json`

Nuova sezione `conti_bancari`:

```
conti_bancari.titolo                 = "Conti bancari"
conti_bancari.nessun_conto           = "Nessun conto bancario"
conti_bancari.aggiungi_conto         = "Aggiungi conto"
conti_bancari.modifica_conto         = "Modifica conto"
conti_bancari.nuovo_conto            = "Nuovo conto bancario"
conti_bancari.gestisci_conti         = "Gestisci conti bancari"
conti_bancari.conto_creato           = "Conto bancario aggiunto"
conti_bancari.conto_salvato          = "Conto bancario aggiornato"
conti_bancari.conto_eliminato        = "Conto bancario rimosso"
conti_bancari.iban                   = "IBAN"
conti_bancari.bic_swift              = "BIC/SWIFT"
conti_bancari.banca_filiale          = "Banca / Filiale"
conti_bancari.intestatario           = "Intestatario"
conti_bancari.uso                    = "Tipo d'uso"
conti_bancari.uso_incasso            = "Incasso"
conti_bancari.uso_pagamento          = "Pagamento"
conti_bancari.uso_rimborso           = "Rimborso"
conti_bancari.uso_generico           = "Generico"
conti_bancari.predefinito            = "Predefinito"
conti_bancari.valido_dal             = "Valido dal"
conti_bancari.valido_al              = "Valido al"
conti_bancari.intestazione_dichiarata = "Intestazione dichiarata"
conti_bancari.verificato             = "Verificato"
conti_bancari.bloccato               = "Bloccato"
conti_bancari.ereditato              = "Ereditato"
conti_bancari.conferma_elimina       = "Eliminare il conto {iban} dall'uso {uso}?"
soggetti.section_conti_bancari       = "Conti bancari"
```

---

## Dipendenze tra fasi

```
Fase 1 (Repository)
  │
  ├──→ Fase 2 (Service) ──→ Fase 3 (API) ──→ Fase 4 (Test)
  │                                              │
  │                                              ▼
  │                                    Fase 5 (Composable)
  │                                              │
  │                                    Fase 6 (Form) ──→ Fase 7 (Drawer)
  │                                                           │
  │                                                 Fase 8 (SoggettoDrawer)
  │                                                           │
  └──────────────────────────────────────────────── Fase 9 (i18n) — trasversale
```

Le fasi 1→2→3→4 sono sequenziali (backend).
Le fasi 5→6→7→8 sono sequenziali (frontend), ma partono solo dopo fase 3.
La fase 9 (i18n) si fa in parallelo con fase 6.

---

## Punti di attenzione

### IBAN come chiave del registro

Il frontend invia l'IBAN in chiaro. Il backend:
1. Normalizza (trigger DB: uppercase, strip spazi)
2. Cerca nel registro → se esiste, riusa; se no, crea
3. Crea il legame soggetto/ruolo con il `conto_bancario_id` risultante

Questo pattern e trasparente per l'utente: non deve sapere se l'IBAN esiste gia.

### Predefinito: vincolo DB-first

Il vincolo UNIQUE parziale `WHERE predefinito=true` garantisce un solo predefinito per (soggetto/ruolo, uso).
Il backend non deve gestire logica "togli predefinito dal vecchio": e sufficiente tentare l'INSERT/UPDATE
e il DB fara il check. Se l'utente vuole cambiare predefinito, deve prima toglierlo dall'altro.

L'UI dovrebbe guidare: se esiste gia un predefinito per quell'uso, mostrare un avviso.

### Mascheramento IBAN nel riepilogo

Nel riepilogo card (SoggettoDrawer), mostrare IBAN parziale per sicurezza visiva:
`IT60****...3456` (primi 4 + ultimi 4). Nel drawer dedicato mostrare completo.

### Riuso per ruoli (futuro)

Il drawer `ContiBancariDrawer` accetta `context: 'soggetto' | 'ruolo'`.
In context ruolo:
- Chiama API ruolo (`/anagrafiche/ruoli/{id}/conti-bancari/`)
- Mostra conti ereditati dal soggetto (sola lettura, tag "Ereditato")
- I conti ereditati non sono modificabili/eliminabili dal contesto ruolo

---

## Note operative

- Non serve creare migrazioni DB — tutto gia implementato
- L'implementazione backend segue il pattern `soggetti_repository` + `soggetti_service`
- Il repository usa file separato (`conti_bancari_repository.py`) perche ha logica autonoma (registro IBAN, legami a due livelli) — coerente con naming convention AGENTS.md
- Il service usa file separato (`conti_bancari_service.py`) per lo stesso motivo
- I test Django usano `unittest.TestCase` con mock (compatibilita CI senza DB)

---

*ZeroERP — Conti Bancari WIP — rev. 1 (20 marzo 2026)*
