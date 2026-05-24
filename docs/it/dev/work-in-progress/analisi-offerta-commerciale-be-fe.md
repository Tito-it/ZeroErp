# Piano BE + FE — Dominio Offerta Commerciale

> **Stato**: piano in attesa di completamento brief DB. Nessun codice ancora
> scritto.
>
> **Revisione 2026-05-24a**: allineato alle correzioni del brief DB
> (B1/B2/B3/I1/I2/I3/I4) e alla conferma di modello sulla utility.
>
> **Revisione 2026-05-24b**: chiusi 5 gap emersi dalla verifica BE contro il
> `ContrattoDrawer` reale e il brief DB accettato. In sintesi: la utility
> **non è solo l'id** ma porta i campi business di `contratti_utilities`
> (tipo/classe utenza + parametri), quindi rientra una sezione utility editabile
> (GAP 1); tolti tab "giornale stati" e "allegati" per simmetria col contratto
> (GAP 2/3); aggiunta `motivazione_rifiuto` (GAP 4); annullamento via cambio
> stato con nuovo stato `ANNULLATA` distinto da `RIFIUTATA` (GAP 5).
>
> **Revisione 2026-05-24c** (questa): rifiniture di coerenza dopo verifica
> incrociata col `ContrattoDrawer` reale e risposte utente. (1) La utility non
> ha un tab/panel separato: i campi business sono **inline nella testata**
> esattamente come nel `ContrattoDrawer` (tab del drawer offerta passano da
> 4 a **3**); (2) state machine asimmetrica simmetrica al contratto:
> **BOZZA → ANNULLATA** (annullamento da noi), **EMESSA → RIFIUTATA** (no
> cliente). Nessun annullamento da EMESSA, nessun rifiuto da BOZZA;
> (3) endpoint utility mirror del contratto (POST + PATCH per id);
> (4) altre rifiniture di coerenza interna (count stati, count tab, test,
> smoke UI, dipendenza addendum DB). Vedi §0.4 changelog.
> **Alcune correzioni toccano anche il brief DB** (già accettato): vedi
> nota DB in §0.3.
>
> **Sorgente di verità**:
>
> - Modello: [analisi-offerta-commerciale.md](analisi-offerta-commerciale.md)
>   (decisioni §5 chiuse 2026-05-23)
> - Brief DB: [brief-db-offerta-commerciale.md](brief-db-offerta-commerciale.md)
>   (revisione 2026-05-24, correzioni B1/B2/B3/I1/I2/I3/I4)
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

## 0. Changelog correzioni

### 0.1 Revisione 2026-05-24a (allineamento al brief DB)

Il piano era stato scritto contro la stesura precedente del brief DB (offerta
multi-utility e FK errate). Queste correzioni lo riallineano al brief corretto.

| Rif. | Punto del piano corretto     | Cosa cambia                                                             |
| ---- | ---------------------------- | ----------------------------------------------------------------------- |
| B2   | `OffertaRow` (BE-1)          | `istanza_utility_id` / `utility_id` NOT NULL derivati dal BA            |
| B3   | `EccezioneOffertaRow` (BE-1) | `tipo_eccezione: str` (enum `vendite.tipo_eccezione_contratto`, non FK) |
| I2   | `OffertaRow` (BE-1)          | `tipo_variazione_globale: str` (VARCHAR+CHECK, non FK)                  |

### 0.2 Revisione 2026-05-24b (chiusura 5 gap verifica BE)

| Gap   | Punto corretto                                                     | Cosa cambia                                                                                                                                                                                                                                                                                                                                                                             |
| ----- | ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GAP 1 | Utility: TypedDict, repository, drawer (testata + sezione utility) | La utility porta **tutti** i campi business di `contratti_utilities` (`tipo_utenza_id`, `classe_utenza_id`, `param_1_num`, `param_2_txt`, `istanza_dati_precontrattuali_id`), editabili come nel `ContrattoDrawer`. `istanza_utility_id`/`utility_id` restano derivati dal BA. **Rientra la sezione utility** (la semplificazione "solo testata sola lettura" della rev. a era errata). |
| GAP 2 | FE-3 drawer                                                        | **Rimosso tab "Giornale stati"** (non esiste tabella log né nel contratto né nel preventivo). Resta simmetrico al contratto.                                                                                                                                                                                                                                                            |
| GAP 3 | FE-3 / FE-4                                                        | **Rimosso `AllegatiPanel`** (non esiste oggi; il contratto non lo ha). Allegati rinviati a brief separato.                                                                                                                                                                                                                                                                              |
| GAP 4 | OffertaEsitoDialog + testata                                       | Aggiunta colonna `motivazione_rifiuto` sulla testata (non JSONB). Tocca il brief DB (vedi nota).                                                                                                                                                                                                                                                                                        |
| GAP 5 | Lifecycle + endpoint                                               | Annullamento via **cambio stato** (no hard delete come via di processo), con nuovo stato **`ANNULLATA`** (da noi) distinto da `RIFIUTATA` (dal cliente). Logica uniforme col contratto ("annulla contratto").                                                                                                                                                                           |

### 0.4 Revisione 2026-05-24c (rifiniture coerenza)

