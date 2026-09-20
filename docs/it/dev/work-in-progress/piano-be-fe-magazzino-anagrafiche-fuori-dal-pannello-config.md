# Piano BE/FE — le anagrafiche di magazzino escono dal pannello config, e il pannello si sana

> **Piano operativo** (cosa va fatto adesso), nato il **2026-09-20** da un rilievo
> di Tid in-app: *«in Gestione tabelle, `Causali` ha le label sbagliate; `Lotti`,
> `Magazzini`, `Ubicazioni` sono messe peggio, e non sono sicuro che il drawer
> che compare sia corretto per inserimento/modifica»*.
> Decisione presa lo stesso giorno (§2, opzione **B**). ✅ **Le otto domande di §8
> sono decise da Tid il 2026-09-21**, tutte sulla raccomandazione: si parte dal
> Pezzo A. Prerequisiti DB nel brief
> [brief-db-magazzino-anagrafiche-guard-ubicazioni-e-codici.md](brief-db-magazzino-anagrafiche-guard-ubicazioni-e-codici.md).
>
> Contesto: cantiere `acquisti + magazzino`, Lotto 2 «il motore»
> ([piano-be-fe-magazzino-lotto-2-motore.md](piano-be-fe-magazzino-lotto-2-motore.md)).
> Questo piano ne è un **figlio**: corregge una scelta del Pezzo 1 (§3.1 di quel
> piano, `magazzino.lotti` nel pannello config) che a video non ha retto.

## 0. In una riga

Il pannello «Gestione tabelle» è fatto per i **vocabolari** (`codice`, `descrizione`,
`attivo`, qualche flag). `magazzini`, `ubicazioni` e `lotti` non sono vocabolari:
sono **anagrafiche con chiavi esterne** — un magazzino ha un emittente e un
indirizzo, un'ubicazione ha un magazzino, un tipo e un padre, un lotto ha un
articolo e due date. Vanno nella loro casa (dominio magazzino / articolo), con i
drawer che il progetto già sa fare. `causali` resta nel pannello, e il pannello
smette di mostrare nomi di colonna, id grezzi e date in una casella di testo.

## 1. Il difetto, misurato sul codice (2026-09-20)

Provato sul percorso reale (service BE contro il DB di sviluppo, in transazione
con rollback), non dedotto dal nome dei file.

