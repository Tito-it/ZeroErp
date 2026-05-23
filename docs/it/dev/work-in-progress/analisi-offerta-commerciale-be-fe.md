# Piano BE + FE — Dominio Offerta Commerciale

> **Stato**: piano in attesa di completamento brief DB. Nessun codice ancora
> scritto.
>
> **Sorgente di verità**:
>
> - Modello: [analisi-offerta-commerciale.md](analisi-offerta-commerciale.md)
>   (decisioni §5 chiuse 2026-05-23)
> - Brief DB: [analisi-offerta-commerciale-db.md](analisi-offerta-commerciale-db.md)
>   (in attesa team DB)
>
> **Prerequisito di applicabilità**: il piano BE può partire solo dopo che il
> team DB ha chiuso almeno gli step 1-3 del brief DB (sorgenti, tabelle, ALTER
> su contratti). Il piano FE può iniziare in parallelo al BE se ci si attiene
> a contratti API stabili (vedi §6 sequenza).
>
> **Cosa NON è questo documento**:
>
> - non è un brief DB (quello è separato)
> - non riformula il modello (lo applica)
> - non descrive il flusso pratiche `OFFERTA_QUADRO` (quello è nel documento
>   pratiche §11.2: si aggancia a questo dominio una volta esistente)

---

## 1. Inquadramento del lavoro applicativo

### 1.1 Obiettivo

Esporre il dominio `vendite.offerte_commerciali` come funzionalità end-to-end
operativa: drawer di editing, lista con filtri, push verso contratto,
revisioni, lifecycle BOZZA → EMESSA → ACCETTATA / RIFIUTATA. L'utente
operatore commerciale deve poter:

1. Creare un'offerta in BOZZA dal menù vendite (punto di ingresso autonomo,
   §5.8 del documento pratiche).
2. Compilare testata + utilities + eccezioni proposte.
3. Emettere l'offerta congelando la versione del listino.
4. Registrare l'esito dell'accettazione cliente (ACCETTATA / RIFIUTATA).
5. Su ACCETTATA, lanciare il push verso contratto DRAFT e navigare al
   `ContrattoDrawer` del nuovo contratto.
6. Creare revisioni (rev.N+1 da rev.N EMESSA) — pattern preventivi.

### 1.2 Pattern architetturali da rispettare (no negoziabili)

- **3 layer Django**: API view → service → repository (vedi `AGENTS.md` e
  `PROJECT_CONTEXT.md`).
- **Pricing centralizzato**: mai lookup diretto a `listini_righe` o
  `contratti` dal codice offerta — il pricing passa da `PricingService` o
  funzioni DB equivalenti (memoria `feedback_pricing_centralizzato`).
- **Display fields via JOIN backend**: la lista offerte deve già ritornare
  descrizioni leggibili (cliente, stato, listino, ecc.). Niente lookup
  client-side per dati di riga (memoria `feedback_display_fields_backend`).
- **Drawer autonomo + readonly**: il drawer offerta deve supportare prop
  `readonly` con `useInjectReadonly` (memoria `feedback_drawer_readonly`).
- **Store Pinia con `userScoped: true`**: lo store offerte contiene dati
  utente, va flaggato per evitare leak cross-user al logout (memoria
  `feedback_pinia_userscoped`).
- **i18n obbligatorio**: ogni testo visibile usa `$t(...)`, mai stringhe
  hardcoded (AGENTS.md §Frontend).
- **Master-detail inline**: eccezioni e utilities sono pannelli detail dentro
  il drawer master (memoria `feedback_master_detail_inline`).
- **Dialog dedicato cambio stato**: la transizione BOZZA→EMESSA, EMESSA→
  ACCETTATA, EMESSA→RIFIUTATA che richiede dati di processo (es. data
  accettazione, motivazione rifiuto) usa dialog dedicato — pattern
  `feedback_dialog_cambio_stato_dati_processo`.