| Punto | Cosa cambia                                                                                                                                                                                                                                                                                                                                                                |
| ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| C1    | **Utility inline in testata** (verifica `ContrattoDrawer.vue:777-785` + `:401-405`): i campi business (`tipo_utenza_id`, `classe_utenza_id`, `param_1_num`, `param_2_txt`) sono form fields della testata, **non** un tab a sé. Drawer offerta passa da **4 → 3 tab** (Testata con sezione utility inline, Eccezioni, Revisioni). `UtilityOffertaPanel.vue` **rimosso**.    |
| C2    | **Endpoint utility mirror contratto**: `POST .../utility/` (create record 1:1) + `PATCH .../utility/{utilityId}/` (update), simmetrico ad `apps/vendite/api/contratti.js`. Sostituisce la coppia `GET/PUT .../utility/` proposta in rev. b. In create offerta, la utility entra **inline nel payload** POST `/offerte/` (sub-oggetto `utility: {...}`), come fa il contratto. |
| C3    | **State machine asimmetrica chiusa**: `BOZZA → ANNULLATA` solo (annullamento da noi); `EMESSA → RIFIUTATA` solo (no del cliente). **Nessun annullamento da EMESSA**, **nessun rifiuto da BOZZA**. Logica uniforme col contratto (`DRAFT → ANNULLATO` solo da DRAFT). Punto aperto §0.3 GAP 5 chiuso.                                                                       |
| C4    | **Coerenze numeriche**: count stati passa a **6** in i18n (BOZZA, EMESSA, ACCETTATA, RIFIUTATA, ANNULLATA, SUPERATA); count tab del drawer **3** (era 4); critical path FE-4 nominato correttamente "panel eccezioni" (la utility non è più un panel).                                                                                                                     |
| C5    | **Dipendenze addendum DB**: §8 esplicita che BE-1 dipende **anche** dall'addendum (colonna `motivazione_rifiuto`, stato `ANNULLATA` + transizioni), non solo dagli step 1-3 originali del brief.                                                                                                                                                                          |
| C6    | **Test BE/smoke UI**: aggiunti casi per upsert utility (tipo/classe utenza + parametri), annullamento da BOZZA con motivazione, simmetria push utility completa.                                                                                                                                                                                                           |

> **Principio guida invariato**: l'offerta è **specchio fedele del contratto**.
> Il GAP 1 nasce proprio dall'aver violato questo principio (utility
> semplificata). La correzione lo ripristina: utility ricca come nel contratto.

### 0.3 Nota per il team DB — il brief DB va ritoccato

Le correzioni GAP 4 e GAP 5 (e la verifica GAP 1) **toccano il brief DB già
accettato**. Da girare al team DB come addendum:

1. **GAP 1 — verifica campi utility**: confermare che
   `offerte_commerciali_utilities` (brief §3 step 3, "mirror fedele di
   `contratti_utilities`") includa **esplicitamente** i 5 campi business:
   `tipo_utenza_id`, `classe_utenza_id`, `param_1_num`, `param_2_txt`,
   `istanza_dati_precontrattuali_id`. Se il mirror è davvero fedele ci sono
   già; va solo confermato, non assunto.
2. **GAP 4 — colonna nuova**: aggiungere
   `vendite.offerte_commerciali.motivazione_rifiuto TEXT NULL` (testata).
   Valorizzata alla transizione verso RIFIUTATA/ANNULLATA.
3. **GAP 5 — sesto stato + transizioni (chiusa rev. c)**: aggiungere lo stato
   `ANNULLATA` al seed `config.stati_doc_offerte` (ora **6 stati**: BOZZA,
   EMESSA, ACCETTATA, RIFIUTATA, ANNULLATA, SUPERATA) e le transizioni in
   `config.stati_doc_offerte_transizioni`:
   - `BOZZA → ANNULLATA` (annullamento da noi) — **unica via di uscita "negativa"
     dalla bozza**
   - `BOZZA → RIFIUTATA` **rimossa dal brief originale**: RIFIUTATA è solo "no
     del cliente", e dal cliente non si arriva mai con un'offerta ancora in
     bozza (la deve aver vista). Coerente col contratto (`DRAFT → ANNULLATO`
     solo da DRAFT)
   - `EMESSA → RIFIUTATA` (no del cliente) — **unica via terminale negativa
     post-emissione**
   - `EMESSA → ANNULLATA` **non ammessa**: una volta emessa, o accetta o
     rifiuta il cliente. Se ci si accorge di un errore strutturale, si crea
     una revisione (rev.N+1) che manda la corrente in SUPERATA
   - `EMESSA → SUPERATA` (via trigger revisione, già nel brief)
   - `EMESSA → ACCETTATA` (già nel brief)
   - `ANNULLATA` terminale, nessuna transizione uscente
   - codice errore: nessuno nuovo necessario (riusa
     `E_OFFERTA_TRANSIZIONE_NON_AMMESSA`)

---

## 1. Inquadramento del lavoro applicativo

### 1.1 Obiettivo

Esporre il dominio `vendite.offerte_commerciali` come funzionalità end-to-end
operativa: drawer di editing, lista con filtri, push verso contratto,
revisioni, lifecycle:

- **BOZZA → EMESSA** (emissione al cliente)
- **BOZZA → ANNULLATA** (annullamento da noi, terminale)
- **EMESSA → ACCETTATA** (sì del cliente)
- **EMESSA → RIFIUTATA** (no del cliente, terminale)
- **EMESSA → SUPERATA** (creazione rev.N+1, automatica via trigger DB)

L'utente operatore commerciale deve poter:

1. Creare un'offerta in BOZZA dal menù vendite (punto di ingresso autonomo,
   §5.8 del documento pratiche).
2. Compilare testata (con utility derivata dal BA) + eccezioni proposte.
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
  descrizioni leggibili (cliente, stato, listino, utility, ecc.). Niente
  lookup client-side per dati di riga (memoria
  `feedback_display_fields_backend`).
- **Drawer autonomo + readonly**: il drawer offerta deve supportare prop
  `readonly` con `useInjectReadonly` (memoria `feedback_drawer_readonly`).
- **Store Pinia con `userScoped: true`**: lo store offerte contiene dati
  utente, va flaggato per evitare leak cross-user al logout (memoria
  `feedback_pinia_userscoped`).
- **i18n obbligatorio**: ogni testo visibile usa `$t(...)`, mai stringhe
  hardcoded (AGENTS.md §Frontend).
