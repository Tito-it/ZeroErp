# Brief DB — Liste ancora su `DataTable` grezza, secondo giro

## ⏭️ Chi riparte — aggiornato al 2026-10-31

**Riparte: team DB** (`dev/db-tid`) per le richieste del §4.5 (le colonne
di ricerca della ricerca universale e il suo ordinamento per utility) e del §4.6 (il preavviso delle scadenze
validato in scrittura). Le sei liste del §4.1 sono
convertite (§4.3, §4.4); poi si archivia il brief.

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
| 9 | team DB | La ricerca universale e le colonne `ricercabile_full` della lista 113, più l'ordinamento per utility (§4.5) | `20_code/script/` o seed `ui` | — |
| 9-bis | BE | A funzione pronta: `utility_list` nella whitelist della ricerca e nei registri (§4.5) | `dev/backend-tid` | 9 |
| 10 | team DB | Il valore di un parametro intero si valida quando si scrive, non quando si legge (§4.6) | `config` | — |
| 11 | BE/FE | ✅ Revisione critica del lavoro non committato, 2026-10-31 (§4.7) | `dev/backend-tid` | — |
| 12 | BE/FE | Archiviare il brief in `work-done/` | — | 9, 9-bis, 10 |

**Decisioni aperte di Tid:** nessuna. D-1, D-2, B1-bis, B8 e l'ordinamento per utility della 113 (§4.5) decisi il 2026-10-31.
**Committato:** il lato DB del 2026-10-31 (§7) è su `dev/db-tid`. Il lato BE/FE (righe 6-8 e 11) è **da committare** su `dev/backend-tid`. Il rotto temporaneo
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
