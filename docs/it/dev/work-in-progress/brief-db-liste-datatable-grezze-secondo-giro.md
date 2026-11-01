# Brief DB — Liste ancora su `DataTable` grezza, secondo giro

## ⏭️ Chi riparte — aggiornato al 2026-11-01

**Riparte: BE** (`dev/backend-tid`) con il §7.8.5: la view della ricerca legge la soglia dal
catalogo (D-6). Il lato DB è chiuso: `20261101-01…03` applicati e pgTAP verdi (Tid, 2026-11-01).
Poi si archivia il brief.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | Tid | ✅ D-2 e B1-bis decisi il 2026-10-31 (§5.2) | questo brief | — |
| 2 | team DB | ✅ Seed delle liste (§2) e presidio delle note (§3.3), scritti il 2026-10-31 (§7.1, §7.3) | `80_data/sql/ui/`, `db/pgtap/` | — |
| 3 | team DB | ✅ La regola «in scadenza senza successore» a DB (§3.1), scritta il 2026-10-31 (§7.2) | `20_code/vendite/` | — |
| 4 | team DB | ✅ Visibilità della colonna emittente nella ricerca (§3.2): risposta «no», limite dichiarato | `ui` | — |
| 5 | Tid | ✅ Apply (`20261031-27` e i mirror dei CSV) e corsa pgTAP verde, 2026-10-31 (§7.5) | dbdev | — |
| 6 | BE/FE | ✅ Lavoro senza seed (§4.2) fatto il 2026-10-31: dialog di selezione, `MatriceCatalogo` (Reparto, Utilities), catch dell'alert. Registro a 24 | `dev/backend-tid` | — |
| 7 | BE/FE | ✅ Conversione delle 6 liste (§4.1), fatta il 2026-10-31: riga 5 al §4.3, righe 1-4 e 6 al §4.4 | `dev/backend-tid` | — |
| 8 | BE/FE | ✅ Registro `datatable.baseline.json` abbassato a **17** grezze, **0** senza motivo | `frontend/scripts/` | — |
| 8-bis | Tid | ✅ D-3 (nessun cambiamento), D-4 (strada 2 e caso gemello), D-5 (strada 1) decise il 2026-10-31, col via | §4.5.1, §4.6.1 | — |
| 9 | team DB | ✅ Ricerca universale sui campi del catalogo, `filtrabile = f` sulla 113 (§4.5.1, D-4), scritti il 2026-10-31 (§7.6) | `20_code/script/`, seed `ui` | — |
| 10 | team DB | ✅ La forma del valore di ogni parametro, rispettata in scrittura (§4.6.1, D-5), scritta il 2026-10-31 (§7.6) | `config`, `script` | — |
| 10-bis | Tid | ✅ Apply di `20261031-53…59` e dei mirror, 2026-10-31 (verificato: 56 parametri tipizzati, una firma della ricerca, i due trigger a07, i due codici d'errore, `filtrabile = f`). ✅ Corsa pgTAP verde (Tid, 2026-10-31) | dbdev | — |
| 9-bis | BE | ✅ L'elenco chiuso del §7.6.5, fatto il 2026-10-31 (§7.7): `p_campi_ricerca` dal BB `colonne_ricerca_attive`, la 113 registrata, l'eccezione al nucleo dichiarata, i due codici nuovi, l'helper col tipo | `dev/backend-tid` | — |
| 9-ter | team DB | ✅ I due guard a07 mettono il campo sotto `'campo'` (§7.7.1), e il pgTAP legge il canale `COLUMN`: scritto il 2026-11-01 (§7.8) | `20_code/config/`, `db/pgtap/config/` | — |
| 9-quater | Tid | ✅ D-6 decisa il 2026-11-01: la soglia della 113 viene dal catalogo, come per ogni lista (§7.7.2) | questo brief | — |
| 9-quinquies | team DB | ✅ D-6: `fn_search_soggetti_universale` senza la soglia scritta nel corpo (§7.7.2), scritto il 2026-11-01 (§7.8) | `20_code/script/`, `db/pgtap/script/` | — |
| 9-quinquies-bis | Tid | ✅ Apply di `20261101-01…03` su dbdev e corsa dei tre pgTAP verde, 2026-11-01 (§7.8.4) | dbdev | — |
| 9-sexies | BE | §7.8.5, D-6: la view della ricerca usa `soglia_ricerca('anagrafiche.ricerca_soggetti')` al posto di `RICERCA_MIN_CARATTERI`. Il test `test_valore_fuori_forma_non_si_salva` diventa verde da solo (§7.7.1) | `dev/backend-tid` | 9-quinquies-bis |
| 11 | BE/FE | ✅ Revisione critica del lavoro non committato, 2026-10-31 (§4.7) | `dev/backend-tid` | — |
| 12 | BE/FE | Archiviare il brief in `work-done/` | — | 9-sexies |

**Decisioni aperte di Tid:** nessuna. D-6 decisa il 2026-11-01 (§7.7.2); D-3, D-4 e D-5 decise il 2026-10-31 (§4.5.1, §4.6.1); D-1, D-2, B1-bis, B8 e l'ordinamento per utility della 113 (§4.5) decisi il 2026-10-31.
**Committato:** il terzo giro DB (§7.8) è committato su `dev/db-tid` (2026-11-01). Il lato DB, primo e secondo giro (§7.1-§7.6, con guida e pagine manual), è su `dev/db-tid` e mergiato in `dev/backend-tid` (#1988); il lato BE del §7.7 è committato su `dev/backend-tid`; il lato BE/FE (righe 6-8 e 11) è su `Tito-dev` (`82ea9e3a1`, PR #1987). Il rotto temporaneo
dichiarato fino alla conversione BE (Tid, 2026-10-31: «non ci preoccupiamo se
alcune liste andranno in errore temporaneamente») è **chiuso**: §7.4 tutto
fatto, verificato il 2026-10-31 (§7.4, in fondo).

---

> **Destinatari:** team DB (`dev/db-tid`) per §2 e §3; `dev/backend-tid` per
> §4. La conversione FE di una lista **parte solo a seed applicato**: senza le
> righe di catalogo `<ListaConfigurabile>` non ha colonne.
>
> **Tipo:** seed (`ui.lista_definizione` + `ui.lista_colonna`, preset dove
> serve) più una funzione `vendite` (§3.1). Nessuna DDL di tabella.
>
> **Decisioni:** di Tid, 2026-10-31 (§5.1). Il brief precedente,
> [brief-db-liste-datatable-grezze](../work-done/brief-db-liste-datatable-grezze.md),
> aveva lasciato aperte queste decisioni nel suo §5; ora sono prese.

## 1. Perché

`frontend-standards` §«Regola zero della lista»: una lista si monta con
`<ListaConfigurabile>`. Il criterio è il **modello**: un'entità con endpoint
suo, popolazione arbitraria e ciclo di vita indipendente è una lista, ovunque
sia montata.

Le sei righe del §2 sono liste vere per questo criterio. Due di loro hanno un
difetto che non dà errore, e la conversione lo chiude:

- 🔴 **`NoteDrawer` tronca a 200.** Chiede `limit=200`, il cap del BE, e non ha
  paginatore («tipicamente le note per documento sono poche decine»: è una
  previsione sui dati, non una regola del modello). Dalla 201ª nota in poi le
  note **spariscono senza errore**;
- 🔴 **La regola «versione in scadenza senza successore» sta in SQL nel
  repository BE** (`listini_repository.listini_in_scadenza`): è logica di
  business fuori dal DB (§3.1).

## 2. Richiesta al team DB — i seed

Le bozze si generano dal `.vue` di oggi, come nel giro precedente:

```bash
.venv/bin/python scripts/gen_seed_lista.py \
    --codice <codice> --descrizione "<descrizione>" \
    --vue <file .vue> [--vista <vista>]
```

⚠️ **I codici sono proposte.** Vince la convenzione del catalogo (prefisso =
schema dei dati) e il codice scelto va riportato qui, perché è quello che il FE
scriverà nel `.vue`.

| # | Codice proposto | `.vue` di partenza (sotto `frontend/src/`) | Righe da | Oggi |
| --- | --- | --- | --- | --- |
| 1 | `pratiche.definizioni_workflow` | `amministrazione/views/DefinizioniWorkflowListView.vue` | `GET pratiche/definizioni/` (`list_definizioni`) | non paginata, ordine fisso |
| 2 | `config.parametri_impostazioni` | `config/components/ImpostazioniSearchTable.vue` | `GET core/parameters/settings/` | carica tutto, ricerca nel client |
| 3 | `vendite.note` e `catalogo.note` (v. D-2) | `core/components/NoteDrawer.vue` | `GET <documento>/note/` (`PartitionedNoteRepository.list`, 6 partizioni di `vendite.note`); `GET catalogo/articoli/<id>/note/` e `…/componenti/<id>/note/` (partizioni di `catalogo.note`) | 🔴 vendite tronca a 200; catalogo non pagina |
| 4 | `catalogo.articolo_uom` | `catalogo/components/ArticoloUomDrawer.vue` | `GET catalogo/articoli/<id>/uom/` (`list_uom_operative`) | non paginata |
| 5 | `vendite.listini_versioni` | `vendite/components/ListiniSearchTable.vue` (la riga espansa) | `GET vendite/listini/<id>/versioni/` (`list_versioni`) | non paginata, nella riga espansa |
| 6 | `core.ricerca_soggetti` | `core/components/SearchDrawer.vue` | `GET core/search/` (`fn_search_soggetti_universale`) | paginazione e ordinamento scritti a mano |

Note per riga:

- **2 — i livelli sono colonne.** Default, emittente, gruppo, categoria
  cliente, utente e valore risolto: sei colonne, e l'operatore può ritirare i
  livelli che non usa (decisione B1). L'azione d'override resta nel kebab.
- **3 — un codice per tabella-madre `<schema>.note`**, che copre tutte le sue
  partizioni (D-2). Le colonne sono quelle del `_SELECT_COLUMNS` del BB e
  sono **le stesse** nei due codici: le tiene allineate il presidio del §3.3.
- **5 — una colonna in più.** Per il segno «in scadenza senza successore» la
  lista legge la funzione del §3.1;
- **anche `vendite.listini` (lista 27) si tocca**: le serve il filtro «versione
  in scadenza senza successore», che è la destinazione del link dell'alert
  (D-1). Filtro e colonna leggono la funzione del §3.1.
- **6 — la colonna emittente** (`emittente_ragione_sociale`) ha senso solo per
  i clienti: v. §3.2.

## 3. Richiesta al team DB — oltre i seed

### 3.1 «In scadenza senza successore» diventa una regola del DB

Oggi la regola è scritta solo in
`backend/apps/vendite/db/listini_repository.py` (`listini_in_scadenza`):

1. la versione in vigore alla data operativa
   (`fn_listino_versione_in_vigore`);
2. che scade entro N giorni;
3. di un listino attivo;
4. senza un successore attivo che nasca dopo la sua scadenza, in BOZZA oppure
   operativo con validità che copre il giorno dopo.

Si chiede **una funzione `vendite`** che la dica una volta sola, con i giorni
rimanenti, letta da tutti i consumatori: il filtro della lista listini (D-1),
la colonna della lista versioni e il conteggio del badge. A funzione applicata il BE ritira la query del repository **nello
stesso giro**: due copie della stessa regola divergono al primo ritocco.

⚠️ N (i giorni) oggi ha due default, 15 nel FE e `_ALERT_GIORNI_DEFAULT` nel
BE, e quello del BE non si raggiunge mai perché il FE lo manda sempre. La sede
giusta è un parametro di `config.parameters`: si chiede il seed del parametro
insieme alla funzione.

### 3.2 Colonna visibile secondo il filtro (ricerca soggetti)

La colonna emittente della ricerca ha senso solo quando il tipo ruolo cercato
è CLIENTE. Domanda al team DB: il catalogo liste ha già una condizione di
visibilità di colonna legata al valore di un filtro?

- **se sì**, la si usa;
- **se no**, la colonna resta sempre visibile e vuota per gli altri ruoli. Si
  scrive qui come limite dichiarato, senza inventare una regola nel FE.

✅ **Risposta del team DB (2026-10-31): no.** `ui.lista_colonna` non ha una
condizione di visibilità legata al valore di un filtro (la struttura: nessuna
colonna del genere, e `fn_resolve_lista_config` non ne legge una). Vale il
secondo ramo: la colonna `emittente_ragione_sociale` è a catalogo sempre
attiva, ed è vuota per i ruoli diversi da CLIENTE. Limite dichiarato.
L'operatore può nasconderla dal preset personale.

### 3.3 Presidio: le liste delle note restano gemelle

Le tabelle `<schema>.note` hanno tutte la stessa forma (`vendite`,
`catalogo`, `acquisti`, `magazzino`: stesse colonne, dalla doc auto-generata) e
il FE le legge con un BB solo. Due codici con le stesse colonne divergono al
primo ritocco fatto da una parte sola, senza errore.

Si chiede un pgTAP che **ricavi l'elenco dalla struttura e non dai seed**: per
ogni tabella `<schema>.note` che ha una lista a catalogo, l'insieme delle
colonne di quella lista (codice, campo sorgente, ordinabile) è identico a
quello di `vendite.note`. Quando `acquisti` o `magazzino` avranno la loro
lista, ci entreranno da sole.

## 4. Ricaduta BE e FE (`dev/backend-tid`)

### 4.1 Dopo i seed — la conversione delle sei liste

Per ogni riga del §2: endpoint paginato (`limit`/`offset`, whitelist di
ordinamento, tie-break sulla PK), `useDrawerTabLista` + `<DrawerTabLista>`
dentro i drawer, `<ListaConfigurabile>` nelle pagine.

| # | Cosa cambia oltre alla conversione |
| --- | --- |
| 1 | Le azioni di ciclo di vita (fork, nuova versione, pubblica) passano nel kebab; il banner di drift resta sopra la lista |
| 2 | La ricerca passa dal client al server |
| 3 e 4 | Lista + form inline su `useFormInline`. ⭐ Con `RigheMasterDetailTable` sono la 2ª e la 3ª shell «lista configurabile + form sotto»: **prima di scrivere** si dichiara a Tid l'estrazione del BB (regola del 2). `RigheMasterDetailTable` non si riusa: è legato a BoM ed emittente dei documenti di vendita |
| 5 | Nuovo tab «Versioni» in `ListinoDrawer`; la riga espansa di `ListiniSearchTable` si toglie, e con lei la sua `DataTable` |
| 6 | La riga espansa resta su `SearchDetailTable` (eccezione nominata) dentro lo slot `row-expansion` |

### 4.2 Subito, senza seed

- ✅ **B6 — `TabellaSelezioneRighe`** (fatto il 2026-10-31: registro a 26, presidio `TabellaSelezioneRighe.spec.js`, catalogo BB FE) in `vendite/_shared/righe/`: possiede la
  `DataTable`, la checkbox, «seleziona tutte», la colonna articolo e la cella
  quantità sopra `useRigheSelezioneQta`. Le colonne proprie di ciascun dialog
  arrivano dagli slot. Consumatori: `OrdineEvasioneDialog`,
  `ResoRiconsegnaDialog`, `DdtResoDialog`. Le tre `DataTable` diventano una,
  eccezione «selezione in un dialog». `PreventiviSmistamentoDialog` resta
  fuori: assegna una destinazione, non sceglie quantità;
- ✅ **B1 — fatto il 2026-10-31 nella forma di B1-bis** (§5.2): base `MatriceCatalogo` estratta da `MatriceOverride` (che ne è ora lo strato, coperto da `MatriceOverride.spec.js` scritto prima dello spostamento); Reparto e Utilities montano la base. Il testo qui sotto è la proposta originale, superata. La colonna «ereditato» diventa facoltativa, e
  `RepartoProfiloEditor` ci passa sopra (aree e azioni, come
  `OperatorePermessiTab`). Il BB accetta **più colonne di override**, ed
  `EmittenteFiscaleUtilitiesTab` ci passa sopra (soglie, decimali, metodo,
  attivo). ⛔ Il BB resta cieco sul dominio: le colonne le disegna il chiamante;
- ✅ **Alert scadenze, i due difetti** (il catch fatto il 2026-10-31, presidio `AlertScadenzeWidget.spec.js`): il `catch {}` vuoto fa sparire il widget
  in silenzio quando la chiamata fallisce, e va sostituito con lo stato
  d'errore. Il doppio default dei 15 giorni si chiude invece col parametro del
  §3.1.

### 4.3 Riga 5 e §7.4 dei listini — fatto il 2026-10-31

- **BE.** `vendite.listini` (27): `giorni_alla_scadenza` e filtro
  `in_scadenza` da `LEFT JOIN vendite.fn_listini_in_scadenza_senza_successore()`,
  colonna in whitelist. `GET …/listini/<id>/versioni/` è la pagina della lista
  `vendite.listini_versioni` (112: ricerca, ordinamento `VERSIONI_ORDER_COLUMNS`
  con le date DESC, la stessa colonna sulla versione); `list_versioni` resta
  la collezione intera per il dettaglio del listino e i default della nuova
  versione. ⛔ Ritirati nello stesso giro `listini_in_scadenza`,
  `_filter_versioni_in_scadenza`, `STATO_VERSIONE_BOZZA`, `fn_alert_scadenze`
  con `_ALERT_GIORNI_*`, l'endpoint `alert-scadenze/` col parametro `giorni`.
  La lista 112 è iscritta nei cinque registri (`WHITELIST_BE`,
  `test_liste_configurabili_seed`, `test_ricerca_full_seed`, proiezione e
  ricerca sul DB vero). I due test DB che leggevano la query ora leggono la
  regola attraverso le due liste; il filtro è provato per mutazione.
- **FE.** Il badge (`AlertScadenzeWidget`) conta i listini `in_scadenza=true`
  (il totale, una riga) e al clic accende il filtro «Solo in scadenza» della
  lista (D-1); popover e `DataTable` ritirati. La riga espansa di
  `ListiniSearchTable` è ritirata con la cache delle versioni nello store
  (N richieste per pagina): le versioni sono il tab «Versioni» di
  `ListinoDrawer` (`ListinoVersioniTab`, `DrawerTabLista`, store
  `listinoVersioni`), con le azioni di ciclo di vita nel kebab e «Nuova
  versione» fra le azioni di pagina; il clic sulla riga apre le righe. Ritirato
  il ripiego di `VersioneFormDrawer` sulla cache. Chiavi i18n del §7.1
  (`vendite.listini.col_giorni_alla_scadenza`, `note.col_seq`) aggiunte.
  Registro `DataTable` 24 → 22. Presidi: `ListinoVersioniTab.spec.js` (tab
  chiuso non legge, provato per mutazione), `AlertScadenzeWidget.spec.js`.
- ⚠️ **Rosso atteso fino alle altre righe:** i registri del BE
  (`test_il_registro_copre_ogni_lista_senza_vista`,
  `test_ogni_lista_ricercabile_e_registrata_o_in_debito`) elencano le cinque
  liste seminate e non ancora servite.

### 4.4 Righe 1, 2, 3, 4 e 6 — fatte il 2026-10-31

Ogni lista: endpoint paginato (`limit`/`offset`, whitelist di ordinamento,
spareggio sulla PK), ricerca dal BB `RicercaFull` dove il catalogo la accende,
la lista nei cinque registri (`WHITELIST_BE`, `test_liste_configurabili_seed`,
`test_ricerca_full_seed`, proiezione e ricerca sul DB vero).

| # | Lista | BE | FE |
| --- | --- | --- | --- |
| 1 | `pratiche.definizioni_workflow` | pagina su `_DEFINIZIONE_SELECT` (subquery), drift in colonne piatte (`versioni_indietro`), `multi_emittente` | `<ListaConfigurabile>` con fork / nuova versione / pubblica nel kebab, clic = editor; store `createListaStore`, ritirato il filtro emittente che nessuna casella impostava |
| 2 | `config.parametri_impostazioni` | pagina sopra `script.fn_list_parameters_for_user` | `<ListaConfigurabile>`, i livelli come colonne; store `createListaStore` (ora `userScoped`); `useParameterSettings` tiene i soli override |
| 3 | `vendite.note` · `catalogo.note` | BB `pagina_note` (core): UNA whitelist e la stessa ricerca per le due liste gemelle; `make_note_views` col cancello di `vendite.note` | `NoteDrawer` sul BB **`ListaConFormInline`** (regola del 2, ok Tid), form estratto in `NotaForm`, store per sede `useNoteListaStore`; l'emittente del documento passa dai sei wrapper e dagli undici punti di montaggio. ⛔ Ritirato `useNote` |
| 4 | `catalogo.articolo_uom` | `list_uom_operative_pagina` sulla vista, `non_editable_fields` accanto alla busta; il lookup resta la collezione intera | `ArticoloUomDrawer` sul BB, form estratto in `ArticoloUomForm`; il riepilogo del drawer articolo legge il lookup (intero) |
| 6 | `anagrafiche.ricerca_soggetti` | `lista_codice` sulla view, whitelist `ALLOWED_ORDER_COLUMNS` nei registri, la funzione letta per colonne (`r.*`, non piu' `row_to_json`) | `SearchDrawer` su `<DrawerTabLista>` con la riga espansa su `SearchDetailTable`; store `useRicercaSoggettiStore` (`search` → `q`) |

⚠️ Due effetti da sapere:
- **`config.parametri_impostazioni` e `vendite.listini_versioni` hanno il
  perimetro** a catalogo: chi vede piu' emittenti senza averne scelto uno
  (super admin su «Tutti») ora riceve il cancello «scegli un emittente», come
  sulle altre liste col perimetro. Prima la pagina impostazioni si apriva.
- `catalogo.note` e `catalogo.articolo_uom` sono globali (`perimetro_emittente
  = false`): niente `lista_codice` sulla view, esenzione motivata in
  `test_perimetro_emittente_copertura`, come gli altri cataloghi globali.
- ⭐ **`anagrafiche.ricerca_soggetti` (113) è mono-emittente: non vale per
  «Tutti» (Tid, 2026-10-31).** Il super admin su «Tutti gli emittenti» riceve
  il cancello «scegli un emittente» anche sulla ricerca universale, ed è
  voluto: il seed (`multi_emittente = f`, `perimetro_emittente = t`) dice il
  vero. ⛔ Non è il caso della 107 (`pratiche.definizioni_workflow`,
  `multi_emittente = t`): che la funzione restituisca
  `emittente_ragione_sociale` non basta a farne una lista multi-emittente.
- **Il cancello di `vendite.note` vale anche per la creazione.** Sta in
  `DomainAPIView.initial()`, cioè su ogni verbo dell'endpoint di lista, POST
  compreso. Fino alla revisione del §4.7 il FE mandava l'emittente solo sulla
  lettura: chi vede più emittenti vedeva le note ma non poteva crearle (422).
  Ora lo manda anche `makeNotesApi(...).createNota`.

### 4.5 Richiesta al team DB — la ricerca della lista 113

La ricerca universale cerca dentro `script.fn_search_soggetti_universale`
(`p_search_term`), che sceglie lei i campi e pagina da se'. Il seed della lista
113 dichiara invece `ricercabile_full = t` su codice, ragione sociale e id
fiscale: il pannello di amministrazione le mostra accendibili e spegnibili, ma
spegnerle **non cambia niente**, e il backend non puo' applicarle senza rompere
la paginazione della funzione. Oggi `test_ogni_lista_ricercabile_e_registrata_o_in_debito`
e' rosso su questa sola lista (rotto dichiarato).

Le due strade, da decidere col modello davanti:
- **la funzione legge il catalogo** (`ui.fn_lista_colonne_ricerca_full('anagrafiche.ricerca_soggetti')`)
  e cerca sulle colonne accese: la lista torna come le altre, e il BE la
  registra con una `RicercaFull`;
- **il catalogo dice il vero**: `ricercabile_full = f` sulle tre colonne,
  perche' la ricerca e' della funzione e non del catalogo.

⭐ **Nello stesso giro, l'ordinamento per utility** (emerso il 2026-10-31,
deciso da Tid lo stesso giorno). La regola di dominio del 2026-07-31 dice che
la utility, quando una lista ce l'ha, ordina **sempre** (`NUCLEO_ORDINABILE` di
`gen_seed_lista.py`). Sulla 113 il seed marca `utility_list` (id 1162) come non
ordinabile, perché è un aggregato della pagina, e
`fn_search_soggetti_universale` la rifiuta in `p_order_by`. Per questo
`gen_seed_lista.py --verifica-ordinamento anagrafiche.ricerca_soggetti` dà
**KO** («NUCLEO rotto: utility»), e la 113 è l'unica lista del brief in questo
stato.
- **La richiesta:** la funzione deve saper ordinare per utility, e il seed
  deve dire `ordinabile = t`. ⛔ Non vale un'eccezione nello script: Tid ha
  deciso che la regola vale anche qui.
- **La forma** la sceglie il team DB, per esempio una chiave d'ordine
  deterministica dell'insieme delle utility del soggetto, calcolata prima
  della paginazione.
- **Lato BE**, a funzione pronta: `utility_list` entra in
  `ALLOWED_ORDER_COLUMNS` (`core/db/search_repository.py`) e nei registri.

#### 4.5.1 Ricognizione del team DB (2026-10-31, dopo il push BE) — da decidere

Percorso letto: il corpo di `script.fn_search_soggetti_universale` (doc
auto-gen), `ui.fn_lista_colonne_ricerca_full`, il seed della 113
(colonne 1159-1163), il chiamante (`core/db/search_repository.py`, l'unico
nel BE), i cinque pgTAP `script/test-search-*` e
[brief-db-ricerca-universale-tetto-10000](../work-done/brief-db-ricerca-universale-tetto-10000.md).

⛔ **L'ordinamento per utility è una revoca, e va detta.** Le date:

| Data | Decisione |
| --- | --- |
| 2026-07-31 | regola di dominio: la utility, se la lista ce l'ha, ordina sempre (`NUCLEO_ORDINABILE`) |
| 2026-10-10 | **D-2 (a)** di brief-db-ricerca-universale-tetto-10000: `utility_list` esce dalla whitelist della ricerca universale. Motivo scritto: «l'ordine di una lista di forniture concatenate dice poco, e la fornitura si filtra nel dettaglio». Scartata la (b): l'aggregato su tutte le corrispondenze, solo quando si sceglie quell'ordinamento |
| 2026-10-31 | Tid: la regola del 07-31 vale anche qui |

La decisione del 31-10 **revoca D-2 (a)** del 10-10 e prende, di fatto, la
(b). Il tetto che la (b) portava con sé non serve più: dal 10-10 il conteggio e la pagina stanno
sulle colonne semplici (strada B), e l'aggregato si calcolerebbe **solo**
quando l'operatore ordina per utility.

✅ **D-3 — DECISO da Tid il 2026-10-31: nessun cambiamento.** Resta D-2 (a)
del 2026-10-10: `utility_list` non si ordina, il seed resta `ordinabile = f`,
la funzione non cambia. ⚠️ Effetto: `gen_seed_lista.py --verifica-ordinamento`
continua a dare KO («NUCLEO rotto: utility») sulla 113. Come renderlo un
caso dichiarato è da fissare (vedi sotto). La proposta che segue resta scritta
come storia, ed è **superata**.

~~**D-3 — la forma dell'ordinamento per utility. Proposta:**~~ la chiave d'ordine
è **la stessa stringa che la colonna mostra** (`string_agg(DISTINCT
codice_interno, ', ' ORDER BY codice_interno)` sulle righe cliente),
calcolata su tutte le corrispondenze **solo** con `p_order_by =
'utility_list'`, prima della pagina, con lo spareggio su
`soggetto_ruolo_id` come oggi. NULL in fondo in ASC. Così l'ordine che si
vede è quello della colonna, e senza quell'ordinamento la query resta quella
di oggi. La RLS di `anagrafiche.clienti` filtra la chiave come filtra la
colonna, quindi le due non possono dissentire. Il costo lo dirà un `EXPLAIN`
sul DB vero, come verifica e non come motivo.
Alternativa scartata: il codice minimo della utility come chiave. È più
leggera, ma ordina in un modo che la colonna non mostra («GAS» davanti a
«ENERGIA, GAS» se il criterio è il primo elemento).

✅ **D-4 — DECISO da Tid il 2026-10-31: strada 2 («fare funzionare l'interruttore»), e `filtrabile = f` per il caso gemello.** Scritto al §7.6.

**D-4 — le colonne di ricerca. Proposta: una terza strada**, fra le due del
§4.5:

- **la funzione riceve i campi dal chiamante**: `p_campi_ricerca text[]`, in
  coda alla firma, validati contro una whitelist della funzione
  (`soggetto_codice`, `ragione_sociale_completa`, `id_fiscale_univoco`). Il BE
  li legge da `ui.fn_lista_colonne_ricerca_full('anagrafiche.ricerca_soggetti')`
  con la `RicercaFull`, come per le altre liste. L'elenco vuoto o un campo
  fuori whitelist: `E_PARAMETRO_INVALIDO`;
- il **codice dell'entità** (l'`EXISTS` dinamico su
  `tipi_ruoli.entita_tabella`) segue `soggetto_codice`: è lo stesso concetto,
  «il codice», su due tabelle.

Perché non le due strade del §4.5:

- **«il catalogo dice il vero» (`ricercabile_full = f`)** lascia un buco del
  modello. `fn_lista_colonne_ricerca_full` esclude le colonne a livello
  `BLOCCATO` per l'utente, e la funzione di oggi cerca comunque su
  `id_fiscale_univoco`. Chi non può vedere il CF lo può **sondare**,
  cercandolo. Con i campi dal catalogo, il livello di colonna vale anche per la
  ricerca, come sulle altre liste;
- **«la funzione legge il catalogo»** chiude lo stesso buco, ma lega una
  funzione di dominio (`script`) a un codice lista di `ui`. Oggi lo schema
  `ui` lo legge solo chi presenta (il BE), e nessuna funzione `script`.

Ricaduta: la firma cambia, quindi `DROP` + `CREATE` (`RETURNS TABLE`). Va
toccato l'unico chiamante BE, insieme ai cinque pgTAP `script/test-search-*`.
`filtrabile = t` sulle tre colonne 1159-1161 ha lo stesso problema: la
funzione non sa filtrare per colonna. ⚠️ Da decidere nello stesso giro se la
113 offre filtri (allora servono parametri) o se il seed dice `filtrabile = f`.
**Proposta: `f`**. La ricerca universale ha un termine solo, e i filtri
veri stanno nel dettaglio (`p_utility_id`).

### 4.6 Richiesta al team DB — il preavviso delle scadenze si valida quando si scrive

`LISTINI_SCADENZA_PREAVVISO_GIORNI` (§7.2) ha `ammette_override = true`, e
`vendite.fn_listini_in_scadenza_senza_successore` lo valida **in lettura**
(`script.fn_intero_positivo_da_testo`: non intero positivo =
`E_CONFIG_MANCANTE`, classe TECNICO, cioè un 500).

- **Il difetto, sul modello.** Il valore lo scrive chi lavora, e
  `config.parameter_overrides` accetta qualunque testo: nessuna colonna di
  `config.parameters` dice che il valore è un intero, e nessun trigger lo
  controlla (oggi c'è solo il guard `ammette_override`). Un override «0» o
  «abc» si salva senza errori, e da lì l'operatore non apre più la lista
  listini né il tab «Versioni» del listino. Le due liste chiamano la funzione
  sempre, perché proiettano la colonna `giorni_alla_scadenza`, anche quando
  non filtrano né ordinano per scadenza. L'errore arriva lontano dal gesto
  che l'ha causato, e con la classe sbagliata.
- **La richiesta.** Rifiutare il valore sbagliato quando si scrive l'override
  (e il default), con un errore di dominio sul campo: la stessa regola di
  `fn_intero_positivo_da_testo`, applicata in scrittura. La forma la sceglie
  il team DB. Una strada è un tipo del valore dichiarato su
  `config.parameters`, con un guard su `parameter_overrides` che lo applica:
  questa vale per ogni parametro numerico, non solo per questo. La lettura
  resta fail-loud com'è.
- **Lato BE, già fatto (§4.7).** La query di conteggio della lista listini
  chiama la funzione solo quando il filtro `in_scadenza` è acceso. Le righe
  la chiamano comunque.

#### 4.6.1 Ricognizione del team DB (2026-10-31) — da decidere

Struttura letta (doc auto-gen): `config.parameters` non ha una colonna che
dica la forma del valore (`default_value text NOT NULL`). Su
`parameter_overrides` girano il guard `ammette_override` (a05) e il
dispatcher **FK-surrogata** (a10, registro `config.parameter_fk_surrogate`).
Il dispatcher è il precedente giusto: valida già **in scrittura** il valore
di un parametro, sia il default sia l'override (`E_PARAMETER_DEFAULT_VALUE_INVALID`,
`E_PARAMETER_OVERRIDE_VALUE_INVALID`), ma solo per i codici di un'altra tabella.
In lettura validano oggi tre funzioni (`fn_intero_positivo_da_testo`, con
consumatori `fn_idempotency_soglia_secondi`, `fn_login_parametri` e
`fn_listini_in_scadenza_senza_successore`).

✅ **D-5 — DECISO da Tid il 2026-10-31: strada 1, il tipo su tutti i parametri.** Scritto al §7.6.

**D-5 — la forma. Proposta:** ogni parametro **dichiara il tipo del suo
valore**.

- Colonna `tipo_valore` su `config.parameters`, `NOT NULL` e **senza
  default**, come `ammette_override`: un parametro nuovo la dichiara. FK
  verso un vocabolario piccolo `config.tipi_valore_parametro`. I tipi si
  ricavano dal seed di `80_data`, che è contratto: `BOOLEANO`,
  `INTERO_POSITIVO`, `INTERO_NON_NEGATIVO` (i `*_LEAD_GG` e gli sconti
  ammettono 0), `DECIMALE`, `DATA`, `TESTO`. Il vuoto ammesso (per esempio
  `EMITTENTE_DEFAULT_BOLLO_SOGLIA`) è un tipo a sé o un flag, da fissare
  scrivendo.
- **Un BB solo** per la regola, `script.fn_valore_parametro_ammesso(tipo,
  valore) boolean`. Lo leggono due guard nuovi, uno su `parameters` (il
  default) e uno su `parameter_overrides` (l'override), con un errore di
  dominio (`DATO_ERRATO`, 422) che nomina il parametro e la forma attesa.
  `fn_intero_positivo_da_testo` resta il lettore fail-loud, ma prende la
  regola dal BB, così la regex non vive in due posti (regola del 2).
- La FK-surrogata resta com'è. Dice **quale** valore (un codice esistente),
  il tipo dice **che forma**: sono due domande diverse.

⚠️ **È un tema su tutta la famiglia dei parametri**: la colonna `NOT NULL`
chiede il tipo per **ogni** riga di `parameters.csv`, e il seed va riscritto
tutto. Per `AGENTS.md` un tema così non si apre senza l'ok esplicito di Tid.
La strada stretta, un tipo nullable solo sui parametri numerici, lascerebbe
un «non dichiarato» che il modello non sa distinguere da «testo libero».
**Non la si propone.**

### 4.7 Revisione del lavoro non committato — fatta il 2026-10-31

Revisione critica BE e FE del lavoro di §4.3 e §4.4 prima del commit, con le
correzioni ok di Tid. Quello che cambia il contratto o il comportamento:

- **Liste.** Il form inline rinasce a ogni voce. Prima, cliccando un'altra
  riga a form aperto, si salvavano i dati della voce precedente sopra quella
  nuova.
- **Ordinamenti.** `valido_al` vuoto è la validità più lontana, e
  `giorni_alla_scadenza` vuoto (non in scadenza) va in fondo nell'ordine
  crescente.
- **Viste.** Gli slot di cella della lista 107 sono allineati ai codici del
  seed (`emittente`, `drift`). La ricerca universale non perde più il tipo
  ruolo alla riapertura.
- **Sola lettura.** In sola lettura il tab «Versioni» resta consultabile, e
  i verbi li nasconde il tab.
- **Regola del 2.** Sono stati ritirati i sei wrapper delle note di vendita e
  la colla gemella di `NoteDrawer`/`ArticoloUomDrawer`. Sono stati estratti
  la validazione dell'ordine delle note e la lettura dello stato obbligatorio
  del modello documento. Il dettaglio è nei due cataloghi BB.

## 5. Decisioni

### 5.1 Prese da Tid il 2026-10-31

| # | Decisione |
| --- | --- |
| B1 | Reparto → `MatriceOverride` con «ereditato» facoltativo; Utilities emittente → `MatriceOverride` esteso a più colonne di override; Impostazioni → `ListaConfigurabile` (i livelli sono colonne) |
| B2 | Note e UoM dell'articolo sono liste vere (`DrawerTabLista` + `useFormInline`) |
| B3+B4 | Le versioni dei listini diventano una lista configurabile in un tab del drawer listino; l'alert diventa un badge con un link a una lista filtrata, senza una lista sua |
| B5 | La ricerca universale dei soggetti è una lista vera |
| B6 | I tre dialog di selezione righe hanno un BB comune (§4.2) |
| B7 | ✅ Fatto: il guard vuole il motivo in un commento **attaccato** all'import |
| B8 | La ricerca universale dei soggetti (113) è **mono-emittente**: su «Tutti» il cancello di perimetro è voluto (§4.4) |

### 5.2 Aperte

- ✅ **D-1 — Dove porta il link dell'alert: DECISO da Tid il 2026-10-31.**
  Il link apre la lista **listini** (`vendite.listini`) col filtro «versione
  in scadenza senza successore», perché il gesto che segue (creare il
  successore) parte dal listino. Non nasce nessuna lista versioni
  trasversale.
- ✅ **D-2 — Note dell'articolo: DECISO da Tid il 2026-10-31.** Le alternative
  erano un codice lista solo per tutte le note, o un codice per sede.
  **Proposta: un codice per tabella-madre `<schema>.note`** (`vendite.note`
  e `catalogo.note`, non `catalogo.note_articoli`: il codice copre la madre e
  quindi anche le note dei componenti). Più il presidio del §3.3.
  - **Perché non un codice solo.** Una `lista_definizione` porta proprietà
    **della sede**: `schema_dati`, la vista, `perimetro_emittente`. Queste
    proprietà differiscono davvero, perché le note di un documento di vendita
    stanno dentro il perimetro dell'emittente e quelle di un articolo no. Un
    codice solo dovrebbe mentire su una delle due sedi.
  - **Perché non è una copia da ritirare.** Sono due liste con la stessa
    forma per contratto del modello, come la regola del 2 distingue fra testo
    e significato. Il rischio vero è la divergenza delle colonne, e lo copre
    il presidio del §3.3.
  - **Cosa ne guadagna il futuro.** `acquisti.note` e `magazzino.note` esistono
    già a DB: quando arriverà il loro FE avranno il codice per costruzione, e
    il presidio li includerà.

  In entrambi i casi l'endpoint delle note di catalogo va paginato come quello
  di vendita.
- ✅ **B1-bis — La premessa di B1 non regge per due file su tre** (emerso il
  2026-10-31, leggendo il modello prima di scrivere).
  - **Reparto.** `config.fn_scrivi_profilo_accesso` **sostituisce** l'intero
    profilo: ogni area ha il suo livello e ogni azione il suo stato. Non c'è
    un livello da cui ereditare (il reparto È la sorgente da cui eredita
    l'operatore), né una riga da «togliere per tornare all'ereditato».
    `MatriceOverride` disegnerebbe «Override» su ogni riga e un ripristino che
    non significa niente.
  - **Utilities dell'emittente.** La semantica di presenza c'è (configurata /
    non configurata, «rimuovi» cancella la riga), ma un ereditato no: la riga
    non configurata mostra «—». In più ha la modifica e il salvataggio **per
    riga**, che `MatriceOverride` non ha.
  - **Cosa hanno in comune davvero:** sono matrici **limitate dal catalogo**
    (tutte le voci, nessuna paginazione, nessuna combo «aggiungi»). Lo strato
    override è dell'operatore, non loro.
  - ➡️ **Decisione di Tid (2026-10-31): base comune più strato.** Da
    `MatriceOverride` si estrae la base `MatriceCatalogo` (tutte le voci,
    ricerca, readonly, slot per le colonne valore e per le azioni di riga), e
    `MatriceOverride` diventa la base più lo strato ereditato/stato/ripristino.
    Reparto e Utilities montano la base, `OperatorePermessiTab` resta su
    `MatriceOverride`.

## 6. Fuori da questo brief

- **Gruppo C, master-detail di amministrazione:** `CollectionEditorPanel`
  (sede unica delle 6 sotto-collezioni di step e archi) e
  `DefinizioneEditorView`. Sono debito dichiarato nel commento sopra l'import
  e vanno ragionati a parte;
- **Eccezioni con motivo scritto** (2026-10-31): `ConfigTablePanel`,
  `MatriceOverride`, `ScadenzeSintesi`, `RiepilogoIvaTable`, le anteprime dei
  dialog, `SituazioneMerceContenuto`, la seconda tabella di `PraticaFlussiTab`,
  `ListaPresetColonneDrawer` e `ComponentiDialog`.

## 7. Lato DB — cosa è stato scritto (2026-10-31, applicato)

### 7.1 I seed — i codici che il FE scrive nel `.vue`

Righe in coda ai quattro CSV di `80_data/sql/ui/` (li caricano i mirror
`runOnChange`; le sequenze le riallinea il resync runAlways
`90_end/20260602-17`). Bozze dal generatore, curate a mano sui campi che il BE
restituisce oggi.

| # | Codice | id lista/preset | colonne | Flag |
| --- | --- | --- | --- | --- |
| 1 | `pratiche.definizioni_workflow` | 107 | 1113-1119 | ⭐ `multi_emittente` (v. sotto) |
| 2 | `config.parametri_impostazioni` | 108 | 1120-1128 | con perimetro |
| 3 | `vendite.note` | 109 | 1129-1136 | con perimetro |
| 3 | `catalogo.note` | 110 | 1137-1144 | globale |
| 4 | `catalogo.articolo_uom` | 111 | 1145-1151 | globale, `vista_sql` = `vw_articoli_uom_operativa_dettaglio`, ricerca da 1 carattere |
| 5 | `vendite.listini_versioni` | 112 | 1152-1158 | con perimetro |
| 6 | ⚠️ **`anagrafiche.ricerca_soggetti`** | 113 | 1159-1163 | con perimetro |
| — | `vendite.listini` (27): colonna `giorni_alla_scadenza` | — | 1164 | spenta nel preset 27 |

⚠️ **Riga 6: il codice non è `core.ricerca_soggetti`.** Vince il catalogo: il
prefisso è lo schema dei dati, e la ricerca legge soggetti di `anagrafiche`
(lo schema `core` non esiste).

⚠️ **Riga 1: `multi_emittente = t`, non globale.** Ogni edizione di workflow è
di un emittente, il preset di sistema di nessuno (`emittente_fiscale_id` NULL),
come i modelli standard di `documenti.template_documenti`. La lista globale con
una colonna d'emittente era la combinazione che il presidio
`ui/test-lista-definizione-perimetro-emittente-v1` (test 8) rifiuta, e aveva
ragione: la lista sa dire di chi è ogni riga. Il super admin la apre su «Tutti».

Note di cura, per il BE:

- **note (3).** I due codici hanno le **stesse** colonne (le tiene gemelle il
  presidio del §7.3): `anchor_tipo`, `riga` (← `target_riga_id`, l'etichetta la
  compone il FE), `posizione`, `testo`, `stile` (← `stile_descrizione`),
  `lingua` (← `lingua_codice_iso`), `seq` (nascosta), `azioni`. Preset ordinato
  per `posizione`, `seq`.
- **impostazioni (2).** I sei livelli sono colonne (B1); le colonne dei valori
  non sono ordinabili né filtrabili: sono testo di tipi diversi.
- **versioni (5).** `giorni_alla_scadenza` è il campo che il BE deve
  restituire da `vendite.fn_listini_in_scadenza_senza_successore` (§7.2).
- **ricerca (6).** `utility_list` ed `emittente_ragione_sociale` non
  ordinabili (aggregati: `fn_search_soggetti_universale` li rifiuta in
  `p_order_by`). Nessuna colonna azioni: la riga espansa resta su
  `SearchDetailTable`.

⚠️ **Chiavi i18n nuove** (FE, `it.json` + `en.json`): `note.col_seq`,
`vendite.listini.col_giorni_alla_scadenza`. Le altre sono quelle che i `.vue`
usano già. ✅ Aggiunte dal BE/FE: `check_i18n_keys` verde il 2026-10-31.

### 7.2 La regola «in scadenza senza successore» (§3.1)

| changeSet / file | Cosa |
| --- | --- |
| `20_code/vendite/20261031-27` | `vendite.fn_listini_in_scadenza_senza_successore(p_data date DEFAULT NULL)` → `(listino_id, versione_id, valido_al, giorni_rimanenti)`, una riga per versione in scadenza. STABLE, SECURITY INVOKER, EXECUTE a `zeroerp_app` |
| `80_data/sql/config/parameters.csv` (id 63) | `LISTINI_SCADENZA_PREAVVISO_GIORNI` = 15, `ammette_override = true`: è una preferenza di chi lavora |

La regola è quella del BE, riga per riga (versione in vigore dalla sede
`fn_listino_versione_in_vigore`, fine entro N giorni, listino attivo, nessun
successore in preparazione o operativo dal giorno dopo). Due differenze di
forma:

- lo stato «in preparazione» si legge dal vocabolario (`iniziale`), non dal
  letterale `BOZZA`;
- **N non si passa**: è il parametro, letto con la cascata degli override
  della sessione e validato (`script.fn_intero_positivo_da_testo`: assente o
  non intero positivo = `E_CONFIG_MANCANTE`). I due default di 15 giorni (FE e
  `_ALERT_GIORNI_DEFAULT`) si chiudono qui.

⭐ È **set-returning** di proposito: i consumatori la chiamano una volta per
query, con una `LEFT JOIN`, e il parametro si risolve una volta sola. Una
funzione per riga avrebbe risolto la cascata degli override a ogni riga.

Prova (2026-10-31): SQL estratto + seed del parametro, su `zeroerp_ruoli` come
owner, pgTAP nuovo **9/9**; su dbdev, la query del BE (N = 15) e la funzione
danno lo stesso insieme nei due versi. Fatto datato: su dbdev oggi nessun
listino è in scadenza, quindi l'equivalenza sui dati è a vuoto; i casi li
costruisce il pgTAP.

### 7.3 Presidi pgTAP

| File | Cosa |
| --- | --- |
| `db/pgtap/vendite/test-listini-in-scadenza-senza-successore-v1.sql` (nuovo, 9) | cinque listini costruiti attorno a N letto dal parametro: in scadenza, fuori finestra, coperto da una BOZZA, coperto da un'ATTIVA, bozza che nasce prima della fine (non è un successore); i giorni da una data diversa da oggi; una riga per versione |
| `db/pgtap/ui/test-lista-note-gemelle-v1.sql` (nuovo, 4) | §3.3: l'elenco dalla struttura (le tabelle `note` di ogni schema, con una lista `<schema>.note`), stesse colonne di `vendite.note` su codice, campo, tipo, ordinabile, filtrabile; non a vuoto |
| `ui/test-lista-definizione-perimetro-emittente-v1` (test 6) | + `catalogo.articolo_uom`, `catalogo.note`, col motivo |
| `ui/test-lista-definizione-multi-emittente-v1` (test 5) | + `pratiche.definizioni_workflow`, col motivo |
| `ui/test-lista-ricerca-min-caratteri-v1` (test 16) | + `catalogo.articolo_uom` (codici UoM corti) |

Prova (2026-10-31), su `zeroerp_ruoli` come owner, seed simulato dai CSV dentro
la transazione: i 18 pgTAP di `ui/` e i 10 fuori da `ui/` che leggono il
catalogo liste, prima e dopo. Cambiano solo i tre previsti (perimetro test 6,
note gemelle, ricerca test 16), tutti verso il verde. Restano rossi **come
prima**: perimetro test 4 e multi-emittente (precondizione 0), che girano solo
come app.

### 7.4 Per il BE (`dev/backend-tid`)

- **I sette codici** del §7.1 nei `.vue`; whitelist di ordinamento sui campi
  `ordinabile = t` (`gen_seed_lista.py --verifica-ordinamento` oggi le dà
  «NON MAPPATA»); registrare le liste in `test_liste_configurabili_seed` e
  `test_ricerca_full_seed`.
- **`vendite.listini` (27)**: la colonna `giorni_alla_scadenza` (filtrabile,
  ordinabile) va restituita da `LEFT JOIN
  vendite.fn_listini_in_scadenza_senza_successore() s ON s.listino_id = l.id`
  e messa in whitelist. Oggi il comando di verifica dà **KO** su questa lista:
  è il rotto temporaneo dichiarato. Il link dell'alert apre la lista filtrata
  su `giorni_alla_scadenza` non vuoto (D-1).
- **`vendite.listini_versioni`**: stessa colonna, `LEFT JOIN … s ON
  s.versione_id = v.id`.
- **Il badge** conta le righe della funzione (o del filtro). ⛔ **Nello stesso
  giro si ritirano** `listini_repository.listini_in_scadenza`,
  `_filter_versioni_in_scadenza`, `_ALERT_GIORNI_DEFAULT`/`_MIN`/`_MAX` e il
  parametro `giorni` dell'endpoint, e il default 15 del FE: N è il parametro.
  I due test Django che leggono `listini_in_scadenza(30)` vanno riscritti
  sulla funzione.
- **`pratiche.definizioni_workflow`** è `multi_emittente`: la view la serve
  anche su «Tutti», e la colonna `emittente_display` è il biglietto.
- **`catalogo.note`**: l'endpoint delle note di catalogo va paginato come
  quello di vendita (D-2).

✅ **Tutto fatto, verificato il 2026-10-31** (§4.3, §4.4, §4.7):
- `gen_seed_lista.py --verifica-ordinamento` dà **ok** in tutte e tre le
  direzioni su sette delle otto liste del brief: `vendite.listini` (prima KO),
  `vendite.listini_versioni`, le due note, `catalogo.articolo_uom`,
  `config.parametri_impostazioni`, `pratiche.definizioni_workflow`;
- l'ottava, `anagrafiche.ricerca_soggetti`, dà **KO** sul nucleo «utility»
  (v. §4.5);
- ritirati `listini_in_scadenza`, `_filter_versioni_in_scadenza`,
  `_ALERT_GIORNI_*`, l'endpoint `alert-scadenze/` (un test controlla che non
  risponda più) e il default 15 del FE.

### 7.5 Per Tid — apply e corsa

`20261031-27`, poi i mirror dei CSV `ui` e `config/parameters.csv` al migrate.
Corsa pgTAP: i due file nuovi e i tre `ui/` toccati (§7.3).

✅ **Fatto il 2026-10-31** (Tid): migrazione applicata su dbdev, pgTAP verdi.

## 7.6 Secondo giro DB — D-4 e D-5 (2026-10-31, applicato su dbdev)

### 7.6.1 I changeSet

| changeSet | Cosa |
| --- | --- |
| `00_schema/config/20261031-53` | `config.parameters.tipo_valore text NOT NULL` + `chk_parameters_tipo_valore` (otto forme). DEFAULT `'TESTO'` temporaneo, come `ammette_override`: backfill e seed `80_data/20260224-38`, che inserisce senza la colonna |
| `20_code/script/20261031-54` | **BB** `script.fn_valore_parametro_non_conforme(tipo, valore)`: NULL se conforme, altrimenti la forma attesa in parole (la frase del messaggio). Regola e frase in un posto. Tipo sconosciuto: `E_SCRIPT_CHIAMATA_NON_VALIDA` |
| `20_code/script/20261031-55` | `script.fn_intero_positivo_da_testo` prende la regola dal BB (la regex stava qui: regola del 2). Firma, risultato ed errori invariati, resta fail-loud |
| `20_code/config/20261031-56` | guard a07 su `config.parameters` (`INSERT OR UPDATE OF default_value, tipo_valore`): il default ha la forma del tipo; cambiando il tipo, anche ogni override, **anche spento** (`E_PARAMETER_OVERRIDE_NON_CONFORME_AL_TIPO`, CONFLITTO_STATO) |
| `20_code/config/20261031-57` | guard a07 su `config.parameter_overrides` (`INSERT OR UPDATE OF parameter_id, overridden_value`): `E_PARAMETER_VALORE_NON_CONFORME` (DATO_ERRATO, 422), campo `value` nel contesto. Dopo a05 (famiglia), prima di a10 (FK-surrogata) |
| `20_code/script/20261031-58` | `script.fn_search_soggetti_universale(…, p_campi_ricerca text[] DEFAULT NULL)`, **in coda**. Whitelist `soggetto_codice` (codice del soggetto **e** dell'entità), `ragione_sociale_completa`, `id_fiscale_univoco`; vuoto = nessuna riga (come `RicercaFull`); NULL = i tre di prima; un campo fuori whitelist o NULL = `E_SCRIPT_CHIAMATA_NON_VALIDA`. `DROP` della firma a sei argomenti + `CREATE` + `GRANT` a `zeroerp_app` |
| `90_end/20261031-59` | `DROP DEFAULT` di `tipo_valore` |

Seed:

- `parameters.csv` e `parameters_sistema.csv`: colonna `tipo_valore` in coda, su ogni riga; la
  colonna nei due mirror (`20250715-01`, `70_dati_sistema/20260825-12`, entrambi
  `runOnChange` + `ANY`). Le forme: 7 `BOOLEANO`, 12 `INTERO_POSITIVO`, 8
  `INTERO_NON_NEGATIVO` (i `*_LEAD_GG`, `CATALOGO_UOM_OP_DEFAULT_MAX_DECIMALS`,
  `VENDITE_LIMITE_EMISSIONE_IMMEDIATA_GIORNI`: 0 = solo oggi), 3 `DECIMALE_POSITIVO` (fattore,
  passo e coefficiente della distinta), 2 `DECIMALE_NON_NEGATIVO` (le due percentuali), 1
  `DECIMALE_NON_NEGATIVO_O_VUOTO` (`EMITTENTE_DEFAULT_BOLLO_SOGLIA`), 1 `DATA`, 22 `TESTO` (i
  codici di catalogo, che valida la FK-surrogata, gli enum e il fuso).
  `VENDITE_LIMITE_EMISSIONE_DIFFERITA_GIORNO_MESE` è `INTERO_POSITIVO`: un giorno del mese 0
  non esiste, anche se il lettore oggi accetta da 0 a 9999.
- `codici_errore.csv` + `messaggi_errore.csv` (id 1415, 1416): i due codici nuovi.
- `ui/lista_colonna.csv`: `filtrabile = f` su 1159-1161 (caso gemello di D-4).

Le scelte fatte scrivendo (§4.6.1 le lasciava aperte):

- **Il vocabolario è un `CHECK`, non una tabella.** Ogni forma ha la sua regola nel BB, e una
  riga di catalogo senza il suo ramo non vorrebbe dire niente. Il pgTAP prova che ogni forma del
  CHECK ha il ramo.
- **Il vuoto ammesso è una forma a sé** (`DECIMALE_NON_NEGATIVO_O_VUOTO`), non un flag: una
  colonna in più da dichiarare su ogni riga per un caso solo.
- **Le forme sono canoniche**: `true`/`false` minuscolo, niente segno, spazi o zeri iniziali, il
  punto per i decimali. Il tipo dice la forma. Il confine del dominio (giorno del mese,
  percentuale fino a 100) resta a chi legge.

### 7.6.2 pgTAP

| File | Cosa |
| --- | --- |
| `config/test-parameters-tipo-valore-v1.sql` (nuovo, 20) | colonna; BB ⊇ CHECK; 39 casi di forma; i due guard in INSERT e UPDATE di una colonna sola; il cambio di tipo con override acceso e spento; le fasi a05 < a07 < a10; il caso del brief (`LISTINI_SCADENZA_PREAVVISO_GIORNI` = `'0'` rifiutato); il lettore fail-loud |
| `script/test-search-universale-campi-ricerca-v1.sql` (nuovo, 11) | una firma sola; NULL = i tre; ogni campo da solo trova e gli altri no (CF, ragione sociale, codice del soggetto, codice dell'entità); vuoto = zero righe; campo fuori whitelist e NULL rifiutati |
| `script/test-intero-positivo-da-testo-v1.sql` (test 7) | la regex «intero positivo» sta ora nel BB delle forme: la sede attesa passa a `fn_valore_parametro_non_conforme` |
| `config/test-credenziale-login-v1.sql` (test 22) | per provare il lettore fail-loud con un vuoto, il parametro si dichiara prima `TESTO` (il guard rifiuterebbe il vuoto su un `INTERO_POSITIVO`) |
| `config/test-elimina-credenziale-v1.sql` | la pesca del parametro per l'override `'pgtap'` vuole anche `tipo_valore = 'TESTO'` |
| 8 file con `INSERT INTO config.parameters` (13 istruzioni) | `tipo_valore = 'TESTO'` dichiarato: dopo `90_end` il NOT NULL non ha più default. Nel test 4 di `ammette-override` così il 23502 viene solo da `ammette_override` |

### 7.6.3 Prova (2026-10-31, scratch `zeroerp_ruoli` come owner, SQL estratto in transazione annullata)

- L'SQL estratto dei sette changeSet, più il seed simulato dai CSV (un `UPDATE` per parametro
  con valore e tipo, i due codici d'errore, `filtrabile`), si applica. **I 56 parametri dei due
  CSV passano il guard** col tipo dichiarato, e resta **una** funzione
  `fn_search_soggetti_universale`. ⚠️ Il seed simulato non prova il loader di Liquibase
  (`tipo_valore` non ha celle vuote, i mirror sono `nullValue: "NULL"`).
- I due pgTAP nuovi: **20/20** e **11/11** con l'SQL estratto, rossi senza: distinguono il
  corpo nuovo dal vecchio.
- Regressione, prima (file di HEAD, DB com'è) e dopo (file nuovi + SQL estratto), su 41 file:
  i presidi dei parametri, del login, della ricerca, dell'FK-surrogata, delle liste `ui`,
  `test-listini-in-scadenza-senza-successore` e i trasversali
  (`test-catalogo-messaggi-errore-completo`, `test-riferimenti-morti` con `plpgsql_check`,
  `test-vw-codici-errore-*`, `test-rubinetto-primo-motivo`). **Un solo scarto**, il test 7 di
  `test-intero-positivo-da-testo` (la regex spostata nel BB, voluto, aggiornato e verde). I
  rossi restano **identici prima e dopo**: i test «come app» lanciati da owner
  (`test-credenziali-porta` 3-5, `test-elimina-credenziale` 18,
  `test-lista-definizione-perimetro-emittente` 4) e il test 7 di
  `test-search-soggetti-universale`, che pesca un cliente dai dati e sullo scratch si ferma.
- Guardrail statici verdi (`run_on_change`, `precondition_seed`, `ddl_su_trigger_automazione`,
  `grant_ruolo_batch`, `v1_congelato`, `sql_letterali`, `timestamp_senza_fuso`); il preambolo
  pgTAP ha due violazioni preesistenti in `test-grammatica-presidio-tipo-documento-v1`, non di
  questo giro.
- Fatto datato, usato solo come verifica: su dbdev gli override dei parametri ora tipizzati
  rispettano già la forma (`VENDITE_MAX_*_PCT` = `10`). L'apply non si ferma sui dati di oggi.

### 7.6.4 Per Tid — apply e corsa

`20261031-53` … `-59`. All'apply si svegliano i mirror di `parameters.csv`,
`parameters_sistema.csv`, `codici_errore.csv`, `messaggi_errore.csv` e `lista_colonna.csv`.
✅ **Fatto il 2026-10-31** (Tid): apply su dbdev, pgTAP verdi.

Corsa pgTAP: i due nuovi, i tre toccati nel corpo (`test-intero-positivo-da-testo`,
`test-credenziale-login`, `test-elimina-credenziale`), gli otto con l'`INSERT` dei parametri, e
le quattro `script/test-search-*`.

⚠️ I rollback di `80_data/20261002-67` e `20261019-04` reinseriscono parametri senza
`tipo_valore`: dopo `90_end/20261031-59` non girerebbero più (dichiarato nel changeSet).

### 7.6.5 Per il BE (`dev/backend-tid`) — elenco chiuso, dopo l'apply

1. **Ricerca universale (113).** `search_repository` passa a `fn_search_soggetti_universale`
   il settimo argomento, `p_campi_ricerca`. Sono le colonne accese del catalogo
   (`ui.fn_lista_colonne_ricerca_full('anagrafiche.ricerca_soggetti')`, il campo
   `campo_sorgente`), dichiarate con una `RicercaFull` sulle tre colonne. La 113 entra in
   `_RICERCHE` e va tolta dal debito: `test_ogni_lista_ricercabile_e_registrata_o_in_debito`
   torna verde. Il termine resta uno, e la funzione cerca dove il catalogo dice.
   ⛔ Elenco vuoto = nessuna riga, come il BB.
2. **`filtrabile = f`** sulle tre colonne della 113: se un registro BE dei filtri le elencava, si
   allinea al seed.
3. **Utility non ordinabile** (D-3, nessun cambiamento): `utility_list` resta fuori da
   `ALLOWED_ORDER_COLUMNS`, e `gen_seed_lista.py --verifica-ordinamento` resta KO («NUCLEO
   rotto: utility») sulla 113. ⚠️ Da dichiarare dove lo script tiene le eccezioni motivate: la
   decisione del 31-10 è che la regola del nucleo **non** vale qui.
4. **Override con valore fuori forma**: `POST`/`PUT` degli override ricevono
   `E_PARAMETER_VALORE_NON_CONFORME` (DATO_ERRATO, 422, campo `value`). La frase viene dal
   catalogo, con la forma attesa. Nessun controllo di forma da aggiungere nel BE (sarebbe una
   copia della regola). I booleani si scrivono `true`/`false` minuscoli.
5. **Test Django**: l'helper `apps/core/tests/_helpers/parametro_di_prova.py`
   (`crea_parametro_di_prova`, 6 usi) inserisce senza `tipo_valore`. Dopo `90_end` è un
   NOT NULL: aggiungere il tipo (`'TESTO'` come default dell'helper).
6. *(facoltativo, non chiesto)* `script.fn_list_parameters_for_user` non espone `tipo_valore`.
   Se la UI delle impostazioni vuole un campo adatto alla forma (numero, sì/no, data), è una
   colonna in più della lista: richiesta al DB, non un elenco nel FE.

## 7.7 Lato BE — l'elenco del §7.6.5, fatto il 2026-10-31

| # | Voce | Cosa è stato fatto |
| --- | --- | --- |
| 1 | Ricerca universale (113) | `RICERCA_SOGGETTI` (`RicercaFull` sui tre campi) in `core/db/search_repository.py`; `search_soggetti` passa `p_campi_ricerca` dal BB nuovo **`colonne_ricerca_attive`**, estratto da `add_ricerca_full_condition` (regola del 2, ok Tid; catalogo BB backend). Elenco vuoto passato vuoto, mai `NULL`. La 113 è in `_RICERCHE` e in `_ESERCITATE_DAL_REPOSITORY`. Presidio `test_ricerca_full_db.test_ricerca_soggetti_cerca_dove_il_catalogo_dice`: ogni colonna accesa trova, il CF spento non trova, tutte spente nessuna riga. Provato per mutazione (con `NULL` il test va rosso: «CF spento a catalogo: la funzione lo cerca ancora») |
| 2 | `filtrabile = f` | nessun registro BE dei filtri nomina la 113; il FE legge i filtri dal catalogo. Niente da allineare |
| 3 | Utility non ordinabile | `NUCLEO_ECCEZIONI` in `scripts/gen_seed_lista.py`: un'eccezione per (lista, concetto), col motivo e la decisione. La verifica la stampa, e segnala come **stantia** un'eccezione che non serve più. La 113 dà ok; i 4 KO di `pagamenti` (`canali_incasso`, `eccedenze`, `rate`, `righe`) erano rossi già prima e non sono di questo brief |
| 4 | Override fuori forma | i due codici nuovi in `error_policies_generated.py` (rigenerato; classi: `DATO_ERRATO`, `CONFLITTO_STATO`) e i due ripieghi senza `%s` in `error_messages_fallback.py`. Nessun controllo di forma nel BE. Il drawer `ImpostazioniOverrideDrawer` evidenzia il campo valore su `campiErrati.includes('value')`. ⚠️ Il campo non arriva: v. §7.7.1 |
| 5 | Helper dei test | `crea_parametro_di_prova` dichiara `tipo_valore` (default `'TESTO'`) e accetta `default_value` |

⚠️ **Lo status di `DATO_ERRATO` nel BE è 400**, non 422 come scrive il §7.6.1: vale la mappa del BE (`error_policies.py`).

⚠️ **Rigenerando le policy è entrato `E_PREV_VALIDITA_SCADUTA`**, che sta su dbdev ma non nel CSV in git (è del giro di brief-db-scadenza-preventivi, `20261031-62`). È stato tolto a mano dal file generato: il BE non si aggancia a un changeSet non pushato. Finché quel giro non arriva in git, `genera_error_policies --check` su dbdev dà «DIVERGE»: è atteso.

### 7.7.1 Richiesta al team DB — il campo dei due guard a07 non arriva

🔴 **Difetto che non dà errore.** `config.trgfn_parameter_overrides_guard_tipo_valore` e
`config.trgfn_parameters_guard_tipo_valore` (`20261031-56`, `-57`) mettono il campo nel contesto
sotto la chiave **`'field'`** (`'field', 'value'` e `'field', 'default_value'`). Però
`script.fn_log_and_raise_error` porta sul canale `COLUMN` solo **`p_context->>'campo'`**
(doc auto-gen, blocco 4-bis). Il codice d'errore arriva, il campo no: il FE mostra il messaggio ma
non sa quale campo evidenziare. Il gemello `trgfn_parameters_guard_ammette_override` usa
`'campo'`, ed è la forma giusta.

- **Visto da**: `core/tests/db/test_parameter_overrides_db.test_valore_fuori_forma_non_si_salva`
  (nuovo), che si aspetta il campo `value` dal canale strutturato. Oggi è **rosso** su
  `None != 'value'`, ed è il rosso giusto. Il pgTAP `config/test-parameters-tipo-valore-v1` non
  controlla il campo, per questo è verde.
- **La richiesta**: nei due guard, `'campo'` al posto di `'field'` (changeSet nuovi, corpo dalla
  doc auto-gen), più un'asserzione nel pgTAP sul campo (`COLUMN` dell'eccezione) per i due casi.
  Il BE non cambia: il test diventa verde da solo.

### 7.7.2 D-6 — la soglia della ricerca universale sta in tre posti (deciso da Tid il 2026-11-01)

Una lista a catalogo prende la soglia da `ui.lista_definizione.ricerca_min_caratteri`
(`soglia_ricerca`, brief-db-be-fe-ricerca-soglia-per-lista). La 113 ce l'ha (3), ma oggi la
dicono anche:

- la view del BE, `require_min_search_length(q)` con `RICERCA_MIN_CARATTERI` (400 sotto soglia);
- la funzione, `length(btrim(p_search_term)) < 3` scritto nel corpo.

Sono tre copie della stessa regola. Se l'amministratore cambia la soglia della 113, il FE (che
legge il catalogo) manda termini che il BE rifiuta, o che la funzione scarta. **Proposta**: la
funzione non ha una soglia sua (o la legge da `ui.fn_lista_da_codice`), e la view usa
`soglia_ricerca('anagrafiche.ricerca_soggetti')`. Il lato BE si fa quando il lato DB è
pronto.

✅ **D-6 — DECISO da Tid il 2026-11-01: la proposta.** La soglia della 113 è quella del
catalogo, come per ogni lista. **Al team DB**: togliere il controllo `< 3` dal corpo di
`fn_search_soggetti_universale`, nello stesso giro del §7.7.1. Il termine vuoto resta un
rifiuto della funzione, ma la lunghezza minima la giudica il chiamante dalla soglia della
lista. Va aggiornato il pgTAP che oggi la prova, se c'è. **Al BE, dopo**: la view usa
`soglia_ricerca('anagrafiche.ricerca_soggetti')`, sempre con il 400 sotto soglia.

## 7.8 Terzo giro DB — §7.7.1 e D-6 (2026-11-01, applicato)

### 7.8.1 I changeSet

| changeSet | Cosa |
| --- | --- |
| `20_code/config/20261101-01` | `config.trgfn_parameters_guard_tipo_valore`: `'campo'` al posto di `'field'` nei due rami (`default_value` sul default, `tipo_valore` sul cambio di tipo) |
| `20_code/config/20261101-02` | `config.trgfn_parameter_overrides_guard_tipo_valore`: `'campo'` al posto di `'field'` (`value`) |
| `20_code/script/20261101-03` | `script.fn_search_soggetti_universale` senza `length(btrim(p_search_term)) < 3`. Il termine vuoto (NULL o soli spazi) resta `E_PARAMETRO_INVALIDO`; esce dal contesto la chiave `minimo_caratteri` |

Tutti e tre sono `CREATE OR REPLACE` sul corpo dello YAML precedente (`-56`, `-57`, `-58`),
confrontato riga per riga con la doc auto-gen: identico. La firma della ricerca viene dallo YAML,
che conserva il `%TYPE`. Trigger e GRANT non cambiano. Codici, messaggi e regole sono invariati.

Censimenti fatti:
- `'field'` come chiave di contesto: nella doc auto-gen la usano solo i due guard (tre punti);
- consumatori della soglia nel DB: nessun altro pgTAP chiama la ricerca con un termine corto
  aspettandosi il rifiuto, e nessuno legge `minimo_caratteri`.

### 7.8.2 pgTAP

| File | Cosa |
| --- | --- |
| `config/test-parameters-tipo-valore-v1.sql` (20 → 23) | 21-23: codice (`CONSTRAINT`) e campo (`COLUMN`) dell'eccezione per override, default e cambio di tipo |
| `script/test-search-universale-campi-ricerca-v1.sql` (11 → 12) | 12: un termine di **un** carattere (`§`, nella ragione sociale della fixture) trova il soggetto costruito |
| `script/test-search-soggetti-universale.sql` (22) | il test 6 pinnava «`'ab'` rifiutato»: ora pinna il termine di soli spazi |

### 7.8.3 Prova (2026-11-01, SQL estratto in transazione annullata)

- Scratch `zeroerp_ruoli`, come owner:
  - `test-parameters-tipo-valore`: **23/23** con l'SQL estratto, **20/23** senza. I tre nuovi
    distinguono il corpo nuovo dal vecchio;
  - `test-search-universale-campi-ricerca`: **12/12** con, senza si ferma al 12 sul rifiuto
    «minimo 3 caratteri»;
  - `test-search-soggetti-universale`: si ferma al test 7 **prima e dopo**, ed è il rosso noto
    dello scratch (§7.6.3: pesca un cliente dai dati). Il test 6 nuovo è verde.
- dbdev, come owner, solo la versione con l'SQL estratto di `test-search-soggetti-universale`:
  **22/22**. L'md5 delle tre funzioni è lo stesso prima e dopo.
- Guardrail statici verdi (`run_on_change`, `precondition_seed`, `ddl_su_trigger_automazione`,
  `grant_ruolo_batch`, `v1_congelato`, `sql_letterali`, `timestamp_senza_fuso`). Il preambolo
  pgTAP ha le due violazioni preesistenti di `test-grammatica-presidio-tipo-documento-v1`.
  Debito `throws_ok` invariato (110).

### 7.8.4 Per Tid — apply e corsa

`20261101-01`, `-02`, `-03`. Nessun mirror si sveglia. Corsa pgTAP: i tre file del §7.8.2.
✅ **Fatto il 2026-11-01** (Tid): migrazione applicata su dbdev, pgTAP verdi.

### 7.8.5 Per il BE (`dev/backend-tid`), dopo l'apply

1. **D-6**: la view della ricerca usa `soglia_ricerca('anagrafiche.ricerca_soggetti')` al posto
   di `RICERCA_MIN_CARATTERI`, sempre con il 400 sotto soglia. Il DB rifiuta solo il termine
   vuoto (`E_PARAMETRO_INVALIDO`, campo `search_term`).
2. **§7.7.1**: niente da cambiare. `test_valore_fuori_forma_non_si_salva` diventa verde da solo.
   Il campo arriva anche sul default (`default_value`) e sul cambio di tipo (`tipo_valore`), se
   un form del BE li scrive.