- **Master-detail inline**: le eccezioni sono pannello detail dentro il drawer
  master (memoria `feedback_master_detail_inline`). La utility è un record 1:1
  i cui campi business (`tipo_utenza_id`, `classe_utenza_id`, `param_*`) stanno
  **inline nella testata** del drawer, esattamente come nel `ContrattoDrawer`
  ([ContrattoDrawer.vue:777-785](../../../../frontend/src/vendite/components/ContrattoDrawer.vue#L777-L785) +
  [:401-405](../../../../frontend/src/vendite/components/ContrattoDrawer.vue#L401-L405)).
  Nessun tab/panel utility separato (vedi §0.4 C1).
- **Dialog dedicato cambio stato**: le transizioni che richiedono dati di
  processo (BOZZA→EMESSA conferma versione listino; EMESSA→ACCETTATA;
  EMESSA→RIFIUTATA con motivazione; BOZZA→ANNULLATA con motivazione) usano
  dialog dedicato — pattern `feedback_dialog_cambio_stato_dati_processo`.
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
- **Offerta multi-utility**: l'offerta è mono-utility come il contratto
  (§5.1). Niente gestione di più utility per offerta (errore della stesura
  precedente del piano, corretto in §0).
- **Job di scadenza che cambiano stato**: la scadenza è segnalazione UI
  (decisione §5.6). Implementare il calcolo "scaduta = `validita_al < today`"
  come **attributo computato** lato BE nei display fields o lato FE in
  composable, mai come UPDATE su `stato_doc_offerta_id`.
- **Causale recesso/cessazione**: rinviata a brief separato (vedi nota in
  analisi §5.5). Il drawer offerta non ha campi "recesso".

---

## 2. Inventario complessivo BE + FE

### 2.1 Backend Django (`apps/vendite/`)

| Layer      | File nuovo                                                                                           | Pattern                                |
| ---------- | ---------------------------------------------------------------------------------------------------- | -------------------------------------- |
| Types      | `apps/vendite/types.py` (estensione)                                                                 | 4 TypedDict nuovi (vedi §3.1)          |
| Repository | `apps/vendite/db/offerte_repository.py`                                                              | CRUD + list paginato + lookup          |
| Service    | `apps/vendite/services/offerte_service.py`                                                           | Facade orchestrazione                  |
| API views  | `apps/vendite/api/views_offerte.py`                                                                  | view (vedi §3.4)                       |
| API routes | `apps/vendite/api/urls.py` (estensione)                                                              | path nuove                             |
| Tests      | `apps/vendite/tests/services/test_offerte_service.py` + `apps/vendite/tests/api/test_offerte_api.py` | mock DB, no DB reale (AGENTS.md §Test) |

> **Nota**: i TypedDict sono 4 — `UtilityOffertaRow` è reintrodotto con i campi
> business (GAP 1). Gli endpoint utility tornano come **sub-resource a record
> singolo** (1:1), non collezione: vedi §3.4.

### 2.2 Frontend Vue (`frontend/src/vendite/`)

| Layer      | File nuovo                                                           | Pattern                                                                                                  |
| ---------- | -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| API client | `frontend/src/vendite/api/offerte.js`                                | Wrapper axios + token refresh                                                                            |
| Store      | `frontend/src/vendite/stores/useOfferteStore.js`                     | Pinia + `userScoped: true` + filters persistiti                                                          |
| View       | `frontend/src/vendite/views/OfferteView.vue`                         | Layout SearchTable + Drawer + lookup filters                                                             |
| Search     | `frontend/src/vendite/components/OfferteSearchTable.vue`             | ListaConfigurabile + paginazione + filtri data + filtro utility                                          |
| Drawer     | `frontend/src/vendite/components/OffertaDrawer.vue`                  | Drawer **3 tab** (testata con sezione utility inline, eccezioni, revisioni)                              |
| Panels     | `frontend/src/vendite/components/EccezioniOffertaPanel.vue`          | Master-detail inline (lista + form sotto)                                                                |
| Dialog     | `frontend/src/vendite/components/dialogs/OffertaEmissioneDialog.vue` | Cambio stato BOZZA→EMESSA con conferma versione listino                                                  |
| Dialog     | `frontend/src/vendite/components/dialogs/OffertaEsitoDialog.vue`     | Dialog multi-modalità: ACCETTATA / RIFIUTATA (da EMESSA), ANNULLATA (da BOZZA)                           |
| Dialog     | `frontend/src/vendite/components/dialogs/OffertaPushDialog.vue`      | Conferma push verso contratto + navigazione                                                              |
| i18n       | `frontend/src/i18n/it.json` (estensione `vendite.offerte.*`)         | Tutte le label, errori, conferme                                                                         |

> **Tab del drawer (3)**: Testata (form completo: anagrafica offerta + sezione
> utility inline con `tipo_utenza_id`/`classe_utenza_id`/`param_*` editabili,
> `istanza_utility_id`/`utility_id` mostrati in sola lettura), Eccezioni,
> Revisioni. **`UtilityOffertaPanel.vue` rimosso** in rev. c (la utility è
> inline come nel `ContrattoDrawer`, non in un tab a sé). **Tab non
> introdotti**: "giornale stati" (GAP 2, non esiste tabella log; il contratto
> e il preventivo non lo hanno) e "allegati" (GAP 3, `AllegatiPanel` non
> esiste oggi — rinviato a brief separato).

### 2.3 Navigation + permessi

- `frontend/src/core/navigation.js`: aggiungere voce "Offerte commerciali" in
  area Vendite, con icona e route `/vendite/offerte`.
- `config.azioni_processo` (seed DB, **non in questo piano** — chiedere al
  team DB se serve riga seed per `OFFERTA_GESTISCI`): azione di processo per
  granularità permessi sul drawer offerta. Pattern azioni di processo
  esistente (memoria `feedback_lookup_skip_area_check`).

> **Segnalazione coordinamento DB**: il seed `OFFERTA_GESTISCI` in
> `config.azioni_processo` **non è nel brief DB offerta corrente**. Va o
> aggiunto a quel brief o gestito come seed a parte prima di arrivare ai
> permessi del drawer, altrimenti resta un buco.

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
    istanza_utility_id: int          # NOT NULL (B2) — derivato dal BA
    utility_id: int                  # NOT NULL (B2) — derivato dal BA
    listino_id: int
    listino_versione_id: int | None
    valore_variazione_globale: Decimal | None
    tipo_variazione_globale: str | None   # VARCHAR+CHECK (I2), NON FK id
    validita_dal: date
    validita_al: date | None
    stato_doc_offerta_id: int
    revisione_numero: int
    revisione_padre_id: int | None
    data_emissione: datetime | None
    data_accettazione: datetime | None
    data_rifiuto: datetime | None
    motivazione_rifiuto: str | None  # (GAP 4) valorizzata a RIFIUTATA/ANNULLATA
    note: str | None
    meta: dict
    # Display fields da JOIN
    stato_codice_interno: str
    stato_descrizione: str
    billing_account_display: str
    utility_display: str             # (B2) display della utility derivata
    listino_codice: str
    listino_descrizione: str
    listino_versione_codice: str | None
    is_scaduta: bool  # attributo calcolato (validita_al < today)
    # Audit
    data_insert: datetime
    user_insert: str

class UtilityOffertaRow(TypedDict):
    # (GAP 1) Estensione 1:1 — mirror fedele di contratti_utilities.
    # istanza_utility_id/utility_id derivano dal BA; il resto è editabile.
    id: int
    offerta_id: int
    istanza_utility_id: int
    utility_id: int
    tipo_utenza_id: int | None       # editabile (LookupSelect config.tipi_utenze)
    classe_utenza_id: int | None     # editabile (LookupSelect config.classi_utenze)
    param_1_num: Decimal | None      # editabile
    param_2_txt: str | None          # editabile
    istanza_dati_precontrattuali_id: int | None
    # Display fields da JOIN
    tipo_utenza_display: str | None
    classe_utenza_display: str | None

class EccezioneOffertaRow(TypedDict):
    id: int
    offerta_id: int
    articolo_id: int
    tipo_eccezione: str              # enum vendite.tipo_eccezione_contratto (B3), NON FK id
    # ... mirror di ContrattoRigaRow (stesse colonne, esclusi
    #     stato_approvazione_prezzo e pratica_approvazione_prezzo_id — I4) ...

class OffertaPushResult(TypedDict):
    contratto_id: int
    contratto_codice: str
    sorgente_uid: str
```

> **Correzioni B2/B3/I2/GAP1/GAP4**: `istanza_utility_id`/`utility_id` NOT NULL
> derivati dal BA + `utility_display`; `tipo_variazione_globale` è `str`;
> `tipo_eccezione` è `str` enum; **`UtilityOffertaRow` reintrodotto** con i
> campi business di `contratti_utilities` (GAP 1, la utility non è solo l'id);
> aggiunta `motivazione_rifiuto` sulla testata (GAP 4).

**Test**: nessun test dedicato (sono TypedDict). Verifica indiretta nei test
service.

### Step BE-2 — Repository `offerte_repository.py`

**Scopo**: accesso DB tramite cursor + funzioni PG (no ORM).

**Deliverable**: classe `OfferteRepository` con metodi:

| Metodo                                                                 | Scopo                                                                                                              |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `list_offerte(filters: dict) -> list[OffertaRow]`                      | Lista paginata con JOIN display fields + filtri (stato, cliente, utility, validita_dal/al, ricerca testo, scaduta) |
| `get_offerta(offerta_id: int) -> OffertaRow`                           | Dettaglio con display fields (incl. `utility_display`)                                                             |
| `create_offerta(data: dict) -> int`                                    | INSERT testata (incl. `istanza_utility_id`/`utility_id` derivati dal BA), ritorna id                               |
| `update_offerta(offerta_id: int, data: dict) -> bool`                  | UPDATE testata (solo in BOZZA, guard lato service)                                                                 |
| `delete_offerta(offerta_id: int) -> bool`                              | DELETE (solo BOZZA, guard lato service)                                                                            |
| `change_state(offerta_id: int, new_state: str, payload: dict) -> bool` | UPDATE stato_doc_offerta_id + valorizza data_emissione/accettazione/rifiuto                                        |
| `list_eccezioni(offerta_id: int) -> list[EccezioneOffertaRow]`         | Lista eccezioni dell'offerta                                                                                       |
| `create_eccezione(offerta_id, data) -> int`                            | INSERT eccezione                                                                                                   |
| `update_eccezione(eccezione_id, data) -> bool`                         | UPDATE                                                                                                             |
| `delete_eccezione(eccezione_id) -> bool`                               | DELETE                                                                                                             |
| `crea_revisione(offerta_id: int) -> int`                               | `SELECT vendite.fn_crea_revisione_offerta(...)`                                                                    |
| `push_a_contratto(offerta_id: int, pratica_id: int \| None) -> int`    | `SELECT vendite.fn_push_offerta_a_contratto(...)`                                                                  |
| `list_revisioni(offerta_padre_id: int) -> list[OffertaRow]`            | Lista catena revisioni                                                                                             |
| `lookup_utility_da_ba(billing_account_id: str) -> dict`                | Risolve `istanza_utility_id`/`utility_id` dal BA (per popolare la testata in create, come fa il contratto)         |
| `get_utility(offerta_id: int) -> UtilityOffertaRow`                    | Legge il record utility 1:1 dell'offerta (campi business, GAP 1)                                                   |
| `upsert_utility(offerta_id: int, data: dict) -> int`                   | Crea/aggiorna il record utility 1:1 (tipo/classe utenza + parametri). Guard stato BOZZA lato service               |

> **Utility come record singolo (GAP 1)**: la utility è 1:1, quindi non c'è
> CRUD a collezione (`list/add/remove`). C'è `lookup_utility_da_ba` per
> derivare id utility dal BA in creazione, e `get/upsert_utility` per i campi
> business editabili (tipo/classe utenza, parametri), mirror di come il
> `ContrattoDrawer` gestisce `contratti_utilities`.

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

| Metodo                                       | Scopo                                                                                                                                                |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `list_offerte(filters)`                      | Pass-through al repository                                                                                                                           |
| `get_offerta(offerta_id)`                    | Pass-through + arricchimento `is_scaduta`                                                                                                            |
| `crea_offerta(payload)`                      | Validazione payload (`PayloadValidator`) + risoluzione utility dal BA + INSERT bozza                                                                 |
| `aggiorna_offerta(offerta_id, payload)`      | Guard: solo se stato BOZZA. ServiceError `E_OFFERTA_NON_EDITABILE`                                                                                   |
| `emetti(offerta_id, payload)`                | Guard: stato BOZZA + versione listino impostata. Cambia stato a EMESSA                                                                               |
| `registra_accettazione(offerta_id, payload)` | Guard: stato EMESSA. Cambia stato a ACCETTATA                                                                                                        |
| `registra_rifiuto(offerta_id, payload)`      | Guard: stato EMESSA. Cambia stato a RIFIUTATA (no del cliente) + `motivazione_rifiuto`                                                               |
| `annulla(offerta_id, payload)`               | Guard: **solo stato BOZZA**. Cambia stato a ANNULLATA + `motivazione_rifiuto`. Mirror "annulla contratto DRAFT" (GAP 5, chiarito C3)                 |
| `push_a_contratto(offerta_id, pratica_id?)`  | Guard: stato ACCETTATA. Delega a repository (fn DB idempotente)                                                                                      |
| `crea_revisione(offerta_id)`                 | Guard: stato EMESSA. Delega a fn DB                                                                                                                  |
| `crud_eccezioni(...)`                        | Wrapper attorno a CRUD eccezioni. Guard: solo se stato BOZZA                                                                                         |
| `add_utility(offerta_id, payload)`           | Crea record utility 1:1 (tipo/classe utenza + parametri). Guard: solo se stato BOZZA. Mirror `add_utility_contratto`                                 |
| `update_utility(offerta_id, utility_id, payload)` | Aggiorna record utility 1:1. Guard: solo se stato BOZZA. Mirror `update_utility_contratto`                                                       |

> **Utility (GAP 1, mirror contratto, C2)**: `add_utility` / `update_utility`
> sono mirror di `add_utility_contratto` / `update_utility_contratto` (vedi
> `apps/vendite/api/contratti.js`). In `crea_offerta`, se il payload contiene
> il sub-oggetto `utility: {...}` (pattern `ContrattoDrawer.vue:401-405`), il
> service smista internamente verso `add_utility` nella stessa transazione.
> Gli id utility si derivano dal BA via `lookup_utility_da_ba`.

**Error handling**:

- Usa `ServiceError` + `ErrorManager.require(...)`.
- Cattura `DatabaseError` con codici PG `P0001` e mappa al codice errore
  semantico (es. `E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO`,
  `E_OFFERTA_CONTRATTO_GIA_GENERATO`) tramite `error_policies.py`.

**Test**: `test_offerte_service.py` con mock repository, casi:

- crea offerta valida → INSERT (con utility inline derivata dal BA + campi
  business `tipo_utenza`/`classe_utenza`/`param_*`)
- crea offerta con BA inesistente → fallisce
- emetti BOZZA senza versione listino → ServiceError mappato
- emetti EMESSA → ServiceError "non in BOZZA"
- push offerta ACCETTATA → contratto creato con utility **completa** copiata
  (id + tipo/classe utenza + parametri, verifica simmetria GAP 1)
- push offerta ACCETTATA doppia volta → seconda chiamata fallisce con
  `E_OFFERTA_CONTRATTO_GIA_GENERATO` (idempotenza testata anche lato BE)
- `update_utility` su offerta BOZZA → record aggiornato
- `update_utility` su offerta EMESSA/ACCETTATA → ServiceError
  `E_OFFERTA_NON_EDITABILE`
- `annulla` da BOZZA con motivazione → stato ANNULLATA + `motivazione_rifiuto`
  salvata
- `annulla` da EMESSA → ServiceError `E_OFFERTA_TRANSIZIONE_NON_AMMESSA` (non
  si annulla dopo l'emissione, C3)
- `registra_rifiuto` da BOZZA → ServiceError (no rifiuto da bozza, C3)

### Step BE-4 — API views + routes

**Scopo**: esporre gli endpoint REST.

**Endpoint da creare**:

| Metodo | Path                                            | Scopo                                    |
| ------ | ----------------------------------------------- | ---------------------------------------- |
| GET    | `/api/v1/vendite/offerte/`                      | Lista paginata + filtri (search ≥3 char) |
| GET    | `/api/v1/vendite/offerte/{id}/`                 | Dettaglio                                |
| POST   | `/api/v1/vendite/offerte/`                      | Crea (BOZZA)                             |
| PATCH  | `/api/v1/vendite/offerte/{id}/`                 | Aggiorna testata (solo BOZZA)            |
| DELETE | `/api/v1/vendite/offerte/{id}/`                 | Cancella (solo BOZZA)                    |
| POST   | `/api/v1/vendite/offerte/{id}/emetti/`          | BOZZA → EMESSA                           |
| POST   | `/api/v1/vendite/offerte/{id}/registra-esito/`  | EMESSA → ACCETTATA / RIFIUTATA           |
| POST   | `/api/v1/vendite/offerte/{id}/annulla/`         | **BOZZA** → ANNULLATA (GAP 5, C3)        |
| POST   | `/api/v1/vendite/offerte/{id}/push-contratto/`  | ACCETTATA → crea contratto DRAFT         |
| POST   | `/api/v1/vendite/offerte/{id}/crea-revisione/`  | EMESSA → rev.N+1 BOZZA                   |
| POST   | `/api/v1/vendite/offerte/{id}/utility/`         | Crea record utility 1:1 (solo BOZZA, C2) |
| PATCH  | `/api/v1/vendite/offerte/{id}/utility/{uid}/`   | Aggiorna utility 1:1 (solo BOZZA, C2)    |
| GET    | `/api/v1/vendite/offerte/{id}/eccezioni/`       | Lista eccezioni                          |
| POST   | `/api/v1/vendite/offerte/{id}/eccezioni/`       | Crea eccezione                           |
| PATCH  | `/api/v1/vendite/offerte/{id}/eccezioni/{eid}/` | Aggiorna                                 |
| DELETE | `/api/v1/vendite/offerte/{id}/eccezioni/{eid}/` | Cancella                                 |

> **Utility sub-resource — mirror contratto** (C2): `POST .../utility/` e
> `PATCH .../utility/{utilityId}/`, simmetrico agli endpoint contratto
> (`apps/vendite/api/contratti.js:65-71`). Il record è 1:1 logicamente ma
> l'endpoint usa il pattern collezione per coerenza col contratto. In create
> offerta, il payload POST `/offerte/` può includere `utility: {...}` inline
> (mirror `ContrattoDrawer.vue:401-405`) — il service smista internamente.
> Il `DELETE` offerta resta solo per pulizia tecnica di bozze vuote;
> l'annullamento di processo è `POST .../annulla/` → ANNULLATA (GAP 5, solo
> da BOZZA come per i contratti DRAFT, C3).

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

**`frontend/src/vendite/api/offerte.js`**: funzioni wrapper async che mappano
gli endpoint §3.4: `list`, `get`, `create` (payload può includere `utility`
inline come nel contratto), `update`, `remove`, `emetti`, `registraEsito`,
`annulla`, `pushContratto`, `creaRevisione`, 4 per eccezioni, e 2 per utility
(`addUtilityOfferta`, `updateUtilityOfferta`, mirror di
`addUtilityContratto`/`updateUtilityContratto`). Usa axios centralizzato.

**`frontend/src/vendite/stores/useOfferteStore.js`**: store Pinia con:

- state: `offerte`, `currentOfferta`, `filters` (persistiti localStorage per
  user), `loading`, `error`
- `userScoped: true` (memoria `feedback_pinia_userscoped`)
- actions: `fetchList`, `fetchOne`, `create`, `update`, `remove`,
  `cambiaStato` (wrapper di `emetti`/`registraEsito`/`annulla`), `push`,
  `creaRevisione`, azioni per eccezioni, `addUtility`/`updateUtility`
- `result !== null` check su save (memoria `feedback_drawer_result_check`)

### Step FE-2 — `OfferteSearchTable.vue`

**Scopo**: lista offerte con filtri e azioni.

**Specifiche**:

- Riusa `ListaConfigurabile` esistente (pattern Blocco F)
- Colonne default: codice (`OFC-*`), cliente (BA display), utility (display),
  stato (tag con severity), listino + versione, validità (range), data
  emissione, scaduta (badge giallo se `is_scaduta && stato in BOZZA/EMESSA`)
- Filtri: stato (Select), utility (Select), validita_dal/al (DatePicker),
  cliente (AutoComplete server-side soggetto), ricerca testo (≥3 char, memoria
  `gestione-pratiche-v2.md` §6.4 dashboard)
- Filtro data obbligatorio (memoria `feedback_filtro_data_liste`):
  `validita_dal` default = inizio anno-1
- Azioni: bottone "Nuova offerta" (apre Drawer in create), click su riga apre
  Drawer in edit/read

> **Nota (risposta utente 2026-05-24)**: il filtro per utility nella lista è
> coerente con l'interfaccia contratti (anche lì si filtra per utility nella
> SearchTable). Replica quel pattern.

### Step FE-3 — `OffertaDrawer.vue` (master)

**Scopo**: drawer **3 tab** per gestione end-to-end dell'offerta.

**Tab**:

1. **Testata** — form completo:
   - **Anagrafica offerta**: emittente, **cliente (BA)** → alla selezione del
     BA `istanza_utility_id`/`utility_id` vengono popolati automaticamente e
     mostrati in sola lettura (identico al `ContrattoDrawer`); listino +
     versione listino (Select dipendente, solo versioni ATTIVE); variazione
     globale (% + tipo VARCHAR); validità (range date); note.
   - **Sezione utility inline** (mirror `ContrattoDrawer.vue:777-785`):
     `tipo_utenza_id` (LookupSelect `config.tipi_utenze`), `classe_utenza_id`
     (LookupSelect `config.classi_utenze`), `param_1_num`, `param_2_txt`,
     `istanza_dati_precontrattuali_id`. Tutti editabili in BOZZA.
   - Auto-save al primo set completo (memoria
     `feedback_drawer_create_autosave_bozza`). In create, il payload include
     `utility: {...}` inline come fa il `ContrattoDrawer` (`:401-405`).
2. **Eccezioni** — `EccezioniOffertaPanel.vue` (master-detail inline)
3. **Revisioni** — lista catena revisioni (rev.1 SUPERATA, rev.2 EMESSA,
   ecc.), navigazione tra revisioni. Sola lettura.

> **Tab non introdotti**: "Utility" (C1 — rev. b lo prevedeva separato; in
> rev. c rientra inline nella testata per simmetria col `ContrattoDrawer`),
> "Giornale stati" (GAP 2 — non esiste tabella log), "Allegati" (GAP 3 —
> `AllegatiPanel` non esiste oggi, rinviato a brief separato). Tab finali: 3.

**Prop `readonly`**: drawer supporta `useInjectReadonly` (memoria
`feedback_drawer_readonly`). Drawer auto-readonly se stato ≠ BOZZA per i
campi testata (incl. sezione utility) ed eccezioni.

**Header**: codice + tag stato (severity da `core/utils/severity.js`) + badge
"SCADUTA" se applicabile + badge "rev.N" se revisione.

**Footer azioni** (dipendenti dallo stato):

- BOZZA: bottoni "Emetti" (apre `OffertaEmissioneDialog`), "Annulla offerta"
  (apre `OffertaEsitoDialog` in modalità ANNULLATA)
- EMESSA: bottoni "Registra accettazione" / "Registra rifiuto" (apre
  `OffertaEsitoDialog`), "Crea revisione"
- ACCETTATA: bottone "Push verso contratto" (apre `OffertaPushDialog`); se
  già pushato, mostra link al contratto generato (lettura sola)
- RIFIUTATA / ANNULLATA / SUPERATA: solo `DrawerFooter close-only` (memoria
  `feedback_drawer_footer_close_only`)

> **GAP 5 + C3 — state machine asimmetrica**: l'annullamento è un cambio di
> stato (→ ANNULLATA), non un hard delete, esattamente come "annulla contratto
> DRAFT". `RIFIUTATA` è "no del cliente" raggiungibile **solo da EMESSA**;
> `ANNULLATA` è "ritiro da parte nostra" raggiungibile **solo da BOZZA**.
> Niente bottone "Annulla offerta" su EMESSA (se serve correggere un'offerta
> emessa si crea revisione → SUPERATA). Entrambe le transizioni terminali
> negative salvano `motivazione_rifiuto`.

**`@after-show` content ready** (memoria `feedback_content_ready_after_show`):
caricamento dati con loading skeleton per evitare rimbalzo.

### Step FE-4 — Pannello detail eccezioni

**`EccezioniOffertaPanel.vue`** (master-detail inline, memoria
`feedback_master_detail_inline`):

- Lista paginata eccezioni dell'offerta (tipo, articolo, prezzo/sconto)
- Form sotto per nuova eccezione / edit (Select tipo OVERRIDE / ESCLUSIONE /
  AGGIUNTA — valori dall'enum `vendite.tipo_eccezione_contratto`, B3;
  AutoComplete articolo; prezzo)
- Editabile solo se stato offerta = BOZZA

> **Utility — niente panel** (C1): la sezione utility è **inline nella tab
> Testata** del drawer (vedi FE-3), non un panel separato. Mirror del
> `ContrattoDrawer`. `UtilityOffertaPanel.vue` (previsto in rev. b) è
> **rimosso** in rev. c.

### Step FE-5 — Dialogs cambio stato + push

**`OffertaEmissioneDialog.vue`** (memoria
`feedback_dialog_cambio_stato_dati_processo`):

- Conferma "Vuoi emettere questa offerta?"
- Mostra riepilogo: listino + versione fissata, validità, eccezioni count
- Avviso se versione listino non ATTIVA (lato BE solleverà
  `E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA`)

**`OffertaEsitoDialog.vue`** (esito cliente + annullamento, multi-modalità):

- Modalità ammesse (mutuamente esclusive, dipendenti dallo stato corrente):
  - ACCETTATA / RIFIUTATA → da EMESSA (esito cliente)
  - ANNULLATA → **solo da BOZZA** (annullamento da noi, C3)
- Data esito (DatePicker)
- Motivazione (Textarea) → salvata in `offerte_commerciali.motivazione_rifiuto`
  (GAP 4). Obbligatoria se RIFIUTATA o ANNULLATA, non richiesta se ACCETTATA
- Allegato opzionale: rinviato a brief allegati separato (GAP 3). In v1
  nessun upload qui

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
vendite.offerte.colonne.utility = "Utility"
vendite.offerte.field_tipo_utenza = "Tipo utenza"
vendite.offerte.field_classe_utenza = "Classe utenza"
vendite.offerte.field_param_1_num = "Parametro 1"
vendite.offerte.field_param_2_txt = "Parametro 2"
vendite.offerte.field_motivazione = "Motivazione"
... (~50-60 chiavi totali tra colonne, label form testata+utility inline,
    bottoni, dialog, conferme annulla)
vendite.offerte.stati.BOZZA = "Bozza"
vendite.offerte.stati.EMESSA = "Emessa"
vendite.offerte.stati.ACCETTATA = "Accettata"
vendite.offerte.stati.RIFIUTATA = "Rifiutata"
vendite.offerte.stati.ANNULLATA = "Annullata"
vendite.offerte.stati.SUPERATA = "Superata"
... (6 stati, C4)
vendite.offerte.errori.E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO = "..."
... (6 codici errore)
```

### Step FE-7 — Navigation

**Scopo**: voce menu Offerte Commerciali in `core/navigation.js`.

- Sezione vendite, posizionata vicino a "Preventivi" e "Contratti"
- Icona: `pi pi-file-edit` o equivalente
- Permesso: si lega ad azione di processo (TODO seed DB, vedi §2.3)

---

## 5. Test e smoke test

### 5.1 Test BE Django

| Suite                        | Cosa copre                                                                                                                       |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `test_offerte_repository.py` | CRUD offerta + utility 1:1 (`get_utility`/`add_utility`/`update_utility`) + list filtri + display fields + lookup utility da BA  |
| `test_offerte_service.py`    | Logica orchestrazione + guard di stato (annullamento solo da BOZZA, rifiuto solo da EMESSA, C3) + idempotenza push               |
| `test_offerte_api.py`        | Tutti gli endpoint con mock service + error envelope (incl. POST/PATCH utility, POST annulla, POST registra-esito)               |

### 5.2 Smoke test bash

**File**: `backend/scripts/smoke-test-offerte.sh`

Con `# Indice test (0..N):` nell'header (regola AGENTS.md). Test minimi:

- 0: cleanup proattivo (memoria `feedback_smoke_test_idempotenti`)
- 1: crea offerta BOZZA (utility id popolati dal BA via payload inline)
- 2: PATCH utility (tipo/classe utenza + parametri) + aggiungi 2 eccezioni
- 3: emetti offerta (BOZZA → EMESSA)
- 4: tentativo modifica testata su EMESSA → 422 `E_OFFERTA_NON_EDITABILE`
- 5: tentativo annulla su EMESSA → 422 `E_OFFERTA_TRANSIZIONE_NON_AMMESSA` (C3)
- 6: registra accettazione (EMESSA → ACCETTATA)
- 7: push verso contratto → contratto DRAFT creato con utility **completa**
  copiata: id + tipo/classe utenza + parametri (verifica simmetria GAP 1)
- 8: ripeti push → seconda invocazione fallisce con
  `E_OFFERTA_CONTRATTO_GIA_GENERATO`
- 9: crea offerta nuova → emetti → crea revisione → rev.1 SUPERATA, rev.2 BOZZA
- 10: crea offerta nuova → tentativo registra-esito RIFIUTATA su BOZZA → 422
  (C3, rifiuto solo da EMESSA)
- 11: stessa offerta → annulla (BOZZA → ANNULLATA) → verifica stato +
  `motivazione_rifiuto` salvata
- 12: cleanup finale

### 5.3 Smoke test UI

Manuale, end-to-end, da fare in browser dopo deploy locale:

- Creazione offerta + selezione BA (verifica `istanza_utility_id`/`utility_id`
  auto-popolati in sola lettura) + compilazione **sezione utility inline**
  (tipo/classe utenza + parametri) + auto-save BOZZA
- Emissione → accettazione → push, verifica navigation verso `ContrattoDrawer`
  post-push e contratto con utility completa copiata (incl. tipo/classe utenza
  e parametri)
- Verifica badge "SCADUTA" su offerta EMESSA con `validita_al` superata
- Verifica readonly drawer per offerte non in BOZZA (testata + sezione utility
  inline + eccezioni)
- Verifica catena revisioni (rev.1 EMESSA → crea rev.2 → rev.1 SUPERATA,
  rev.2 BOZZA)
- Verifica annullamento da BOZZA via `OffertaEsitoDialog` modalità ANNULLATA,
  motivazione obbligatoria, stato finale ANNULLATA con motivazione visibile
- Verifica rifiuto da EMESSA via `OffertaEsitoDialog` modalità RIFIUTATA,
  motivazione obbligatoria salvata
- Verifica che il bottone "Annulla offerta" **non compare** su offerta EMESSA
  (C3) e "Registra rifiuto" non compare su BOZZA
- Verifica filtro utility nella lista

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
                      FE-2 (lista)  FE-3 (drawer 3 tab)  FE-5 (dialogs)
                                        │
                                  FE-4 (panel eccezioni)
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
  step 1-3 (tabelle + ALTER esistono). I metodi che chiamano fn DB
  (`crea_revisione`, `push_a_contratto`) si stub-bano e si completano quando
  le fn esistono.
- **FE-1/FE-2 in parallelo a BE-4**: appena gli endpoint sono firmati (anche
  prima dell'implementazione), il FE può scrivere api client + store con dati
  mock e SearchTable contro mock. Si collega al BE reale quando disponibile.
- **i18n FE-6 in parallelo a FE-3/FE-4/FE-5**: il file `it.json` si compila
  man mano che i componenti chiedono nuove chiavi (non aspettare la fine).

### 6.3 Critical path stimato (indicativo, dipende dal team DB)

| Settimana | DB                                   | BE                                        | FE                                              |
| --------- | ------------------------------------ | ----------------------------------------- | ----------------------------------------------- |
| 1         | Step 1-3 (seed + tabelle + ALTER)    | BE-1 (types) inizia                       | —                                               |
| 2         | Step 4-6 (state machine + revisione) | BE-2 (repository) + BE-3 (service inizio) | FE-1 (api+store) con mock                       |
| 3         | Step 7-8 (fn rev + push)             | BE-3 (service) completa + BE-4 (API)      | FE-2 (lista) + FE-3 (drawer scaffold)           |
| 4         | Step 9 (pgTAP suite completa)        | Test BE + smoke 5.2                       | FE-3/4/5 completi + FE-6 i18n + FE-7 navigation |
| 5         | —                                    | Smoke UI 5.3 + bugfix                     | Smoke UI 5.3 + bugfix                           |

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
  (oggi solo ossatura, vedi §11.2.5 di quel documento). Dipende dall'esistenza
  reale del dominio → è davvero l'ultimo passo, dopo che BE+FE girano.
- **Branch**: lavoro su `dev/backend-tid` come da prassi (AGENTS.md §Ambiente
  di sviluppo).
- **Test idempotenza obbligatorio**: il caso "doppio push offerta → secondo
  fallisce con codice semantico" è obbligatorio sia in BE-3 (test_service
  mock) sia in smoke 5.2 step 7 (vedi convenzione §6.9.5 documento pratiche).

---

## 8. Stato del piano

| Step | Stato    | Dipendenze                                                                  |
| ---- | -------- | --------------------------------------------------------------------------- |
| BE-1 | Pronto   | Brief DB step 2-3 **+ addendum §0.3** (colonna `motivazione_rifiuto`, stato `ANNULLATA` + transizioni C3) |
| BE-2 | Pronto   | BE-1 + Brief DB step 2-3 + addendum                                         |
| BE-3 | Pronto   | BE-2 + Brief DB step 4-8 + addendum (state machine `ANNULLATA`)             |
| BE-4 | Pronto   | BE-3                                                                        |
| FE-1 | Pronto   | BE-4 (firma endpoint, anche solo bozza)                                     |
| FE-2 | Pronto   | FE-1                                                                        |
| FE-3 | Pronto   | FE-1                                                                        |
| FE-4 | Pronto   | FE-3                                                                        |
| FE-5 | Pronto   | FE-3                                                                        |
| FE-6 | Continuo | Parallelo a FE-3/4/5                                                        |
| FE-7 | Pronto   | FE-2/3 testabili                                                            |

> **Blocco esplicito**: BE-1 non può consolidare il `TypedDict` finale finché
> il team DB non ha recepito l'**addendum §0.3** (motivazione_rifiuto +
> ANNULLATA). Si può comunque scrivere lo scaffold del TypedDict in parallelo
> all'addendum, con il riserbo che il campo `motivazione_rifiuto` e lo stato
> `ANNULLATA` riflettano la versione finale dell'addendum.

---

*Piano BE + FE Offerta Commerciale — ZeroErp. Revisione 2026-05-24c
(rifiniture coerenza: utility inline in testata C1, endpoint utility mirror
contratto C2, state machine asimmetrica BOZZA→ANNULLATA / EMESSA→RIFIUTATA C3,
coerenze numeriche C4, dipendenza addendum DB esplicitata C5, test/smoke
estesi C6). Eredita rev. b: GAP 1 utility ricca, GAP 2/3 no giornale/allegati,
GAP 4 motivazione_rifiuto, GAP 5 ANNULLATA. Alcune correzioni toccano il brief
DB già accettato — vedi §0.3 (addendum). Pronto per applicazione su
`dev/backend-tid` dopo recepimento addendum DB. Documento vivo, da aggiornare
a ogni step chiuso.*