| Fatto | Dove | Conseguenza a video |
| --- | --- | --- |
| Il drawer generico etichetta ogni campo col **nome della colonna** (`{{ col.name }}`) | [GenericConfigDrawer.vue:149-178](../../../../frontend/src/core/components/GenericConfigDrawer.vue#L149-L178) | su `causali`: `segno`, `is_installazione_asset`, `consente_stock_negativo`, `meta`. Vale per **tutte** le 70 tabelle del registro FE; sui vocabolari passa inosservato perché `codice`/`descrizione` si leggono da soli |
| Il metadata legge solo `information_schema.columns`: **non sa cosa sia una FK** | [config_metadata_repository.py](../../../../backend/apps/core/db/config_metadata_repository.py) | ogni `*_id` è un `InputNumber` di id grezzo: `magazzino_id`, `tipo_id`, `parent_id` (ubicazioni), `indirizzo_dettaglio_id`, `emittente_fiscale_id` (magazzini), `articolo_id` come **testo uuid** (lotti). Struttura, non popolazione: **41 colonne FK** nelle 90 tabelle ammesse dal BE (`config.iva` ×5, `pratiche.template_flussi` ×6, `pagamenti.enti_incasso` ×4, `config.classi_utenze` ×3, …) |
| Il tipo `date` esiste nel metadata ma il drawer lo rende nel ramo «fallback» → `InputText` | GenericConfigDrawer.vue, ultimo `v-else` | `data_arrivo`, `data_scadenza`, `obsoleto_dal` (5 tabelle) si scrivono a mano |
| `uid` di `magazzini` (default `uuidv7()`) esce come campo **obbligatorio** (`uid *`) | `_EXCLUDED_COLUMNS` non lo conosce | l'operatore vede un campo che non deve compilare; per fortuna vuoto = non inviato |
| **Ogni `IntegrityError` è «Record già esistente»** (`E_ANAG_DUPLICATO`) | [config_crud_service.py:60-75](../../../../backend/apps/core/services/config_crud_service.py#L60-L75) | un `CHECK` violato (`segno` ≠ ±1), una FK sbagliata, un NOT NULL: tutti «duplicato». Non passa dal BB `map_integrity_error` (`feedback_payload_helpers_duplicati`) |
| 🔴 **`Lotti` è rotta**: la lista del pannello passa da `fn_list_lookup_codici`, che rifiuta `magazzino.lotti` (`E_CORE_VALIDATION`, non è in `_REL_CONSENTITE` e non ha `descrizione`) | [views_config_crud.py:47-63](../../../../backend/apps/core/api/views_config_crud.py#L47-L63) → [ConfigTablePanel.vue:105-108](../../../../frontend/src/core/components/ConfigTablePanel.vue#L105-L108) | il **400** viene ingoiato da `catch { items = [] }`: lista vuota, nessun errore, nessun toast. Il piano Lotto 2 §3.1 diceva *«il pannello legge `information_schema` e non ne ha bisogno»* — vero per il **drawer**, falso per la **lista**. È il caso di `feedback_contratto_dichiarato_provalo_intero`, e il registro di quel piano lo ammette («non provato a video») |
| `config-tables.js` ha un campo `drawer` («null = generico») che **nessuna riga valorizza** e che `ConfigTablePanel` **non legge** | [config-tables.js:4](../../../../frontend/src/core/config-tables.js#L4), [ConfigTablePanel.vue:296](../../../../frontend/src/core/components/ConfigTablePanel.vue#L296) | il meccanismo del «drawer dedicato associabile» (`feedback_pattern_config`) è dichiarato e mai cablato |

Cosa **non** è un difetto di questo piano: la `DataTable` grezza di `ConfigTablePanel`
è già nel registro del debito del [piano PrimeVue 5](piano-migrazione-primevue-5.md)
e resta lì; i dati di `causali.csv` sono corretti (`codice`/`descrizione` a posto).

## 2. Decisione — opzione B (Tid, 2026-09-20)

Tre alternative messe sul tavolo con raccomandazione; scelta **B**:

- **B — casa propria + generico sanato** ✅: magazzini, ubicazioni e lotti hanno
  endpoint, liste e drawer **propri**; il generico resta per i vocabolari e si
  sana (etichette, date, FK→lookup, errori, lista che non ingoia).
- ~~A — tutto nel pannello, generico che legge il modello~~ (metadata con le FK e
  un registro target→widget): meno file, ma «i lotti di *questo* articolo» e «le
  ubicazioni di *questo* magazzino» restavano una ricerca piatta su tutta la
  tabella, e i permessi di un'anagrafica di magazzino restavano sotto l'area
  `config`.
- ~~Solo il minimo~~: etichette + date + lotti fuori dal pannello, il resto dopo.

**La ragione sul modello, non sul rilievo**: `magazzini` è **per emittente**
(RLS, `trgfn_default_emittente_fiscale`, `trgfn_guard_emittente_scope`) e ha un
indirizzo; `ubicazioni` è figlia del magazzino con gerarchia (`parent_id`);
`lotti` è figlia dell'articolo (chiave naturale `articolo_id + codice`). Il
progetto tratta i figli con i **drawer autonomi** raggiungibili dal padre e
dalla lista (`ArticoloUomDrawer`, `ArticoloBomDrawer`; `feedback_drawer_autonomi`)
e le entità con FK con `EntityFormDrawer` — lo dice il catalogo BB FE alla voce
`GenericConfigDrawer`: *«per entità descrittive con store tipizzato + i18n + FK
usare invece `EntityFormDrawer`»*.

⚠️ **Conseguenza dichiarata**: creare un magazzino passa dall'area `magazzino`
(`DomainAPIView`, livello `TUTTO`), non più da `config`. Un profilo che oggi ha
`TUTTO` su `config` e `LETTURA` su `magazzino` perde la scrittura: è il posto
giusto in cui perderla.

## 3. Pezzo A — il pannello config, sanato *(core BE + FE, nessun prerequisito DB)*

Vale per **tutte** le tabelle del pannello, non per `causali` sola. Nessuna
riga per-tabella: il drawer generico resta metadata-driven, ma legge **più**
modello.

| Cosa | Dove | Come |
| --- | --- | --- |
| **Etichette** | `GenericConfigDrawer.vue` + `it.json`/`en.json` | dizionario `config_panel.campi.<colonna>` risolto con `labelOrCode` (fail-visible: chiave assente ⇒ nome colonna, cioè oggi). Le colonne sono un vocabolario **condiviso** fra tabelle (`codice` in 84, `descrizione` in 89, `attivo` 70, `codice_interno` 61, `meta` 58, `ordine` 23…): un dizionario piatto per nome è la forma giusta, e si allarga aggiungendo chiavi. Misurato: **182 nomi distinti** sulle 90 tabelle ammesse dal BE. ⚠️ Chiavi costruite dinamicamente ⇒ punto cieco di `check_i18n_keys.py`: il presidio è un test sul DB provvisto (§7) |
| **FK → `LookupSelect`** | `config_metadata_repository.py` (BE) + `GenericConfigDrawer.vue` | il metadata emette `references: "<schema>.<tabella>"` per le colonne FK (`information_schema.referential_constraints` + `key_column_usage`, stessa sorgente delle colonne). Il drawer: se `references` è in `_REL_CONSENTITE` ⇒ `<LookupSelect :rel>`; altrimenti resta `InputNumber` **e lo dichiara** (hint sotto il campo). Copre da solo le FK verso vocabolari (`config.iva.natura_iva_id`, `classi_utenze.tipo_utenza_id`, `tipi_soggetto_dettaglio.stato_id`, …). ⚠️ Il metadata deve dire anche se la tabella target è ammessa al lookup: lo sa il BE (`_REL_CONSENTITE`), non il FE — esce come `references_lookup: bool` |
| **Date** | `GenericConfigDrawer.vue` | `type === 'date'` ⇒ `DatePicker` (`toDateString`/`parseIsoDate` di `core/utils/date.js`); `datetime` resta fuori dal form (sono audit, già esclusi) |
| **Colonne generate** | `_EXCLUDED_COLUMNS` | `uid` si esclude come `tx_id`: identità tecnica, la scrive il DB. ⚠️ Regola, non elenco: *una colonna il cui default è una **funzione** e che non è mai un dato dell'operatore*. Oggi è la sola |
| **Errori DB parlanti** | `config_crud_service.py` | via da `except IntegrityError → E_ANAG_DUPLICATO`: si usa `translate_db_errors` (BB) — UNIQUE → duplicato **col campo** (`fields`), `CHECK`/FK/NOT NULL → il loro codice, `P0001` dei trigger → il codice del DB (`CODICE_NON_MODIFICABILE`, `E_ATTIVO_BLOCK_CHILDREN_EXIST`) invece di «duplicato» |
| **La lista non ingoia** | `ConfigTablePanel.vue` | il `catch` diventa un toast (`useApiHandler`): un 400 su una tabella dichiarata ammessa è un difetto da vedere, non una lista vuota |
| **Registri allineati** | `config-tables.js` + `dbops_repository.CONFIG_TABLES` | escono `magazzino.lotti`, `magazzino.magazzini`, `magazzino.ubicazioni`. `CONFIG_TABLES` torna **uguale** a `_REL_CONSENTITE` (il superset era nato solo per i lotti): si valuta se tenerlo come alias o toglierlo — Q-6. `magazzini`/`ubicazioni` **restano** in `_REL_CONSENTITE`: i picker del documento interno le usano |
| **Il campo `drawer` del registro** | `config-tables.js` | Q-5: o si cabla (il pannello monta il componente dichiarato al posto del generico) o si toglie. Un campo che nessuno legge è un contratto che mente |

Fuori perimetro, dichiarato: `segno` di `causali` resta un `InputNumber` (il
`CHECK` a DB lo presidia, e con gli errori tradotti il rifiuto dice la cosa
giusta); un widget «valore da CHECK» sarebbe un terzo tipo di campo che oggi
serve a una colonna sola.

## 4. Pezzo B — Magazzini *(BE + FE; prerequisito: la lista a catalogo, §7)*

### 4.1 BE — `apps/magazzino`

| Cosa | Note |
| --- | --- |
| `GET/POST /magazzino/magazzini/` · `GET/PATCH /magazzino/magazzini/<id>/` · `GET .../export/` | `DomainAPIView(area_funzionale="magazzino")`, lista **offset-based** su `<ListaConfigurabile>` (`limit`/`offset`, `{count, results}`, `fetch_paged_with_total`), whitelist `MAGAZZINI_SORT_COLUMNS` chiavata sul nome fisico + `descrizione_order_by`. La lista **non** riscrive lo scope: `magazzino.magazzini` è sotto RLS, `security_invoker` fa il perimetro; il dettaglio fuori scope è **404** (`E_MAG_MAGAZZINO_NON_TROVATO`, già a catalogo? → §7) |
| Display fields via JOIN | `indirizzo_normalizzato` da `anagrafiche.indirizzi_dettaglio`, `emittente_codice`/`ragione_sociale` come le altre liste del dominio (`feedback_display_fields_backend`) |
| Payload | `PayloadValidator` (`codice`, `descrizione` obbligatori; `indirizzo_dettaglio_id > 0` obbligatorio; `predefinito`, `usa_ubicazioni`, `attivo` bool; `meta` fuori dal form). `emittente_fiscale_id` **non** viaggia: lo mette `trgfn_default_emittente_fiscale('SOLLEVA')` dalla GUC; l'admin globale in «tutti» prende `E_EMITTENTE_NON_RISOLTO` (400 col campo) e va bene così — la regola è del DB |
| Errori | `make_db_errors_translator`: `uq_magazzini_codice` → duplicato su `codice`; `CODICE_NON_MODIFICABILE` (lock su `codice`, il PATCH manda solo il delta); `trgfn_magazzini_guard_usa_ubicazioni` → il suo codice; `E_ATTIVO_BLOCK_CHILDREN_EXIST` sulla disattivazione con ubicazioni/movimenti attivi |
| File | `db/anagrafiche_magazzino_repository.py` + `services/anagrafiche_magazzino_service.py` (le TRE anagrafiche insieme: magazzini, ubicazioni, lotti — AGENTS.md «non frammentare per entità»; `magazzino_service.py` è di fatto il service del documento interno, 541 righe, e non va gonfiato). Nome in Q-7 |
| Lookup esistente | `LookupSelect rel="magazzino.magazzini"` resta com'è (generico, RLS) |

### 4.2 FE — `src/magazzino`

| Cosa | Note |
| --- | --- |
| Voce «Magazzini» in `navigation.js` (`NAV_ICONS.MAGAZZINO` o icona dedicata) + rotta `/magazzino/magazzini` | prima voce L2 del dominio: le anagrafiche precedono i documenti |
| `MagazziniListView` + `MagazziniSearchTable` su `<ListaConfigurabile codice="magazzino.magazzini">` | `useListaConfigurabilePage` + `createCrudStore` (qui la lista **possiede** l'entità); filtri: ricerca, `FiltroToggle` «mostra non attivi»; export; kebab: «Ubicazioni» (apre il drawer autonomo, `MANAGE_ICONS`), «Disattiva/Riattiva» |
| `MagazzinoDrawer` (`DRAWER_WIDTH.STANDARD`) | `codice` (lucchetto in edit: `isFieldLocked`, lo dice il trigger), `descrizione`, **emittente** con `EmittenteFiscaleField` (sola lettura, dal contesto in create / dal record in edit), **indirizzo**: card con `indirizzo_normalizzato` + pulsante «Scegli» che apre `IndirizziSoggettoDrawer selectable` sul soggetto dell'emittente (`emittenti_fiscali.soggetto_ruolo_id → soggetti_ruoli.soggetto_id`), accettando solo righe con `indirizzo_dettaglio_id` (un `indirizzo_libero` non è un dettaglio: si vede, non si sceglie, col motivo) — Q-2; `usa_ubicazioni`, `predefinito`, `attivo` (solo edit). In edit: sezione riepilogo «Ubicazioni (N)» + «Gestisci ubicazioni» (stampo `ArticoloDrawer` §UoM). `useDrawerContentReady`, `useInjectReadonly`, `FormFooter` |
| Producer cross-tab | lo store emette `TAB_ENTITIES.MAGAZZINO` (da aggiungere all'enum): le liste che mostrano un magazzino si rinfrescano da sole |

## 5. Pezzo C — Ubicazioni *(figlie del magazzino)*

| Cosa | Note |
| --- | --- |
| BE: `GET/POST /magazzino/magazzini/<id>/ubicazioni/` · `GET/PATCH .../ubicazioni/<uid>/` · `export/` | padre nel path; il perimetro è la **testata** (magazzino fuori scope ⇒ 404 prima di leggere le figlie); lista offset-based; display: `tipo_descrizione`, `parent_codice`. Payload: `codice` obbligatorio, `tipo_id` (lookup `config.tipi_ubicazione`), `parent_id` (una ubicazione **dello stesso magazzino**: il picker lo filtra — e il DB? Q-3), `area/corsia/scaffale/piano/posizione`, `descrizione`, `attivo` |
| FE: `MagazzinoUbicazioniDrawer` (autonomo, prop `magazzinoId`) | `useDrawerTabLista` + `<DrawerTabLista>` su `magazzino.ubicazioni` (⛔ non una `DataTable` in un drawer) + form sotto (`RigheMasterDetailTable`-like: `formMode` null/new/edit). Raggiungibile dal kebab della lista magazzini **e** da «Gestisci ubicazioni» nel drawer. Se `usa_ubicazioni = false` il drawer si apre lo stesso con l'avviso «questo magazzino non usa le ubicazioni» (il dato lo governa il flag, non l'assenza di righe) |
| Lookup esistente | `lookup_ubicazioni(magazzino_id)` del documento interno resta |

## 6. Pezzo D — Lotti *(figli dell'articolo)*

| Cosa | Note |
| --- | --- |
| BE: `GET/POST /magazzino/lotti/?articolo_id=` · `GET/PATCH /magazzino/lotti/<id>/` · `export/` | `articolo_id` **obbligatorio** in lista (un elenco di tutti i lotti di tutti gli articoli non è una domanda di nessuno; il cancello empty-state dello store lo dice). Niente RLS (`lotti` è dell'articolo: brief Lotto 1 §4.3). Payload: `codice`, `data_arrivo` obbligatori, `data_scadenza` ≥ `data_arrivo` (lo dice `chk_mag_lotti_scadenza_dopo_arrivo`: il BE traduce, non ricontrolla), `attivo`. Errori: `uq_mag_lotti_articolo_codice` → duplicato su `codice`; `E_ATTIVO_REQUIRE` dell'articolo non attivo (TECNICO: il drawer non si apre su un articolo disattivo — lo legge dal dettaglio, prima). Il lookup `lotti/lookup/` resta (attivi, per il form di riga) |
| FE: `ArticoloLottiDrawer` (autonomo, prop `articoloId`) | stesso scheletro di C. Montato in `ArticoloDrawer` (sezione «Lotti (N)» + «Gestisci lotti», visibile quando `gestito_a_magazzino` — un lotto ha senso solo su merce che movimenta; con `requires_lotto` la sezione lo **dice**) e in `ArticoliView` (kebab). Dove vive il file: Q-1 |

## 7. Richieste al DB e prerequisiti

Nessun DDL nuovo per i pezzi A–D: tabelle, trigger e vincoli ci sono già. Restano:

| # | Cosa | Chi | Blocca |
| --- | --- | --- | --- |
| P-1 | **Tre liste a catalogo** — `magazzino.magazzini`, `magazzino.ubicazioni`, `magazzino.lotti` (`ui.lista_definizione` + `lista_colonna`, con `formato = date_short` sulle date e `etichetta_i18n_key` su ogni colonna). È **dato, non DDL**: righe generate con `scripts/gen_seed_lista.py`, riviste, poi **apply del mirror `ui`: Tid** (come per le liste 70-77) | BE/FE genera, Tid applica | B, C, D (le liste) |
| P-2 | **Tre codici a catalogo, classe `NON_TROVATO`**: `E_MAG_MAGAZZINO_NON_TROVATO`, `E_MAG_UBICAZIONE_NON_TROVATA`, `E_MAG_LOTTO_NON_TROVATO`. Verificato il 20-09 nel modulo generato: **nessuno dei tre esiste** — c'è `E_MAG_DOCUMENTO_NON_TROVATO` (il documento interno), e `_magazzino_o_400` risponde `E_VALIDAZIONE` col campo perché lì il magazzino è un **dato di form**; sul dettaglio `GET /magazzini/<id>/` la persona chiede una risorsa che non vede: è un 404. Riga in `codici_errore.csv` + `genera_error_policies` + ripiego senza `%s` (`feedback_ripiego_ogni_codice_vivo`) | team DB / Tid | B, C, D (i 404) |
| P-3 (Q-3) | Guard «`ubicazioni.parent_id` appartiene allo stesso magazzino» — oggi non c'è (solo `require_active_parent`). ✅ **Deciso «ora» da Tid (21-09)**: R-1 del brief, col codice `E_MAG_UBICAZIONE_PADRE_DI_ALTRO_MAGAZZINO`; il picker FE la **rispecchia**, non la sostituisce | team DB | no (il picker filtra intanto) |

## 8. Domande a Tid — ✅ tutte decise il 2026-09-21, sulla raccomandazione

> Q-1: il file sta in `src/magazzino/components` (Tid ha chiesto prima cosa fosse un
> lotto di magazzino: la **partita di merce** di un articolo — `articolo_id + codice`,
> `data_arrivo`, `data_scadenza`, nominata da `movimenti.lotto_id` quando
> `requires_lotto` — da non confondere con `vendite.fatturazione_lotti`, il giro di
> fatturazione). Q-2 **(a)**. Q-3 **ora** (brief, R-1). Q-4 voce propria. Q-5 si toglie.
> Q-6 si toglie. Q-7 `anagrafiche_magazzino_*`. Q-8 export su tutte e tre.

| # | Domanda | Raccomandazione |
| --- | --- | --- |
| **Q-1** | Dove vive `ArticoloLottiDrawer`: in `src/magazzino/components` (la tabella è di magazzino, l'API e lo store pure) importato da `catalogo`, o in `src/catalogo/components` accanto a UoM/BoM che chiama l'API di magazzino? | **`src/magazzino/components/ArticoloLottiDrawer.vue`**, montato da `ArticoloDrawer` e `ArticoliView`. È lo stesso verso di `catalogo → anagrafiche/api` (unico precedente cross-dominio FE) e il verso della mappa concentrica non c'entra: il FE è presentazione, e chi possiede il dato possiede il componente |
| **Q-2** | L'indirizzo del magazzino: (a) si **sceglie** fra gli indirizzi del soggetto emittente (`IndirizziSoggettoDrawer selectable`, che sa anche aggiungerne uno), oppure (b) form indirizzo **inline** nel drawer (`useIndirizzoBase`) che crea un `indirizzi_dettaglio` slegato dal soggetto | **(a)**: un magazzino sta a un indirizzo dell'azienda (sede, deposito), e così l'indirizzo compare nell'anagrafica del soggetto con il suo tipo. Con (b) nascerebbero `indirizzi_dettaglio` orfani di ogni soggetto |
| **Q-3** | Il vincolo «padre nello stesso magazzino» per le ubicazioni: brief DB ora, o dopo | **Ora, piccolo** (una guard `a10` sull'`INSERT/UPDATE OF parent_id`): il picker FE filtra, ma un client qualunque no — e «lo fa il FE» è la seconda sede di una regola |
| **Q-4** | `MagazziniListView`: voce L2 propria in sidebar, o dentro «Disponibilità» | **Voce propria**, prima del blocco documenti: `Magazzini · Inventari · Rettifiche · Disponibilità · Movimenti` |
| **Q-5** | Il campo `drawer` di `config-tables.js`: si cabla (il pannello monta il dedicato) o si toglie | **Si toglie**: con B nessuna tabella lo usa, e un meccanismo cablato senza consumatore è la cosa che questo piano sta correggendo. Torna il giorno che serve, con il suo primo caso |
| **Q-6** | `CONFIG_TABLES` (BE) torna uguale a `_REL_CONSENTITE`: tenerlo come alias o usare direttamente `_REL_CONSENTITE` nei quattro consumer | **Toglierlo**: due nomi per lo stesso insieme sono la forma in cui divergono |
| **Q-7** | Nome dei file BE: `anagrafiche_magazzino_{repository,service}.py` dentro `apps/magazzino` | ok così; alternativa `strutture_*` (magazzini+ubicazioni) e lotti nel repository generico — sconsigliata, spezza le tre |
| **Q-8** | Export sulle tre liste: sì per magazzini (anagrafica), e per le due figlie in drawer? | **Sì su tutte e tre**: costa una view `…/export/` con `lista_codice = ApiLista.lista_codice` e il presidio delle coppie le conta. Un elenco di ubicazioni stampato è un fatto di magazzino |

## 9. Ordine dei passi

| # | Passo | Chi | Dipende da |
| --- | --- | --- | --- |
| 1 | ✅ Q-1…Q-8 decise (21-09) | Tid | — |
| 2 | **Pezzo A** (pannello sanato, i tre fuori dal registro FE e BE) — chiude il rilievo su `causali` e toglie la lista rotta | BE/FE | 1 |
| 3 | P-1: righe di seed per le tre liste (`gen_seed_lista.py`), P-2: i codici, P-3: il guard — [brief DB](brief-db-magazzino-anagrafiche-guard-ubicazioni-e-codici.md) | BE/FE genera → **team DB / Tid applica** | 1 |
| 4 | **Pezzo B** BE (magazzini) + **C** BE (ubicazioni) + **D** BE (lotti) con test service/API e **DB provvisto** (RLS: 404 no-leak sul magazzino di un altro emittente) | BE | 1 |
| 5 | Pezzo B FE, poi C, poi D | FE | 3 applicato, 4 |
| 6 | Smoke a mano + collaudo in-app; aggiornare §0-bis e §11 del piano Lotto 2, catalogo BB (FE e BE), `api.md` §Endpoint attivi (Magazzino), `apps.md` di magazzino | BE/FE | 5 |

## 10. Presidi

- BE: unit su service (validazione, 404, delta PATCH), API (envelope, whitelist
  ordinamento → `test_ogni_ordinamento_dichiarato_produce_sql_valido` come per le
  righe del documento interno), **DB provvisto** (`richiedi_db_provvisto`): il
  magazzino di un altro emittente è 404 e non è in lista; un lotto su articolo
  disattivo è rifiutato dal DB e tradotto; `CODICE_NON_MODIFICABILE` arriva come
  codice, non come «duplicato».
- Pannello config: test sul DB provvisto che **ogni colonna** delle tabelle del
  registro FE ha la sua chiave `config_panel.campi.*` in `it.json` **e** `en.json`
  (legge i locales dal repo, come `etichette.spec.js` fa per i vocabolari) — è
  l'unico modo di presidiare chiavi costruite dinamicamente; e un test che ogni
  `references` emesso dal metadata sia una rel esistente.
- FE: `vitest` sulla risoluzione del widget del generico (FK in whitelist →
  `LookupSelect`, FK fuori → numero dichiarato, `date` → `DatePicker`,
  etichetta fail-visible); `check_i18n_keys` a 0; `npm run guards`; il conteggio
  delle `DataTable` grezze **non sale** (`grep -rl "from 'primevue/datatable'"`).
- Presidio esistente da far passare: `test_export_lista_codice_pari` (le tre
  coppie nuove), `test_perimetro_emittente_copertura` (le view di lista con
  `lista_codice` letterale, come le quattro del documento interno).

## 11. Registro

| Data | Cosa |
| --- | --- |
| 2026-09-21 | ✅ **Q-1…Q-8 decise da Tid**, tutte sulla raccomandazione (§8). Scritto il [brief DB](brief-db-magazzino-anagrafiche-guard-ubicazioni-e-codici.md): R-1 guard sul padre dell'ubicazione (Q-3 «ora»), R-2 i tre codici `NON_TROVATO`, R-3 le tre liste a catalogo. Si parte dal **Pezzo A**, che non dipende dal brief |
| 2026-09-20 | **Nascita.** Rilievo in-app di Tid su `causali`/`lotti`/`magazzini`/`ubicazioni` in «Gestione tabelle». Diagnosi provata sul percorso reale (§1): etichette = nomi colonna, FK = id grezzi, date = testo, ogni `IntegrityError` = «duplicato», `Lotti` con lista rotta (400 ingoiato). Tre opzioni con raccomandazione, **B decisa da Tid** (§2). Otto domande in §8, tre prerequisiti in §7. **Zero righe di codice**: si parte da Q-1 |