- **Drawer create auto-save bozza**: il drawer in creazione auto-salva come
  BOZZA al primo set di campi minimi (memoria
  `feedback_drawer_create_autosave_bozza`).
- **Niente quick fix**: ogni proposta deve essere la soluzione corretta in
  assoluto (memoria `feedback_no_quick_fix_soluzione_assoluta`).

### 1.3 Quello che NON va fatto in v1

- **Portale cliente-facing**: l'accettazione è dell'operatore, non
  self-service (decisione §5.4 dell'analisi). Niente endpoint pubblici di
  accettazione.
- **Pacchetto commerciale multi-contratto**: il dominio applicativo non
  conosce il pacchetto (predisposizione DB §5.1-bis non esercitata). Niente
  componenti `PacchettoOffertaPanel`, niente API di raggruppamento.
- **Job di scadenza che cambiano stato**: la scadenza è segnalazione UI
  (decisione §5.6). Implementare il calcolo "scaduta = `validita_al < today`"
  come **attributo computato** lato BE nei display fields o lato FE in
  composable, mai come UPDATE su `stato_doc_offerta_id`.
- **Causale recesso/cessazione**: rinviata a brief separato (vedi nota in
  analisi §5.5). Il drawer offerta non ha campi "recesso".

---

## 2. Inventario complessivo BE + FE

### 2.1 Backend Django (`apps/vendite/`)

| Layer       | File nuovo                                      | Pattern                            |
| ----------- | ----------------------------------------------- | ---------------------------------- |
| Types       | `apps/vendite/types.py` (estensione)            | 4 TypedDict nuovi (vedi §3.1)      |
| Repository  | `apps/vendite/db/offerte_repository.py`         | CRUD + list paginato + lookup      |
| Service     | `apps/vendite/services/offerte_service.py`      | Facade orchestrazione              |
| API views   | `apps/vendite/api/views_offerte.py`             | 9 view (vedi §3.4)                 |
| API routes  | `apps/vendite/api/urls.py` (estensione)         | 9 path nuove                       |
| Tests       | `apps/vendite/tests/services/test_offerte_service.py` + `apps/vendite/tests/api/test_offerte_api.py` | mock DB, no DB reale (AGENTS.md §Test) |

### 2.2 Frontend Vue (`frontend/src/vendite/`)

| Layer      | File nuovo                                                            | Pattern                                              |
| ---------- | --------------------------------------------------------------------- | ---------------------------------------------------- |
| API client | `frontend/src/vendite/api/offerte.js`                                 | Wrapper axios + token refresh                        |
| Store      | `frontend/src/vendite/stores/useOfferteStore.js`                      | Pinia + `userScoped: true` + filters persistiti      |
| View       | `frontend/src/vendite/views/OfferteView.vue`                          | Layout SearchTable + Drawer + lookup filters         |
| Search     | `frontend/src/vendite/components/OfferteSearchTable.vue`              | ListaConfigurabile + paginazione + filtri data      |
| Drawer     | `frontend/src/vendite/components/OffertaDrawer.vue`                   | Drawer 6 tab (testata, eccezioni, utilities, revisioni, giornale, allegati) |
| Panels     | `frontend/src/vendite/components/EccezioniOffertaPanel.vue`           | Master-detail inline (lista + form sotto)            |
| Panels     | `frontend/src/vendite/components/UtilitiesOffertaPanel.vue`           | Master-detail inline                                 |
| Dialog     | `frontend/src/vendite/components/dialogs/OffertaEmissioneDialog.vue`  | Cambio stato BOZZA→EMESSA con conferma versione listino |
| Dialog     | `frontend/src/vendite/components/dialogs/OffertaEsitoDialog.vue`      | Cambio stato EMESSA→ACCETTATA/RIFIUTATA              |
| Dialog     | `frontend/src/vendite/components/dialogs/OffertaPushDialog.vue`       | Conferma push verso contratto + navigazione         |
| i18n       | `frontend/src/i18n/it.json` (estensione `vendite.offerte.*`)          | Tutte le label, errori, conferme                     |

### 2.3 Navigation + permessi

- `frontend/src/core/navigation.js`: aggiungere voce "Offerte commerciali" in
  area Vendite, con icona e route `/vendite/offerte`.
- `config.azioni_processo` (seed DB, **non in questo piano** — chiedere al
  team DB se serve riga seed per `OFFERTA_GESTISCI`): azione di processo per
  granularità permessi sul drawer offerta. Pattern azioni di processo
  esistente (memoria `feedback_lookup_skip_area_check`).

---

## 3. Step BE — Backend Django

### Step BE-1 — TypedDict in `types.py`

**Scopo**: definire i contratti tipizzati di scambio backend ↔ API.

**Deliverable**:

```python
class OffertaRow(TypedDict):
    id: int
    uid: str
    codice: str
    emittente_fiscale_id: int
    billing_account_id: str
    listino_id: int
    listino_versione_id: int | None
    valore_variazione_globale: Decimal | None
    tipo_variazione_globale_id: int | None
    validita_dal: date
    validita_al: date | None
    stato_doc_offerta_id: int
    revisione_numero: int
    revisione_padre_id: int | None
    data_emissione: datetime | None
    data_accettazione: datetime | None
    data_rifiuto: datetime | None
    note: str | None
    meta: dict
    # Display fields da JOIN
    stato_codice_interno: str
    stato_descrizione: str
    billing_account_display: str
    listino_codice: str
    listino_descrizione: str
    listino_versione_codice: str | None
    is_scaduta: bool  # attributo calcolato (validita_al < today)
    # Audit
    data_insert: datetime
    user_insert: str

class EccezioneOffertaRow(TypedDict):
    id: int
    offerta_id: int
    articolo_id: int
    tipo_eccezione_id: int
    # ... mirror di ContrattoRigaRow ...

class UtilityOffertaRow(TypedDict):
    id: int
    offerta_id: int
    utility_id: int
    istanza_utility_id: int | None

class OffertaPushResult(TypedDict):
    contratto_id: int
    contratto_codice: str
    sorgente_uid: str
```

**Test**: nessun test dedicato (sono TypedDict). Verifica indiretta nei test
service.

### Step BE-2 — Repository `offerte_repository.py`

**Scopo**: accesso DB tramite cursor + funzioni PG (no ORM).

**Deliverable**: classe `OfferteRepository` con metodi:

| Metodo                                       | Scopo                                                        |
| -------------------------------------------- | ------------------------------------------------------------ |
| `list_offerte(filters: dict) -> list[OffertaRow]` | Lista paginata con JOIN display fields + filtri (stato, cliente, validita_dal/al, ricerca testo, scaduta) |
| `get_offerta(offerta_id: int) -> OffertaRow` | Dettaglio con display fields                                 |
| `create_offerta(data: dict) -> int`          | INSERT testata, ritorna id                                   |
| `update_offerta(offerta_id: int, data: dict) -> bool` | UPDATE testata (solo in BOZZA, guard lato service)  |
| `delete_offerta(offerta_id: int) -> bool`    | DELETE (solo BOZZA, guard lato service)                      |
| `change_state(offerta_id: int, new_state: str, payload: dict) -> bool` | UPDATE stato_doc_offerta_id + valorizza data_emissione/accettazione/rifiuto |
| `list_eccezioni(offerta_id: int) -> list[EccezioneOffertaRow]` | Lista eccezioni dell'offerta                       |
| `create_eccezione(offerta_id, data) -> int`  | INSERT eccezione                                             |
| `update_eccezione(eccezione_id, data) -> bool` | UPDATE                                                     |
| `delete_eccezione(eccezione_id) -> bool`     | DELETE                                                       |
| `list_utilities(offerta_id) -> list[UtilityOffertaRow]` | Lista utilities                                    |
| `add_utility(offerta_id, data) -> int`       | INSERT                                                       |
| `remove_utility(rel_id) -> bool`             | DELETE                                                       |
| `crea_revisione(offerta_id: int) -> int`     | `SELECT vendite.fn_crea_revisione_offerta(...)`              |
| `push_a_contratto(offerta_id: int, pratica_id: int \| None) -> int` | `SELECT vendite.fn_push_offerta_a_contratto(...)` |
| `list_revisioni(offerta_padre_id: int) -> list[OffertaRow]` | Lista catena revisioni                            |

**Note pattern**:

- `_map_row()` con named columns (`cursor.description`), no indici posizionali
  (memoria `gestione-pratiche-v2.md` §2.3 — pattern già consolidato).
- Guard `if not row` / `assert row is not None` dopo `fetchone()`
  (AGENTS.md §Backend).
- Display fields via JOIN diretto (no lookup tramite altre repository).

**Test**: `test_offerte_repository.py` con `unittest.TestCase` + mock di
`django.db.connection` (AGENTS.md §Test).

### Step BE-3 — Service `offerte_service.py`

**Scopo**: orchestrazione business logic (validazioni applicative + delega
repository).

**Deliverable**: classe `OfferteService` con metodi:

| Metodo                                       | Scopo                                                                    |
| -------------------------------------------- | ------------------------------------------------------------------------ |
| `list_offerte(filters)`                      | Pass-through al repository                                               |
| `get_offerta(offerta_id)`                    | Pass-through + arricchimento `is_scaduta`                                |
| `crea_offerta(payload)`                      | Validazione payload (`PayloadValidator`) + INSERT bozza                  |
| `aggiorna_offerta(offerta_id, payload)`      | Guard: solo se stato BOZZA. ServiceError `E_OFFERTA_NON_EDITABILE`       |
| `emetti(offerta_id, payload)`                | Guard: stato BOZZA + versione listino impostata. Cambia stato a EMESSA   |
| `registra_accettazione(offerta_id, payload)` | Guard: stato EMESSA. Cambia stato a ACCETTATA                            |
| `registra_rifiuto(offerta_id, payload)`      | Guard: stato EMESSA. Cambia stato a RIFIUTATA                            |
| `push_a_contratto(offerta_id, pratica_id?)`  | Guard: stato ACCETTATA. Delega a repository (fn DB idempotente)         |
| `crea_revisione(offerta_id)`                 | Guard: stato EMESSA. Delega a fn DB                                      |
| `crud_eccezioni(...)`                        | Wrapper attorno a CRUD eccezioni. Guard: solo se stato BOZZA             |
| `crud_utilities(...)`                        | Wrapper attorno a CRUD utilities. Guard: solo se stato BOZZA             |

**Error handling**:

- Usa `ServiceError` + `ErrorManager.require(...)`.
- Cattura `DatabaseError` con codici PG `P0001` e mappa al codice errore
  semantico (es. `E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO`,
  `E_OFFERTA_CONTRATTO_GIA_GENERATO`) tramite `error_policies.py`.

**Test**: `test_offerte_service.py` con mock repository, casi:

- crea offerta valida → INSERT
- crea offerta con BA inesistente → fallisce
- emetti BOZZA senza versione listino → ServiceError mappato
- emetti EMESSA → ServiceError "non in BOZZA"
- push offerta ACCETTATA → contratto creato
- push offerta ACCETTATA doppia volta → seconda chiamata fallisce con
  `E_OFFERTA_CONTRATTO_GIA_GENERATO` (idempotenza testata anche lato BE)

### Step BE-4 — API views + routes

**Scopo**: esporre 9 endpoint REST.

**Endpoint da creare**:

| Metodo | Path                                                | Scopo                                     |
| ------ | --------------------------------------------------- | ----------------------------------------- |
| GET    | `/api/v1/vendite/offerte/`                          | Lista paginata + filtri (search ≥3 char)  |
| GET    | `/api/v1/vendite/offerte/{id}/`                     | Dettaglio                                 |
| POST   | `/api/v1/vendite/offerte/`                          | Crea (BOZZA)                              |
| PATCH  | `/api/v1/vendite/offerte/{id}/`                     | Aggiorna testata (solo BOZZA)             |
| DELETE | `/api/v1/vendite/offerte/{id}/`                     | Cancella (solo BOZZA)                     |
| POST   | `/api/v1/vendite/offerte/{id}/emetti/`              | BOZZA → EMESSA                            |
| POST   | `/api/v1/vendite/offerte/{id}/registra-esito/`      | EMESSA → ACCETTATA / RIFIUTATA            |
| POST   | `/api/v1/vendite/offerte/{id}/push-contratto/`      | ACCETTATA → crea contratto DRAFT          |
| POST   | `/api/v1/vendite/offerte/{id}/crea-revisione/`      | EMESSA → rev.N+1 BOZZA                    |
| GET    | `/api/v1/vendite/offerte/{id}/eccezioni/`           | Lista eccezioni                           |
| POST   | `/api/v1/vendite/offerte/{id}/eccezioni/`           | Crea eccezione                            |
| PATCH  | `/api/v1/vendite/offerte/{id}/eccezioni/{eid}/`     | Aggiorna                                  |
| DELETE | `/api/v1/vendite/offerte/{id}/eccezioni/{eid}/`     | Cancella                                  |
| GET    | `/api/v1/vendite/offerte/{id}/utilities/`           | Lista utilities                           |
| POST   | `/api/v1/vendite/offerte/{id}/utilities/`           | Aggiungi utility                          |
| DELETE | `/api/v1/vendite/offerte/{id}/utilities/{uid}/`     | Rimuovi                                   |

**Pattern obbligatori**:

- `@extend_schema` su ogni metodo HTTP pubblico (AGENTS.md §Test CI).
- `handle_post_json(...)` per parsing input + error envelope uniforme.
- `is_search_endpoint = True` sul GET lista per attivare throttling
  (AGENTS.md §Backend).
- Policy ricerca e paginazione (helper `apps/core/api/pagination.py`).

**Test**: `test_offerte_api.py` per ogni endpoint, mock di service.

---

## 4. Step FE — Frontend Vue

### Step FE-1 — API client + Store

**Scopo**: layer di accesso dati lato FE.

**`frontend/src/vendite/api/offerte.js`**: 16 funzioni wrapper async che
mappano gli endpoint §3.4 (list, get, create, update, delete, emetti,
registraEsito, pushContratto, creaRevisione + 7 per eccezioni/utilities). Usa
`useTokenedFetch` o axios centralizzato del progetto.

**`frontend/src/vendite/stores/useOfferteStore.js`**: store Pinia con:

- state: `offerte`, `currentOfferta`, `filters` (persistiti localStorage per
  user), `loading`, `error`
- `userScoped: true` (memoria `feedback_pinia_userscoped`)
- actions: `fetchList`, `fetchOne`, `create`, `update`, `remove`,
  `cambiaStato` (wrapper di emetti/registraEsito), `push`, `creaRevisione`,
  e azioni per eccezioni/utilities
- `result !== null` check su save (memoria `feedback_drawer_result_check`)

### Step FE-2 — `OfferteSearchTable.vue`

**Scopo**: lista offerte con filtri e azioni.

**Specifiche**:

- Riusa `ListaConfigurabile` esistente (pattern Blocco F)
- Colonne default: codice (`OFC-*`), cliente (BA display), stato (tag con
  severity), listino + versione, validità (range), data emissione, scaduta
  (badge giallo se `is_scaduta && stato in BOZZA/EMESSA`)
- Filtri: stato (Select), validita_dal/al (DatePicker), cliente
  (AutoComplete server-side soggetto), ricerca testo (≥3 char, memoria
  `gestione-pratiche-v2.md` §6.4 dashboard)
- Filtro data obbligatorio (memoria `feedback_filtro_data_liste`):
  `validita_dal` default = inizio anno-1
- Azioni: bottone "Nuova offerta" (apre Drawer in create), click su riga apre
  Drawer in edit/read

### Step FE-3 — `OffertaDrawer.vue` (master)

**Scopo**: drawer 6 tab per gestione end-to-end dell'offerta.

**Tab**:

1. **Testata** — form: emittente, cliente (BA), listino + versione listino
   (Select dipendente, solo versioni ATTIVE), variazione globale (% +
   tipo), validità (range date), note. Auto-save al primo set completo
   (memoria `feedback_drawer_create_autosave_bozza`).
2. **Eccezioni** — `EccezioniOffertaPanel.vue` (master-detail inline)
3. **Utilities** — `UtilitiesOffertaPanel.vue` (master-detail inline)
4. **Revisioni** — lista catena revisioni (rev.1 SUPERATA, rev.2 EMESSA,
   ecc.), navigazione tra revisioni. Sola lettura.
5. **Giornale stati** — log transizioni di stato + dati di processo
   (chi, quando, motivazione). Sola lettura.
6. **Allegati** — riusa pattern `AllegatiPanel` esistente (PDF firmati,
   email del cliente, ecc.).

**Prop `readonly`**: drawer supporta `useInjectReadonly` (memoria
`feedback_drawer_readonly`). Drawer auto-readonly se stato ≠ BOZZA per i
campi testata; eccezioni/utilities readonly se stato ≠ BOZZA.

**Header**: codice + tag stato (severity da `core/utils/severity.js`) + badge
"SCADUTA" se applicabile + badge "rev.N" se revisione.

**Footer azioni** (dipendenti dallo stato):

- BOZZA: bottoni "Emetti" (apre `OffertaEmissioneDialog`), "Cancella"
- EMESSA: bottoni "Registra accettazione" / "Registra rifiuto" (apre
  `OffertaEsitoDialog`), "Crea revisione"
- ACCETTATA: bottone "Push verso contratto" (apre `OffertaPushDialog`); se
  già pushato, mostra link al contratto generato (lettura sola)
- RIFIUTATA / SUPERATA: solo `DrawerFooter close-only` (memoria
  `feedback_drawer_footer_close_only`)

**`@after-show` content ready** (memoria `feedback_content_ready_after_show`):
caricamento dati con loading skeleton per evitare rimbalzo.

### Step FE-4 — Pannelli detail

**`EccezioniOffertaPanel.vue`** (master-detail inline, memoria
`feedback_master_detail_inline`):

- Lista paginata eccezioni dell'offerta (tipo, articolo, prezzo/sconto)
- Form sotto per nuova eccezione / edit (Select tipo OVERRIDE / ESCLUSIONE /
  AGGIUNTA, AutoComplete articolo, prezzo)
- Editabile solo se stato offerta = BOZZA

**`UtilitiesOffertaPanel.vue`**: stesso pattern.

### Step FE-5 — Dialogs cambio stato + push

**`OffertaEmissioneDialog.vue`** (memoria
`feedback_dialog_cambio_stato_dati_processo`):

- Conferma "Vuoi emettere questa offerta?"
- Mostra riepilogo: listino + versione fissata, validità, eccezioni count
- Avviso se versione listino non ATTIVA (lato BE solleverà
  `E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA`)

**`OffertaEsitoDialog.vue`**:

- Toggle ACCETTATA / RIFIUTATA
- Data esito (DatePicker)
- Motivazione (Textarea, obbligatoria se RIFIUTATA)
- Allegato opzionale (es. email cliente)

**`OffertaPushDialog.vue`**:

- Conferma "Vuoi generare il contratto da questa offerta?"
- Avviso "L'offerta resterà ACCETTATA, il contratto nascerà in DRAFT"
- Dopo push positivo: bottone "Apri contratto" che apre `ContrattoDrawer` del
  nuovo contratto (cross-component navigation via store)
- Su errore `E_OFFERTA_CONTRATTO_GIA_GENERATO`: dialog parlante con link al
  contratto esistente (pattern §5.3.3 documento pratiche "Opzione 1 errore
  propagato")

### Step FE-6 — i18n

**Scopo**: tutte le label sotto `vendite.offerte.*`.

**Chiavi minime**:

```
vendite.offerte.titolo = "Offerte commerciali"
vendite.offerte.nuova = "Nuova offerta"
vendite.offerte.colonne.codice = "Codice"
vendite.offerte.colonne.cliente = "Cliente"
... (~40-50 chiavi totali tra colonne, label form, bottoni, dialog)
vendite.offerte.stati.BOZZA = "Bozza"
vendite.offerte.stati.EMESSA = "Emessa"
... (5 stati)
vendite.offerte.errori.E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO = "..."
... (6 codici errore)
```

### Step FE-7 — Navigation

**Scopo**: voce menu Offerte Commerciali in `core/navigation.js`.

- Sezione vendite, posizionata vicino a "Preventivi" e "Contratti"
- Icona: `pi pi-file-edit` o equivalente
- Permesso: si lega ad azione di processo (TODO seed DB)

---

## 5. Test e smoke test

### 5.1 Test BE Django

| Suite                          | Cosa copre                                                          |
| ------------------------------ | ------------------------------------------------------------------- |
| `test_offerte_repository.py`   | CRUD + list filtri + display fields (mock DB)                       |
| `test_offerte_service.py`      | Logica orchestrazione + guard di stato + idempotenza push           |
| `test_offerte_api.py`          | Tutti i 16 endpoint con mock service + error envelope               |

### 5.2 Smoke test bash

**File**: `backend/scripts/smoke-test-offerte.sh`

Con `# Indice test (0..N):` nell'header (regola AGENTS.md). Test minimi:

- 0: cleanup proattivo (memoria `feedback_smoke_test_idempotenti`)
- 1: crea offerta BOZZA
- 2: aggiungi 2 eccezioni + 1 utility
- 3: emetti offerta
- 4: tentativo modifica testata su EMESSA → 422
- 5: registra accettazione
- 6: push verso contratto → contratto DRAFT creato
- 7: ripeti push → seconda invocazione fallisce con `E_OFFERTA_CONTRATTO_GIA_GENERATO`
- 8: crea offerta nuova → emetti → crea revisione → rev.1 SUPERATA, rev.2 BOZZA
- 9: cleanup finale

### 5.3 Smoke test UI

Manuale, end-to-end, da fare in browser dopo deploy locale:

- Creazione offerta + emissione + accettazione + push
- Verifica navigation verso `ContrattoDrawer` post-push
- Verifica badge "SCADUTA" su offerta EMESSA con `validita_al` superata
- Verifica readonly drawer per offerte non in BOZZA
- Verifica catena revisioni (rev.1 → rev.2)

---

## 6. Sequenza di applicazione e parallelismi

### 6.1 Dipendenze dure

```
brief DB step 1-3 → BE-1 (types) → BE-2 (repository)
brief DB step 4-8 → BE-3 (service) → BE-4 (API)
                                        │
                                        ▼
                                    FE-1 (api client + store)
                                        │
                          ┌─────────────┼─────────────┐
                          ▼             ▼             ▼
                      FE-2 (lista)  FE-3 (drawer)  FE-5 (dialogs)
                                        │
                                  FE-4 (panels)
                                        │
                                        ▼
                                  FE-6 (i18n) + FE-7 (navigation)
                                        │
                                        ▼
                                  Smoke tests (5.2 + 5.3)
```

### 6.2 Parallelismi possibili

- **BE-1/BE-2 in parallelo a brief DB step 4-8**: i types e il repository
  scaffold (firma metodi) si possono scrivere appena il brief DB ha chiuso
  step 1-3 (tabelle + ALTER esistono). I metodi che chiamano fn DB (`crea_revisione`,
  `push_a_contratto`) si stub-bano e si completano quando le fn esistono.
- **FE-1/FE-2 in parallelo a BE-4**: appena gli endpoint sono firmati (anche
  prima dell'implementazione), il FE può scrivere api client + store con dati
  mock e SearchTable contro mock. Si collega al BE reale quando disponibile.
- **i18n FE-6 in parallelo a FE-3/FE-4/FE-5**: il file `it.json` si compila
  man mano che i componenti chiedono nuove chiavi (non aspettare la fine).

### 6.3 Critical path stimato (indicativo, dipende dal team DB)

| Settimana | DB                                  | BE                                | FE                                  |
| --------- | ----------------------------------- | --------------------------------- | ----------------------------------- |
| 1         | Step 1-3 (seed + tabelle + ALTER)   | BE-1 (types) inizia               | —                                   |
| 2         | Step 4-6 (state machine + revisione)| BE-2 (repository) + BE-3 (service inizio) | FE-1 (api+store) con mock        |
| 3         | Step 7-8 (fn rev + push)            | BE-3 (service) completa + BE-4 (API) | FE-2 (lista) + FE-3 (drawer scaffold) |
| 4         | Step 9 (pgTAP suite completa)       | Test BE + smoke 5.2               | FE-3/4/5 completi + FE-6 i18n + FE-7 navigation |
| 5         | —                                   | Smoke UI 5.3 + bugfix             | Smoke UI 5.3 + bugfix               |

---

## 7. Note operative

- **Autorizzazioni esplicite** (memoria `feedback_autorizzazioni_esplicite`):
  aggiunta dipendenze `requirements.in` o `package.json` solo dopo OK Tid. In
  v1 il piano non prevede dipendenze nuove (tutto su stack esistente Django
  6.01 + Vue 3.5 + PrimeVue 4.5).
- **Memoria pricing centralizzato** (`feedback_pricing_centralizzato`): se in
  futuro il drawer offerta dovesse mostrare anche un'anteprima prezzi
  calcolati, va via `PricingService` esistente, non implementare logica nuova.
- **Documentazione finale**: a chiusura sprint, scrivere/aggiornare:
  - `docs/it/dev/api_offerte.md` (specchio di `api_preventivi.md`)
  - `docs/it/backend/vendite/manual/offerte_service.md` (struttura standard
    AGENTS.md §Regole Documentazione)
  - Aggiornamento `docs/it/guide/offerte-commerciali.md` (guida operatore)
- **Pratiche cross-link**: a fine sprint, scrivere il runtime end-to-end
  dell'asse `OFFERTA_QUADRO` in `analisi-pratiche-domini-anello3.md` §11.2
  (oggi solo ossatura, vedi §11.2.5 di quel documento).
- **Branch**: lavoro su `dev/backend-tid` come da prassi (AGENTS.md §Ambiente
  di sviluppo).
- **Test idempotenza obbligatorio**: il caso "doppio push offerta → secondo
  fallisce con codice semantico" è obbligatorio sia in BE-3 (test_service
  mock) sia in smoke 5.2 step 7 (vedi convenzione §6.9.5 documento pratiche).

---

## 8. Stato del piano

| Step  | Stato      | Dipendenze                                |
| ----- | ---------- | ----------------------------------------- |
| BE-1  | Pronto     | Brief DB step 2-3                         |
| BE-2  | Pronto     | BE-1 + Brief DB step 2-3                  |
| BE-3  | Pronto     | BE-2 + Brief DB step 4-8                  |
| BE-4  | Pronto     | BE-3                                      |
| FE-1  | Pronto     | BE-4 (firma endpoint, anche solo bozza)   |
| FE-2  | Pronto     | FE-1                                      |
| FE-3  | Pronto     | FE-1                                      |
| FE-4  | Pronto     | FE-3                                      |
| FE-5  | Pronto     | FE-3                                      |
| FE-6  | Continuo   | Parallelo a FE-3/4/5                      |
| FE-7  | Pronto     | FE-2/3 testabili                          |

---

*Piano BE + FE Offerta Commerciale — ZeroErp. Pronto per applicazione su
`dev/backend-tid` dopo completamento brief DB. Documento vivo, da aggiornare
a ogni step chiuso.*
