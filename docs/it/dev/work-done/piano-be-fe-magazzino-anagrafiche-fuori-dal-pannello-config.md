# Piano BE/FE — le anagrafiche di magazzino escono dal pannello config, e il pannello si sana

> **Piano operativo** (cosa va fatto adesso), nato il **2026-09-20** da un rilievo
> di Tid in-app: *«in Gestione tabelle, `Causali` ha le label sbagliate; `Lotti`,
> `Magazzini`, `Ubicazioni` sono messe peggio, e non sono sicuro che il drawer
> che compare sia corretto per inserimento/modifica»*.
> Decisione presa lo stesso giorno (§2, opzione **B**). ✅ **Le otto domande di §8
> sono decise da Tid il 2026-09-21**, tutte sulla raccomandazione: si parte dal
> Pezzo A. Prerequisiti DB nel brief
> [brief-db-magazzino-anagrafiche-guard-ubicazioni-e-codici.md](brief-db-magazzino-anagrafiche-guard-ubicazioni-e-codici.md).
> **Stato:** ✅ **CHIUSO e archiviato in `work-done/` il 2026-09-21** (sera).
> Il riquadro sotto dice che cosa è consegnato e che cosa resta; il resto del
> documento è com'era, registro compreso.
>
> **✅ CHIUSO — 2026-09-21.** I **quattro pezzi sono a codice, riletti e con i
> loro presidi**; il mirror `ui` (liste 80-82) è applicato e il **collaudo
> in-app** è fatto da Tid: un magazzino nuovo e un'ubicazione caricati dalla
> voce «Magazzini». Gli scostamenti dal piano sono dichiarati nel corpo (§5:
> drawer autonomo al posto del form sotto la lista) e nel registro §11.
>
> | Pezzo | Stato | Dove si legge |
> | --- | --- | --- |
> | **A** — pannello config sanato | ✅ etichette, date, FK→lookup, errori parlanti, lista che non ingoia; registro senza i tre di magazzino (e senza `config.stati`, `config.titoli_cortesia`) | §3, `api_config_tables.md` |
> | **B** — Magazzini | ✅ `GET/POST/PATCH /magazzino/magazzini/` + export; lista 80, `MagazziniListView`, `MagazzinoDrawer` (indirizzo dal soggetto emittente, Q-2) | §4, `api_anagrafiche_magazzino.md` |
> | **C** — Ubicazioni | ✅ sotto il padre; lista 81, `MagazzinoUbicazioniDrawer` + `UbicazioneDrawer` (padre dal lookup del magazzino, R-1 a DB) | §5 |
> | **D** — Lotti | ✅ per articolo; lista 82, `ArticoloLottiDrawer` + `LottoDrawer` montati da catalogo (Q-1) | §6 |
> | **Rilettura critica** | ✅ tre bug muti corretti (indirizzo dell'admin, cache del picker del padre, 404 che lasciava il drawer aperto) e tre BB per regola del 2 (`useAzioniAttivo`, `max_len` su `extract_optional_string`, `app-riepilogo-*`) | §11 |
> | **Collaudo in-app** | ✅ magazzino + ubicazione (Tid, 21-09). ⚠️ I **lotti** non sono stati provati a video: il percorso è lo stesso delle ubicazioni, ma resta un fatto non verificato | §9 passo 6 |
>
> **Che cosa resta, e dove va:**
>
> * 🔵 **`config.titoli_cortesia`** (P-4): senza `codice`/`attivo`, senza
>   consumatori, fuori dal pannello e da `REL_CONSENTITE` — o guadagna le due
>   colonne o si ritira come dato morto. **Decisione al team DB / Tid**.
> * ✅ **`magazzino.lotti` nell'elenco del pgTAP delle liste globali** (R-3 del
>   [brief DB](brief-db-magazzino-anagrafiche-guard-ubicazioni-e-codici.md)):
>   scritto dal team DB, `test-lista-definizione-perimetro-emittente-v1.sql`
>   test 6.
> * ✅ **Il lock su `ubicazioni.magazzino_id`** (D1 del brief DB): generato dal
>   job delle automazioni — il BE continua a non mandarlo nel PATCH e a non
>   provarlo, la colonna non è nel form.
> * 🔵 Candidati dichiarati a catalogo per `useAzioniAttivo`:
>   `EmittenteFiscaleRegistriTab`, `FamiglieDocumentoListView`.
> * 🔵 `apps.md` di magazzino è ancora il template `${app}` (fuori da questo
>   piano); la riga di §0-bis/§11 del
>   [piano Lotto 2](piano-be-fe-magazzino-lotto-2-motore.md) è scritta.
> * ⏳ **Commit** (Tid).
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
| 🔴 **`Lotti` è rotta**: la lista del pannello passa da `fn_list_lookup_codici`, che rifiuta `magazzino.lotti` (`E_CORE_VALIDATION`, non è in `REL_CONSENTITE` e non ha `descrizione`) | [views_config_crud.py:47-63](../../../../backend/apps/core/api/views_config_crud.py#L47-L63) → [ConfigTablePanel.vue:105-108](../../../../frontend/src/core/components/ConfigTablePanel.vue#L105-L108) | il **400** viene ingoiato da `catch { items = [] }`: lista vuota, nessun errore, nessun toast. Il piano Lotto 2 §3.1 diceva *«il pannello legge `information_schema` e non ne ha bisogno»* — vero per il **drawer**, falso per la **lista**. È il caso di `feedback_contratto_dichiarato_provalo_intero`, e il registro di quel piano lo ammette («non provato a video») |
| `config-tables.js` ha un campo `drawer` («null = generico») che **nessuna riga valorizza** e che `ConfigTablePanel` **non legge** | [config-tables.js:4](../../../../frontend/src/core/config-tables.js#L4), [ConfigTablePanel.vue:296](../../../../frontend/src/core/components/ConfigTablePanel.vue#L296) | il meccanismo del «drawer dedicato associabile» (`feedback_pattern_config`) è dichiarato e mai cablato |

Cosa **non** è un difetto di questo piano: la `DataTable` grezza di `ConfigTablePanel`
è già nel registro del debito del [piano PrimeVue 5](../work-in-progress/piano-migrazione-primevue-5.md)
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
| **FK → `LookupSelect`** | `config_metadata_repository.py` (BE) + `GenericConfigDrawer.vue` | il metadata emette `references: "<schema>.<tabella>"` e `references_column` per le colonne FK (da `pg_constraint`: `conkey`/`confkey`). Il drawer: se `references_lookup` ⇒ `<LookupSelect :rel :value-field="references_column">` (⚠️ una FK non punta per forza a `id`: `stati_doc_*.esito` e `template_flussi.esito_default` → `esiti_flussi_pratiche(codice_interno)` — col default `id` il drawer avrebbe salvato un intero in una colonna testo, trovato in revisione il 21-09); altrimenti resta un valore a mano (numero o testo secondo il tipo) **e lo dichiara** (hint sotto il campo). Copre da solo le FK verso vocabolari (`config.iva.natura_iva_id`, `classi_utenze.tipo_utenza_id`, `tipi_soggetto_dettaglio.stato_id`, …). ⚠️ Il metadata deve dire anche se la tabella target è ammessa al lookup: lo sa il BE (`REL_CONSENTITE`), non il FE — esce come `references_lookup: bool` |
| **Date** | `GenericConfigDrawer.vue` | `type === 'date'` ⇒ `DatePicker` (`toDateString`/`parseIsoDate` di `core/utils/date.js`); `datetime` resta fuori dal form (sono audit, già esclusi) |
| **Colonne generate** | `_EXCLUDED_COLUMNS` | `uid` si esclude come `tx_id`: identità tecnica, la scrive il DB. ⚠️ Regola, non elenco: *una colonna il cui default è una **funzione** e che non è mai un dato dell'operatore*. Oggi è la sola |
| **Errori DB parlanti** | `config_crud_service.py` | via da `except IntegrityError → E_ANAG_DUPLICATO`: si usa `translate_db_errors` (BB) — UNIQUE → duplicato **col campo** (`fields`), `CHECK`/FK/NOT NULL → il loro codice, `P0001` dei trigger → il codice del DB (`CODICE_NON_MODIFICABILE`, `E_ATTIVO_BLOCK_CHILDREN_EXIST`) invece di «duplicato» |
| **La lista non ingoia** | `ConfigTablePanel.vue` | il `catch` diventa un toast (`useApiHandler`): un 400 su una tabella dichiarata ammessa è un difetto da vedere, non una lista vuota |
| **Registri allineati** | `config-tables.js` + `dbops_repository.CONFIG_TABLES` | escono `magazzino.lotti`, `magazzino.magazzini`, `magazzino.ubicazioni`. `CONFIG_TABLES` torna **uguale** a `REL_CONSENTITE` (il superset era nato solo per i lotti): si valuta se tenerlo come alias o toglierlo — Q-6. `magazzini`/`ubicazioni` **restano** in `REL_CONSENTITE`: i picker del documento interno le usano |
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
| `MagazzinoDrawer` (`DRAWER_WIDTH.STANDARD`) | `codice` (lucchetto in edit: `isFieldLocked`, lo dice il trigger), `descrizione`, **emittente** con `EmittenteFiscaleField` (sola lettura, dal contesto in create / dal record in edit), **indirizzo**: `InputText` in sola lettura con `indirizzo_normalizzato` + pulsante «Scegli» accanto (`app-input-with-action`, niente CSS scoped) che apre `IndirizziSoggettoDrawer selectable` sul soggetto dell'emittente (`emittente_soggetto_id` del record in edit; `soggettoIdSessione` di `useEmittenteFiscaleField` in create — ⚠️ per il super admin arriva dal lookup admin, che dal 21-09 proietta `soggetto_id`), accettando solo righe con `indirizzo_dettaglio_id` (un `indirizzo_libero` non è un dettaglio: si vede, non si sceglie, col motivo) — Q-2; `usa_ubicazioni`, `predefinito`, `attivo` (solo edit). In edit: sezione riepilogo «Ubicazioni (N)» + «Gestisci ubicazioni» (`app-riepilogo-*` di `main.css`, lo stampo di `ArticoloDrawer` §UoM). `useDrawerContentReady`, `useInjectReadonly`, `FormFooter`, `useDrawerDetailLoad` (un 404 no-leak chiude il drawer col toast) |
| Producer cross-tab | lo store (`createCrudStore`) emette `TAB_ENTITIES.MAGAZZINO` e in `afterWrite` invalida il lookup `magazzino.magazzini` nelle due chiavi del `rel`: le liste e i picker che mostrano un magazzino si rinfrescano da soli. Le azioni «Disattiva/Riattiva» del kebab sono il BB `useAzioniAttivo` |

## 5. Pezzo C — Ubicazioni *(figlie del magazzino)*

| Cosa | Note |
| --- | --- |
| BE: `GET/POST /magazzino/magazzini/<id>/ubicazioni/` · `GET/PATCH .../ubicazioni/<uid>/` · `export/` | padre nel path; il perimetro è la **testata** (magazzino fuori scope ⇒ 404 prima di leggere le figlie); lista offset-based; display: `tipo_descrizione`, `parent_codice`. Payload: `codice` obbligatorio, `tipo_id` (lookup `config.tipi_ubicazione`), `parent_id` (una ubicazione **dello stesso magazzino**: il picker lo filtra — e il DB? Q-3), `area/corsia/scaffale/piano/posizione`, `descrizione`, `attivo` |
| FE: `MagazzinoUbicazioniDrawer` (autonomo, prop `magazzinoId`) | `useDrawerTabLista` + `<DrawerTabLista>` su `magazzino.ubicazioni` (⛔ non una `DataTable` in un drawer) + `UbicazioneDrawer` autonomo aperto dalla riga e da «Nuova» (⚠️ scostamento da «form sotto la lista», dichiarato nel registro: è la forma dei due precedenti `TitoliIvaSoggettoDrawer`/`EmittenteFiscaleRegistriDrawer`). Il picker del padre è `LookupSelect` col fetcher del magazzino (chiave `chiaveLookupUbicazioni(id)`, invalidata dallo store a ogni scrittura) e `exclude-value` sull'ubicazione stessa — ⛔ non nel `transform`: la cache di `useGlobalLookup` tiene il primo transform per chiave. Azioni di riga: `useAzioniAttivo`. Raggiungibile dal kebab della lista magazzini **e** da «Gestisci ubicazioni» nel drawer. Se `usa_ubicazioni = false` il drawer si apre lo stesso con l'avviso «questo magazzino non usa le ubicazioni» (il dato lo governa il flag, non l'assenza di righe) |
| Lookup esistente | `lookup_ubicazioni(magazzino_id)` del documento interno resta |

## 6. Pezzo D — Lotti *(figli dell'articolo)*

| Cosa | Note |
| --- | --- |
| BE: `GET/POST /magazzino/lotti/?articolo_id=` · `GET/PATCH /magazzino/lotti/<id>/` · `export/` | `articolo_id` **obbligatorio** in lista (un elenco di tutti i lotti di tutti gli articoli non è una domanda di nessuno; il cancello empty-state dello store lo dice). Niente RLS (`lotti` è dell'articolo: brief Lotto 1 §4.3). Payload: `codice`, `data_arrivo` obbligatori, `data_scadenza` ≥ `data_arrivo` (lo dice `chk_mag_lotti_scadenza_dopo_arrivo`: il BE traduce, non ricontrolla), `attivo`. Errori: `uq_mag_lotti_articolo_codice` → duplicato su `codice`; `E_ATTIVO_REQUIRE` dell'articolo non attivo (TECNICO: il drawer non si apre su un articolo disattivo — lo legge dal dettaglio, prima). Il lookup `lotti/lookup/` resta (attivi, per il form di riga) |
| FE: `ArticoloLottiDrawer` (autonomo, prop `articoloId`) | stesso scheletro di C (`DrawerTabLista` + `LottoDrawer` autonomo, `useAzioniAttivo`, `useDrawerDetailLoad`). Montato in `ArticoloDrawer` (sezione «Lotti (N)» + «Gestisci lotti», visibile quando `gestito_a_magazzino` — un lotto ha senso solo su merce che movimenta; con `requires_lotto` la sezione lo **dice**) e in `ArticoliView` (kebab). Dove vive il file: Q-1 |

## 7. Richieste al DB e prerequisiti

Nessun DDL nuovo per i pezzi A–D: tabelle, trigger e vincoli ci sono già. Restano:

| # | Cosa | Chi | Blocca |
| --- | --- | --- | --- |
| P-1 | **Tre liste a catalogo** — `magazzino.magazzini`, `magazzino.ubicazioni`, `magazzino.lotti` (`ui.lista_definizione` + `lista_colonna`, con `formato = date_short` sulle date e `etichetta_i18n_key` su ogni colonna). È **dato, non DDL**: righe generate con `scripts/gen_seed_lista.py`, riviste, poi **apply del mirror `ui`: Tid** (come per le liste 70-77) | BE/FE genera, Tid applica | B, C, D (le liste) |
| P-2 | **Tre codici a catalogo, classe `NON_TROVATO`**: `E_MAG_MAGAZZINO_NON_TROVATO`, `E_MAG_UBICAZIONE_NON_TROVATA`, `E_MAG_LOTTO_NON_TROVATO`. Verificato il 20-09 nel modulo generato: **nessuno dei tre esiste** — c'è `E_MAG_DOCUMENTO_NON_TROVATO` (il documento interno), e `_magazzino_o_400` risponde `E_VALIDAZIONE` col campo perché lì il magazzino è un **dato di form**; sul dettaglio `GET /magazzini/<id>/` la persona chiede una risorsa che non vede: è un 404. Riga in `codici_errore.csv` + `genera_error_policies` + ripiego senza `%s` (`feedback_ripiego_ogni_codice_vivo`) | team DB / Tid | B, C, D (i 404) |
| P-4 | ⚠️ **`config.titoli_cortesia`: che cosa farne** — solo `id`, `descrizione`, `descrizione_breve`; senza `codice` ne' `attivo`, senza consumatori nel BE ne' nel FE. Era nel registro del pannello e in `REL_CONSENTITE` ed era un **500** (trovata dal presidio del Pezzo A, 21-09, insieme a `config.stati` che invece ha lookup e drawer propri). Uscita da entrambi. O guadagna `codice`/`attivo` (e torna), o e' un dato morto da ritirare (`analisi-software-per-dati-morti`) | team DB / Tid | no |
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
| **Q-6** | `CONFIG_TABLES` (BE) torna uguale a `REL_CONSENTITE`: tenerlo come alias o usare direttamente `REL_CONSENTITE` nei quattro consumer | **Toglierlo**: due nomi per lo stesso insieme sono la forma in cui divergono |
| **Q-7** | Nome dei file BE: `anagrafiche_magazzino_{repository,service}.py` dentro `apps/magazzino` | ok così; alternativa `strutture_*` (magazzini+ubicazioni) e lotti nel repository generico — sconsigliata, spezza le tre |
| **Q-8** | Export sulle tre liste: sì per magazzini (anagrafica), e per le due figlie in drawer? | **Sì su tutte e tre**: costa una view `…/export/` con `lista_codice = ApiLista.lista_codice` e il presidio delle coppie le conta. Un elenco di ubicazioni stampato è un fatto di magazzino |

## 9. Ordine dei passi

| # | Passo | Chi | Dipende da |
| --- | --- | --- | --- |
| 1 | ✅ Q-1…Q-8 decise (21-09) | Tid | — |
| 2 | ✅ **Pezzo A** (21-09: pannello sanato, i tre fuori dal registro FE e BE; trovate e tolte anche `config.stati` e `config.titoli_cortesia`) | BE/FE | 1 |
| 3 | ✅ P-2 e P-3 **applicati dal DB il 21-09** (brief §5); ✅ P-1: le righe di seed delle tre liste (80-82: `lista_definizione`, 35 `lista_colonna`, 3 preset, `preset_colonna`) sono nei CSV dal 21-09 — ⏳ **apply del mirror `ui`: Tid**; ✅ il nome `magazzino.lotti` nell'elenco del pgTAP delle liste globali (`ui/test-lista-definizione-perimetro-emittente-v1` test 6, DB, 21-09 sera: era il rosso «che la CI non conosce» sullo scratch) | BE/FE genera → **team DB / Tid applica** | 1 |
| 4 | ✅ **Pezzo B + C + D BE** (21-09): `views_anagrafiche.py`, `anagrafiche_magazzino_{service,repository}.py`, 15 rotte; test service (8, mock), API (8), **DB provvisto** (6: guard e codici veri, 404 dell'altro emittente, ogni ordinamento) | BE | 1 |
| 5 | ✅ **Pezzo B + C + D FE** (21-09): `MagazziniListView` + `MagazziniSearchTable` + `MagazzinoDrawer` + `MagazzinoUbicazioniDrawer` + `UbicazioneDrawer` + `ArticoloLottiDrawer` + `LottoDrawer`, tre store, voce L2 «Magazzini», montaggio in `ArticoloDrawer`/`ArticoliView`; ✅ **riletto** la sera stessa (§11: tre bug muti, tre BB per regola del 2). ⚠️ **Non provato a video**: le liste 80-82 non sono ancora a DB (passo 3) — finche' il mirror `ui` non e' applicato le tre `<ListaConfigurabile>` rispondono `E_UI_LISTA_NON_TROVATA` | FE | 3 applicato, 4 |
| 6 | ⏳ `kill -HUP` su gunicorn, smoke a mano + **collaudo in-app** (dopo il passo 3); ✅ doc: catalogo BB (FE e BE, aggiornati anche per `useAzioniAttivo`, `app-riepilogo-*`, `exclude-value`, `max_len`), `api.md` §Endpoint attivi, `api_anagrafiche_magazzino.md`, `api_amm_software.md` §4.4 (`soggetto_id`); ⏳ §0-bis e §11 del piano Lotto 2 (riga scritta), `apps.md` di magazzino (e' ancora il template `${app}`: fuori da questo piano) | BE/FE | 5 |

## 10. Presidi

- ✅ BE: unit su service (8: validazione, 404, delta PATCH), API (8: envelope,
  rotte non intercettate, filtri tradotti, export sul dataset), **DB provvisto**
  (6, `richiedi_db_provvisto`): il magazzino di un altro emittente è 404 e non
  è in lista; padre di altro magazzino e scadenza prima dell'arrivo rifiutati
  dal DB e tradotti col campo; `CODICE_NON_MODIFICABILE` arriva come codice,
  non come «duplicato»; ogni colonna di whitelist produce SQL che parte.
  `test_payload_helpers` 75 per il `max_len` di `extract_optional_string`.
- Pannello config: test sul DB provvisto che **ogni colonna** delle tabelle del
  registro FE ha la sua chiave `config_panel.campi.*` in `it.json` **e** `en.json`
  (legge i locales dal repo, come `etichette.spec.js` fa per i vocabolari) — è
  l'unico modo di presidiare chiavi costruite dinamicamente; e un test che ogni
  `references` emesso dal metadata sia una rel esistente.
- ✅ FE: `vitest` sulla risoluzione del widget del generico (FK in whitelist →
  `LookupSelect`, FK fuori → numero dichiarato, `date` → `DatePicker`,
  etichetta fail-visible); `check_i18n_keys` a 0; `npm run guards`; il conteggio
  delle `DataTable` grezze **non sale** (`grep -rl "from 'primevue/datatable'"`).
  ⚠️ **Senza presidio automatico**, dichiarati: il picker del padre che non
  avvelena la cache (§5) e la chiusura del drawer sul 404 — si vedono solo al
  collaudo in-app, che è il passo 6.
- ✅ Presidio esistente fatto passare: `test_export_lista_codice_pari` (le tre
  coppie nuove), `test_perimetro_emittente_copertura` (le view di lista con
  `lista_codice` letterale, come le quattro del documento interno; i lotti in
  `_ESENZIONI`).

## 11. Registro

| Data | Cosa |
| --- | --- |
| 2026-09-22 | ✅ **I due residui DB del riquadro sono rientrati**, e il [brief DB](brief-db-magazzino-anagrafiche-guard-ubicazioni-e-codici.md) e' chiuso e archiviato qui accanto: `magazzino.lotti` e' nell'elenco del test 6 delle liste globali, e il lock su `ubicazioni.magazzino_id` e' generato (il PATCH continua a non mandare la colonna). Niente da fare lato BE/FE |
| 2026-09-21 (revisione B/C/D) | 🔍 **Rilettura critica del non committato, sei correzioni.** (1) 🔴 **Il super admin dentro un emittente non poteva scegliere l'indirizzo del magazzino**: `soggettoIdSessione` leggeva `soggetto_id` dal lookup admin degli emittenti, che NON lo proiettava — pulsante «Scegli» spento senza errore. Ora `list_emittenti_fiscali` lo porta (doc §4.4). (2) 🔴 **Il picker del padre dell'ubicazione avvelenava la cache condivisa**: il «senza me stessa» stava nel `transform`, che `useGlobalLookup` registra UNA volta per chiave — la seconda ubicazione aperta non vedeva la prima fra i padri. Ora `LookupSelect` ha `exclude-value` (a valle della cache), fetcher e transform sono puri e il magazzino e' catturato per valore. (3) 🔴 **Un 404 no-leak lasciava i tre drawer aperti e vuoti**: `useDrawerDetailLoad` (toast + chiusura), com'e' in `DocumentoInternoDrawer`. (4) `useMagazziniStore` era una copia a mano di `createCrudStore` (dettaglio, verbi, evento) + una riga: ora e' la factory con `afterWrite`. (5) Le chiavi ammesse del payload nel service erano una seconda copia delle colonne scrivibili del repository: derivate. (6) `MagazzinoDrawer` senza `<style scoped>` (indirizzo su `app-input-with-action`, riepilogo su utility globali); PATCH di magazzino e lotto su `handle_detail_patch`; `MANAGE_ICONS.DISATTIVA/RIATTIVA` e' un concetto e `FamiglieDocumentoListView` (stesso senso, altri glifi) e' allineata. ✅ **Regola del 2 (ok Tid, stesso giorno)**: `useAzioniAttivo` (core) al posto delle tre copie di «Disattiva/Riattiva» + conferma (chiavi i18n normalizzate: `esito_disattiva`/`esito_riattiva`, etichette in `common`); `max_len` su `extract_optional_string` al posto del check a mano nel PATCH; `app-riepilogo-*` in `main.css` al posto degli `<style scoped>` di `ArticoloDrawer`/`SoggettoDrawer`/`MagazzinoDrawer` (in `SoggettoDrawer` la copia era gia' divergente: `.riepilogo-section` senza regola). Verde: BE magazzino/amm 60+17(DB)+147, ruff; FE vitest 193, lint, guards, i18n 0, `vite build` |
| 2026-09-21 (pomeriggio) | ✅ **Pezzi B, C, D scritti — BE e FE — dopo il push del brief DB** (R-1/R-2 applicati). **BE**: `genera_error_policies` rigenerato (SOLO i 6 codici nuovi nel diff), 6 ripieghi in `error_messages_fallback.py`; `db/anagrafiche_magazzino_repository.py` (whitelist di ordinamento con `colonne_desc`, colonne scrivibili per tabella, `_CAST` jsonb/uuid, LEFT JOIN sui display field, `emittente_soggetto_id` per l'indirizzo), `services/anagrafiche_magazzino_service.py` (PayloadValidator, delta, 404 no-leak, `make_db_errors_translator` con UNIQUE/FK/CHECK col campo), `api/views_anagrafiche.py` (15 rotte; `lista_codice` da costanti di modulo perche' il presidio del perimetro legge un `Name`, non un `Attribute`; i lotti SENZA `lista_codice` + esenzione «nessun `emittente_fiscale_id`»). ⭐ **Due estrazioni alla 2ª occorrenza, dichiarate qui e non a chat** (Tid aveva dato il via ai pezzi): `magazzino/db/_helpers.py` (`guard_canale_sistema`, `lista_paginata`, prima staticmethod di `MagazzinoRepository`) e `magazzino/api/_comuni.py` (`AREA`, `params_lista`, `PARAM_FORMATO`, `RISPOSTE_EXPORT`, `filtri_label`, `RISPOSTA_GENERICA`, prima privati di `views.py`) — materiale interno del dominio, stampo `services/_helpers.py`. **Seed** (P-1): liste 80-82 nei quattro CSV di `ui`, `emittente_ragione_sociale` ordinabile (nucleo del generatore), registrate in `_LISTE`, `_ESERCIZI` (proiezione), `WHITELIST_BE` del generatore; `verifica-ordinamento` verde sulle tre. **FE**: API, tre store (`createListaStore` + verbi, invalidazione dei lookup), `MagazziniSearchTable`/`MagazzinoDrawer` (indirizzo da `IndirizziSoggettoDrawer selectable` sul soggetto dell'emittente: `auth.emittenteCorrente.soggettoId` + `useEmittenteFiscaleField.soggettoIdSessione`, il record porta `emittente_soggetto_id`), `MagazzinoUbicazioniDrawer` → `UbicazioneDrawer` (padre da lookup del magazzino, chiave `chiaveLookupUbicazioni`), `ArticoloLottiDrawer` → `LottoDrawer` in `src/magazzino` montati da catalogo (Q-1), rotta + voce L2 (Q-4), `TAB_ENTITIES.MAGAZZINO`, `MANAGE_ICONS.{UBICAZIONI,LOTTO_MAGAZZINO,DISATTIVA,RIATTIVA}`, i18n it/en (`magazzino.{magazzini,ubicazioni,lotti,anagrafiche}.*`, `nav_menu.magazzino.magazzini`). ⚠️ **Scostamento dichiarato da §5**: le figlie NON hanno il form «sotto la lista» ma un drawer autonomo aperto dalla riga — e' la forma dei due precedenti nel repo (`TitoliIvaSoggettoDrawer`, `EmittenteFiscaleRegistriDrawer`), non una terza. **Verde**: BE 4969 (CI mode) + e2e magazzino/core 216 sul DB provvisto (compreso `test_lista_proiezione_campo_sorgente` sulle tre proiezioni), ruff; FE vitest 193, eslint, `npm run guards`, `check_i18n_keys` 0, `check_classi_morte` 0, DataTable grezze 44 → 44, `vite build`. ⏳ **Da fare**: apply del mirror `ui` (Tid), ~~`magazzino.lotti` nel pgTAP delle liste globali (DB)~~ ✅ 21-09 sera, `kill -HUP` su gunicorn, collaudo in-app |
| 2026-09-21 (revisione) | 🔍 **Revisione critica del Pezzo A, quattro correzioni.** (1) 🔴 **FK verso colonna ≠ `id`**: quattro FK del registro puntano a `esiti_flussi_pratiche(codice_interno)` e il metadata leggeva solo la tabella → `LookupSelect` col `valueField` di default avrebbe salvato l'`id` in una colonna testo. Ora il metadata porta `references_column`, `references_lookup` e' vera solo se la colonna e' in `LOOKUP_COLONNE_VALORE` (BE, `dbops_repository`), il drawer passa `:value-field`, e il test 4 del presidio **pretende** che una FK verso tabella ammessa punti a una colonna del payload. (2) 🔴 **Metadata stantio al cambio tabella** (pre-esistente): `columns` non si azzerava al cambio di `rel` — la seconda tabella si apriva col form della prima e il BE, filtrando le colonne sconosciute, rispondeva `{}` con successo. `watch(rel)` azzera. (3) `campiErrati` non era legato a nessun input: il campo che il service spedisce non si accendeva. (4) FK a mano sempre `InputNumber` anche su colonna testo; messaggio CHECK con elenco colonne vuoto. Poi le tre segnalazioni minori (ok Tid): `_REL_CONSENTITE` → **`REL_CONSENTITE`** (pubblica: la leggono tre moduli); etichette del registro in **`config_panel.tabelle.<rel>`** it/en (65 chiavi, presidio = test 5 del registro, `label` tolto da `config-tables.js`, `getTableConfig` morto rimosso); asterisco «obbligatorio» solo su NOT NULL **senza** default (`has_default` nel metadata). Verde: unit + e2e 5/5 sul DB provvisto, vitest, eslint, ruff, `check_i18n_keys` |
| 2026-09-21 (poi) | ✅ **Pezzo A scritto e verde** (`inizia la parte che puoi fare, fermati quando c'è connessione con attività DB`). **BE**: `ConfigMetadataRepository` legge le FK (`references`, `references_lookup`: vera sse la tabella nominata e' in `REL_CONSENTITE`) e i vincoli (`get_table_constraints`), esclude `uid`; `ConfigCrudService` passa da `translate_db_errors` con le mappe **lette dal catalogo** (UNIQUE col campo, CHECK/FK col campo, NOT NULL col `column_name`, `P0001` dei trigger col loro codice — provato sul DB vivo: `CODICE_NON_MODIFICABILE` arriva com'e'); `CONFIG_TABLES` tolto (Q-6), `map_integrity_error` porta `fields` nel fallback. **FE**: `campoConfig.js` (puro, `widgetPerColonna` + spec), `GenericConfigDrawer` con etichette `config_panel.campi.*` (125 chiavi it/en), `DatePicker`, FK→`LookupSelect`/numero dichiarato, create senza campi vuoti; `ConfigTablePanel` non ingoia piu' (toast); registro senza i tre di magazzino e senza il campo `drawer` (Q-5). 🔴 **Il presidio nuovo** (`apps/core/tests/db/test_config_panel_registro_db.py`: ogni rel del registro FE risponde a lista e metadata, ogni colonna ha l'etichetta in it **e** en, ogni FK esiste) **ha trovato subito altre due righe rotte**: `config.stati` (le nazioni, senza `codice`: lookup dedicato e `StatiDrawer` esistono gia') e `config.titoli_cortesia` (senza `codice` ne' `attivo`, zero consumatori → P-4). Entrambe erano un 500 dichiarato ammesso. Whitelist a **87**. **Verde**: core 1160 + 132 sul DB provvisto, ruff, vitest 192, lint, guards, `check_i18n_keys` 0, DataTable grezze invariate, `vite build`. Doc: `api_config_tables.md`, `api_lookup_codici.md` (blocco config rigenerato dal codice: era gia' stantio di una riga), `api.md`, i due cataloghi BB, frontend-standards. ⏸️ **Fermo qui**: B/C/D vogliono R-2/R-3 del brief |
| 2026-09-21 | ✅ **Q-1…Q-8 decise da Tid**, tutte sulla raccomandazione (§8). Scritto il [brief DB](brief-db-magazzino-anagrafiche-guard-ubicazioni-e-codici.md): R-1 guard sul padre dell'ubicazione (Q-3 «ora»), R-2 i tre codici `NON_TROVATO`, R-3 le tre liste a catalogo. Si parte dal **Pezzo A**, che non dipende dal brief |
| 2026-09-20 | **Nascita.** Rilievo in-app di Tid su `causali`/`lotti`/`magazzini`/`ubicazioni` in «Gestione tabelle». Diagnosi provata sul percorso reale (§1): etichette = nomi colonna, FK = id grezzi, date = testo, ogni `IntegrityError` = «duplicato», `Lotti` con lista rotta (400 ingoiato). Tre opzioni con raccomandazione, **B decisa da Tid** (§2). Otto domande in §8, tre prerequisiti in §7. **Zero righe di codice**: si parte da Q-1 |
