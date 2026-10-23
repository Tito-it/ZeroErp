# ZeroERP — Standard Frontend

> Questo documento definisce le regole di progettazione e sviluppo dell'interfaccia utente di ZeroERP.
> È vincolante per qualsiasi contributo al frontend. Le deroghe devono essere documentate e motivate.
>
> Ultimo aggiornamento: 26 settembre 2026
>
> Vedi anche:
>
> * [Catalogo building block frontend](catalogo-building-block-frontend.md) — inventario completo componenti, composable, utility, classi CSS

---

## Stack tecnologico

> ⛔ **Le versioni non stanno qui.** Fonte unica di verità:
> **`frontend/package.json`** (versione risolta in `package-lock.json`, runtime
> Node in `engines.node`). Questa tabella dichiara **a cosa serve** ogni pezzo —
> il ruolo non invecchia, il numero sì.
>
> ⚠️ **Perché la colonna «Versione» è sparita il 2026-09-09.** Lo stesso stack
> era scritto in tre documenti — qui, in `.codex/AGENTS.md` e in
> `.codex/PROJECT_CONTEXT.md` — e li diceva **tutti e tre diversi e tutti e tre
> sbagliati** rispetto al lock: Pinia, vue-i18n e Vite erano indietro, e due
> salti di **major** erano passati senza che nessuno dei tre se ne accorgesse. ⭐ Vale il precedente di Python
> (`.python-version`): *un numero scritto in due posti ne ha sempre uno stantio,
> e quello senza presidio è sempre il documento.*

| Componente | Ruolo                   |
| ---------- | ----------------------- |
| Vue.js     | Framework UI            |
| Vite       | Build tool e dev server |
| PrimeVue   | Libreria componenti     |
| PrimeIcons | Iconografia             |
| Pinia      | Gestione stato          |
| Vue Router | Navigazione             |
| vue-i18n   | Multilingua             |
| Axios      | Client HTTP (⛔ importato in **un solo file**: `src/core/api.js`) |
| Node.js    | Runtime di sviluppo (via nvm) |

* **Build**: `./node_modules/.bin/vite build` (serve nvm per caricare Node).
* **Dipendenze npm**: non se ne aggiungono senza conferma dell'utente.
* **Header di licenza sui file nuovi** (decisione di Tid, 2026-08-26):
  `templates/javascript-header.txt` per i `.js`, `templates/vue-header.txt` per
  i `.vue`. Lo presidia `scripts/check_license.py` (pre-commit), che guarda i
  file **aggiunti** e legge le prime 10 righe. In un `.vue` l'header va **prima
  di `<script setup>`**, in commento HTML (l'unica forma valida in cima a un
  Single File Component); lo `// Scopo: ...` resta dentro `<script setup>`.

---

## Struttura del progetto

La struttura delle cartelle rispecchia i domini del database. Chi conosce il backend riconosce immediatamente il frontend.

```
src/
  core/               ← client API, composables, componenti riutilizzabili, utilities
  amministrazione/    ← dominio amm-software (solo ADMIN)
  anagrafiche/        ← dominio anagrafiche (gestione geografica, soggetti)
  catalogo/           ← dominio catalogo
  pratiche/           ← dominio pratiche
  vendite/            ← dominio vendite
  acquisti/           ← dominio acquisti
  magazzino/          ← dominio magazzino
  pagamenti/          ← dominio pagamenti
  contabilita/        ← dominio contabilita'
  strumenti/          ← viste operative trasversali. Dominio SENZA `schemaDb`
                        (dal 2026-09-26): le voci sono di aree diverse e
                        ognuna porta la sua con `requireArea` — code di lavoro
                        (`strumenti`), giornale eventi (`vendite`: vista e
                        client restano in `vendite/`), email dell'operatore
                        (nessuna: `skip_area_check` BE, la vede ogni operatore).
                        Dal 2026-10-06 il gruppo «Diagnostica» (`adminOnly`
                        sul gruppo, ereditato dai figli): processi automatici,
                        audit log, errori tecnici, log email — viste ed
                        endpoint restano di `amministrazione/` / `/amm-software/`
  documenti/          ← MOTORE: generazione ed emissione dei documenti (PDF,
                        scelta template), condivisa dai domini che stampano
  config/             ← configurazione (tabelle, impostazioni, modelli documenti)
  ui/                 ← personalizzazione delle liste (definizioni, colonne, preset)
  portale/            ← portale esterno (attivazione, profilo)
  shop/               ← shop esterno (attivazione)
  router/             ← definizione rotte
  stores/             ← store Pinia globali (auth, ui, tabs, navigation, context,
                        ai, parameters)
  locales/            ← file i18n (it.json, en.json)
  assets/             ← stili globali (theme.css, main.css)
```

Ogni cartella di dominio contiene:

```
anagrafiche/
  api/                ← client API per gli endpoint del dominio
  stores/             ← store Pinia per il dominio
  views/              ← pagine intere (lista, dettaglio, tab)
  components/         ← componenti specifici del dominio
  composables/        ← logica riusabile del dominio
  iscrizioni.js       ← cio' che il dominio aggiunge ai registri di `core` e dei
                        motori (facoltativo; lo carica `main.js` all'avvio)
```

`pratiche/` e `documenti/` sono **motori**: ogni dominio li usa, e loro non
nominano nessun dominio (§«Confini fra domini»).

`core/` e' l'equivalente frontend di `dbops` e `script`: nessun dominio lo chiama esplicitamente, ma tutti dipendono da lui.

---

## Principio di omogenita' UI

> **L'operatore deve sentirsi a casa in ogni schermata.**

Tutte le UI seguono gli stessi pattern visivi e comportamentali. Non esistono eccezioni per dominio.
Se un pattern viene migliorato, il miglioramento si applica a tutte le schermate — mai a una sola.

Le regole di consistenza sono:

1. **Un solo modo di fare ogni cosa** — lista, form, filtri, paginazione, notifiche
2. **Stesso layout ovunque** — toolbar + tabella + drawer, senza varianti
3. **Stessi componenti ovunque** — `PageActionsBar`, `RowActionsMenu`, `FormFooter`, `useSearchTable`, Tag per stati
4. **Stesse classi CSS ovunque** — `app-page`, `app-datatable`, `form-grid`, mai CSS scoped per layout
5. **Nessun testo hardcoded** — tutto via `$t()`, sempre
6. **Modifiche al pattern devono essere globali** — se cambi il paginator, cambi `useSearchTable` una volta e tutte le liste si aggiornano

### Import PrimeVue riservati — li ferma il lint

⛔ Un componente PrimeVue che ha un wrapper nostro **non si importa
direttamente**. Lo ferma `no-restricted-imports` in
[eslint.config.js](../../../../frontend/eslint.config.js)
(`IMPORT_PRIMEVUE_RISERVATI`, dal 2026-10-03): l'errore compare nell'editor
mentre si scrive, e `npm run lint` è rosso. La regola la verifica lo strumento,
non la memoria di chi scrive.

| Import | Al suo posto | Chi lo può importare |
| --- | --- | --- |
| `primevue/dialog` | `<AppDialog>` | solo `core/components/AppDialog.vue` |
| `primevue/confirmdialog` | `useConfirmAction` | solo `App.vue` (la ConfirmDialog globale) |
| `primevue/useconfirm` | `useConfirmAction` | solo `core/composables/useConfirmAction.js` |
| `primevue/datatable` | `<ListaConfigurabile>` | i componenti **standard** (sezione `standard` del registro, che il lint legge da lì), più le eccezioni del registro marcate sul punto (§«Regola zero della lista») |
| `primevue/drawer` | `<AppDrawer>` | solo `core/components/AppDrawer.vue`, più `AppLayout` (menu mobile) e `FiltriLista` (filtri dal basso), che non sono drawer laterali (dal 2026-10-03, a migrazione finita: nessun registro) |

- **La sede** è esentata dalla configurazione, non da un commento.
  ⚠️ Il lint da solo **non** la protegge: un `eslint-disable-next-line
  no-restricted-imports` lo zittisce in qualunque file (provato il 2026-10-03:
  `primevue/dialog` importato così, lint verde). A fermarlo sono i guard, che le
  direttive non le leggono: `check-dialog-chrome.mjs` per dialog, confirmdialog e
  useconfirm, il registro per la DataTable, `check-drawer-width.mjs` per il
  drawer (con la larghezza scritta a mano sul tag di `<AppDrawer>`).
- **Un'eccezione della DataTable** si scrive in tre posti, ed è voluto: il
  motivo in un commento sopra l'import,
  `// eslint-disable-next-line no-restricted-imports -- <motivo>` subito sopra
  l'import, e la riga nel registro (`scripts/check-datatable-baseline.mjs
  --baseline`). Il lint da solo non basterebbe: un commento costa dieci secondi,
  mentre il registro è un cricchetto e la sua modifica si vede nel diff. ⚠️ La
  direttiva **non** conta come motivazione per il registro.
- **Un'eccezione scaduta è un errore** (`reportUnusedDisableDirectives:
  'error'`): se l'import se ne va e il commento resta, il lint è rosso.
- I guard `check-dialog-chrome.mjs` e `check-datatable-baseline.mjs` restano.
  Il primo controlla anche il chrome (`header`, `closable`, `confirmAction`), il
  secondo il verso del debito.
- **Un componente entra nella tabella quando nasce il suo wrapper**, non prima:
  un divieto senza un'alternativa da indicare non si può rispettare. Il caso
  di `primevue/drawer`: il 2026-10-03 `AppDrawer` era un guscio minimo con un
  consumatore e 82 file montavano `<Drawer>` direttamente; prima è nata la sede
  vera (§«Drawer (nuovo e modifica)»), poi gli 80 drawer laterali ci sono passati sopra, e solo
  allora il drawer è entrato in tabella — a zero, senza registro. Storia e
  decisioni in `work-done/analisi-fe-chrome-drawer.md`.

---

## Layout generale

```
┌─────────────────────────────────────────────────────────┐
│                       TOPBAR (48px)                      │
├──────────┬──────────────────────────────────────────────┤
│          │  CONTENT TABS (tab aperti, multi-entita')    │
│          ├──────────────────────────────────────────────┤
│ SIDEBAR  │  BREADCRUMB                                  │
│          ├──────────────────────────────────────────────┤
│          │                                              │
│          │           AREA CONTENUTO                     │
│          │                                              │
└──────────┴──────────────────────────────────────────────┘
```

### Sidebar sinistra

- Sempre visibile, collassabile (larghezze nei token `--app-sidebar-width` e
  `--app-sidebar-width-collapsed` di `theme.css`)
- Stato a tre fasi: HOME (domini L1) → DOMINIO (voci L2) → collassata (icone + tooltip)
- Preferenza persistita in localStorage
- Configurazione centralizzata in `core/navigation.js` — una sola fonte di verita'
- Logo e nome applicazione in cima, logout e comprimi in fondo
- Mobile (< 768px): overlay drawer invece di sidebar fissa, **sempre espanso**
  (icone + etichette, `--app-sidebar-mobile-width`)
- Tablet (768–1023px): rail inline compresso a forza; il pulsante «espandi» in
  fondo apre lo **stesso drawer** espanso. Motivo: sul touch non c'e' hover,
  quindi niente tooltip — il menu coi nomi deve esistere come superficie

### Preferiti utente

I preferiti di navigazione sono **solo frontend**: nessuna API, nessun backend,
nessun DB. La persistenza usa `localStorage` tramite `useNavigationStore`, con
chiavi user-scoped sincronizzate al login da `syncUserFavorites(userId)`.

Regole:

- Modello dati store: `{ [domainKey]: routePath[] }`, array ordinato per dominio.
- Cap: massimo 4 preferiti per dominio. Il quinto tentativo mostra toast warn
  `nav.preferiti_limite_raggiunto` e non modifica lo stato.
- Migrazione legacy: un vecchio valore stringa salvato su
  `domain_default_<domain>` viene letto come array di 1 elemento, copiato
  nella chiave personale `domain_default_<domain>_user_<id>` e rimosso dalla
  chiave legacy.
- Logout: `clearUserState` pulisce solo lo stato in memoria e non cancella
  il localStorage personale. Al nuovo login dello stesso utente i preferiti
  ricompaiono; al login di un altro utente vengono caricate altre chiavi.
- Atterraggio dominio: clic su dominio dalla sidebar HOME apre il primo
  preferito del dominio; se assente, la prima voce L2; se assente, la route
  base dominio.
- Regola anti-salto: se l'utente e' già nel dominio attivo, ricliccare il
  dominio non deve forzare la navigazione al preferito #1.
- I preferiti filtrati da permessi/accessi BLOCCATI non vengono renderizzati,
  ma restano nello storage e ricompaiono se l'accesso torna disponibile.
- Sidebar collassata: i preferiti sono icone con tooltip `Dominio · Voce`;
  drag-and-drop disabilitato.

Building block obbligatori:

- `useNavigationFavorites` centralizza risoluzione label/icona, filtro permessi,
  apertura tab, `router.push`, `nav.setDomain` e riordino del sottoinsieme
  visibile.
- `FavoriteItem` renderizza il singolo preferito nelle varianti `sidebar` e
  `tile`.

I consumer (`SidebarHome`, `HomeView`) gestiscono solo il layout e gli handler
drag-and-drop; non devono duplicare filtro permessi, label/icon resolution o
logica di navigazione.

### Topbar

- Altezza fissa 48px
- Selettore dell'emittente attivo, **titolo dell'area** (il dominio della rotta
  con la sua icona — non la pagina: quella la dicono già la scheda e il
  breadcrumb; decisione di Tid 2026-09-19), chip del contesto globale
- Iniziali dell'utente (chip `SUPER_ADMIN` per chi lo è) e data
- ⭐ **Il gruppo «salute del sistema»** (`.topbar-actions-inline`), due contatori
  ambientali gemelli, entrambi sopra `useRefreshPeriodico`, entrambi spenti su
  403 per chi non passa la porta: il **badge delle code** (`pi-inbox`, lavori ·
  stampa, warn se un worker è giù, 60 s, click → drawer code) e, dal 2026-09-18,
  il **pallino dei presidi** (`NAV_ICONS.PROCESSI_AUTOMATICI`, allarmi · non
  letti, **verde con lo `0` quando è tutto a posto**, 300 s, click → «Processi
  automatici»). ⛔ Stanno **qui e non accanto alle iniziali**: parlano del
  sistema, non «notifiche per te» (decisione #8 di Tid). Catalogo BB:
  `useQueueCountsPolling`, `usePresidiPolling`
- Pulsante ricerca universale (Ctrl+K) e assistente AI (se abilitato)
- Kebab utente (preferiti, lingua, tema; su mobile promuove anche le voci inline)
  e logout

### Content Tabs

- Barra tab sotto la topbar per navigazione multi-entita'
- Massimo 10 tab aperti (`TABS.MAX_OPEN` in `constants.js`). ⭐ **Oltre il limite la decima si sostituisce** (Tid, 2026-09-30): le prime nove sono il tavolo di lavoro, l'ultima in fila è la scheda di passaggio. Una conferma **nomina** la scheda che si chiude, ed è **rossa** se quella ha modifiche non salvate, come la X di chiusura. «Annulla» lascia l'operatore dov'era. Fino a quel giorno l'undicesima era bloccata con un toast
- ⛔ **Le schede le apre solo il guard del router** (`router.beforeEach`): sidebar, preferiti e widget fanno solo `router.push`. Un secondo punto che chiama `openTab` prima del push farebbe due conferme per un clic. La conferma la mostra `ContentTabs`, perché il guard non ha un componente in cui aprire una dialog: lo store custodisce la richiesta in attesa (`chiediSostituzione`) e ContentTabs risponde. Presidio: `stores/tabs.spec.js`
- KeepAlive per preservare lo stato dei tab
- Shortcut: Ctrl+W chiude tab, Ctrl+Tab prossimo, Ctrl+Shift+Tab precedente
- Tab label derivata automaticamente da route meta via `resolveTabLabel()`

### Area contenuto

- Occupa tutto lo spazio rimanente (flex: 1)
- Padding uniforme (token `--app-content-padding` di `theme.css`)
- Il contenuto non scrolla — la DataTable gestisce il suo scroll interno

---

## Pattern lista (standard per tutte le schermate)

Ogni schermata di elenco segue questo schema fisso:

```
┌─────────────────────────────────────────────────────────┐
│ [Paginatore: ◀ 1 2 3 ▶ | 25/pag | Vai a | 1/5]  SOPRA │
├─────────────────────────────────────────────────────────┤
│ [🔍 Cerca...]  [Filtro 1 ▼]  [Filtro 2 ▼]    [+ Nuovo] │
├─────────────────────────────────────────────────────────┤
│ Colonna A │ Colonna B │ Colonna C │ Colonna D │ Stato  │
│───────────┼───────────┼───────────┼───────────┼────────│
│ dato      │ dato      │ dato      │ dato      │ ● att  │  ← click riga → drawer edit
│ dato      │ dato      │ dato      │ dato      │ ● att  │
│ dato      │ dato      │ dato      │ dato      │ ○ dis  │
│           │           │           │           │        │
│           (scroll verticale interno)           │        │
└─────────────────────────────────────────────────────────┘
```

### ⛔ Regola zero della lista — `<ListaConfigurabile>`, non `DataTable` grezza

> **Una lista si monta con `<ListaConfigurabile codice="...">`. Importare
> `primevue/datatable` in una view è l'ECCEZIONE, e va motivata.**

⚠️ **Questa regola non era scritta da nessuna parte fino al 2026-08-30**, e si
è visto: nel mese di agosto i file con `DataTable` grezza sono tornati a
crescere. Nel frattempo questo stesso documento spiegava
*come* configurare una `DataTable` (poco più sotto) senza dire prima di non
scriverla: chi legge in buona fede trova le istruzioni per fare la cosa
sbagliata.

**Cosa si guadagna**, e vale anche se non si cambierà mai libreria:

* colonne, ordine, larghezze, visibilità e permessi arrivano dal **catalogo**
  (`ui.lista_colonna`, risolto da `ui.fn_resolve_lista_config`) invece che da
  `<Column>` scritte a mano;
* l'operatore può **personalizzare** le colonne, e la preferenza è sua;
* ritiro dinamico, export, azioni di utility e paginazione arrivano **gratis**;
* il file della view smette di nominare PrimeVue — e il giorno di un cambio
  libreria si tocca **un** building block invece di N view.

**Come si fa, e non serve aspettare nessuno:** la lista ha bisogno del suo
`codice` — una riga in `ui.lista_definizione` più N righe in `ui.lista_colonna`.
⭐ È **dato, non DDL**: si crea dall'amministrazione in-app (`ListaDefinizionePanel`,
`ListaColonnaPanel`), oppure con `scripts/gen_seed_lista.py`. Nessun brief,
nessun blocco.

**Le eccezioni legittime — le uniche:**

| Caso | Cosa si usa |
| --- | --- |
| **Dettaglio espanso di un risultato** della ricerca universale | `SearchDetailTable` (`core/components/details/`), **non** il BB |
| **Matrice slot/override** (la popolazione la decide il catalogo, l'operatore imposta l'override sulla riga) | `MatriceOverride`, **non** il BB |
| Tabella di **anteprima** dentro un dialog, non paginata e non configurabile | `DataTable` grezza, con il motivo scritto in un commento sopra l'import |

⛔ **Le righe di un documento NON sono un'eccezione, dal 2026-09-28** (decisione
di Tid, brief-db-liste-righe-documento). Fino a quel giorno lo erano, e su tablet
le 9-10 colonne di un preventivo uscivano in uno scroll orizzontale che col
touch non si usa. Un documento ha un numero arbitrario di righe con molti
attributi: e' una lista. `RigheMasterDetailTable` monta `<DrawerTabLista>` con
la macchina del form `useFormInline`; chi ha ancora una `DataTable` di righe
(BoM, fattura, contratto: lotti C e D) sta nel registro del debito, non fra le
eccezioni.

⛔ **«È dentro un drawer» NON è un'eccezione, ed è l'errore che si fa più
spesso.** Una lista su un tab di drawer — un'entità con endpoint suo,
popolazione arbitraria e ciclo di vita indipendente dal padre — **è una lista**:
le manca il paginator, non la natura. Si monta con
`useDrawerTabLista` + `<DrawerTabLista>` (2026-09-01), che sono
`useListaConfigurabilePage` + `<ListaConfigurabile>` più il legame col padre.
⭐ Il criterio in tre domande sta nel
[piano PrimeVue 5 §Gruppo B](../work-in-progress/piano-migrazione-primevue-5.md),
riscritto il giorno in cui il secondo caso è emerso.

⭐ **La matrice slot/override ha il suo building block: `MatriceOverride`**
(regola del 2, estrazione approvata da Tid il 2026-09-05; primo consumatore
`OperatorePermessiTab`). Non pagina per scelta di modello: la popolazione è
limitata dal catalogo e la schermata esiste per farla vedere tutta. 🔴 Il
pattern è nato sul tab Utilities degli emittenti
(`EmittenteFiscaleUtilitiesTab`), che però monta ancora una `DataTable` grezza:
debito dichiarato, non eccezione.

⛔ **Non sono eccezioni**: «è una lista piccola», «è solo per l'admin», «tanto
non la guarda nessuno», «faccio prima». Una lista che nessuno guarda non è una
lista senza problemi: è una lista che nessuno ha ancora aperto.

**Come si verifica**, prima di dire che una view è finita:

```bash
cd frontend && npm run guard:datatable
```

Il presidio (`scripts/check-datatable-baseline.mjs`) confronta gli import di
`primevue/datatable` con il registro `scripts/datatable.baseline.json`, che
**elenca i file**: se ne compare uno nuovo è rosso e lo nomina — hai aggiunto
una lista fuori standard, o un'eccezione senza il commento che la motiva. È un
cricchetto: rosso anche quando il numero **cala**, perché la baseline va
abbassata nello stesso giro. Prima ancora del guard, l'import lo ferma il lint
(§«Import PrimeVue riservati»): un'eccezione vuole anche la direttiva
`eslint-disable-next-line no-restricted-imports` sopra l'import.

### Regole fisse

> ℹ️ Le regole qui sotto valgono **dentro** `<ListaConfigurabile>` (che le
> applica da sé) e nelle due eccezioni sopra. ⛔ Non sono un invito a montare una
> `DataTable` a mano: quella decisione la prende la regola zero.

- **Paginazione SOPRA** la tabella (`paginatorPosition: 'top'`)
- **Righe per pagina**: ⭐ **misure e default stanno nel DATABASE** (catalogo `ui.misure_pagina`, dal 2026-09-30, decisioni di Tid del 29-09) e si leggono dal BB [`core/misurePagina.js`](../../../../frontend/src/core/misurePagina.js): `misureOpzioni()` per il selettore, `misuraDefault(USO_MISURA.PAGINA | USO_MISURA.COMPATTA)` per la partenza. Le carica il guard del router **una volta per sessione, attese**, prima di qualunque rotta sotto `AppLayout` per l'operatore (anche 404 e forbidden: le legge anche il layout); se la chiamata fallisce si apre la pagina «Avvio non riuscito», che sta **fuori** dal layout, ⛔ **senza ripiego** scritto nel FE (sarebbe una copia del catalogo). ⛔ Nessun numero di righe e nessun array di opzioni scritto in un componente o in uno store: fino al 2026-09-30 erano `PAGINATION` in `constants.js` più due array a mano, e un preset a 15 lasciava il selettore **vuoto** senza errore. Una lista standard parte dalla misura `PAGINA`, adattata al viewport da `useSearchTable` (la `COMPATTA` sotto `BREAKPOINTS.TABLET`, regola unica in `misuraPerViewport`). ⭐ **Dentro un drawer o un dialog la lista parte dalla `COMPATTA`** (decisione di Tid del 2026-09-28): lo dichiara lo store con l'**uso**, `misura: USO_MISURA.COMPATTA` in `useListaStoreCore`/`createListaStore`/`createCrudStore` (e in `usePagedDashFetch`) — ⛔ mai il numero: le opzioni di uno store si scrivono a livello di modulo, e un numero letto lì verrebbe letto **prima** che il guard carichi il catalogo (la vecchia opzione `limit` è ritirata e **solleva**). Il preset di sistema della lista lo dichiara a DB (`ui.lista_preset.pagina_dimensione`), che rifiuta una misura fuori catalogo (`E_UI_MISURA_PAGINA_NON_AMMESSA`).
- **Indicatore pagina**: `1/5` con JumpToPageDropdown per salto diretto. ⭐ Su **tablet e schermo stretto** (`(hover: none), (max-width: 1023.98px)`) il JumpToPageDropdown è **nascosto** via CSS in `main.css` (2026-09-28): doppia la navigazione ◀ 1 2 3 ▶, e `1/5` resta visibile
- **Font compatto** sul paginator (`0.8rem`)
- **Azioni pagina/lista**: building block `PageActionsBar` — refresh, nuovo e azioni utility/secondarie con comportamento responsive unico
- **Click riga** → apre drawer in edit (modifica = interazione principale)
- **Colonna azioni** riservata alle **azioni secondarie** (apri sub-drawer, disattiva, ecc.) — mai mettere la modifica tra le azioni: e' il click riga. Vedi sotto "Colonna azioni di riga".
- **Filtri** sopra la tabella nella toolbar, dentro `<FiltriLista>` (vedi
  §«Filtri della lista» qui sotto): in linea su desktop, in un drawer dal basso
  in modalità compatta. Flex-wrap per il responsive della riga in linea
- **Ricerca** con debounce 400ms (gestito da `useSearchTable`)
- **DataTable** sempre con: `lazy`, `removable-sort`, `striped-rows`, `scrollable`, `scrollHeight="flex"`
- **Scroll orizzontale** gestito globalmente da `.app-datatable` — non impostare `table-style="min-width: ..."` nelle singole liste salvo eccezioni documentate. Le soglie per 8/10/12 colonne partono dal root `.app-datatable`, così restano valide anche quando PrimeVue ricalcola il container scrollable dopo il caricamento dei record.
- **Liste annidate** dentro drawer, expansion row o sub-pannelli devono aggiungere `app-datatable--inner` oltre a `app-datatable`: restano compatte e sono escluse dalle soglie larghezza delle liste principali. Esempio: righe preventivo e pannello componenti BoM.

### Filtri della lista — `FiltriLista` (drawer dal basso in modalità compatta)

> ✅ **Adozione COMPLETA dal 2026-09-23** (lotti L2 e L3 chiusi): nessuna view
> scrive più `app-page-filters` a mano, nessuna coppia di date è scritta a mano,
> nessuna larghezza di filtro sta in un tag. I tre registri di
> `npm run guard:filtri` sono a **zero** e da qui in avanti dicono una cosa
> sola: *una lista nuova fuori standard li fa risalire*.
> Decisioni e cronaca: [brief-fe-filtri-lista-su-schermo-compatto.md](../work-done/brief-fe-filtri-lista-su-schermo-compatto.md).

**La regola**: un filtro è **stato della lista**, non decorazione della view.
Ne discende che *dove* i filtri si rendono — e il segno che sono attivi —
appartengono al building block della lista, come il paginator, il ritiro delle
colonne e le azioni di testata.

```vue
<FiltriLista :store="store" :inert="perimetroBloccato">
  <template #sempre>
    <InputText v-model="searchText" :placeholder="…" />
  </template>
  <LookupSelect … @change="onStatoChange" />
  <FiltroPeriodo :periodo="periodo" />
</FiltriLista>
```

⚠️ L'esempio **non** mostra due `<DatePicker>` con `@date-select`: quel
cablaggio è il difetto che `<FiltroPeriodo>` esiste per togliere (§«Il periodo è
UN filtro»).

| Modalità | Resa |
| --- | --- |
| Desktop | `#sempre` + slot di default in linea, dentro `app-page-filters` |
| Compatta (`< 1024px` **o** touch senza hover) | `#sempre` in linea + **icona filtro col segno**; al click lo **stesso** slot dentro un `Drawer position="bottom"`, su una griglia di **al massimo due filtri per riga** (§sotto), «Pulisci filtri» in fondo |

⭐ **«Pulisci filtri» vive su entrambe le rese** (A3, Tid 2026-09-23): nel
drawer compatto col nome per esteso, nella toolbar desktop come **icona sola col
tooltip**, come ogni altro comando di quella riga. Compare quando c'è qualcosa da
riportare al default — non quando c'è un segno: le due domande divergono da
quando esistono i valori neutri.

**Il segno ha tre stati**, e dal 2026-09-23 il **numero c'è sempre**: niente
(niente sta restringendo) · **numero grigio** (qualcosa restringe, tutto al suo
default) · **numero blu** (almeno uno diverso dal default). ⛔ Prima lo stato
«tutto al default» era un **pallino senza numero**, e a video si leggeva
«0 → 2» toccando **una** cosa sola: il filtro già attivo valeva zero un istante
e uno quello dopo. *Il conteggio non è mai cambiato — era la forma a
nasconderlo, e un segno che nasconde ciò che conta fa sembrare sbagliato un
conto giusto.*

**La ricerca non è un filtro** e resta **sempre** a video (slot `#sempre`): è il
gesto principale di una lista, gli altri filtri la restringono.

⭐ **Ma solo se la lista cerca** (Tid, 2026-09-23 — brief-be-ricerca-full-liste-residue
§7-bis). La configurazione della lista porta `ricerca_full`: vero se il catalogo
accende almeno una colonna in cui l'operatore può cercare. Lo scaffolding
(`useListaConfigurabilePage`, quindi anche `useDrawerTabLista`) lo scrive in
`store.ricercaFull`, e `<FiltriLista>` **non rende `#sempre`** quando è `false`.
La chiave la dichiara **`useListaEmptyStateFetch`** (dal 2026-09-24), quindi la
ha ogni store-lista, anche quelli scritti a mano: nessuno store la dichiara per
conto suo. Nessuna view lo scrive a mano: la casella e il catalogo non possono più dire due
cose diverse. ⚠️ Solo `false` la toglie — `null` («non si sa ancora») la lascia,
così non lampeggia a ogni apertura. ⛔ Le caselle **senza lista a catalogo**
(`ConfigTablePanel`, i drawer di BoM e righe del contratto) e la
casella della dashboard gruppi, fuori da `FiltriLista`, restano come sono: non
hanno un catalogo da leggere.

**I filtri si applicano subito**, a ogni cambio, anche col drawer aperto:
`useStoreFilterBindings` scrive diretto sullo store, che è la sede del filtro.

#### ⛔ Un filtro si lega con un **binder**, mai con un `ref` che spinge e basta

```js
// ⛔ NO — spinge nello store e non torna indietro
const attivoFilter = ref(true)
function onAttivoChange() { store.filters.attivo = attivoFilter.value; applyFilters() }

// ✅ SÌ — `bindSelect` porta con sé il `watch` store → widget
const { bindSelect } = useStoreFilterBindings(store, applyFilters)
const { value: attivoFilter, onChange: onAttivoChange } = bindSelect('attivo')
```

**Perché è una regola e non uno stile**: dal 2026-09-22 i filtri si possono
cambiare **da fuori** il widget — «Pulisci filtri» del drawer compatto
(`azzeraFiltri`), un deep-link `?search=` che azzera i default data, un reset.
Un `ref` a senso unico resta a mostrare il valore di prima su una lista che non
ce l'ha più: *la casella dice una cosa e l'elenco ne dice un'altra*, e
**nessuno fallisce**. ⚠️ Si vede solo **sotto i 1024px**, perché è lì che vive
il pulsante che pulisce.

🔴 **Non era teorico**: i filtri a senso unico sono stati sanati il 2026-09-23. E la
forma del difetto si vedeva dentro un file solo — `PraticheSearchTable` aveva
il `watch` scritto a mano per **uno** dei quattro filtri e non per gli altri
tre: non una policy, una dimenticanza. Presidio: il controllo 2-bis di
`npm run guard:filtri` verifica che dietro un `:store` ci sia davvero il
contratto; per il verso store → widget la difesa è questa regola.

⭐ **Dove un binder non arriva, ci arriva un `computed` sullo store** — che è la
stessa cosa detta meglio, perché lo stato non si copia affatto:
`scadenza_mese` dei contratti (lo store tiene `YYYY-MM`, il widget una `Date`:
è un punto che *traduce*) e i tre criteri di `RatePickerDialog`. ⛔ Ciò che non
va bene è la **terza** forma: un `ref` che scrive nello store e non lo rilegge.
⛔ Nessun pulsante «Applica»: vorrebbe una copia temporanea dei filtri accanto a
quella vera, e quella copia diverge alla prima cosa che la tocca da fuori (un
deep-link `?search=`, un `reset()`, un cambio di emittente).

#### Il segno dei filtri attivi — tre stati

| Stato dei filtri | Segno |
| --- | --- |
| Nessun filtro con valore | niente |
| Filtri con valore, **tutti** al loro default | **numero grigio** = quanti filtri limitano la lista |
| Almeno un filtro diverso dal default | **numero blu** = quanti filtri limitano la lista, **default compresi** |

⭐ **Perché i default contano**: `data_da` a «oggi-60gg al primo del mese»
restringe esattamente come un filtro scelto a mano — che nessuno l'abbia
digitato non lo rende meno vero. Nel momento in cui i filtri non sono più
sempre a video, una lista ristretta e una lista vuota si assomigliano, e
l'operatore attribuisce il buco al sistema («il documento non c'è»).
⚠️ Il colore esiste perché un segno **sempre** uguale smette di essere un
segno: il grigio distingue «ristretta come nasce» dal blu «ristretta da te». Il
numero, invece, c'è in entrambi i casi (§sopra: il pallino senza numero è
ritirato il 2026-09-23).

⛔ **Il grigio non copre i default risolti a RUNTIME, ed è deciso** (D9, Tid
2026-09-22). I default sono il letterale `filterDefaults` dello store, cioè la
fotografia scattata alla *nascita* della lista: un default che arriva dopo il
mount — `UtilityPerRuoloSelect apply-default` — lì non c'è, quindi il numero
esce **blu** e non grigio. **La regola è una sola: si contano sempre i filtri,
default compresi.** L'eccezione non starebbe in piedi da sola — il caso gemello
(l'operatore che *svuota* un filtro di default) vorrebbe la regola opposta, e il
conteggio risponderebbe a due domande diverse a seconda di come il valore ci è
arrivato. Il numero resta vero comunque: dice quante cose stanno restringendo
l'elenco.

⛔ **Il conteggio non si calcola nelle view.** Nasce in `useListaStoreCore`, che
già conosce l'elenco dei filtri di quella lista (`filterDefaults`) e i loro
valori di partenza (`filtriDiPartenza()`), e passa da una funzione pura con il
suo `.spec.js` (`core/utils/segnoFiltri.js`). Una lista che «dimentica» di contare direbbe *«nessun filtro»
mentre filtra*, senza nessun errore.

#### Nel drawer: al massimo DUE filtri per riga

```
┌──────────────────────── Filtri ────────────────────────┐
│ [ Servizi                                     ▼ ]      │  ← combo: riga intera
│ [ Data da   📅 ]  [ Data a   📅 ]                       │  ← il periodo: sempre in coppia
│ [ ◉ Mostra non attivi                          ]       │  ← interruttore: riga intera
│ Pulisci filtri                                         │
└────────────────────────────────────────────────────────┘
        ↑ drawer ≥ 27rem: anche le combo si affiancano, due per riga
```

**Regola (Tid, 2026-09-22): su una riga non stanno più di due elementi.** Tre
filtri in fila su un telefono sono tre filtri illeggibili, e un tablet non è una
ragione per cambiare la forma della maschera. La griglia ha **due colonne,
sempre**.

**Il periodo sta su una riga sola, e non per via del layout.** `data_da`/`data_a`
**non sono due filtri**, sono *un* filtro con due estremi: si montano con il
building block del periodo (§sotto), che è **una** cella della griglia e si
divide in due. Spezzarli su due righe rompe la cosa che l'operatore legge come
una.

**Tutto il resto prende la riga intera finché due non ci stanno LEGGIBILI.** La
soglia è una `@container` (min-width 27rem = 2 × `--app-filtro-min-combo` + gap),
non una `@media`: dipende dalla larghezza del **drawer**, non della finestra.
⛔ L'interruttore (`FiltroToggle`) prende la riga intera **anche** sopra la
soglia: la sua etichetta sta fuori dal controllo e non sa degradare in ellissi.
⭐ Il filtro che a mezza riga non si legge nemmeno lì ha una leva dichiarata,
`class="app-filtro-largo"`, valida solo dentro il drawer. ⚠️ È una leva, non un
default: se la mettessero tutti, la griglia tornerebbe una pila.

#### Il periodo è UN filtro — `bindPeriodo` + `<FiltroPeriodo>`

```vue
<script setup>
const { bindPeriodo } = useStoreFilterBindings(store, applyFilters)
const periodo = bindPeriodo()                                  // 'data_da' / 'data_a'
// con un floor su un solo estremo (contratti):
// const periodo = bindPeriodo('data_da', 'data_a', { clearToDa: defaultFiltroDataDa })
</script>

<FiltroPeriodo :periodo="periodo" />
```

⛔ **Due `<DatePicker>` scritti a mano nei filtri sono fuori standard** e li
conta `npm run guard:filtri` (registro `coppie_date_a_mano`, a zero dal
2026-09-23: una coppia nuova lo fa risalire). Un DatePicker **solo** resta legittimo: è un filtro a sé («scadenza
mese» dei contratti), non un periodo.

⭐ **La ragione meno visibile per cui il BB esiste è il verso degli eventi.**
Nelle liste che scrivevano la coppia a mano il cablaggio era
**divergente**: `@date-select` + `@clear-click` in quasi tutte,
`@update:modelValue` nei contratti. Non sono equivalenti — col primo una data
**digitata** nella casella non applica il filtro: l'operatore vede la data che
ha scritto e una lista che non l'ha ricevuta, senza nessun errore. Il BB usa
`@update:model-value`, che copre calendario, digitazione e svuotamento.

⚠️ **`bindPeriodo` espone `setDa`/`setA`, non i ref nudi**: il componente legge
`periodo.da.value` e *chiede* il cambio. Un `v-model` su un ref che arriva in
una prop scrive in casa d'altri — funziona e nasconde chi possiede lo stato
(lo respinge `vue/no-mutating-props`).
#### ⛔ Un intervallo invertito non è un periodo

> **`da > a` non può esistere** (Tid, 2026-09-22). Non è una validazione di
> comodo: `da > a` descrive un insieme vuoto, e una lista che torna vuota per
> questo **non lo dice a nessuno** — l'operatore legge «non ci sono documenti»
> invece di «hai chiesto un intervallo che non esiste».

**Il meccanismo: l'estremo che tocchi vince, l'altro si apre.** Chi sposta `da`
oltre `a` sta dicendo dove comincia la finestra; il vecchio `a` non descrive più
niente, quindi **si svuota** — e un estremo vuoto è «aperto da quella parte»,
che è un periodo legittimo. Simmetrico nei due versi
(`feedback_normalize_guard_simmetrico`), e in **una sola fetch**.

| Strada | Perché no |
| --- | --- |
| `min-date`/`max-date` incrociati | trappola d'uso: legando un estremo all'altro, spostare la finestra *in avanti* diventa impossibile finché non tocchi prima l'altra data |
| scambiare i due estremi | inventa un periodo che nessuno ha chiesto, e in silenzio |
| rifiutare con un avviso | un filtro non è un form: blocca un gesto che ha una lettura ovvia |

⚠️ La correzione porta l'altro estremo a `null`, **mai al suo `clearTo`**: il
floor è la risposta al gesto «svuoto io», e qui il gesto è un altro — per
giunta un floor può essere a sua volta invertito rispetto alla data appena
scelta, e si tornerebbe al punto di partenza.
⚠️ **Il guard vive in `bindPeriodo`**: una coppia di date scritta a mano non
ce l'ha, ed è una delle ragioni per cui il quinto controllo di
`npm run guard:filtri` la respinge (registro a zero dal 2026-09-23).
Presidio: `useStoreFilterBindings.spec.js` (senza la correzione, i casi
dell'intervallo invertito vanno rossi).

#### Quanto si può stringere una combo con le descrizioni

> **Il minimo riguarda la lettura di ciò che è GIÀ scelto, non la scelta.**

È la domanda che sembra senza risposta («quanto stretta può stare una combo che
mostra descrizioni?») e ne ha una precisa, che sta nel comportamento di PrimeVue:

* il **pannello** delle opzioni riceve `min-width` = larghezza del trigger
  (`alignOverlay`), e le opzioni hanno `white-space: nowrap` ⇒ **il pannello
  cresce col contenuto**: un trigger stretto non taglia le descrizioni, e la
  scelta si legge per intero;
* il **valore selezionato** degrada in **ellissi** (`.p-select-label` ce l'ha
  nel tema) ⇒ stringere non rompe niente, rende solo meno riconoscibile ciò che
  è attivo.

⇒ Il pavimento è quindi una soglia di **riconoscibilità**, e si dichiara una
volta: `--app-filtro-unita: 8rem` ≈ 13 caratteri al font della toolbar — cioè
`31/12/2026` intero più l'icona, e per una combo il punto in cui
«Energia el…» si legge ancora e «Ene…» no.
✅ **Il testo intero sta nel `title`** (A4 del brief, 2026-09-24): PrimeVue non
lo fa da sé, e fino a quel giorno una selezione troncata non si rileggeva senza
riaprire il pannello. Lo fanno le due combo `md` dei filtri — `LookupSelect` e
`UtilityPerRuoloSelect` — con il BB `etichettaSelezionata`, come fa
`.app-lista-cella` per le celle: il `title` dice **ciò che si legge a video**
(anche `descrizione (codice)` con `show-code`), e senza selezione l'attributo
non c'è. ⚠️ Serve solo al desktop: su touch non c'è hover. ⛔ Le `Select` con
opzioni scritte in pagina (`sm`) non lo portano, e non per dimenticanza: le
loro etichette sono corte per costruzione, lo stesso criterio che le fa `sm`.

#### Come si verifica

```bash
cd frontend && npm run guard:filtri
```

**Sette** controlli, e due nature diverse: i file che scrivono i filtri a mano,
le larghezze inline e le **coppie di date scritte a mano** sono **cricchetti**
(rossi se crescono **e** se calano senza riscrivere il registro con
`--baseline`); «ogni `<FiltriLista>` ha `:store` o `:segno`», «dietro quel
`:store` c'è davvero il contratto» (2-bis), «la ricerca sta in `#sempre`» e
«`app-page-toolbar-start` non contiene filtri» sono **cancelli a zero**.

⭐ **Il 2-bis esiste perché il 2 non basta** (2026-09-23): quello guarda che
l'attributo sia *scritto*, non che dietro ci sia qualcosa — uno store a mano
senza `useContrattoFiltriLista` lo supera e lascia il segno spento identico. Il
componente lo grida in console, ma una console la guarda chi apre quella lista,
non la CI.
⚠️ **E il buco che resta è dichiarato**: quando il `:store` non si risolve a una
sorgente leggibile (lo store arriva come **prop**: `DrawerTabLista`,
`CodaFiltriToolbar`) il file finisce fra i «non verificabili»
e viene **stampato**. Un cancello che tace su ciò che non sa guardare fa credere
di averlo guardato.

⭐ **Il cancello guarda anche i tab-lista di drawer** (`<DrawerTabLista>`, che
gira i propri slot a `FiltriLista`): i nomi là sono `#filtri-sempre` e
`#filtri`, e senza questa riga le liste dentro un drawer — cioè le
più difficili da guardare a video — sarebbero fuori dal presidio.
⚠️ **E legge la sola sezione `<template>`**, perché le intestazioni di questi
componenti *nominano* i tag di cui parlano: leggendo il file intero, un
`<DrawerTabLista>` scritto in un commento diventava un tag senza attributi —
quindi «senza `:store`» — e la ricerca della chiusura inghiottiva mezzo file.
⭐ I due cancelli guardano proprio ciò che **da desktop non si vede**: là i due
slot si rendono uno accanto all'altro e il segno non serve a niente — il difetto
compare solo sotto i 1024px, dove nessuno sta guardando mentre scrive il codice.
Gira in CI dentro `npm run guards`.

#### La zona sinistra della toolbar che filtri NON porta — `app-page-toolbar-start`

Una toolbar di lista ha due zone: a sinistra i filtri, a destra le azioni.
Quando a sinistra non ci sono filtri — il **titolo** di una pagina, un pulsante
«torna alla lista» — la classe è `app-page-toolbar-start`, **non**
`app-page-filters`.

⛔ **Non è un alias di comodo, ed è presidiato**: `app-page-filters` significa
«gruppo filtri», e il registro di `npm run guard:filtri` la conta come debito da
portare in `<FiltriLista>`. Diversi blocchi la usavano per un `<h2>`; avvolgerli nel
building block avrebbe mandato il titolo della pagina dentro il drawer dal basso,
dietro un'icona a forma di imbuto. ⚠️ Il verso opposto è un **cancello a zero**:
un filtro messo in `app-page-toolbar-start` non scende nel drawer e non conta nel
segno, e **da desktop la resa è identica** — il controllo guarda il contenuto,
non il nome.

⭐ E una toolbar **senza** zona sinistra non ha bisogno di niente: le azioni
restano a destra per regola di foglio
(`.app-page-toolbar > .app-page-actions:first-child`). Fino al 2026-09-23 lo
faceva uno spaziatore scritto nel markup — `<div class="app-page-filters" />`
— cioè un gruppo filtri senza filtri: *la spaziatura è del foglio,
non del markup.*

#### Una lista dentro un drawer — gli slot di `DrawerTabLista`

Un tab-lista di drawer non scrive `<FiltriLista>`: lo monta il contenitore, e il
caller riempie **due** slot, che sono i due del building block.

```vue
<DrawerTabLista :store="store" codice="magazzino.ubicazioni" …>
  <template #filtri-sempre>              <!-- la ricerca: sempre a video -->
    <InputText v-model="searchText" class="app-filter-w-lg" … />
  </template>
  <template #filtri>                     <!-- gli altri: nel drawer in compatta -->
    <FiltroToggle v-model="mostraNonAttive" … />
  </template>
</DrawerTabLista>
```

⚠️ **`:store` serve anche qui**: è da lì che arriva il segno dei filtri attivi.
⛔ E i due slot si dichiarano **condizionati** (`<template v-if="…" #filtri>`),
non condizionando il widget dentro: uno slot che esiste e rende il vuoto accende
comunque l'icona a imbuto su un drawer senza niente dentro.

#### ⛔ Il valore che NON restringe si dichiara (`filtriNeutri`)

```js
filterDefaults: { solo_ultima_revisione: true, … },
// «mostra storico» scrive `false`, che DEVE viaggiare (il BE è `default=True`)
// ma è lo stato più largo possibile: non deve contare nel segno.
filtriNeutri: { solo_ultima_revisione: false },
```

Il segno conta un filtro quando **restringe**. Sapeva riconoscere un solo
«tutto» — l'assenza (`null`/`''`) — e per la maggior parte dei filtri basta.
Non per quelli il cui «tutto» è un valore **vero**:

| Filtro | Neutro | Perché non può essere `null` |
| --- | --- | --- |
| `solo_ultima_revisione` (offerte, preventivi) | `false` | il BE è `qp_bool(..., default=True)`: **assente significa `true`** |
| `ambito` (code di lavoro) | `'tutti'` | il parametro parte **solo** a «tutti»: sul filo il verso è rovesciato |
| `ampiezza` (task del lotto) | `'TUTTI'` | è una `ref`, non va sul filo (→ `neutro` in `useContrattoFiltriLocali`) |
| `archiviate` (code), `annullati` (lotti), `scartate` (righe distinta) | `true` | acceso **chiede in più**: il parametro parte e l'elenco diventa il più largo |

⛔ **Senza, il numero SALE quando l'operatore ALLARGA la lista.**

> ⭐ **La regola che li trova tutti, e va guardata prima del valore:**
> **un interruttore «mostra anche X» ha SEMPRE un valore neutro, ed è quello
> acceso.** Spento nasconde qualcosa — restringe, e conta a ragione; acceso apre
> l'elenco al massimo che quella lista sappia mostrare.
> ⚠️ Il dominio lo dichiara già: un interruttore che **allarga** porta il
> conteggio di ciò che nasconde (`archiviate_count`, `scartate_count`,
> `annullati_count`), uno che **restringe** («solo negativa», «solo interne»)
> non ha niente da contare. Se il `count` c'è, il neutro esiste.
> 🔴 Scritta il 2026-09-23 **dopo** che il primo censimento, fatto filtro per
> filtro, ne aveva mancati più della metà — uno nello store che stava
> modificando (brief §11.10).

⛔ **Non si deriva e non si indovina**: `archiviate: false` — l'interruttore
**spento** — nasconde le righe archiviate, quindi conta a ragione. È lo stesso
filtro del neutro qui sopra, guardato dall'altro verso: è conoscenza del
**filtro**, come `paramNames` e `gateKeys`.
⭐ **E se il neutro può essere `null`, si usa quello**: su `pratiche` il BE legge
«falso» e «assente» allo stesso modo, quindi il rimedio non è dichiarare il
neutro ma **smettere di mandare il parametro** (default `null`, `bindToggle`
senza `off`).
⛔ **Un interruttore non è un filtro se ACCENDE un altro filtro**: nel drawer BoM
«tutte le versioni» spegne `valido_al`, e dichiararlo come chiave a sé contava
**2** per una restrizione sola e **1** su un elenco intero. Lì la chiave è una,
e il legame vive nel `computed` scrivibile — come `data_da`/`data_a` sono un
periodo e non due date.
⚠️ **Niente cancello, ed è dichiarato**: un controllo statico non può sapere se
un valore restringe — boccerebbe `archiviate: false`. Il presidio è la spec di
`segnoFiltri` (i casi sui neutri) e la regola qui sopra, che si applica
leggendo il `count`.

#### ⛔ Un filtro che l'operatore non può togliere è un difetto

Se un filtro nasce valorizzato, ci dev'essere un gesto per riportarlo a «tutti»:
la terna dal BB **`buildAttivoOptions(t)`** (o `buildBoolOptions(t)`, che è la
stessa con `Sì`/`No`), `show-clear`, oppure — forma migliore per i booleani —
`bindToggle('attivo', { on: null, off: true })`, dove accendere «mostra non
attivi» porta il filtro a `null` e **lo fa smettere di contare**.
⛔ **La terna non si riscrive a mano**, ed è la lezione del 2026-09-23: era
copiata in **più** sedi e ne bastava una senza la voce «tutti» per avere un
filtro che non si spegne. Due di quelle copie scrivevano già nella tendina una
parola diversa da quella della loro stessa colonna.
⚠️ Senza, il segno conta un'unità su cui non c'è nessuna azione possibile.
Trovato il 2026-09-23 su `/catalogo/articoli` (nessun «Tutti») e, peggio, sulle
**conversioni UoM**, dove il filtro `attivo: true` non aveva **nessun widget**:
la lista era ristretta e non lo diceva a nessuno.
🟡 Restano per scelta i **floor data** con `clearTo` (contratti, code di
lavoro): non si tolgono, ma restringono davvero.

⭐ **E c'è una terza risposta, che non è un widget: non era un filtro.** Se il
valore non lo decide l'operatore ma il **dominio** — «la rata di una bozza non è
un credito» — allora non va in `filterDefaults` affatto: è un **perimetro**, e la
sua sede è il backend (api.md §«Un PERIMETRO non è un filtro»). ⛔ Tenerlo qui fa
due danni insieme: il segno conta un'unità su cui non c'è nessun gesto, **e** la
regola di dominio vale solo per il client che si ricorda di mandarla.
⇒ La domanda è una: *«se domani un altro client chiamasse lo stesso endpoint,
questa regola dovrebbe valere anche per lui?»* Se sì, non è un filtro.
Successo reale: `solo_numerate` del picker delle rate, spostato nel backend il
2026-09-23 (decisione di Tid).

#### Le larghezze dei filtri stanno in una classe, non nel tag

```vue
<DatePicker class="app-filter-w-sm" />   <!-- ✅ -->
<DatePicker style="width: 150px;" />     <!-- ⛔ -->
```

Tre taglie, dichiarate in `theme.css` come multipli dell'unità del filtro:
`app-filter-w-sm` (10rem: date, stati, codici brevi), `app-filter-w-md` (13rem:
combo con descrizioni), `app-filter-w-lg` (16rem: ricerca, lookup ricchi).
🔵 Valgono per la toolbar **in linea**; nel drawer la larghezza la decide la
griglia (§sotto). ✅ Al 2026-09-23 **nessun tag porta più un numero**, e
`npm run guard:filtri` tiene il registro a zero — in `px` come in `rem`, e
anche sull'`input-style` di un `InputNumber`: l'unità non cambia il difetto, e
un criterio che ne guarda una sola è cieco sull'altra.

**Come si sceglie la taglia** (§A1 del brief, decisa convertendo tutte le
liste): `lg` alla **ricerca** e ai **lookup ricchi** (articolo, billing account,
comune); `md` alle **combo con descrizioni** che vengono da un catalogo
(`LookupSelect` su un `rel`, `UtilityPerRuoloSelect`); `sm` alle **date**, agli
**stati** e alle liste di opzioni **scritte in pagina** (`attivo`, `sì/no`,
`super admin`), che portano etichette corte.

Una larghezza scritta nel tag **vince su qualunque foglio di stile**: nel drawer
dal basso, dove ogni filtro deve occupare la riga intera, resta quella. Non dà
nessun errore — si vede solo guardando il telefono.
⭐ Vale anche su desktop: al 2026-09-22 i filtri portavano larghezze inline con
decine di valori distinti (150px, 160px, 120px, 200px, 220px, 260px…), cioè lo
stesso filtro largo in modo diverso da una schermata all'altra.
Non era una scelta: era una sedimentazione — e con le tre taglie è finita.

⭐ **Un involucro non spegne le regole del drawer** (corretto il 2026-09-23): le
regole della griglia — la taglia che si annulla, l'interruttore e il periodo che
prendono la riga intera — parlano del **filtro**, non della forma del markup che
lo avvolge. Erano scritte come figli **diretti** (`>`), quindi un filtro dentro
un `<div class="form-field">` con la sua etichetta — markup legittimo, e nel
repo ce n'è — le perdeva in silenzio: la taglia sopravviveva dentro la cella e
l'interruttore restava a mezza riga. Ora sono descendant + `:has()`.
⚠️ Si vedeva **solo sotto i 1024px**.

### Ritiro dinamico colonne — `useResponsiveColumns` (responsive, ResizeObserver)

Le liste configurabili (`<ListaConfigurabile>`) **ritirano dinamicamente** le
colonne meno prioritarie in una riga di espansione quando lo spazio non basta
(tipicamente all'**apertura della sidebar**), invece di attivare la scrollbar
orizzontale. È attivo di default (`prop responsive`, default `true`): tutte le
liste configurabili ne beneficiano (omogeneità UI). Building block:
`src/core/composables/useResponsiveColumns.js`.

**Come funziona (packing a somma):** ogni colonna contribuisce con la sua
`larghezza_default` (catalogo); quando la somma supera la larghezza reale del
contenitore si ritira la colonna a `priorita` più bassa (catalogo
`ui.lista_colonna.priorita`, esposta da `fn_resolve_lista_config`; tiebreaker
`ordine_default` = la più a destra per prima), finché la somma rientra. Le
colonne `tipo_colonna IN ('identificatore','azione')` e quelle `fissata` non si
ritirano mai. Le ritirate finiscono nell'expansion row riusando gli slot
`cell-{codice}` del caller (zero dati persi, resa identica). Niente
`larghezza_min`: la soglia riusa `larghezza_default`. Le liste responsive sono
**escluse dalle soglie min-width 8/10/12 colonne** (`.app-datatable--responsive`
in `main.css`): il packing garantisce già che le colonne entrino.

#### ⛔ La larghezza di catalogo è un TETTO, non un minimo (2026-09-18)

> **Regola**: su una lista responsive **non compare mai una scrollbar
> orizzontale**, e la colonna azioni è **sempre l'ultima a video**. Le colonne
> che non entrano stanno nella riga di espansione, e «Espandi tutte» le apre
> tutte insieme. (Decisione di Tid, rilievo in-app sui preventivi.)

🔴 **Il difetto che questa regola chiude era controintuitivo**: la scrollbar
compariva a sidebar **chiusa**, non aperta. Il packing somma le larghezze
**dichiarate**, ma la tabella è `width: max-content` — ogni colonna era larga
quanto il suo contenuto più lungo, e la larghezza di catalogo era solo un
**minimo**. A sidebar aperta il ritiro compensava per caso; con più spazio il
packing diceva «entra tutto» sui numeri dichiarati, il browser rendeva quelli
veri, e la differenza usciva come scrollbar. *Il packing faceva una promessa che
il rendering non manteneva.*

**Come si chiude**: `<ListaConfigurabile>` passa la larghezza anche come
**tetto** della cella e dell'intestazione (`--col-w` + `.app-lista-cella`,
`main.css` §liste responsive). Un contenuto più lungo va in **ellissi** su una
riga, col testo intero nel `title`. Così la somma resa **è** quella dichiarata:
la scrollbar non può comparire, e la colonna azioni — alla sua larghezza
naturale, mai tagliata — resta l'ultima.

⭐ **Ne discende che una larghezza di catalogo troppo stretta si VEDE** (una
colonna piena di «…») invece di produrre una scrollbar muta: si corregge
dall'amministrazione, è un dato di `ui.lista_colonna`, non un intervento sul
codice.

⚠️ **L'unica larghezza che il catalogo non conosce è quella dei pulsanti inline
della colonna azioni**, e la dichiara il chiamante: prop `azioni-inline`
(default 4). Fino a quel giorno era una costante — 130px, «~3-4 pulsanti» —
che copriva **tre** pulsanti (2rem + 0.25rem di gap): diverse liste ne hanno
di più, e la differenza usciva dal
contenitore senza che il packing lo sapesse. Un numero più basso del vero non
taglia niente, ma riporta la scrollbar: chi aggiunge una quinta azione di riga
alza la prop.

⚠️ Nello stesso giro sono entrate nel conto le colonne di **chrome** che il
packing ignorava: la checkbox di selezione e l'expander sempre presente delle
liste con dettaglio inline (48px l'una).

Presidio: `useResponsiveColumns.spec.js`.

> **⚠️ DEROGA DOCUMENTATA allo standard "responsive CSS-first, niente JS di
> detection".** Le media query CSS reagiscono solo a `window.innerWidth`, ma
> l'apertura della sidebar **non cambia la larghezza della finestra** — restringe
> solo l'area contenuto. Le media query sono **cieche** a questo evento, e la
> scrollbar appare proprio lì. L'unico modo per reagire alla larghezza **reale
> del contenitore** (che cambia sia col viewport sia con la sidebar) è osservarla
> con un `ResizeObserver`. **Non è una scelta di comodo**: l'alternativa
> puramente-CSS per questo caso non esiste. La deroga è circoscritta a questo
> building block; non legittima JS-detection altrove.

### Colonna azioni di riga — `RowActionsMenu` (responsive)

Le azioni secondarie su una riga (apri sub-drawer, disattiva, clona, ecc.) vanno
sempre renderizzate tramite il building block **`RowActionsMenu`**
(`src/core/components/RowActionsMenu.vue`). La modifica del record NON va tra le azioni:
e' gestita dal click sulla riga del DataTable.

**Comportamento responsive (CSS-first, nessun JS di detection):**

| Contesto | Variante | Dettaglio |
| --- | --- | --- |
| Desktop `hover` + viewport `>=1024px` | Inline | Pulsanti icon-only con tooltip, un click = una azione |
| Tablet / touch / viewport `<1024px` | Compact | Kebab `⋮` che apre un menu popup con label esplicite |

Lo switch e' realizzato da `@media (hover: none), (max-width: 1023.98px)` in `main.css`
sulle classi `.app-row-actions-inline` / `.app-row-actions-compact`. Il componente
renderizza entrambe le varianti, il CSS ne mostra una sola. Il breakpoint `hover: none`
intercetta esplicitamente i dispositivi touch (es. iPad Pro) indipendentemente dalla
larghezza del viewport.

**Perche':** su touch i tooltip non funzionano; con 3-4 azioni inline la colonna
ruba larghezza; sul desktop c'e' spazio e il mouse hover — l'inline resta piu' veloce.
La soluzione responsive combina il meglio di entrambe senza compromessi.

**Pattern di uso nella SearchTable:**

```vue
<script setup>
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { MANAGE_ICONS } from '../../core/constants'

// Costruttore azioni contestualizzato alla riga (dati, stato, permessi).
function buildRowActions(data) {
  return [
    {
      key: 'gestisci-righe',
      label: t('dominio.gestisci_righe'),
      icon: MANAGE_ICONS.RIGHE,
      command: () => emit('open-righe', data),
    },
    {
      key: 'disattiva',
      label: t('common.disattiva'),
      icon: 'pi pi-ban',
      severity: 'danger',
      visible: data.attivo === true,
      command: () => onDisattiva(data),
    },
  ]
}
</script>

<template>
  <ListaConfigurabile codice="dominio.entita" …>
    <template #actions="{ data }">
      <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
    </template>
  </ListaConfigurabile>
</template>
```

⭐ **Il kebab sotto spazio stretto arriva da sé** (2026-09-29): quando il
packing responsive della lista ritira la colonna azioni a kebab ne conta la
larghezza compatta (56px), e la cella azioni di `ListaConfigurabile`
(`CellaAzioniRiga`, BB `useAzioniRigaCompatte`) consegna quella decisione a
`RowActionsMenu` via provide/inject. Fino a quel giorno il caller doveva girare
lo scope `compact` a `:force-compact`: quattordici liste non lo facevano — anche
l'esempio qui sopra lo ometteva nel commento del BB — e su desktop rendevano i
pulsanti inline, più larghi del conto; la differenza usciva come **scrollbar
orizzontale**, senza errori (righe della distinta contabile). Lo scope
`compact` resta, per chi nella cella rende altro; `:force-compact` passato a
mano vince sempre. ⛔ **Dentro la cella azioni non si scrive
`:force-compact="compact"`**: le 40 copie che lo facevano sono state ritirate
nello stesso giro (regola del 2) — ripeterlo è una seconda sede della stessa
decisione. ⚠️ Fuori da una `ListaConfigurabile` (DataTable grezza,
tabelle di dashboard) non c'è provider: lì, se serve, `:force-compact` si passa
esplicito.

Nelle sole eccezioni con `DataTable` grezza (§«Regola zero della lista») la
stessa chiamata sta dentro
`<Column :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">`.

**Formato azione:**

```js
{
  key: string,              // identificatore univoco
  label: string,            // testo (tradotto, visibile nel popup + tooltip inline)
  icon: string,             // classe PrimeIcons (es. 'pi pi-ban' o MANAGE_ICONS.X)
  severity?: 'primary' | 'warn' | 'danger', // opzionale (vedi tabella sotto)
  visible?: boolean,        // default true — azioni non applicabili si nascondono
  disabled?: boolean,       // default false — azione grigia ma presente
  allowWhenInactive?: boolean, // default false — escape per azioni ammesse su record inattivi
  action?: string,          // codename permesso processo (auth.isActionAllowed) — senza, la voce NON si renderizza
  command: () => void,      // handler click
}
```

⚠️ **`action` è lo stesso campo di `PageActionsBar`/`DrawerActionsBar`**, con lo
stesso effetto: **nasconde**. Fino al 2026-08-17 `RowActionsMenu` lo **ignorava**
— chi lo passava credeva di aver messo un cancello che non esisteva, e le azioni
di governo del lotto («Riporta in lavorazione», «Annulla», «Numera») comparivano
nel kebab della lista anche a chi non aveva il permesso (rilievo in-app di Tid).
Un campo dichiarato e non letto è peggio della sua assenza: sembra presidiato.
Il gate vero resta il backend; questo è il non-proporre.

**Permesso ⇒ nascondi, stato ⇒ disabilita col motivo.** Il permesso non è
qualcosa che l'operatore possa risolvere dal kebab, quindi una voce grigia
sarebbe una promessa che non si mantiene; ciò che invece dipende dallo stato del
record può cambiare, e lì `disabled` + `tooltip` spiega e resta a video.

> ⭐ **E la regola vale prima di tutto per il DATABASE**, che è chi decide se
> un'azione è proposta, spenta o assente: sono le `script.fn_available_actions_*`
> a emettere `enabled` / `reason` / `reason_key`, e il frontend le rende.
> La stessa regola è scritta per chi lavora in SQL in
> [linee-guida-sql §12](/linee-guida-sql). ⚠️ Le due copie vanno tenute
> allineate: il 2026-08-20 una decisione DB è stata presa ignorando questa
> pagina, perché chi scrive SQL non la legge.
>
> ⭐ **E per le azioni PER RIGA il motivo lo deve dare il database lo stesso**
> (`linee-guida-sql §12.5`, dal 2026-08-26). Le capability stanno sul dettaglio,
> quindi una riga non le ha: il motivo arriva come **colonna della vista di
> riga**, prodotta da una `script.fn_check_*` che la **madre chiama** per
> rifiutare — così il tooltip e l'errore non possono dire due cose diverse.
> ⛔ **Non ricalcolare la regola qui**: fra «riscriverla nel frontend» e «non
> dirla affatto» la terza strada è chiederla al DB. È il difetto trovato in app
> sul pulsante «Annulla l'accredito», acceso su un annullo che sarebbe stato
> rifiutato dopo aver fatto scrivere all'operatore un motivo obbligatorio.

⛔ **E il campo si chiama `tooltip`, non `motivo`.** `RowActionsMenu` legge
`action.tooltip` e da lì ricava **da solo** il tooltip inline e la riga sotto la
voce nel kebab (`actionMotivo`). Un `motivo:` sull'azione non lo legge nessuno:
misurato il 2026-08-26, il motivo di un pulsante spento **non era mai stato
reso** — ed è anche il motivo per cui la chiave i18n mancante non si era mai
vista a video, perché l'etichetta non veniva proprio chiesta. È la terza
occorrenza della stessa specie in questa pagina, insieme allo slot delle azioni
col nome sbagliato e al campo `action` ignorato fino al 2026-08-17.

**Regola record inattivo (`attivo=false` / `is_active=false`):**

- Se la lista ha una colonna stato standard (`attivo` o `is_active`), passare sempre
  la riga al componente: `<RowActionsMenu :row="data" :actions="buildRowActions(data)" />`.
- `RowActionsMenu` disabilita automaticamente le azioni operative su record inattivi,
  sommando questa regola a eventuali `disabled` gia' presenti per permessi/capability.
- Il click riga resta abilitato: la modifica/consultazione del record continua ad aprire
  il drawer, dove possono vivere azioni come riattiva o consultazione.
- Le azioni esplicitamente ammesse su record inattivi devono dichiarare
  `allowWhenInactive: true` (es. `riattiva`, `visualizza storico`, `modifica`
  quando la matita e' l'entrypoint standard del form nella lista/drawer).
- Il tooltip standard per il blocco e' `common.azione_non_disponibile_record_inattivo`.

**Severity — colore inline e popup:**

Il popup del kebab segue la stessa palette dell'inline. La classe `.app-menu-item-*`
viene applicata via helper centralizzato `menuItemClass(severity, fallback)` in
`src/core/utils/rowActions.js`: i consumer (`RowActionsMenu`, `PageActionsBar`,
`DrawerActionsBar`) passano il proprio fallback (manage o action) e la severity
dell'azione, l'helper restituisce la classe corretta.

| Severity | Inline (desktop) | Popup (tablet/touch) | Uso tipico |
| --- | --- | --- | --- |
| `undefined` | Blu (`app-manage-btn`) | Blu (`app-menu-item-manage`) | Default: apri sub-drawer, clona, gestisci |
| `'primary'` | Blu (`app-action-btn`) | Blu (`app-menu-item-action`) | State transition positiva (attiva, approva) |
| `'warn'` | Arancio (PrimeVue `severity="warn"`) | Arancio (`app-menu-item-warn`) | Cautela (chiudi, blocca, scade) |
| `'danger'` | Rosso (`app-delete-btn`) | Rosso (`app-menu-item-danger`) | Distruttivo (elimina, disattiva) |
| `'info'` | Blu (`app-manage-btn`) | Blu (`app-menu-item-manage`) | Sinonimo di default |
| `'success'` | Blu | Blu (`app-menu-item-action`) | Sinonimo di primary |

ℹ️ `app-action-btn` e `app-menu-item-action` hanno classi proprie ma **lo stesso
colore** di `app-manage-btn`: blu dal 2026-08-27 (decisione di Tid), sede unica
`--app-btn-action-*` in `theme.css`.

Le voci `:disabled` ricadono sul colore muted PrimeVue (`--app-btn-disabled-color`)
sovrascrivendo la severity — evita di mostrare "vivace" un'azione non cliccabile.

**Convenzioni centralizzate (niente valori hardcoded nelle liste):**

| Cosa | Dove |
| --- | --- |
| Icona kebab | `MANAGE_ICONS.KEBAB` in `src/core/constants.js` |
| Icona elimina | `MANAGE_ICONS.DELETE` in `src/core/constants.js` |
| Stile bottone standard | `.app-manage-btn` in `main.css` |
| Stile bottone distruttivo | `.app-delete-btn` in `main.css` |
| Larghezza colonna (auto / 60px) | `.app-col-actions` in `main.css` (media query) |
| Voci menu popup | `.app-menu-item-{manage,action,warn,danger}` in `main.css` |
| Helper severity → classe | `menuItemClass(severity, fallback)` in `src/core/utils/rowActions.js` |
| Tooltip fallback kebab | `common.altre_azioni` ("Altre azioni") in `it.json` |
| Tooltip record inattivo | `common.azione_non_disponibile_record_inattivo` in `it.json` |
| Header colonna azioni | `common.col_azioni` ("Azioni") in `it.json` — sempre questa chiave, mai domain-specific |

**Regole fisse:**

- La modifica record NON e' mai un'azione del menu: si apre via click riga.
- Ogni azione deve avere `label` tradotta (i18n) — l'inline la mostra come tooltip,
  il popup come voce.
- Usare `visible: false` (non `disabled`) per azioni non applicabili — il popup
  resta corto, la UX piu' leggibile.
- `severity: 'danger'` per azioni irreversibili (elimina, disattiva), mai inline
  `class="..."`.
- La colonna va sempre `class="app-col-actions"` + `:exportable="false"`.

### Empty state — liste che partono vuote (standard)

Le liste che possono selezionare troppi dati partono **vuote** e mostrano un placeholder
finche' l'utente non applica una ricerca (min 3 caratteri) o un filtro.

**Componenti coinvolti:**

| Elemento | Dove |
| --- | --- |
| `SearchHint.vue` | `core/components/` — placeholder riutilizzabile (icona search + messaggio) |
| `hasSearched` | Nello store Pinia — `ref(false)`, diventa `true` dopo il primo fetch |
| Guardia in `fetchList()` | Nello store — blocca la chiamata API se non ci sono filtri attivi |

**1. Store — la guardia la porta il building block, non si riscrive.**

⛔ **Uno store-lista NON si scrive a mano** (dal 2026-09-18): filtri nella forma
di `useSearchTable`, fetch paginata, guardia empty-state, `hasSearched`,
`fetchSospesa`, anti-race e `buildParams` (search ≥3, filtri non-null, pagina,
ordinamento) vivono in **`useListaStoreCore`** — via `createCrudStore` (lista +
CRUD), `createListaStore` (sola lista, anche col padre nel path) o chiamato
direttamente dentro il `defineStore` quando lo store è quasi tutto dominio.
Fino a quel giorno molti store tenevano la propria copia del blocco qui
sotto, ognuna con la sua piccola differenza (un `'ASC'` maiuscolo, un ripiego
diverso, una ricerca a qualunque lunghezza): la casa di quelle differenze sono
le opzioni del core (`ricercaCorta`, `orderDirDefault`, `paramNames`), non un
`fetchList` riscritto. Le liste che partono vuote dichiarano `gateKeys`.

Il blocco che segue è **la regola che il BB applica**, lasciato qui perché si
legga cosa fa — non un modello da copiare in uno store.

⛔ **La soglia della ricerca non si scrive sul posto** (dal 2026-09-24, regola del
2): il termine si manda con **`paramsRicerca(f)`** e il «sto ancora digitando»
si chiede a **`termineCorto(termine)`**, entrambi in `core/utils/listParams.js`,
con la **soglia della lista**. Prima lo stesso `trim` + `>= 3` stava copiato in più store.

⭐ **La soglia è un fatto della lista** (dal 2026-09-26,
[brief-db-be-fe-ricerca-soglia-per-lista](../work-done/brief-db-be-fe-ricerca-soglia-per-lista.md)):
arriva nella configurazione (`ricerca_min_caratteri`, la stessa colonna con cui
il backend decide se filtrare), `onConfigLoaded` la scrive in
`store.ricercaMinCaratteri` (dichiarata da `useListaEmptyStateFetch`), e il BB
la passa a `buildParams` come terzo argomento. Uno store scritto a mano la gira
a `paramsRicerca`:

```js
function buildParams(f, _termine, ricerca) {
  const p = paramsFinestra(f)                   // limit/offset + ordinamento
  Object.assign(p, paramsRicerca(f, ricerca))  // soglia della lista
  // ... filtri di dominio ...
  return p
}
```

⛔ Nessun numero nel codice della lista: `RICERCA.MIN_CARATTERI` è il ripiego
finché la configurazione non è arrivata (`null`).

⭐ **Un tasto che non cambia la richiesta non ricarica** (dal 2026-09-26). Il
watcher della casella chiede allo store `ricercaCambiaLaRichiesta(termine)`
(BB `useListaEmptyStateFetch`): se il `search` che partirebbe è quello
dell'ultima richiesta partita — termine sotto soglia, o uguale dopo il `trim` —
lo store si allinea e basta, senza fetch e senza tornare a pagina 1. Senza,
sulle liste col filtro data di default (preventivi, offerte, ordini) «a» e «ab»
ricaricavano la stessa lista senza `search`.

⛔ **Uno store scritto a mano sul BB ne espone lo stato INTERO** (dal 2026-09-26,
regola del 2): `const lista = useListaEmptyStateFetch({...})`, si destruttura
solo ciò che lo store usa dentro, e il `return` comincia con `...lista`. Prima
ogni store elencava a mano i ref del BB, e a ogni ref nuovo (`ricercaFull`,
`ricercaMinCaratteri`, `ricercaCambiaLaRichiesta`) andavano ricopiati in tutti:
metà non erano allineati, e a quelli la lista ricaricava a ogni tasto
senza errore. Presidio: `npm run guard:lista-stato`.

```js
const hasSearched = ref(false)

async function fetchList() {
  const f = filters.value
  const searchTerm = termineRicerca(f)
  const hasFilters = f.filtro_1 != null || f.filtro_2 != null // adattare ai filtri reali

  // Search sotto la soglia della lista e nessun filtro attivo → ignora
  const ricerca = { minCaratteri: ricercaMinCaratteri.value }
  if (termineCorto(searchTerm, ricerca) && !hasFilters) return
  // Primo caricamento senza filtri → resta vuoto
  if (!searchTerm && !hasFilters && !hasSearched.value) return
  // Search svuotata senza filtri → torna a stato vuoto
  if (!searchTerm && !hasFilters) {
    items.value = []
    totalRecords.value = 0
    hasSearched.value = false
    return
  }

  loading.value = true
  try {
    const params = { ...paramsRicerca(f, ricerca) }
    // ... costruzione params ...
    const res = await listEntita(params)
    items.value = res.data.data.results
    totalRecords.value = res.data.data.count
    hasSearched.value = true
  } finally {
    loading.value = false
  }
}

// In uno store sul BB: `return { ...lista, filters, ... }` (vedi sopra)
return { items, totalRecords, loading, hasSearched, filters, fetchList, ... }
```

**2. SearchTable — placeholder + fetch condizionale** (modello reale:
`anagrafiche/components/FornitoriSearchTable.vue`):

```vue
<script setup>
import { onMounted } from 'vue'
import SearchHint from '../../core/components/SearchHint.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'

const {
  searchText, listaRef, paginatorProps, tablePage, onPage, onSort, onConfigLoaded,
  mostraLista, mostraSearchHint, ...
} = useListaConfigurabilePage(store, { ... })

useTabFreshness(store, TAB_ENTITIES.ENTITA)
// La lista parte vuota — salvo che arrivi con search precaricata da URL/context.
onMounted(() => {
  if (searchText.value) {
    store.fetchList()
  }
})
</script>

<template>
  <!-- Placeholder: nessuna ricerca effettuata -->
  <SearchHint v-if="mostraSearchHint" />

  <ListaConfigurabile ref="listaRef" v-show="mostraLista" codice="dominio.entita" …
    @config-loaded="onConfigLoaded" />
</template>
```

`mostraSearchHint`/`mostraLista` li calcola lo scaffolding a partire da
`store.hasSearched` e `store.loading`: la view non riscrive la condizione.

**Regole:**

- **NON usare** `onMounted(() => store.fetchList())` incondizionato — caricerebbe tutti i dati
- Il `onMounted` condizionale (`if searchText.value`) serve per la **ricerca universale e AI**:
  quando l'utente arriva da SearchDrawer, AI Assistant o link con `?search=...`,
  il termine e' gia' in `searchText` e la lista deve mostrare i risultati immediatamente
- `SearchHint` accetta prop `message` opzionale per messaggi personalizzati;
  default: `$t('common.eseguire_ricerca')`
- La chiave i18n `common.eseguire_ricerca` e' condivisa da tutte le liste

### Filtro data standard (obbligatorio su liste con date)

Ogni SearchTable che mostra dati con data di apertura/creazione deve avere il filtro data:

- **Un periodo** "Dal" (`data_da`) – "Al" (`data_a`) nella toolbar filtri,
  montato con `<FiltroPeriodo>` (§«Il periodo è UN filtro»), mai con due
  `<DatePicker>` scritti a mano
- **Default `data_da` solo frontend**: **oggi - 60 giorni, riportato al primo
  giorno del mese risultante** (es. oggi `15-08-2026` -> `01-06-2026`).
  Il calcolo NON si riscrive nello store: si chiama
  `defaultFiltroDataDaString()` da `core/utils/date`
- **`data_a`**: null (nessun limite superiore di default)
- Il filtro si applica su `data_insert` (o colonna data apertura dedicata se esiste)
- Backend: su una colonna istante applica il BB `predicato_giorno_operativo` (giorni dell'**azienda**,
  `data_a` incluso; dal 2026-10-09, catalogo BB backend) **solo se i parametri arrivano dalla
  request**; non deve applicare default temporali impliciti
- «Oggi» è quello dell'**azienda** (`oggiAziendale`, `core/utils/date`), non del PC: anche il
  default di `data_da` parte da lì
- Il tiebreaker `id` nell'ORDER BY garantisce paginazione deterministica

Il default temporale e' una scelta UX, non una regola backend. Va impostato nello
store/componente solo quando il filtro e' visibile nella toolbar (`<FiltroPeriodo>`):
l'operatore deve poter vedere, modificare o cancellare il valore che limita la lista.
Se una lista non espone il periodo `data_da`/`data_a`, non deve inviare `data_da`
di default e il backend non deve inventarlo.

**Perche' allineato al primo del mese** e non "oggi - 60 giorni" secco: cosi' il
default e' **stabile dentro il mese** — non scorre di un giorno ogni giorno,
quindi l'operatore non vede la lista cambiare da sola — e il mese piu' vecchio
del periodo si vede sempre per intero, che e' come si legge un archivio
operativo.

> **Storico**: fino al 2026-08-01 il default era il 1° gennaio dell'anno-1. Era
> troppo largo: su liste popolate significava scorrere fino a due anni di
> documenti per arrivare a quelli di ieri. La formula viveva **copiata a mano in
> più punti**; ora e' una funzione sola.

**Implementazione nello store** — si importa, non si ricalcola:

```js
import { defaultFiltroDataDaString } from '../../core/utils/date'

const filters = ref({
  // ... altri filtri ...
  data_da: defaultFiltroDataDaString(),
  data_a: null,
})
```

Se serve una `Date` invece della stringa (es. il `clearTo` di
`useStoreFilterBindings`, o un filtro tenuto in `reactive` come nelle code di
lavoro), la variante e' `defaultFiltroDataDa()`. Le due condividono la formula:
cambiare i 60 giorni e' una riga in `core/utils/date`
(`LISTE_FILTRO_DATA_GIORNI`).

**Implementazione nella SearchTable** — ⛔ **non due `<DatePicker>`**: il
periodo è UN filtro con due estremi, e si monta col suo building block (§«Il
periodo è UN filtro»).

```vue
<script setup>
const { bindPeriodo } = useStoreFilterBindings(store, applyFilters)
const periodo = bindPeriodo()                    // 'data_da' / 'data_a'
</script>

<FiltroPeriodo :periodo="periodo" />
```

⚠️ **Fino al 2026-09-23 questo paragrafo mostrava esattamente la forma
sbagliata** — due `DatePicker` con `@date-select` + `@clear-click` e
`style="width: 150px"` — cioè le istruzioni per riprodurre due difetti muti: una
data **digitata** che non applica il filtro, e una larghezza nel tag che vince
sul drawer. È la stessa lezione della «regola zero della lista»: *chi legge in
buona fede trova le istruzioni per fare la cosa sbagliata.*

Le chiavi i18n `common.data_da` ("Dal") e `common.data_a` ("Al") sono condivise da tutte le liste.

### Interruttore di filtro — `FiltroToggle` + `bindToggle`

Un filtro acceso/spento nella toolbar di una lista («Mostra storico», «Solo
interne», «Solo negativa», «Mostra annullati») è il BB `FiltroToggle`:
`[switch] Etichetta`. ⛔ Non un `ToggleSwitch` + `<label>` scritti in pagina:
il 2026-09-18 erano più copie, con lo stile inline
ricopiato e un id inventato a mano per non collidere fra due schede — il root
del BB è un `<label>`, e non ha bisogno di nessun id.

Il **legame con lo store** non si scrive nel componente:
`useStoreFilterBindings.bindToggle(storeKey, { on, off })`. Quelle stesse
copie avevano **tre** forme del legame (un `ref` + handler, un `computed`
invertito, un `computed` che scrive `true | null`): `on`/`off` sono i due
valori che lo store porta, e coprono tutte e tre.

- ⚠️ `off` è **`null`** di default, non `false`: il core manda ogni filtro
  `!= null`, e un `false` sul filo sarebbe un parametro che il backend legge
  senza che filtri niente. Chi ha `false` come default dello store lo dichiara;
- il filtro **invertito** («mostra storico» acceso ⇔ `solo_ultima_revisione =
  false`) si scrive `bindToggle('solo_ultima_revisione', { on: false, off: true })`,
  non con un `computed` a mano;
- il cambio ricarica **da pagina 1** (`applyFilters`): la pagina 3
  dell'insieme piccolo può non esistere in quello grande, e viceversa.

**Quando l'interruttore ALLARGA la lista** — rimette dentro elementi che
**esistono** e che di default restano fuori (righe archiviate, lotti
annullati) — porta anche il **numero**: `[switch] Mostra annullati (3)`, prop
`count`. Il numero lo **dichiara il backend** (`archiviate_count`,
`annullati_count`): spento e senza numero, «elenco pulito» e «tre righe messe
via» si leggono uguali — è la stessa regola di `ritirate_count` sul giornale.
La forma è `Etichetta (N)` (decisione di Tid, 2026-09-12), non una frase
plurale: la chiave i18n è una. Un interruttore che **restringe** non ha niente
da contare e non passa `count`.

> Fino al 2026-09-18 il BB si chiamava `ToggleNascoste` e copriva il solo
> caso col conteggio: le copie senza conteggio erano lo stesso
> componente, e si è ritirato nel giro che le ha assorbite.

Esempio di consumatore: `LottiListView` (col conteggio). Dettaglio nel
[catalogo](catalogo-building-block-frontend.md).

### Filtro con lookup ricco — `bindLookup`

Quando il filtro è un lookup **ricco** (`ArticoloLookup`,
`BillingAccountLookup`…) il widget tiene l'**oggetto** scelto e lo store
l'**id**: il legame è `useStoreFilterBindings.bindLookup(storeKey, { idField })`,
con `onChange` su `@update:model-value` (i lookup ricchi lo emettono su select
**e** su clear). ⛔ Non un `watch` sul widget con un guard anti-giro-a-vuoto:
erano due copie identiche (registro e disponibilità di magazzino, 2026-09-18).
⭐ L'oggetto scelto **si ricorda nello store** (`<storeKey>_obj`, come il
`_obj` del form per il restore dell'AutoComplete): un widget che rimonta —
la scheda di un `<Tabs lazy>` — lo ritrova, invece di mostrare un picker
vuoto sopra una lista filtrata. ⚠️ Un id messo da fuori **senza** l'oggetto
(deep-link col solo id) non si rende: da colmare con un'opzione `risolvi`
il giorno che un deep-link lo chiederà.

### Scorciatoie da tastiera (Keyboard Shortcuts)

Scorciatoie globali per operatori ERP power user. Due meccanismi:

**1. `useKeyboardShortcuts(shortcuts)` — composable generico**

Per shortcut che NON devono attivarsi dentro input/textarea/select (evita conflitti con la digitazione).

```js
import { useKeyboardShortcuts } from '../composables/useKeyboardShortcuts'
import { SHORTCUTS } from '../constants'
useKeyboardShortcuts([
  { ...SHORTCUTS.SEARCH, action: () => ui.openSearchDrawer() },
])
```

Le combinazioni si dichiarano in `SHORTCUTS` (`core/constants.js`), non nel
chiamante. Usato da: `AppLayout` (ricerca universale, schede, sidebar, home,
split, assistente AI).

**2. `useScorciatoie` — le scorciatoie di un'AZIONE (dal 2026-10-04)**

Per le scorciatoie legate a un pulsante (Salva, i tasti F delle liste), attive
anche dentro un campo. ⛔ **Mai un listener su `window` nel componente**: uno
per componente si somma agli altri — il vecchio F5 ricaricava tutte le liste
visitate (sotto KeepAlive non si smontano), il vecchio Ctrl+S salvava tutti i
form montati. La sede è una, con un listener solo: il tasto va all'**unico**
iscritto a video al livello davanti (dialog in cima, drawer in cima, pagina).
Il componente si iscrive con le sue azioni; il tasto si lega alla **chiave**
dell'azione (`SCORCIATOIE`):

```js
const radice = ref(null)
useScorciatoie({
  elemento: () => radice.value,
  azioni: () => (showSave.value ? [{ key: 'salva' }] : []),
  spenta: () => props.disabled || props.loading,
  esegui: () => emit('save'),
})
```

Iscritti oggi: `PageActionsBar`, `FiltriLista`, `FormFooter`. Il tooltip dice
il tasto con `conTastoDiAzione`.

**Shortcut attive:**

| Shortcut | Contesto | Azione | Componente |
|----------|----------|--------|------------|
| `F2` · `F4` · `F5` · `F6` · `F8` · `F9` | La lista a video, al livello davanti (pagina, o drawer in cima) | Pulisci filtri · Scarica lista · Ricarica · Nuovo · Espandi/Comprimi tutte · Personalizza colonne — l'azione con quella chiave nella `PageActionsBar` (F2: in `FiltriLista`) | `useScorciatoie` |
| `Ctrl+S` (⌘S) | Il form a video al livello davanti (dialog in cima, o drawer in cima) | Salva — rispetta disabled/loading/readonly | `FormFooter` → `useScorciatoie` |
| `Esc` | Il drawer in cima | Chiude quel drawer, con la sua conferma (`useDrawerInCima`) | `AppDrawer` |
| `Ctrl+K` | Globale (fuori dai campi di input) | Apre ricerca universale | `AppLayout` (`SHORTCUTS.SEARCH`) |
| `Ctrl+W` / `Ctrl+Tab` / `Ctrl+Shift+Tab` | Globale (fuori dai campi di input) | Chiude / scheda successiva / precedente | `AppLayout` |
| `Ctrl+B`, `Ctrl+Home`, `Ctrl+.` … | Globale (fuori dai campi di input) | Sidebar, home, assistente AI — elenco completo in `SHORTCUTS` | `AppLayout` |

**Regole:**
- `useKeyboardShortcuts` per shortcut che NON devono interferire con la digitazione
- `useScorciatoie` per le scorciatoie di un'azione, attive anche dentro un
  campo (Ctrl+S, i tasti F). ⚠️ Ctrl+K **non** è fra queste: passa da
  `useKeyboardShortcuts`, quindi dentro un input non si attiva
- ⛔ **La scorciatoia di un'azione non si scrive nel componente**: si dà
  all'azione la chiave standard e lo fa `useScorciatoie`
- ⭐ **Una scorciatoia si dice** nel tooltip, «azione (tasto)»
  (`core/utils/scorciatoie.js`, nomi dei tasti nei locales)
- Sempre `e.preventDefault()` per evitare l'azione default del browser
- Sempre cleanup in `onUnmounted`

---

### Classi CSS standard

| Classe                     | Dove applicare                    | Scopo                                                                      |
| -------------------------- | --------------------------------- | -------------------------------------------------------------------------- |
| `app-page`                 | Div root della view               | Flex column, riempie altezza                                               |
| `app-page-toolbar`         | Contenitore filtri + azione       | Flex row, space-between                                                    |
| `app-page-filters`         | Gruppo filtri                     | Flex wrap                                                                  |
| `app-datatable`            | DataTable                         | Font compatto, padding ridotto, stripe, hover                              |
| `app-page-action`          | Pulsanti azione primaria/utility generati da `PageActionsBar` | Responsive gestito dal building block |
| `app-page-actions-desktop` | Interno `PageActionsBar`          | Wrapper azioni utility inline desktop                                      |
| `app-page-actions-compact` | Interno `PageActionsBar`          | Wrapper kebab popup su touch/tablet/mobile                                 |
| `app-col-actions`          | `<Column>` azioni di riga         | Larghezza auto su desktop, 60px su tablet/touch (media query `<1024px`)    |
| `app-row-actions-inline`   | Interno `RowActionsMenu`          | Wrapper pulsanti inline — visibile solo con hover + viewport `>=1024px`    |
| `app-row-actions-compact`  | Interno `RowActionsMenu`          | Wrapper kebab + menu popup — visibile su touch o viewport `<1024px`        |
| `app-menu-item-manage`     | Voce `Menu` PrimeVue              | Colore blu — default popup `RowActionsMenu`                                |
| `app-menu-item-action`     | Voce `Menu` PrimeVue              | **Blu dal 2026-08-27** (era verde) — default popup `PageActionsBar` / severity `primary`. Vedi la nota sotto |
| `app-menu-item-warn`       | Voce `Menu` PrimeVue              | Colore arancio — severity `warn` (cautela)                                 |
| `app-menu-item-danger`     | Voce `Menu` PrimeVue              | Colore rosso — severity `danger` (distruttiva)                             |

#### ⭐ I pulsanti di AZIONE sono blu (decisione di Tid, 2026-08-27)

Erano metà verdi e metà blu: sulla **stessa riga** di una lista «Gestisci note»
usciva blu e «Apri documenti» verde, perché la prima non ha `severity` (fallback
`app-menu-item-manage`) e la seconda ha `severity: primary`. La differenza non
voleva dire niente per chi guarda.

**Sede unica**: `--app-btn-action-*` in `theme.css`. I tre punti che erano verdi
— `app-action-btn`, `app-reload-btn`, `app-menu-item-action` — puntano lì. Per
tornare al verde si cambiano quelle tre righe, **non** i blocchi in `main.css`.

⛔ **Restano intatti i colori che PORTANO un significato**: rosso per
cancellazione e PDF, arancio per gli avvisi. Uniformare quelli cancellerebbe
un'informazione, non un'incoerenza.

#### ⛔ Il tooltip di un pulsante che può essere DISABILITATO va sull'involucro

Un `<button disabled>` **non emette eventi del mouse**, e la directive tooltip di
PrimeVue aggancia `mouseenter` sull'elemento stesso: appeso al Button il tooltip
non compare **mai**, e a pulsante spento è esattamente quando serve.

Si avvolge in uno `<span class="app-action-tooltip-wrap">` (`inline-flex`, così
prende il posto del Button come elemento flex e la spaziatura non cambia).
`PageActionsBar` e `DrawerActionsBar` lo fanno **dal 2026-08-27**: prima il
motivo che il DB manda con `enabled:false` + `reason` era muto su tutte le liste
e su tutti i drawer.

### Composable `useSearchTable(store)`

Centralizza debounce search, onPage, onSort e paginatorProps. Tutti i componenti lista lo usano:

```js
const { searchText, onPage, onSort, paginatorProps } = useSearchTable(store)
```

```html
<ListaConfigurabile codice="dominio.entita" :paginator-options="paginatorProps"
  @page="onPage" @sort="onSort" ... />
```

Nelle liste configurabili lo si riceve già da `useListaConfigurabilePage`, che
lo chiama dentro di sé.

Nessun componente lista deve implementare onPage/onSort/debounce manualmente.

### ⛔ Paginazione corretta: **una sola sorgente** per `rows` e `first`

🔴 **Il difetto che questa regola evita**: cambi la dimensione di pagina, poi vai
da pagina 1 a pagina 2 e ti ritrovi su **pagina 3**. Non è un bug di PrimeVue: è
**la dimensione di pagina contata da due parti diverse**.

**La regola, in una riga:** `rows` e `first` li possiede **il caller** — è lui
che ha fatto la fetch, e solo lui sa con quale dimensione. Chi disegna il
paginator li legge, non li ricalcola.

`<ListaConfigurabile>` applica questa cascata, **in quest'ordine**:

1. `paginatorOptions.rows` / `.first` del **caller** — lo stato vero;
2. `config.pagina_dimensione` — il preset a catalogo, finché il caller non ha uno stato suo;
3. la misura `PAGINA` del catalogo (`misuraDefault(USO_MISURA.PAGINA)`).

⛔ **Fino al 2026-08-28 il caller non era nella cascata**: `rows` veniva dalla
sola config e **sovrascriveva** quello che il caller dichiarava. La scelta
«righe per pagina» dell'operatore non arrivava mai al paginator: lui sceglieva
10, il caller rifaceva la fetch con 10, e al render successivo il paginator
tornava a disegnarsi con i 25 del catalogo. Poi PrimeVue calcolava l'offset del
«vai a pagina 2» con **25** e il caller lo interpretava con **10**:
`25/10 + 1 = 3`.

**Come si scrive una lista che pagina bene:**

| Lista | Cosa usare |
| --- | --- |
| lista di ricerca standard | `useSearchTable(store)` — `paginatorProps` porta già `rows`/`first` dallo store, e `onPage` ha le due guardie (evento che non cambia niente → esci; fetch in volo → ignora) |
| **cruscotti / drawer** (che `useSearchTable` non può servire: pretende uno store «ricerca + sort + limit») | `usePagedDashFetch` + `paginatorOptions` che dichiara **sempre** `rows` e `first` calcolati con la **stessa** dimensione della fetch |

⚠️ **Il difetto si nasconde dove i numeri combaciano.** Sulla Lente 1 saltavano
**tre liste su quattro**: gli `errori` hanno `pagina_dimensione = 10` a catalogo,
uguale alla misura compatta di allora, quindi lì i due numeri coincidevano per caso
e non succedeva niente. Sembrava il problema di una lista sola.

⚠️ **Conseguenza da conoscere**: con la cascata, `pagina_dimensione` del preset
vale come **valore iniziale** solo per le liste il cui caller si allinea alla
config (`@config-loaded`, che quasi tutti i consumatori agganciano). Per le altre
il preset resta dichiarato e non applicato — è una divergenza aperta, non un
difetto di questa regola.

### Pattern: Ricerca universale → lista filtrata

Quando l'utente seleziona un risultato dalla ricerca universale (SearchDrawer), il sistema:

1. **Imposta il contesto** globale (`contextStore.setContext` con `searchTerm`)
2. **Naviga** alla rotta lista corrispondente
3. **`useSearchTable`** legge automaticamente il termine da `route.query.search` o `contextStore.searchTerm`

**Nessuna configurazione necessaria nelle singole SearchTable** — `useSearchTable` centralizza
la risoluzione del termine di ricerca iniziale. Le SearchTable si usano esattamente come prima:

```js
const { searchText, onPage, onSort, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'ragione_sociale_completa'
})
```

**Nella View** serve solo il watcher per auto-apertura drawer da contesto:

```js
import { useContextStore } from '../../stores/context'
const ctx = useContextStore()

watch(() => route.fullPath, () => {
  if (route.name === 'anagrafiche-clienti' && ctx.entitaId) {
    nextTick(() => drawer.editRow({ id: ctx.entitaId }, 'id'))
  }
}, { immediate: true })
```

**Compatibilita' con empty state:** le liste che partono vuote (vedi sezione "Empty state")
usano `onMounted(() => { if (searchText.value) store.fetchList() })` per garantire
che il termine precaricato da ricerca universale o AI venga eseguito al mount.
Senza questo `onMounted` condizionale, la lista resta vuota anche con search precaricata.

**Per aggiungere una nuova lista:**

- Aggiungere la rotta nella mappa `TIPO_RUOLO_ROUTES` in `SearchDrawer.vue`
- Implementare il watcher `ctx → drawer.editRow` nella View se supporta auto-apertura
- Se la lista usa empty state: aggiungere `onMounted` condizionale (vedi sezione "Empty state")
- Nient'altro: `useSearchTable` fa il resto

### ⚠️ REGOLA CRITICA: Paginazione deterministica (backend)

**Ogni query SQL paginata (LIMIT/OFFSET) DEVE avere `id` come tiebreaker nell'ORDER BY.**

```sql
-- ❌ SBAGLIATO — ordine non deterministico, pagine duplicate a offset alti
ORDER BY descrizione ASC
LIMIT 25 OFFSET 700

-- ✅ CORRETTO — id garantisce ordine unico per ogni riga
ORDER BY descrizione ASC, c.id
LIMIT 25 OFFSET 700
```

**Perche':** senza tiebreaker, PostgreSQL non garantisce l'ordine tra righe con lo stesso
valore nella colonna di sort. Con OFFSET alto il planner puo' restituire righe gia' viste
nelle pagine precedenti, causando dati duplicati e pagine "bloccate".

Stesso principio dei subfile AS/400 dove il RRN nascosto garantiva la posizione del cursore.

**Dove applicare:** TUTTE le query repository che usano `LIMIT %s OFFSET %s` — nessuna eccezione.

---

## Pattern Master-Detail inline (gestione righe in drawer)

Per le sub-entita' che richiedono inserimento/modifica riga (righe contratto, righe ordine,
componenti BoM, ecc.) si usa un **drawer master-detail inline**: lista paginata sopra,
form dettaglio sotto — tutto nello stesso drawer, zero drawer annidati.

```
┌─────────────────────────────────────────────────────────┐
│ DrawerTitle: "Contratto - Righe"                        │
├─────────────────────────────────────────────────────────┤
│                                           [BOZZA]  (dx) │
│ Numero              │ Cliente                            │
│ CNT0000001          │ Rossi Mario SRL                    │
│ Valido dal          │ Valido al                          │
│ 16/04/2026          │ 31/12/2026                         │
├─────────────────────────────────────────────────────────┤
│                                          [+ Nuovo]       │
│ [◀ 1/3 ▶  10/pag]                                       │
│ Articolo │ UoM │ Prezzo │ Qta │ Tipo   │ 🗑             │
│ ART-001  │ kWh │ 25.50  │ 1   │ CANONE │ 🗑  ← sel.    │
│ ART-002  │ mc  │ 12.00  │ 1   │ CONSUMO│ 🗑             │
├─────────────────────────────────────────────────────────┤
│ ═══════ Modifica riga ═══════                           │  ← visibile solo in form mode
│ Articolo: [ART-001 ...] (disabled)                      │
│ UoM: [kWh ▼]         Tipo: [CANONE ▼]                   │
│ Prezzo: [25.50]       Qta: [1]                           │
│ Ordine: [10]                                             │
│                            [Annulla]  [Salva]            │
├─────────────────────────────────────────────────────────┤
│                                          [Chiudi]        │  ← visibile solo in lista, sparisce in form mode
└─────────────────────────────────────────────────────────┘
```

### Regole del pattern

1. **Drawer largo**: usare `DRAWER_WIDTH.WIDE` (960px) per dare spazio alla lista + form
2. **Intestazione contesto**: in alto mostrare sempre i dati del parent (numero, cliente, stato, date). L'operatore deve sapere dove si trova senza tornare indietro. Tag stato allineato a destra
3. **Paginazione**: `paginator` con `rows="10"` e `rows-per-page-options="[10, 25]"`, `paginator-position="top"`, `data-key="id"`
4. **Azioni toolbar**: usare `PageActionsBar`; l'azione "Nuovo/Aggiungi" e' `kind: 'primary'`
5. **Selezione riga**: `selection-mode="single"` + `v-model:selection`. Click riga popola il form in edit mode con `@row-select`
6. **Form dettaglio**: visibile SOLO quando attivo (Nuovo o click riga). Nascosto di default. Titolo "Nuova riga" o "Modifica riga". ⭐ **All'apertura scorre in vista** (2026-10-07): il form si lega con `:ref="ancoraForm"` di `useFormInline`, che lo porta in vista dopo il gesto (Nuovo o click riga) e mai da solo. Un form non legato si apre sotto un elenco lungo, fuori vista, e il click sembra non fare nulla
7. **Articolo**: in create editabile (autocomplete), in edit disabled (immutabile)
8. **UoM**: filtrate per articolo via `listArticoloUom(articoloId)`, pre-seleziona la UoM base. Placeholder "Seleziona prima l'articolo" se nessun articolo scelto
9. **Salva/Annulla**: sempre in basso dopo il form. Salva crea o aggiorna, chiude form, emette `changed`. Annulla chiude form e deseleziona riga
10. **Elimina**: icona cestino sulla riga (`@click.stop` per non triggerare selezione). Se stavo editando quella riga, chiude il form
11. **`formMode`**: 3 stati, `null` (nessun form), `'create'`, `'edit'`. Governa visibilita' e comportamento. ⛔ **Non si scrive a mano**: la macchina del form e' il BB `useFormInline` (2026-09-28, regola del 2 — era in dieci sedi, unificate con l'ok di Tid), che da' anche «Nuova riga» spenta a form aperto (`azioneNuovaRiga`), il click che apre solo se le righe si scrivono (`apriRiga`) e la **chiusura del form al cambio di documento**
12. **Pulsante Chiudi del drawer (obbligatorio)**: in fondo al drawer, in modalita' lista, deve essere presente un `<FormFooter close-only>` con la sola voce "Chiudi". Quando si entra in form mode (Nuovo/Modifica riga), **il footer scompare** (`v-if="!formMode"`): il form ha gia' Annulla/Salva, e il footer del drawer duplicherebbe l'azione e spingerebbe il form sotto il fold. Vale per qualunque drawer di sub-entita' con lista (BoM, righe contratto, indirizzi, contatti, conti, ecc.). La X in alto resta come escape rapido (semantica diversa: dismiss vs completion). Vedi sezione "Componente `FormFooter`"
13. **La riga aperta si evidenzia** (2026-10-04, Tid). In un **drawer** aperto dal click lo fa la lista da sola (`ListaConfigurabile`, pila `useDrawerInCima`): niente da dichiarare. Nel **form inline**, il contenitore passa alla lista `riga-attiva` (la chiave della riga in modifica, o quella da cui nasce la creazione) e `righe-cliccabili` (`false` quando il click non apre niente). Col form sotto la lista, senza l'evidenza non si vede quale riga si sta modificando

### Riferimento implementativo

Primo caso: `ContrattoRigheDrawer.vue` (righe contratto pricing v5).

### Come applicare a una nuova sub-entita'

⛔ **Non si copia un drawer esistente.** Fino al 2026-09-28 questo passo diceva
«copiare la struttura di `ContrattoRigheDrawer.vue`», e la macchina del form si
è ritrovata scritta in dieci posti (verifica critica del brief
`brief-db-liste-righe-documento`, §5 L1). La macchina è il BB
`useFormInline`; la lista è `useDrawerTabLista` + `<DrawerTabLista>`
(per le righe di vendita, `RigheMasterDetailTable`, che dal 2026-09-28 monta
gli stessi due BB).

1. Montare la lista e la macchina dai BB qui sopra
2. Scrivere i campi del form di riga
3. Passare le props contesto dal parent (numero/codice, cliente, stato, date)
4. Collegare le API CRUD (add/update/delete) allo store o direttamente
5. Mantenere `data-key="id"` + paginazione a 10 + `PageActionsBar` + `@click.stop` sul cestino

---

## Pattern Tab-View (viste multi-sezione)

Quando una pagina contiene piu' sezioni correlate (es. Gestione Geografica con 6 tab):

```
┌─────────────────────────────────────────────────────────┐
│ [ Tab 1 ]  [ Tab 2 ]  [ Tab 3 ]  [ Tab 4 ]             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│    Contenuto del tab attivo (SearchTable)               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Regole (`Tabs`)

> I componenti da usare sono `Tabs`, `TabList`, `Tab`, `TabPanels`, `TabPanel`.
> `TabView` (l'API della generazione precedente di PrimeVue) è **eliminato dal repo** — migrazione
> completata il 2026-07-22, zero residui: se lo trovi in un esempio, l'esempio è
> vecchio.
> ⚠️ La versione di PrimeVue in uso si legge in `frontend/package.json`, non qui:
> ciò che questa sezione fissa è **quale API si usa**, e quella non cambia con la
> patch. Il salto alla generazione successiva ha un piano suo
> ([piano-migrazione-primevue-5.md](../work-in-progress/piano-migrazione-primevue-5.md)).

- Usare `Tabs` con `lazy` (carica il contenuto solo quando il tab è attivo)
- Il div root della vista ha `class="app-page"` — `Tabs` si espande in altezza
- **NON mettere `app-tab-content` sul contenitore `<Tabs>`**: quella classe, come
  figlia diretta di `.app-page`, applica `flex:1; overflow:hidden` pensati per un
  *pannello di contenuto*. Sul contenitore fa sì che i pannelli comprimano la
  `TabList` fuori vista appena il contenuto cresce — sintomo insidioso perché
  **dipende dalla quantità di righe**: chi vede pochi record non nota nulla, chi
  ne vede molti «perde» i tab (bug reale, 2026-07-22).
- `class="app-tab-content"` va sul div root del componente **dentro** ogni `TabPanel`
- La `DataTable` dentro il tab vuole `scrollable` + `scroll-height="flex"`
  (§Regole liste): senza, la catena flex esiste ma la tabella non scrolla
- ⚠️ Con `lazy` ogni attivazione del tab è un **mount**: il primo caricamento va in
  `onMounted` (il solo `onActivated` non scatta per un discendente montato dopo
  l'attivazione della rotta → tab vuoto per sempre). Vedi `CodaLavoriTab.vue`.
- Ogni tab contiene un **SearchTable** riutilizzabile (non logica inline nella vista)
- I drawer sono dichiarati nella vista, fuori da `Tabs`
- Le chiavi `value` sono **stringhe stabili e parlanti** (`indirizzi`, `comuni`…),
  mai indici numerici: sono ciò che rende il tab attivo deep-linkabile
- ⚠️ **Tab condizionali** (`v-if` su permesso/modo): il `value` iniziale va
  **calcolato sul primo tab effettivamente reso**, non fissato al primo in ordine.
  `TabView` attivava da sé il primo pannello presente; `Tabs` no — un
  `value="preset"` fisso lascia la pagina **senza alcun pannello** per chi non ha
  quel tab. Vedi `GestionePersonalizzazioniListeView.vue`.
- ⚠️ **Tab dentro un drawer**: il tab attivo va riportato al primo a ogni
  riapertura (`v-model:value` nel watch su `visible`), altrimenti si riapre sul
  tab dell'ultima consultazione — e se quel tab era condizionale al modo
  (es. «Permessi» solo in modifica) il pannello risulta vuoto. Vedi
  `OperatoreDrawer.vue`, `PraticaDrawer.vue`.

Riferimenti corretti: `ResiView.vue`, `CodeLavoroView.vue`, `IndirizziView.vue`.

### CSS automatico

`main.css` contiene la catena flex `.app-page > .p-tabs > .p-tablist|.p-tabpanels
> .p-tabpanel` (+ `.app-tab-content`): automatica, nessun CSS scoped necessario.
`.p-tablist` è fissata a `flex: 0 0 auto` proprio per non farsi comprimere.

⚠️ La catena è ancorata a `.app-page >`: **i tab dentro un drawer non sono
intercettati** (e non lo erano nemmeno con `TabView`). Lì l'altezza la gestisce il
corpo del drawer — non serve CSS aggiuntivo, e non va aggiunto CSS scoped.

### Residui dell'API precedente di PrimeVue — nessuno

Migrazione completata il **2026-07-22**: `TabView` → `Tabs` e
`InputSwitch` → `ToggleSwitch`. `Dropdown`/`Calendar`/
`OverlayPanel`/`Sidebar` erano già migrati. La catena CSS gemella `.p-tabview` è
stata rimossa da `main.css` insieme all'ultimo uso.

Controllo di non-regressione (deve dare **0 risultati**):

```bash
grep -rn "primevue/tabview\|primevue/inputswitch" frontend/src
grep -c "p-tabview" frontend/src/assets/main.css
```

---

## Drawer (nuovo e modifica)

**Regola unica: qualsiasi form di inserimento o modifica si apre sempre in un drawer laterale destro.**

### Comportamento

- Si apre da destra con animazione slide
- La lista rimane visibile sullo sfondo
- Si chiude con: `ESC`, clic fuori, pulsante Annulla, o salvataggio riuscito
- Non e' possibile aprire due drawer contemporaneamente

### Larghezze standard (da `constants.js`)

| Tipo      | Larghezza | Esempio                                                     |
| --------- | --------- | ----------------------------------------------------------- |
| SIMPLE    | 480px     | Toponomastica, lookup, config                               |
| STANDARD  | 640px     | Indirizzi, anagrafiche, catalogo                            |
| COMPLEX   | 800px     | Pratiche, contratti                                         |
| WIDE      | 960px     | Ricerca universale, liste con dettaglio                     |
| WIDE_PLUS | 1100px    | Master-detail con sub-tabella in expansion (righe + componenti BoM) |
| XLARGE    | 1360px    | Matrici parametri-per-entita' (utility, slot/override), liste a molte colonne dentro un drawer |

La sede è `DRAWER_WIDTH` in `core/constants.js`: se questa tabella e il codice
dissentono, vale il codice.

Le `DRAWER_WIDTH` sono **richieste massime**: il drawer non eccede mai il
viewport. Sotto la larghezza richiesta (es. mobile/tablet) il drawer riempie
lo schermo. Regola globale in [main.css](../../../../frontend/src/assets/main.css):

```css
.p-drawer { max-width: 100vw; }
.app-drawer-content { min-width: 0; overflow-x: auto; }
```

**Logica responsive uniforme per TUTTI i drawer:**

1. La larghezza inline `:style="{ width: DRAWER_WIDTH.X }"` resta la
   preferenza desktop; sotto soglia viewport `max-width: 100vw` vince.
2. I form interni gia' collassano da soli: `form-grid-2col`/`-3col` →
   1 colonna sotto 480px (vedi "Classi CSS form").
3. Le DataTable annidate gestiscono il loro scroll orizzontale via
   `.app-datatable` (e variante `.app-datatable--inner`).
4. Per gli elementi rari che non si adattano (riga widget custom, contenuto
   non collassabile), la scrollbar orizzontale appare sul wrapper
   `.app-drawer-content` come safety net — cintura + bretelle.

Nessun drawer puo' deviare da questa logica con CSS scoped locale: se
serve un overflow diverso, modificare la regola globale, non sovrascriverla.

### Sede: `AppDrawer` (dal 2026-10-03)

⭐ Il chrome di un drawer laterale ha **una sede**: `core/components/AppDrawer.vue`,
mirror di `AppDialog`. Il guscio porta testata, larghezza, uscita con
conferma, montaggio a fine animazione, corpo con readonly e footer; il
chiamante porta solo il **contenuto** (dettaglio nel catalogo BB frontend).

```vue
<AppDrawer
  :visible="visible" @update:visible="(v) => emit('update:visible', v)"
  :title="t('…')" :icon="MANAGE_ICONS.X" :action="t('common.edit')"
  :width="DRAWER_WIDTH.STANDARD"
  :modificato="modificato" :conferma-uscita="chiudiConConferma"
  :loading="loading" :save-disabled="!canSave" @save="onSave"
>
  <div class="form-grid">…</div>
</AppDrawer>
```

- **Il footer è FISSO in basso** (decisione di Tid, 2026-10-03): su un form
  lungo il Salva resta a vista. Varianti: `footer="form"` (Annulla/Salva),
  `"chiudi"`, `"nessuno"` (master-detail con il form inline aperto, che ha il
  suo Annulla/Salva nel corpo).
- **Ogni uscita passa da `confermaUscita`**: X, ESC, clic fuori, Annulla,
  Chiudi. Un drawer con un form gli passa il `chiudiConConferma` di
  `useDrawerFormPreserve` (o di `unisciFotografie`, se le fotografie sono più
  d'una).
- ⭐ **Esce solo il drawer in cima** (`useDrawerInCima`, 2026-10-04, ok Tid):
  con un drawer aperto sopra — figlio nello slot o montato accanto, o il
  drawer dei filtri compatti — l'uscita di quello sotto non fa niente. ESC
  arriva a tutti i drawer aperti (un listener su `document` per ciascuno), e il
  padre si chiudeva smontando il figlio con le sue modifiche, senza chiedere.
  Il chiamante non dichiara niente: niente `:dismissable="!figlioAperto"` per
  un figlio **drawer** (resta per un figlio dialog, o `!loading`).
- ⭐ **Una scorciatoia che funziona si dice** (2026-10-04, ok Tid), nella forma
  unica «azione (tasto)» di `core/utils/scorciatoie.js`: la X del drawer ha
  accanto l'etichetta «Esc» (`app-kbd`, nascosta su `ui.isCompatto`) e il
  tooltip «Chiudi (Esc)»; il Salva di `FormFooter` il tooltip «Salva
  (Ctrl+S)». ⭐ **Multilingua anche il tasto**: i nomi in `common.tasti.*`
  (variante `_MAC`), la forma in `common.con_scorciatoia`. Lo fa il guscio:
  il chiamante non scrive niente.
- **La larghezza è un valore di `DRAWER_WIDTH`**, mai una stringa CSS:
  `check-drawer-width.mjs` ferma quella scritta a mano sul tag.
- **La sola lettura protegge il corpo** (`app-readonly`) per default. Un drawer
  che la protegge **nascondendo le azioni** — consultazione, liste con menu di
  riga, personalizzazioni dell'utente — passa `:proteggi-corpo="false"`: la
  catena readonly arriva lo stesso a `FormFooter` e ai figli, ma il corpo resta
  cliccabile (`RowActionsMenu` non è `.app-escape`).
- **Un documento** sceglie il footer con il BB `useFooterDocumento`
  (Annulla/Salva finché la testata si modifica, «Chiudi» quando il documento c'è
  ma non si tocca, niente col form di una riga aperto).
- **Un pulsante in più accanto ad Annulla/Salva** (il «Ripristina» delle
  personalizzazioni) va nello slot `#footer-azioni`: il footer resta del
  guscio, con la sua uscita. Lo slot `#footer` (che sostituisce tutto) è per
  i casi veri, come un wizard.
- **Un'eccezione salvabile in un contesto in sola lettura** (i riferimenti
  dell'atto di un contratto ATTIVO) passa `:footer-readonly="false"` e libera
  i suoi campi con `app-escape`. La condizione deve già escludere l'area in
  sola lettura: l'override non guarda i permessi.
- **Chi deve aspettare la fine dell'animazione** (l'auto-salvataggio della
  bozza) ascolta `@after-show` di `AppDrawer`.
- ✅ **Tutti i drawer laterali sono su `AppDrawer`** dal 2026-10-03, e il lint
  ferma `primevue/drawer` fuori dalle sedi (§«Import PrimeVue riservati»). Lo
  schema qui sotto descrive ciò che il guscio rende.

### Struttura interna

```
┌──────────────────────────────────┐
│ Header (titolo operazione)       │  ← PrimeVue Drawer header
├──────────────────────────────────┤
│                                  │
│   div.app-drawer-content         │
│     div.form-grid                │
│       div.form-field             │
│         label + input            │
│       div.form-field             │
│         label + input            │
│     div.form-grid-2col           │  ← griglia 2 colonne (opzionale)
│       ...                        │
│                                  │
├──────────────────────────────────┤
│   FormFooter                     │  ← footer FISSO (slot #footer)
│     [Annulla]        [Salva]     │
└──────────────────────────────────┘
```

### Composable `useDrawerState()`

Gestisce stato del drawer (visible, mode, itemId, itemData) con `reactive()`:

```js
const drawer = useDrawerState()
// Apri: drawer.openCreate() / drawer.editRow(data, 'id_field')
// Template: :visible="drawer.state.visible" @update:visible="v => drawer.state.visible = v"
```

### Componente `FormFooter`

Footer standard del drawer — mai duplicare i pulsanti inline. Due modalita':

**1. Default (form di add/edit)**: Annulla + Salva.

```html
<FormFooter :loading="loading" :disabled="!canSave" @save="handleSave" @cancel="close" />
```

**2. `close-only` (drawer di lista / sola visualizzazione)**: solo "Chiudi". Obbligatorio in qualsiasi drawer che mostra una lista di sub-entita' (vedi pattern Master-Detail inline §"Regole del pattern" punto 12). Senza esso, l'operatore deve raggiungere la X in alto per uscire — UX storta su touch e violazione di Fitts's law.

```html
<FormFooter v-if="!formMode" close-only @cancel="onClose" />
```

Regola di visibilita': **nascondere il close-only quando il drawer e' in form mode** (`v-if="!formMode"` o `v-if="!adding"`). Motivi:

* il form ha gia' Annulla/Salva: il footer "Chiudi" duplicherebbe l'azione
* senza `v-if`, il "Chiudi" spinge il form sotto il fold

Pattern di riferimento: `ContrattoRigheDrawer.vue` (o il BB `NoteDrawer.vue`).

Handler standard di chiusura: usare il composable `useDrawerClose(emit)` da
`core/composables/useDrawerClose.js` (centralizza il pattern, evita le
copie identiche). Per drawer che notificano il parent della chiusura con
un evento secondario (es. `cancelled` in pratiche/anagrafiche, `annullato`
in `SoggettoResolver`), passare il nome come secondo argomento:

```js
import { useDrawerClose } from '../../core/composables/useDrawerClose'
const onClose = useDrawerClose(emit)              // base
const onClose = useDrawerClose(emit, 'cancelled') // con notifica al parent
```

Note: la X in alto del drawer PrimeVue resta come escape rapido (semantica diversa da "Chiudi"): X = dismiss/escape, Chiudi = completion deliberata. Non sono duplicati, vanno tenuti entrambi.
⚠️ **Vale per il drawer, NON per il dialog** (2026-09-18): nel drawer il footer di
un form lungo sta sotto il fold e la X in alto ha un ruolo; nel dialog il footer
è **sempre visibile**, e la X è un doppione — vedi §`AppDialog`, «Chrome».

### Componente `AppDialog` (OBBLIGATORIO per le dialog modali)

**Regola**: ogni Dialog modale "azione" (conferma, form one-shot, registrazione
esito) DEVE usare il building block `AppDialog` — mai `<Dialog>` PrimeVue grezzo
con `<template #footer>` hand-rolled. `AppDialog` è il mirror di `AppDrawer` per
le Dialog: incapsula chrome uniforme + `FormFooter` integrato.

⛔ `import Dialog from 'primevue/dialog'` è lecito in **un solo file**,
`core/components/AppDialog.vue` — presidiato da
`frontend/scripts/check-dialog-chrome.mjs` (`npm run guards`, in CI) e, nell'editor,
dal lint (§«Import PrimeVue riservati»).

⭐ **Uscire con dati inseriti chiede** (dal 2026-10-03, D-14 di
`work-done/analisi-fe-chrome-drawer.md`, decisione di Tid: nessuna
eccezione). Ogni uscita — X, ESC, clic sulla maschera, Annulla, e il `chiudi`
che lo slot `#footer` riceve — passa da `confermaUscita(chiudi)`. Un dialog
con dei campi gli passa il `chiudiConConferma` della sua fotografia
(`useFotografiaDialog`), che chiede solo se qualcosa è cambiato rispetto
all'apertura (o al caricamento, per chi carica dati aprendosi). Un footer
personalizzato esce con il `chiudi` dello slot, **mai** con un `emit` diretto.
Un dialog i cui campi non sono dati (una ricerca, i parametri di uno strumento
di prova) lo dichiara sopra il tag:
`<!-- conferma-uscita: nessuna — <motivo> -->`. Presidio:
`check-dialog-chrome.mjs`, regola 6.

Cosa centralizza:

* **chrome**: `modal`/`closable`/`closeOnEscape`/`dismissableMask` con i default
  di **`DIALOG_CHROME`** (`core/constants.js`) — la sede unica, condivisa con la
  `ConfirmDialog` globale (vedi §«Chrome» qui sotto e §«Conferma azioni»);
* **width**: da scala centralizzata `DIALOG_WIDTH` (`sm`/`md`/`lg`/`xl`) — **mai
  più px hardcoded** (`'480px'`, `'90vw'`, ecc.);
* **footer**: `FormFooter` integrato (icone ←/✓, collapse responsive icon-only
  sotto 1024px, Ctrl+S, readonly-aware);
* **`v-model:visible`** uniforme;
* **una via d'uscita sola**: Annulla/Chiudi ed ESC passano dallo **stesso**
  handler ed emettono `cancel` **e poi** `update:visible=false`. Un consumer
  che pulisce stato su `@cancel` lo vede da qualunque uscita.

#### Chrome — le regole (decisione di Tid, 2026-09-18)

| Regola | Perché |
| --- | --- |
| ⛔ **Niente X in alto** (`closable: false`) | Il footer di un dialog è **sempre visibile** (`max-height: 90%`, footer in coda): ogni dialog ha già Annulla o Chiudi, e la X era un doppione con una semantica sua (chiude senza `cancel`). Nel **drawer** la X resta, per la ragione opposta — il footer di un form lungo sta sotto il fold (§`FormFooter`) |
| ⭐ **Il tasto detto in alto a destra** (2026-10-11, Tid): l'etichetta «Esc» (`app-kbd`) | Come accanto alla X del drawer, ma **senza X**: l'etichetta non è un pulsante e non la sostituisce, dice che ESC chiude come Annulla. In `AppDialog` è nello slot `#header` (il titolo lo rende il BB, con l'id di `aria-labelledby` via `useId`); nella `ConfirmDialog` di `App.vue`, che quello slot non lo inoltra, è il `::before` delle azioni di testa (`.app-dialog-tasto-css`, testo da `data-tasto`). Non c'è dove ESC è spento (`closeOnEscape=false`) né su `ui.isCompatto` |
| ⭐ **`header` obbligatorio** (prop `required`) | Un `Dialog` PrimeVue senza titolo rende comunque la riga di testa, e con `justify-content: space-between` l'unico figlio — le azioni — finiva **a sinistra**: era la «X a sinistra» vista in-app, non un secondo chrome. Il titolo è un fatto dell'azione, non un ornamento |
| **ESC = Annulla**, e **si spegne mentre lavora** (`closeOnEscape && !loading`) | La direzione sicura resta aperta da tastiera; a salvataggio in volo il dialog non si chiude sotto la risposta. Era riscritto a mano in due dialog (`ExportDialog`, `AttivaVersioneDialog`): ora lo fa il BB |
| ⭐ **ESC chiude SOLO il dialog in cima**, mai il drawer sotto | In PrimeVue `Dialog` e `Drawer` hanno ciascuno un listener `keydown` su `document` e si chiudono per conto proprio: un ESC in un dialog aperto da un drawer chiudeva **entrambi** (rilievo di Tid, 2026-09-18). Il BB gestisce ESC **sulla propria radice** (`pt.root.onKeydown`, prima di `document` nella risalita) e tiene spento il listener di PrimeVue; `core/utils/escapeSoloInCima` — installato in `main.js` **prima** di ogni Drawer — ingoia l'ESC che sfugge alla radice quando c'è un dialog aperto. Il dialog vede l'ESC **per primo** (fase capture) e lo cede solo a un campo con la **tendina aperta** — segnale ARIA `aria-expanded="true"` sul controllo a fuoco (AutoComplete della lookup, Select, DatePicker): lì l'ESC chiude la tendina, il dialog resta. ⛔ Non `defaultPrevented`: l'AutoComplete di PrimeVue lo fa **sempre**, anche a tendina chiusa — con quel criterio ESC in «Abbina fattura» non chiudeva niente (rilievo di Tid, stesso giorno). ⭐ **All'apertura il fuoco entra nel dialog** (2026-10-11, rilievo di Tid: «ESC funziona su qualcuno, non su tutti»): l'ESC sulla radice si sente solo col fuoco **dentro**, e PrimeVue ce lo porta solo verso un `[autofocus]` o verso la **sua** X — che con `closable: false` non c'è. Nei dialog senza `autofocus` il fuoco restava sul drawer sotto o sul body, e `escapeSoloInCima` ingoiava l'ESC senza chiudere niente. Ora `AppDialog` su `show` mette il fuoco sulla radice (`tabindex=-1`) se non è già dentro; un `autofocus` lo sposta poi PrimeVue. Stessa forma sulla `ConfirmDialog` in `App.vue` (lì il fuoco lo porta già l'`autofocus` del pulsante Conferma). Due **drawer** impilati: la stessa regola nel chrome del drawer, `useDrawerInCima` (§«Sede: `AppDrawer`») |
| **Click fuori non chiude** (`dismissableMask: false`) | Terza via d'uscita accidentale, stessa ragione della X |
| **Un footer c'è sempre** | Nessuna prop `hide-footer`: senza X, un dialog senza footer non avrebbe **nessuna** uscita visibile. Il caso speciale (wizard, terzo bottone) è lo slot `#footer`, che il chrome lo mantiene |

⚠️ **Un override di chrome è una decisione, e si scrive sopra al tag.** L'unico
oggi è `EmittenteAttivoDialog` (`:close-on-escape="false"`: la scelta
dell'emittente non è rimandabile con un tasto). ⛔ Non si rimette `:closable` per
un dialog «che ce l'aveva»: il default è la regola, e un cambio di layout deve
restare **una riga in `DIALOG_CHROME`**, non un giro su tutti i file di dialog.

```html
<!-- Dialog standard: conferma/form -->
<AppDialog
  v-model:visible="visible"
  :header="t('...')"
  width="md"                       <!-- sm | md | lg | xl -->
  :loading="loading"
  :save-disabled="!canSave"
  :save-label="t('...')"           <!-- default 'Salva' -->
  @save="onSave" @cancel="onCancel"
>
  <!-- body -->
</AppDialog>
```

Scala `DIALOG_WIDTH` (in `core/constants.js`):

| Taglia | px | Uso |
| --- | --- | --- |
| `sm` | 480px | conferme brevi, form 1-2 campi |
| `md` | 560px | form standard |
| `lg` | 720px | preview/tabelle |
| `xl` | `min(92vw, 1200px)` | tabelle larghe responsive |

Prop e casi speciali:

* **Azione distruttiva**: `:save-severity="'danger'"` (o `'warn'`) — il bottone
  conferma diventa rosso/arancio, l'icona resta il check. Es. cessazione
  contratto, rifiuto offerta.
* **Footer custom** (terzo bottone, wizard): slot `#footer` per sovrascrivere il
  footer mantenendo il chrome `AppDialog`. Es. `ChiudiVersioneDialog` (bottone
  "Rimuovi chiusura" + Annulla/Conferma), `ApplicaVariazioneDialog` (wizard
  multi-step: i bottoni dello step nello slot), `EmittenteAttivoDialog` (tre
  bottoni: riprova / rimanda / conferma).
* **Solo Chiudi**: `close-only` (dialog informativo/viewer con un solo pulsante:
  registri, situazione merce, genealogia, esiti consuntivi).

Dialog di **sola conferma** (no form, sì/no su un'azione) restano gestiti da
`useConfirmAction()` (ConfirmDialog globale, vedi §"Conferme azioni"), NON da
`AppDialog`: quello serve quando la dialog ha un corpo (campi, tabella, scelta).

#### Dialog con una lista dentro — altezza definita, dieci righe (2026-09-18)

Una lista in un dialog resta una lista (`<ListaConfigurabile>` attraverso
`useDrawerTabLista` + `<DrawerTabLista>`, come nel picker delle rate), ma il
corpo di un `Dialog` **non è una colonna flex e non ha un'altezza sua**: il
blocco lista si rende all'altezza del **contenuto** — corto con l'empty-state,
alto quando le righe arrivano — e il dialog **salta** sotto gli occhi di chi
sta cercando (rilievo di Tid sul picker delle rate).

**Regola**: il blocco lista porta la classe **`app-dialog-lista`** (altezza
**definita**, token `--app-dialog-lista-h` in `theme.css`, ~dieci righe) e lo
store nasce alla misura **compatta** (`misura: USO_MISURA.COMPATTA`, dieci righe al 2026-09-30).
Così la pagina vuota e la pagina piena sono alte uguali, il dialog si apre già
alto e non si muove più; una pagina più lunga scorre **dentro** la tabella
(`scroll-height="flex"`, che è esattamente il caso per cui esiste), non
allunga il dialog.

```html
<DrawerTabLista ref="listaRef" class="app-dialog-lista" codice="..." ... />
```

⛔ **E il preset della lista deve dire lo stesso numero** (`ui.lista_preset`,
`pagina_dimensione = 10`): il `limit` di nascita dello store **non basta**,
perché al primo `config-loaded` lo scaffolding allinea `filters.limit` alla
`pagina_dimensione` risolta dal catalogo (§«Paginazione corretta», cascata 2),
e `fn_resolve_lista_config` la risolve **sempre** (`COALESCE(…, 25)`). Con il
preset a 25 il picker delle rate mostrava 25 righe in un blocco alto dieci alla
**prima** apertura e dieci dalla seconda — dopo il `reset()` alla chiusura,
con l'allineamento già fatto una volta — due aperture, due passi, nessun errore
(trovato in rilettura il 18/09). ⭐ Vale per **ogni** lista che nasce a 10, non solo
per i dialog: `pratiche` (17), `listini` (27) e `listini_righe` (37) avevano lo stesso
scarto da mesi senza che nessuno lo notasse — allineati con 68 lo stesso giorno.

⚠️ Ciò che sta **sotto** la lista (l'area temporanea della modalità multipla
del picker) non entra in quell'altezza: per lui scorre il corpo del dialog, col
tetto del `max-height: 90%` del `Dialog`.

⚠️ **`InputNumber` nella barra filtri: la larghezza va sull'`<input>`**
(`input-style="width: 9rem"`), non sul wrapper (`style`): `.p-inputnumber` è
un `inline-flex` senza bordo, e l'`<input>` dentro tiene la sua larghezza
intrinseca — più larga del wrapper — e **sborda** addosso al controllo
accanto. A video si vedono **due bordi** sul lato destro, e nessun errore
(rilievo di Tid, stesso giorno). È la forma già in uso in `DdtResoDialog` e
`ResoRiconsegnaDialog`.

### Classi CSS form

| Classe               | Scopo                                                   |
| -------------------- | ------------------------------------------------------- |
| `app-drawer-content` | Wrapper contenuto drawer (flex column, gap)             |
| `form-grid`          | Contenitore campi (flex column, gap 0.75rem)            |
| `form-field`         | Coppia label + input (flex column, gap 0.25rem)         |
| `form-grid-2col`     | Griglia 2 colonne responsive (1 colonna sotto 480px)    |
| `app-form-footer`    | Footer Annulla/Salva (FormFooter) — flex, justify-end   |

---

## Componenti riutilizzabili (building block)

### Principio

Ogni sotto-area che potrebbe essere usata in piu' di un contesto deve essere un **componente autonomo**. Dove vive lo decide **di che cosa parla**, non quanti la usano: un pezzo generico (layout, form, UI) sta in `core/components/`; un pezzo che parla di un'entita' sta nel dominio di quell'entita', e gli altri domini lo importano secondo §«Confini fra domini».

### Dove collocare un componente

| Criterio | Collocazione | Esempio |
| --- | --- | --- |
| Componente di layout, form o UI **generico** (non parla di un'entita' di dominio) | `core/components/` | PageActionsBar, FormFooter, TagList, EntityFormDrawer |
| Componente che parla di un'**entita' di dominio**, anche se lo usano piu' domini | `<dominio dell'entita'>/components/` | SoggettoForm, ComuneDrawer (anagrafiche), ArticoloLookup (catalogo), FatturaLookup (vendite) |
| Pezzo che un dominio A VALLE aggiunge alla schermata di un'entita' A MONTE | il dominio a valle, **iscritto** a un punto di estensione | la sezione Lotti della scheda articolo (magazzino) |

### Confini fra domini — chi puo' importare chi

> Decisione di Tid, 2026-09-26 ([analisi](../work-done/analisi-fe-regole-standard-violate-dal-codice.md) R-1/R-2).
> Sostituisce la regola «un dominio importa solo da `core/`» e l'eccezione dei
> componenti geografici.

🔴 **Perché la regola vecchia era sbagliata.** «Un dominio non importa un
altro dominio» contraddiceva il modello: pagamenti *deve* cercare le fatture,
vendite *deve* scegliere un articolo. Per rispettarla, i pezzi finivano in
`core/` — e allora era `core/` a importare i domini: `SoggettoForm` e i
componenti geografici importavano `anagrafiche`, `FatturaLookup` importava
vendite, il motore delle pratiche nominava i drawer di vendite, e il registro
«tipo → drawer» che `core/bersagli.js` legge stava dentro `vendite/`. La regola
produceva la violazione che voleva impedire.

**La regola, sul modello — il verso delle FK:**

1. **Un dominio importa un altro dominio solo se le sue tabelle puntano a
   un'entità di quello.** `vendite.contratti` punta a `billing_account`:
   vendite può usare i componenti di anagrafiche. `magazzino.lotti` punta a
   `catalogo.articoli`: magazzino può usare `ArticoloLookup`. Si guarda
   l'**entità**, non lo schema: fra schemi le FK vanno in tutti e due i versi
   (`anagrafiche.soggetti_titoli_iva_ambiti` punta agli articoli).
2. **Il verso opposto passa da un punto di estensione.** La scheda articolo
   non importa magazzino: offre il punto `ARTICOLO_DRAWER_SEZIONI`, e
   magazzino ci contribuisce la sezione Lotti dal suo `iscrizioni.js`. Così
   per i contratti nella lista clienti, gli accessi web nell'anteprima del
   soggetto, il saldo nel drawer della fattura
   ([`core/estensioni.js`](../../../../frontend/src/core/estensioni.js)).
3. **I motori (`pratiche`, `documenti`) li usano tutti e non nominano
   nessuno.** Il motore possiede il registro; il dominio si iscrive
   (`iscriviAttivitaUi`, `iscriviDrawerEntita`…). È lo specchio del backend,
   dove vendite iscrive i suoi handler in `HANDLER_MAP` da `apps.py:ready()`.
4. **`core/` non importa mai un dominio.** Ciò che un dominio aggiunge a
   `core` si iscrive ([`core/registri.js`](../../../../frontend/src/core/registri.js),
   [`core/drawerEntita.js`](../../../../frontend/src/core/drawerEntita.js)); una
   funzione API che serve a tutti (la lookup degli emittenti, la testata dei
   presidi) sta in `core/api/`, anche se l'endpoint lo serve un'app di dominio.
   ⛔ **Nemmeno dalla porta di servizio del router**: `router/index.js` è la
   radice dell'app e nomina tutti i domini (view e vocabolari), quindi
   `core/` e gli store globali non ne importano il modulo. Chi deve navigare
   fuori da un setup (l'interceptor HTTP, un bersaglio, l'assistente) usa
   `routerApp()` di [`core/routerApp.js`](../../../../frontend/src/core/routerApp.js),
   a cui `main.js` consegna l'istanza prima del mount; dentro un componente,
   `useRouter()`.

`main.js` carica ogni `<dominio>/iscrizioni.js` con `import.meta.glob`, prima
del mount, senza nominarne nessuno: un dominio nuovo — acquisti — si aggiunge
scrivendo il proprio file, senza toccare i motori.

Presidio: `npm run guards` → `check-confini-domini.mjs`. L'elenco degli archi
ammessi porta accanto la FK che li giustifica. ⛔ Un arco non si aggiunge per
far passare il guard: se la FK non c'è, quello che serve è un punto di
estensione.

### Checklist prima di creare un componente

1. **Esiste gia'?** — controllare `core/components/` e `core/composables/`
2. **Di che cosa parla?** — se e' generico, in `core/`; se parla di un'entita', nel dominio di quell'entita' (anche se lo useranno altri domini: §«Confini fra domini»)
3. **Props minimali** — esporre solo cio' che varia tra i contesti
4. **Emits chiari** — `@saved`, `@changed`, `@row-click`, `@new`, `update:modelValue`

> ⭐ **`saved` e `changed` non sono sinonimi, e il drawer deve sceglierne uno.**
> `saved` dice *«il lavoro su questo documento è finito»* — la lista si ricarica
> e il drawer **si chiude**. `changed` dice *«la riga è cambiata, ma sto ancora
> lavorando qui dentro»* — la lista si ricarica e il drawer **resta aperto**.
> È il caso di ogni verbo che **genera un documento senza concludere il
> proprio**: genera DDT da un ordine, genera reso da un DDT, smista un
> preventivo, ri-consegna un reso.
>
> Li implementa entrambi
> [`useDrawerSavedListRefresh`](catalogo-building-block-frontend.md): la vista
> scrive `@saved="onDrawerSaved" @changed="onDrawerChanged"` e non riscrive
> nulla.
>
> 🔴 **Perché la regola è scritta qui**: al 2026-09-01 quel momento esisteva in
> **quattro** domini con **tre** comportamenti diversi — due drawer non
> avvisavano nessuno (la lista restava ferma, e l'operatore ricaricava a mano
> senza sapere perché), uno avvisava solo un'altra tab, uno emetteva `saved` e
> **si chiudeva addosso a chi stava ancora lavorando**. Nessuno dei quattro
> falliva: è la classe di difetto che nessun test vede, perché la pagina non
> sbaglia — è solo **ferma**.
5. **i18n** — tutti i testi tramite `$t()`, mai hardcoded
6. **Responsive** — testare su mobile (flex-wrap, no larghezze fisse)

### Componenti core e composable

Per l'inventario completo di componenti, composable, utility e classi CSS disponibili, consultare il [Catalogo Building Block Frontend](catalogo-building-block-frontend.md).

La checklist sopra resta il riferimento per decidere **dove** collocare un nuovo componente; il catalogo elenca **cosa** esiste gia'.

---

## Azioni Pagina — `PageActionsBar`

Le azioni in alto a destra di liste, SearchTable e sub-liste devono passare da
`PageActionsBar` (`src/core/components/PageActionsBar.vue`). Anche il caso
semplice `refresh + nuovo` usa questo building block: evita varianti locali e
mantiene gia' pronto il menu compatto quando si aggiunge una terza azione.

```vue
<script setup>
import { computed } from 'vue'
import PageActionsBar from '@/core/components/PageActionsBar.vue'
import ReadonlyBadge from '@/core/components/ReadonlyBadge.vue'
import { MANAGE_ICONS } from '@/core/constants'

const pageActions = computed(() => [
  {
    key: 'reload',
    kind: 'utility',
    label: t('common.reload_list'),
    icon: MANAGE_ICONS.RELOAD,
    command: reload,
  },
  {
    key: 'new',
    kind: 'primary',
    label: t('common.new'),
    tooltip: t('dominio.nuovo_record'),
    icon: MANAGE_ICONS.ADD,
    hideWhenReadonly: true,
    command: () => emit('new'),
  },
])
</script>

<PageActionsBar :actions="pageActions">
  <template #suffix>
    <ReadonlyBadge />
  </template>
</PageActionsBar>
```

- Desktop: azione primaria visibile, utility inline, secondarie nel kebab.
- Touch/tablet/mobile: azione primaria visibile, tutte le altre nel kebab.
- `hideWhenReadonly: true` nasconde automaticamente l'azione in LETTURA.
- `action` aggancia i permessi di processo tramite `auth.isActionAllowed`.
- `label`, `tooltip` e menu popup devono essere multilingua (`it/en`).

---

## Azioni Drawer — `DrawerActionsBar`

> ✅ **Tre presidi dal 2026-09-23**, e coprono tre cose diverse:
> `DrawerActionsBar.spec.js` monta il componente **vero** e prova ciò
> che nessuna funzione pura può vedere — fra l'altro che il tooltip del motivo
> sta sull'**involucro** e non sul `<Button disabled>`, che è il difetto del
> 2026-08-27 rimasto senza presidio per mesi;
> `useDrawerActions.spec.js` (casi provati **per mutazione**) fissa il
> contratto del mapper — quale pulsante nasce, se è acceso, che cosa dice
> quando è spento — e vale per tutti i drawer che ci passano;
> `npm run guard:capability` verifica che ogni campo letto da un blob
> `capabilities.*` sia un campo che una `script.fn_available_actions_*`
> **emette davvero**, leggendo il contratto dalla doc auto-generata — e dal
> 2026-09-23 conta le **letture piatte** (una chiave del blob letta fuori da
> `capabilities`, anche con le parentesi o per destrutturazione), ammettendo
> solo gli omonimi dichiarati in `scripts/capability-letture-piatte.json`.
> Un flag **negato con un motivo** che non è un'azione di stato (es.
> `can_push_commessa`) diventa un pulsante spento col tooltip via
> `useEntityCapabilities().azioneNegata(flag, forma)`, mai con un'entry
> composta a mano nel drawer.
> ⚠️ Nessuno dei due guarda la **resa a video**: quella la presidia
> `DrawerActionsBar.spec.js`, che monta il componente (`@vue/test-utils` +
> `jsdom`, nel progetto dal 2026-09-23 — vedi §Test).

Le azioni di processo dei drawer entita' (cambio stato data-driven, apertura
sub-drawer "gestisci righe/note", PDF, export) si renderizzano tramite il
building block **`DrawerActionsBar`** (`src/core/components/DrawerActionsBar.vue`)
in un'unica fascia **sotto l'header informativo** del drawer (`DrawerEntityHeader`),
sopra il form. Il pattern e' speculare a `PageActionsBar` ma adattato al
contesto drawer: niente azione "+ Nuovo", supporto badge counter sui pulsanti
"gestisci" (es. numero righe), categoria `state` per le transizioni
`availableActions`.

**Comportamento responsive (CSS-first, nessun JS di detection):**

| Contesto | Variante |
| --- | --- |
| Desktop `hover` + viewport `>=1024px` | `primary` + `state` + `manage` inline con label, `secondary` nel kebab `⋮` desktop |
| Tablet / touch / viewport `<1024px` | Solo `primary` inline; `state`+`manage`+`secondary` tutti dentro lo stesso kebab `⋮` compact |

Lo switch e' realizzato da `@media (hover: none), (max-width: 1023.98px)` in `main.css`
sulle classi `.app-drawer-actions-desktop` / `.app-drawer-actions-compact`, stesso
breakpoint di `RowActionsMenu` e `PageActionsBar`.

**Perche':** su touch i tooltip non funzionano e una fila di 4-6 pulsanti
manda il drawer su 2-3 righe spingendo il form sotto il fold; sul desktop c'e'
spazio e l'hover funziona. La soluzione responsive combina il meglio di
entrambe senza compromessi (stesso approccio di `RowActionsMenu`).

**Pattern di uso nel drawer:**

```vue
<script setup>
import { computed } from 'vue'
import DrawerEntityHeader from '@/core/components/DrawerEntityHeader.vue'
import DrawerActionsBar from '@/core/components/DrawerActionsBar.vue'
import { mapAvailableActionsToDrawerActions } from '@/core/composables/useDrawerActions'
import { MANAGE_ICONS } from '@/core/constants'

const drawerActions = computed(() => [
  // Transizioni di stato data-driven dal BE (Emetti / Cessa / Riapri / ...).
  ...mapAvailableActionsToDrawerActions({
    availableActions: caps.availableActions,
    t,
    onAction: onCambiaStato,
  }),
  // Apertura sub-drawer con counter (badge).
  {
    key: 'manage-righe',
    kind: 'manage',
    label: t('contratti.gestisci_righe'),
    icon: MANAGE_ICONS.RIGHE,
    badge: righeCount.value,
    command: () => righeVisible.value = true,
  },
  // Utility nel kebab (sempre).
  {
    key: 'pdf',
    kind: 'secondary',
    label: t('contratti.scarica_pdf'),
    icon: 'pi pi-file-pdf',
    command: onScaricaPdf,
  },
])
</script>

<template>
  <DrawerEntityHeader>
    <Tag :value="detail.numero" severity="secondary" />
    <span class="app-drawer-header-muted">{{ displayDate(detail.data) }}</span>
    <Tag :value="t('contratti.forma_con_listino')" severity="info" />

    <template #status>
      <Tag :value="detail.stato_descrizione"
           :severity="statoContrattoSeverity(detail.stato_codice)" />
    </template>
  </DrawerEntityHeader>

  <DrawerActionsBar :actions="drawerActions" />
</template>
```

**Formato azione:**

```js
{
  key: string,              // identificatore univoco
  kind: 'primary' | 'state' | 'manage' | 'secondary',
  label: string,            // testo i18n
  tooltip?: string,         // override tooltip inline (default: label)
  icon: string,             // PrimeIcons o MANAGE_ICONS.*
  severity?: 'primary' | 'success' | 'warn' | 'danger' | 'info' | 'secondary',  // pass-through PrimeVue
  outlined?: boolean,       // default true per kind:'manage', false altrove
  badge?: number | string,  // counter inline + suffisso label nel popup (solo manage)
  visible?: boolean,        // default true
  disabled?: boolean,       // default false
  hideWhenReadonly?: boolean, // nasconde automaticamente in LETTURA
  action?: string,          // codename permesso processo (auth.isActionAllowed)
  command: () => void,      // handler click
}
```

**Semantica `kind`:**

| `kind` | Desktop ≥1024px | Mobile/touch | Esempi |
| --- | --- | --- | --- |
| `primary` | Inline con label, **sempre visibile** | Inline | Azione terminale critica (es. Annulla contratto DRAFT, Accetta preventivo) — raro |
| `state` | Inline con label, severity colorata | Nel kebab popup | Transizioni `availableActions` (Emetti, Cessa, Riapri, ANNULLATO) |
| `manage` | Inline con badge counter | Nel kebab popup (label suffissata col counter) | "Gestisci righe (5)", "Gestisci note (3)" |
| `secondary` | Nel kebab desktop | Nel kebab compact | PDF, Export, Cronologia, Diagnostica |

**Regole fisse:**

- La fascia azioni vive **subito sotto** `DrawerEntityHeader` e **prima** del form.
- La modifica del form NON e' un'azione del BB: resta nel `FormFooter` come "Salva".
- Ogni azione ha `label` tradotta (i18n) — l'inline la mostra come testo, il popup come voce.
- `hideWhenReadonly: true` per le azioni di modifica/transizione che non hanno senso in LETTURA.
- `class="app-escape"` e' applicata **automaticamente** dal BB a tutti i bottoni: in
  modalita' readonly (`app-readonly` sul wrapper drawer) le azioni restano cliccabili —
  il filtro effettivo lo applica `hideWhenReadonly`.
- `kind: 'primary'` solo per azioni terminali/critiche che l'operatore deve avere a
  portata di tap su **ogni** viewport. Nel dubbio usare `state` o `manage`.
- Le transizioni di stato data-driven (`availableActions`) si mappano sempre via
  `mapAvailableActionsToDrawerActions(...)`: niente loop manuale `v-for="action in availableActions"`
  nel template.

### L'informazione di stato — prop `infoKey`

> **Una lista di azioni vuota e' indistinguibile da un errore di caricamento.**
> Se da uno stato non si puo' fare nulla, la barra deve dirlo — e dire cosa si fa
> invece.

E' la faccia a video della regola R3 del brief
[vie d'uscita per l'operatore](../work-done/brief-db-vie-uscita-operatore.md):
per ogni stato, **o la via d'uscita c'e', o c'e' scritto perche' non c'e'**. Il
testo non e' una scelta del componente: e' un **dato**, la chiave i18n seminata
nel `meta` della riga di `config.stati_doc_*`, che le capability
`script.fn_available_actions_*` espongono nel campo **`stato_info_key`**.
Cambiare il messaggio e' cambiare un seed, non toccare il frontend.

⚠️ **Dal 2026-08-10 la nota NON e' piu' subordinata alla lista vuota** (decisione
§5 del test in-app, applicata da `20260810-04/-05/-06`): e' **informazione di
stato** e compare anche accanto a un pulsante vivo — es. un ordine EVASO che ha
ancora il push abilitato. Da qui il rinome del campo, che fino ad allora si
chiamava `nessuna_azione_key`: quel nome descriveva il presupposto caduto, non il
dato. ⚠️ Il campo e' **sempre presente** nel blob, col valore a `null` quando non
si applica: va guardato il **valore**, non la presenza della chiave.

⚠️ **Asimmetria voluta**: la proprieta' dentro il `meta` dello stato si chiama
ancora `nessuna_azione_key`. Rinominarla e' una slice a se': il guard
`scripts/check_i18n_keys.py` trova le chiavi seminate proprio per quel nome, e
cambiarlo senza toccare il guard lo renderebbe **verde per cecita'**.

⚠️ **E il nome del file di seed non e' una garanzia** (2026-08-15). Il guard
ammetteva i soli CSV `transizioni_stati_*` e `stati_doc_*`: la tabella degli
stati della commessa e' `vendite.stati_commessa`, senza il segmento `doc`,
quindi le sue due chiavi non sono mai state guardate — verde per sottrazione,
sullo stesso presidio che aveva gia' pagato due volte la stessa forma di
difetto. Il filtro per nome e' caduto: si scandisce **ogni** CSV di
`80_data/sql` e decide il contenuto (`RE_SEED_KEY`). Chi aggiunge una tabella di
stato non deve piu' ricordarsi di battezzarla in un certo modo perche' il guard
la veda.

**Copertura oggi**: tutti e otto i domini con `fn_available_actions_*`
(preventivo, ordine, DDT, contratto, reso, offerta, commessa, lotto) leggono la
prop nel drawer; i testi esistono per gli stati chiusi di sette di loro. Il
`lotto` e' l'unico dichiarato aperto — la sua tabella di stato
(`config.stati_doc_fiscale`) e' condivisa con le fatture, e una
`fn_available_actions_fattura` non esiste ancora.

```vue
<DrawerActionsBar
  :actions="drawerActions"
  :info-key="detail?.stato_info_key || ''"
/>
```

| Regola | Perche' |
| --- | --- |
| La chiave arriva **dal BE**, mai scritta nel componente | Il vocabolario degli stati vive a DB; un `v-if` su `stato_codice_interno` nel drawer sarebbe la stessa regola scritta due volte |
| La barra **compare** anche con zero azioni se c'e' la nota | Altrimenti l'unica cosa che spiega lo stato sparisce proprio nel caso in cui serve. Attenzione ai `v-if="drawerActions.length"` dei singoli drawer: vanno estesi alla chiave |
| La nota convive con le azioni vive | Non e' la risposta a uno schermo vuoto: e' lo stato del documento. Nessun `v-if` che la spenga quando ci sono pulsanti |
| Risoluzione via `labelOrCode` (fail-visible) | Chiave assente dai locales → si vede la chiave grezza, non il vuoto: il difetto silenzioso torna rumoroso |
| Il testo **non** arriva mai dal DB | Dal DB viaggiano solo indirizzi i18n (§Multilingua) |

Distinta da `enabled: false` + `reasons` della **singola** azione (tooltip sul
pulsante spento, vedi `mapAvailableActionsToDrawerActions`): quello spiega
perche' *quel* pulsante non si puo' premere, questa dice in che stato si trova il
documento.

**Convenzioni centralizzate:**

| Cosa | Dove |
| --- | --- |
| Icona kebab | `MANAGE_ICONS.KEBAB` in `src/core/constants.js` |
| Stile bottone std | `.app-manage-btn` in `main.css` |
| Voce menu distruttiva | `.app-menu-item-danger` in `main.css` |
| Tooltip fallback kebab | `common.altre_azioni` ("Altre azioni") in `it.json` |
| Wrapper barra azioni | `.app-drawer-actions` / `-desktop` / `-compact` in `main.css` |
| Numero sull'azione | campo `badge` dell'azione → `ActionBadge` (in `.app-action-tooltip-wrap`), anche in `PageActionsBar` |
| Nota «nessuna azione» | `.app-drawer-actions-info` in `main.css` |

---

## Header contesto pratica — `PraticaContextHeader` (drawer esecuzione flussi)

**Regola**: ogni drawer aperto per l'**esecuzione di un flusso** di pratica
(`FlussoDrawer` generico e qualsiasi futuro drawer dedicato a un template
flusso, es. `RICHIESTA_CLIENTE` della pratica PREVENTIVI) espone in alto il
building block **`PraticaContextHeader`**
(`src/pratiche/components/PraticaContextHeader.vue`), con il set minimo
identico ovunque:

- **numero pratica** (Tag; fallback `#id` se il codice manca)
- **soggetto** (`ragione_sociale_completa`)
- **data di apertura** della pratica
- **id fiscale univoco** (CF/P.IVA)

L'operatore deve riconoscere a colpo d'occhio *su quale pratica e per quale
soggetto* sta lavorando, qualunque sia il flusso. Il BB e' un wrapper di
`DrawerContextHeader`: il drawer di flusso non ricostruisce items/label, passa
solo i campi del payload BE (i flussi espongono `pratica_codice`,
`pratica_data_apertura`, `pratica_soggetto_display`,
`pratica_soggetto_id_fiscale` come display fields via JOIN).

```html
<PraticaContextHeader
  :codice="flusso.pratica_codice"
  :pratica-id="flusso.pratica_id"
  :soggetto="flusso.pratica_soggetto_display"
  :data-apertura="flusso.pratica_data_apertura"
  :id-fiscale="flusso.pratica_soggetto_id_fiscale"
>
  <template #status>
    <Tag :value="stato" :severity="statoFlussoSeverity(stato)" />
  </template>
</PraticaContextHeader>
```

La `DrawerActionsBar` (sezione precedente) vive subito sotto questo header.
Informazioni aggiuntive specifiche del flusso vanno **sotto**, mai al posto
del set minimo.

---

## Tag stato e severity (standard cromatico)

Le severity PrimeVue (`Tag`, `Badge`) seguono una convenzione fissa in tutta l'app.
Le mappe sono centralizzate in `core/utils/severity.js` — un solo punto di modifica.

### Severity standard PrimeVue

| Severity | Colore | Significato |
|----------|--------|-------------|
| `success` | Verde | Completato, attivo, OK |
| `info` | Azzurro | In corso, informativo, normale |
| `warn` | Arancio | Attenzione, sospeso, intermedio |
| `danger` | Rosso | Errore, annullato, urgente, bloccato |
| `secondary` | Grigio | Bozza, inattivo, basso |

### Attivo / Non attivo (tabelle config)

```html
<Tag :value="data.attivo ? t('indirizzi.attivo') : t('indirizzi.non_attivo')"
     :severity="data.attivo ? 'success' : 'warn'" />
```

(BB: `<AttivoTag :active="data.attivo" />`.)

### Sì / No — un booleano che è un DATO, non uno stato

`info` sul vero, `secondary` sul falso, **vuoto** sul `null`: `<SiNoTag :value="x" />`.
⛔ Non è «attivo/non attivo»: quello è la salute di un record e colora
verde/arancio; questo è un fatto («partecipa alle promo?», «gestito a
magazzino?»), e il vero è un'informazione — blu, non verde.

⭐ **In una `<ListaConfigurabile>` non si scrive lo slot**: la colonna dichiara
`formato = yesno` (o anche solo `tipo_dato = boolean`) in `ui.lista_colonna` e
`CellaConfigurabile` la rende con `SiNoTag`. Fino al 2026-09-14 il formatter
rendeva **testo** e tre liste si erano riscritte il Tag in uno slot — una delle
tre sopra una colonna che aveva già `yesno`: il formatter aveva perso sul campo.
Un booleano nuovo in lista è una riga di CSV, non un componente.

⭐ **E dal 2026-09-18 vale anche per la NATURA di un documento fiscale**
(`formato = natura_doc` → `NaturaDocTag sempre`): lo stesso slot era scritto in
più liste. ⚠️ È il primo formato che legge **due** campi della riga — la
descrizione (il `campo_sorgente`) e la gemella `natura_doc_codice_interno` —
e la gemella è presidiata: `test_lista_proiezione_campo_sorgente` pretende che
ogni lista che dichiara il formato la proietti. La regola generale: *se una
cella si rende allo stesso modo in due liste, è un `formato`, non uno slot.*

### Stati pratica

| Stato | Severity | Colore |
|-------|----------|--------|
| BOZZA | `secondary` | Grigio |
| APERTA | `info` | Azzurro |
| SOSPESA | `warn` | Arancio |
| CHIUSA | `success` | Verde |
| ANNULLATA | `danger` | Rosso |

### Priorita' (scala cromatica progressiva)

| Priorita' | Severity | Colore |
|-----------|----------|--------|
| BASSA | `secondary` | Grigio |
| NORMALE | `info` | Azzurro |
| ALTA | `warn` | Arancio |
| URGENTE | `danger` | Rosso |

### Stati flusso pratica

| Stato | Severity | Colore |
|-------|----------|--------|
| DA_ESEGUIRE | `secondary` | Grigio |
| IN_CORSO | `info` | Azzurro |
| COMPLETATO | `success` | Verde |
| SOSPESO | `warn` | Arancio |
| ANNULLATO | `danger` | Rosso |
| ERRORE | `danger` | Rosso |

### Come aggiungere una nuova mappa

1. Aggiungere la mappa in `core/utils/severity.js` con costante `NOME_MAP` e shortcut `nomeSeverity(codice)`
2. Usare `resolveSeverity(map, codice)` che fa trim automatico e fallback a `'secondary'`
3. Nel componente: `<Tag :value="data.descrizione" :severity="nomeSeverity(data.codice_interno)" />`
4. Il `codice_interno` deve arrivare dal backend via JOIN (no lookup client-side)

---

## Transizione a stato terminale con data (CESSATO / CHIUSO / TERMINATO)

> **Regola standard**: per le entità il cui workflow include uno **stato terminale**
> (es. contratto `CESSATO`, listino-versione `CHIUSA`, soggetto `ESTINTO`)
> accompagnato da una **data finale** (`valido_al`, `data_chiusura`, `data_cessazione`),
> la chiusura **non si fa modificando la data nel form**: si fa con un pulsante
> dedicato che apre un dialog di conferma con DatePicker (default oggi).
> La data e il cambio stato vengono applicati in **transazione atomica** dal BE.

### Motivazione

- Evita lo stato incoerente "stato terminale + data NULL" (resolver/processi che dipendono dalla data continuerebbero a considerare l'entità operativa)
- Rende l'azione esplicita e auditabile (1 click intenzionale, non 2 modifiche separate)
- Previene errori dell'operatore (dimentica data, oppure imposta data senza cambiare stato)
- Allinea l'esperienza fra domini: l'utente impara una volta sola "Chiudi/Cessa = dialog con data"

### Pattern FE — drawer principale

**1. Pulsanti cambio stato sempre attivi anche in modalità readonly.**
Aggiungere classe `app-escape` per bypass del CSS protect:

```vue
<Button v-for="stato in statiTransizionabili" :key="stato"
  :label="t(`<dominio>.azione_${stato.toLowerCase()}`)"
  size="small" outlined
  class="app-escape"
  @click="onCambiaStato(stato)" />
```

**2. Handler `onCambiaStato` distingue lo stato terminale.**

```js
function onCambiaStato(codice) {
  if (codice === 'CESSATO' /* o CHIUSO/TERMINATO */) {
    openCessaDialog()
    return
  }
  // altre transizioni: confirmAction generico
  confirmAction({ ... onAccept: () => store.cambiaStato(id, codice) })
}
```

**3. Dialog dedicato con DatePicker default oggi.** Usa `AppDialog` (vedi
§"Componente `AppDialog`"): `save-severity="danger"` per l'azione distruttiva,
niente px hardcoded né footer custom.

```vue
<AppDialog v-model:visible="cessaDialogVisible"
  :header="t('<dominio>.cessa_dialog_titolo')" width="sm"
  :loading="loading"
  :save-disabled="!cessaDialogData || loading"
  :save-label="t('<dominio>.cessa_dialog_conferma')"
  save-severity="danger"
  @save="onConfermaCessazione">
  <div class="form-field">
    <label>{{ t('<dominio>.cessa_dialog_data') }}</label>
    <DatePicker v-model="cessaDialogData" date-format="dd/mm/yy" show-icon />
  </div>
  <Message severity="warn" :closable="false" size="small">
    {{ t('<dominio>.cessa_dialog_warning') }}
  </Message>
</AppDialog>
```

```js
function openCessaDialog() {
  cessaDialogData.value = new Date()  // default oggi
  cessaDialogVisible.value = true
}
async function onConfermaCessazione() {
  const validoAl = toDateString(cessaDialogData.value)
  const result = await execute(
    () => store.cambiaStato(id, 'CESSATO', { validoAl }),
    { successMessage: t('<dominio>.stato_cambiato') }
  )
  if (result !== null) {
    cessaDialogVisible.value = false
    await refreshDetail()
  }
}
```

**4. Campo data condizionale per stato.**

| Stato            | Visibilità campo data           | Editabile         | Label                                  |
| ---------------- | ------------------------------- | ----------------- | -------------------------------------- |
| DRAFT            | sì                              | sì (opzionale)    | "Fine validità" / "Valido al"          |
| ATTIVO           | nascosto se NULL                | —                 | (cessazione passa dal dialog)          |
| ATTIVO           | readonly se valorizzato         | **no** (readonly) | "Cessazione programmata al"            |
| CESSATO / CHIUSO | sì                              | **no** (readonly) | "Data cessazione" / "Data chiusura"    |

```vue
<div class="form-field"
  v-if="!isEdit || detail?.stato_codice === 'DRAFT' || detail?.stato_codice === 'CESSATO'">
  <label>
    {{ detail?.stato_codice === 'CESSATO'
      ? t('<dominio>.field_data_cessazione')
      : t('<dominio>.field_valido_al') }}
  </label>
  <DatePicker :model-value="parseIsoDate(form.valido_al)"
    @update:model-value="form.valido_al = toIsoDate($event)"
    :disabled="detail?.stato_codice === 'CESSATO'"
    date-format="dd/mm/yy" show-icon />
</div>
```

**5. `buildPayload` non spedisce la data quando il campo è nascosto.** In edit
post-DRAFT il payload PATCH testata deve essere coerente con la whitelist BE
del Profilo A (vedi sotto): non re-spedire campi loaded.

### Cessazione immediata vs programmata (regola data-driven)

Quando l'utente sceglie nel dialog la data, il comportamento si differenzia:

| Data scelta            | Cessazione   | Effetto                                                              |
| ---------------------- | ------------ | -------------------------------------------------------------------- |
| oggi o passata         | immediata    | Service applica PATCH `valido_al` + UPDATE stato `CESSATO` (atomico) |
| futura (>= today)      | programmata  | Service applica solo PATCH `valido_al`. Stato resta ATTIVO/SOSPESO. Job notturno DB allineerà a CESSATO quando la data scade |

**Rationale** (allineato col principio fail-safe): un contratto con stato `CESSATO` ma `valido_al` futuro è incoerente — il resolver/processi che dipendono da `validita @> CURRENT_DATE` continuano correttamente a considerarlo operativo, ma chi legge lo stato vede "cessato". Lo evitiamo per costruzione: il cambio stato avviene solo quando la realtà operativa lo conferma.

**Dialog adattivo**: titolo, severity, label conferma e toast variano in base a `cessazioneProgrammata`:

```js
const cessazioneProgrammata = computed(() => {
  if (!cessaDialogData.value) return false
  const oggi = new Date(); oggi.setHours(0, 0, 0, 0)
  const scelta = new Date(cessaDialogData.value); scelta.setHours(0, 0, 0, 0)
  return scelta >= oggi
})
```

**Cessazione programmata visibile in stato intermedio**: in ATTIVO/SOSPESO con `valido_al` valorizzato, il drawer mostra il campo readonly come "Cessazione programmata al {data}" — l'operatore vede che il contratto è in attesa di scadenza.

### Pattern BE — service `cambia_stato`

Estendere il service per accettare `valido_al` opzionale e applicare la regola data-driven:

```python
def cambia_stato(
    self, contratto_id: int, *, codice_interno: str, valido_al: date | None = None,
) -> dict[str, Any]:
    target_stato_id = self._repo.get_stato_id_by_codice(codice_interno)
    cessazione_programmata = False
    if codice_interno == "CESSATO":
        # data obbligatoria + valido_al >= valido_dal (errore parlante anti CHK constraint)
        ErrorManager.require(valido_al is not None, ...)
        existing = self._repo.get(contratto_id)
        if isinstance(existing.get("valido_dal"), date):
            ErrorManager.require(valido_al >= existing["valido_dal"], ...)
        # Regola fail-safe: data futura -> programmata (no cambio stato)
        if valido_al >= date.today():
            cessazione_programmata = True
    with transaction.atomic():
        if valido_al is not None:
            self._repo.update_contratto(contratto_id, {"valido_al": valido_al})
        if not cessazione_programmata:
            self._repo.update_stato(contratto_id, target_stato_id)
    return self.get_contratto(contratto_id)
```

### Pattern DB — guard transizione + job notturno

Lato DB serve **defense-in-depth** per chiudere il cerchio (analogo a listini-versioni):

1. **Trigger guard** BEFORE UPDATE OF `stato_doc_xxx_id`: ammette transizione a stato terminale (CESSATO/CHIUSA) **solo se** `valido_al IS NOT NULL AND valido_al < CURRENT_DATE`. Nome: `trgfn_<tabella>_a10_guard_transizione_stato`.
2. **Job pgAgent notturno**: UPDATE → CESSATO/CHIUSA quando `valido_al < CURRENT_DATE`. L'UPDATE passa il guard per costruzione. Funzione incapsulante: `<schema>.fn_<tabella>_close_scadute()`.
3. Brief al team DB (vedere [brief-db-contratti-cessazione-data-driven.md](../work-done/brief-db-contratti-cessazione-data-driven.md); il gemello `brief-db-listini-stato-chiusa-sync.md` non è più nel repo).

### Esempi nel codice

| Dominio           | Stato terminale              | File FE                                          |
| ----------------- | ---------------------------- | ------------------------------------------------ |
| Contratti vendite | CESSATO                      | `vendite/components/ContrattoDrawer.vue`         |
| Listini-versioni  | CHIUSA (sync da `valido_al`) | `vendite/components/ChiudiVersioneDialog.vue`    |

### Anti-pattern da evitare

- ❌ **Mostrare `valido_al` come campo editabile in stato ATTIVO**: l'utente potrebbe modificarlo senza cambiare stato → entità tecnicamente cessata ma stato `ATTIVO` (e viceversa)
- ❌ **2 chiamate API separate** PATCH `valido_al` + POST `cambia-stato`: race condition se la seconda fallisce → stato incoerente
- ❌ **Pulsante cambio stato disabilitato in readonly**: l'operatore con permessi LETTURA legittimamente non può, ma in stato post-DRAFT (drawer readonly) deve comunque poter cessare → usa `app-escape`
- ❌ **`statiTransizionabili` con stato terminale come destinazione senza dialog**: se manca il dialog, la chiamata cambia_stato senza valido_al lascia validità aperta

---

## Responsive

| Breakpoint | Dispositivo | Comportamento                                                                                                      |
| ---------- | ----------- | ------------------------------------------------------------------------------------------------------------------ |
| >= 1024px  | Desktop     | Layout completo: sidebar inline, tutti i filtri visibili, azioni di riga inline                                    |
| 768-1023px | Tablet      | Pulsanti azione solo icona + tooltip, **filtri nel drawer dal basso** (`FiltriLista`), azioni di riga in kebab `⋮` |
| < 768px    | Mobile      | Sidebar overlay, padding ridotto, **filtri nel drawer dal basso**, azioni di riga in kebab `⋮`                     |

**Due tipi di soglia, e non si confondono** (decisione Tid, 2026-09-26):

| Dipende da | Si scrive | Soglie | Dove |
| --- | --- | --- | --- |
| la **finestra** (sidebar, topbar, layout di pagina) | `@media` | **solo** quelle di `BREAKPOINTS`, in forma canonica: `max-width: <B − 0.02>px` («sotto B», perché `BREAKPOINTS.X` si legge `< X`) e `min-width: <B>px` | anche nel componente scoped |
| il **riquadro** in cui il contenuto vive (drawer, dialog) | `@container` | libere, scritte accanto alla regola | `main.css` o componente |

Il riquadro è il contenuto di ogni drawer (`.p-drawer-content`) e di ogni
`AppDialog` (classe `app-riquadro`, passata via `pt`): hanno una larghezza
fissa (`DRAWER_WIDTH` / `DIALOG_WIDTH`) e per questo possono portare la
containment senza collassare. Una griglia di form si stringe perché si
stringe il drawer, non la finestra.

Presidio: `npm run guards` → `check-media-soglie.mjs` legge `BREAKPOINTS` da
`constants.js` e rifiuta ogni larghezza di `@media` che non ne sia una. Le
query senza larghezza (`hover`, `pointer`, `prefers-reduced-motion`) sono
libere. 🔴 Fino al 2026-09-26 la regola era «nessun `@media` nei componenti»,
e il difetto vero le passava accanto: `max-width: 1024px` e `768px` in cinque
componenti, contro `1023.98px` e `767.98px` del resto — alla finestra larga
esattamente 1024px la topbar si credeva tablet e la pagina desktop.
Il breakpoint mobile e' gestito dallo store `ui.js` (`isMobile`, `isTablet`).

Le azioni di riga (`RowActionsMenu`) usano in aggiunta `@media (hover: none)` per
intercettare i dispositivi touch indipendentemente dalla larghezza del viewport
(es. iPad Pro in landscape rende comunque il kebab perche' manca l'hover).

> ✅ **Una sola definizione di «modalità compatta» — `ui.isCompatto`, dal
> 2026-09-22** ([brief](../work-done/brief-fe-filtri-lista-su-schermo-compatto.md) §3.3):
> larghezza sotto `BREAKPOINTS.TABLET` **oppure** `matchMedia('(hover: none)')`.
> La legge chi cambia **forma** e non solo dimensione — oggi `FiltriLista`.
> ⛔ **La larghezza da sola non basta**: un iPad Pro in orizzontale è largo
> 1366px e non ha hover, quindi `isDesktop` direbbe «desktop» mentre le azioni
> di riga si sono già compresse — una schermata mezza compatta e mezza no.
> ⚠️ Il `@media (hover: none), (max-width: 1023.98px)` di `main.css` (azioni di
> riga, barra azioni) **cita** la stessa soglia e non ne inventa una seconda:
> `1023.98px` perché `BREAKPOINTS.TABLET` si legge come `< 1024` — un
> `max-width: 1024px` includerebbe 1024, cioè farebbe divergere le due sedi
> esattamente sul confine.

---

## Login

La schermata di login e' l'unica pagina senza sidebar e topbar.

- Centrata verticalmente e orizzontalmente
- Logo ZeroERP in cima
- Form con campi: **Username** e **Password**
- Pulsante **Accedi** (larghezza piena del form)
- Messaggio di errore inline (non toast)
- Nessun link "Registrati" — accesso solo su invito
- **Secondo passo** (dal 2026-10-02): col secondo fattore attivo la password porta
  una sfida e la stessa scheda chiede il codice dell'app, con «usa un codice di
  recupero» e il ritorno alla password. Una sfida scaduta riporta alla password
  col suo messaggio. La pagina **«Sicurezza dell'accesso»** (`/sicurezza`, fuori
  dal layout come il cambio password) configura il secondo fattore: il QR è un
  `<img>` col data URI che dà il backend, **mai** markup del server con `v-html`

---

## Conferma azioni distruttive

Qualsiasi azione irreversibile richiede un **dialog di conferma** centrato:

- **Titolo obbligatorio** (`header`), e il titolo è **il nome dell'azione che
  l'ha aperto**: l'operatore legge la stessa parola sul pulsante e sulla dialog
  (`azione_push_commessa` → «Invia a commessa», `rinuncia_riapri` → «Annulla la
  dichiarazione»). Per le eliminazioni `confirm.delete_title`; per i cambi di
  stato guidati dalle azioni BE `confirm.cambio_stato_title`, uguale in tutti i
  domini. ⛔ Una conferma senza `header` è la «X a sinistra» vista in-app il
  2026-09-18: PrimeVue rende la riga di testa anche vuota, e l'unico figlio
  finisce a sinistra. Presidio: `check-dialog-chrome.mjs` rifiuta ogni
  `confirmAction({...})` senza `header` — e ogni `title:`, che è la chiave
  **sbagliata**: fino al 2026-09-18 il composable leggeva `title` mentre
  `AppDialog` e PrimeVue dicono `header`, e **sette** chiamanti avevano scritto
  `header` (ignorato in silenzio: JS non avvisa su una chiave sconosciuta). Uno
  l'aveva persino scoperto e annotato sul sito invece di correggere la sorgente
- Due pulsanti: **Annulla** (secondario, icona ←) e **Conferma** (primario, icona
  ✓; rosso per distruttive)
- **Niente X** (stessa regola di `AppDialog`, §«Chrome»); **ESC = Annulla**
  (direzione sicura, resta aperta da tastiera); **clic fuori non chiude**.
  ⚠️ Fino al 2026-09-18 questa riga diceva «né con ESC», ma ESC chiudeva da
  sempre: la doc descriveva un comportamento che non c'era
- Gestito da `useConfirmAction()` — mai creare ConfirmDialog custom. Il composable
  applica già le icone standard (`acceptIcon`/`rejectIcon`) e il colore danger
  (`confirmDelete`, o `confirmAction({ danger: true })`) in **un solo punto**
  (`richiedi`): le tre funzioni pubbliche aggiungono solo ciò che le distingue.
  ⚠️ `closable` **non è un'opzione di `confirm.require`** (PrimeVue non la
  inoltra al `Dialog`): sta sul tag `<ConfirmDialog>` in `App.vue`, letto da
  `DIALOG_CHROME` — è l'unico pezzo di chrome che non può vivere nel composable

**Quando `useConfirmAction` e quando `AppDialog`:**

| Caso | Componente |
| --- | --- |
| Solo conferma sì/no di un'azione (nessun campo da compilare) | `useConfirmAction()` |
| Dialog con un corpo: campi form, scelta formato, tabella, motivazione | `AppDialog` (vedi §"Componente `AppDialog`") |

Mai un `<Dialog>` PrimeVue grezzo con `<template #footer>` hand-rolled: o è una
conferma (`useConfirmAction`) o è un form/azione con corpo (`AppDialog`).

---

## Notifiche

| Tipo                             | Componente | Posizione      | Durata (`TOAST_DURATION`)                  |
| -------------------------------- | ---------- | -------------- | ------------------------------------------ |
| Successo                         | Toast      | Alto a destra  | 3 secondi (`SUCCESS`)                      |
| Informativo                      | Toast      | Alto a destra  | 3 secondi (`INFO`)                         |
| Avviso                           | Toast      | Alto a destra  | 4 secondi (`WARN`)                         |
| Errore operativo                 | Toast      | Alto a destra  | 5 secondi (`ERROR`)                        |
| Errore operativo con soluzione   | Toast      | Alto a destra  | 9 secondi (`ERROR_CON_SOLUZIONE`)          |
| Errore con azioni (pulsanti)     | Toast      | Alto a destra  | Persistente, chiusura manuale (`AZIONI`)   |
| Errore validazione               | Inline     | Sotto il campo | Fino a correzione                          |
| Errore di sistema                | Toast      | Alto a destra  | Persistente, chiusura manuale (`SYSTEM_ERROR`) |

Le durate vivono in `TOAST_DURATION` (`core/constants.js`): se questa tabella e
il codice dissentono, vale il codice.

Gestiti da `useNotify()` — mai usare `useToast()` direttamente.
Testo sempre in italiano, chiaro e specifico — mai "Errore" o "OK".

---

## Multilingua

### Regola fondamentale

**Nessun testo visibile all'utente viene scritto nei componenti.**

```html
<!-- NO --> <Button label="Salva" />
<!-- SI --> <Button :label="$t('common.save')" />
```

### Struttura chiavi — radici dei namespace

**La chiave i18n è un contratto fra tre livelli, non una faccenda del solo
frontend.** Il database *emette* l'indirizzo di una traduzione (`label_key`,
`reason_key` nelle capability `script.fn_available_actions_*` e nel `meta` dei
seed `config.transizioni_stati_*`), il backend lo trasporta senza interpretarlo,
il frontend lo risolve. Se l'indirizzo non esiste il frontend **non segnala un
errore: mostra testo mancante** — il difetto è silenzioso e si scopre solo
guardando la schermata. È già costato due difetti in produzione-dev (offerte,
ordini), entrambi da chiavi emesse in una radice inesistente.

**La regola (una sola):**

> Se una stringa appartiene a un modulo che vive in una **cartella d'area** di
> `frontend/src/` (`vendite`, `anagrafiche`, `catalogo`, `amministrazione`,
> `config`, `ui`, `portale`, `shop`, …), il suo indirizzo **parte da
> quell'area**: `vendite.ordini.*`, `anagrafiche.clienti.*`,
> `amministrazione.emittenti_fiscali.*`. Se è **vocabolario trasversale**,
> riusato da più aree o che vive in `core/`, resta in cima: `common.*`,
> `errors.*`, `validation.*`, `nav.*`, `search.*`, `confirm.*`.

Corollari operativi:

- **L'ancora è la cartella del codice, non lo schema DB**: `listini` sta in
  `vendite/`, `clienti` in `anagrafiche/` — l'indirizzo segue il codice.
- **La foglia non ripete l'area**: `amministrazione.emittenti_fiscali`, non
  `amministrazione.amm_emittenti_fiscali`.
- **Niente radici piatte di dominio in cima** (`preventivi.*`, `clienti.*`): sono
  esattamente la forma che ha generato i difetti. Una radice nuova in cima si
  crea solo per vocabolario d'interfaccia trasversale.
- **Vale identica per le chiavi emesse dal DB**: una `reason_key` di un ordine
  deve iniziare per `vendite.ordini.`, non `ordini.`.
- Ogni stringa va aggiunta **in entrambi i file** (`it.json` **e** `en.json`)
  contemporaneamente: la parità è verificata.

**Controllo automatico (obbligatorio prima di toccare chiavi o namespace):**
`python3 scripts/check_i18n_keys.py [--strict-roots]` — rende rumoroso l'errore
silenzioso: chiavi citate ma assenti, chiavi emesse dal DB (capability + seed)
non risolvibili, parità it/en, radici di dominio in cima, e **chiavi definite due
volte nello stesso oggetto**. Va tenuto verde.

⚠️ **Una chiave scritta due volte non è un errore di sintassi**: in JSON è
lecito, e ogni parser tiene l'**ultima** — `JSON.parse` come `json.load`. La
prima è quindi *morta*, senza errori e senza test rossi, e il file mostra una
frase che a video non compare. ⭐ Fa danno quando i consumatori sono **due con
contratti diversi**: il 2026-08-26 `vendite.lotti.numera_esito` era definita due
volte, e la numerazione **di massa** — che passa `{numerati}` — riceveva la frase
del **singolo lotto**, perdendo il conteggio. Un segnaposto che non compare non
si vede.
⛔ E il cancello era **cieco al proprio difetto** fino a quel giorno: faceva
`json.load`, cioè leggeva il dizionario già collassato — guardava il *risultato*
invece del difetto. Ora usa un `object_pairs_hook`, che vede le coppie prima che
si schiaccino. *Un presidio che parsifica il formato eredita la tolleranza del
formato.*

**Procedura di classificazione e inventario** (come si decide dove va una radice
esistente, soglia del 70%, casi «due indirizzi con lo stesso nome»):
[i18n-namespace-radici.md](i18n-namespace-radici.md) — riferimento di dettaglio,
subordinato a questa sezione.

---

## Stili CSS

### Architettura a due livelli

| Livello  | Prefisso  | Fonte       | Ruolo                   |
| -------- | --------- | ----------- | ----------------------- |
| PrimeVue | `--p-*`   | Tema Aura   | Colori base, tipografia |
| ZeroERP  | `--app-*` | `theme.css` | Variabili applicative   |

I componenti usano **solo** `--app-*`. Mai `var(--p-*)` direttamente.

Un `--p-*` usato in piu' punti per la stessa cosa e' un **token non ancora nato**:
il token prende il nome del **significato** (accento, attenzione, dato ereditato
dal soggetto, pannello nello split — vedi il catalogo BB, «Variabili tema»), non
della tinta. ⚠️ Al 2026-09-26 restano circa 60 `var(--p-*)` nei componenti
(`primary-700/500/50`, `yellow-*`, `blue-*`, `surface-200/400`,
`border-radius-sm`…) senza un significato ancora nominato: e' lavoro aperto
(PROJECT_CONTEXT, «Aperto»), e il guard arrivera' quando saranno a zero.

### `theme.css` — personalizzazione visiva

Unico punto di personalizzazione: sidebar, topbar, contenuto, card, drawer, AI widget, transizioni, tipografia.
Importato prima di `main.css` in `main.js`.

### I token neutri e il font — `theme.css` (2026-09-17)

| Token | Punta a | Per |
| --- | --- | --- |
| `--app-font-family` | stack di sistema sans-serif | il `body` (🔴 fino al 17/09 `main.css` scriveva `var(--p-font-family)`, che PrimeVue **non definisce**: dichiarazione invalida, font di default del browser) |
| `--app-surface-bg` | `--p-content-background` | la superficie di un contenuto (ex `--surface-0`) |
| `--app-hover-bg` | `--p-content-hover-background` | riga o voce sotto il mouse (ex `--surface-hover`) |
| `--app-highlight-bg` | `--p-highlight-background` | voce selezionata (ex `--highlight-bg`) |
| `--app-border-color` | `--p-content-border-color` | il bordo neutro (ex `--surface-border`) |
| `--app-border-radius` | `--p-border-radius-md` (6px) | raggi neutri |
| `--app-focus-ring` | `--p-focus-ring-color` | l'anello di fuoco |
| `--app-space-sm` | `0.5rem` | gap e padding piccoli |

⛔ **I nomi della generazione precedente di PrimeVue non esistono più** (`--surface-*`, `--text-color`,
`--highlight-bg`, `--p-info-color`, `--p-font-family`): un `var()` su un nome
assente **annulla l'intera dichiarazione**, non solo il colore — un
`border: 1px solid var(--surface-border)` è un bordo che non c'è. Quelli
trovati il 17/09, quasi tutti negli `<style>` di `pratiche`, sono stati sanati
(catalogo BB, riga `ml-05`). Per i colori semantici (info, warn, danger,
success) i token sono `--app-severity-*`.

### Dark/Light mode

Il tema supporta dark e light mode tramite la classe `.p-dark` su `<html>`.

| Aspetto | Dettaglio |
| --- | --- |
| Selettore | `:root` = dark (default), `:root:not(.p-dark)` = light override |
| Store | `useUiStore().isDark` (ref), `toggleDarkMode()` (toggle + persist) |
| Persistenza | `localStorage` chiave `STORAGE_KEYS.DARK_MODE` |
| Pulsante | Topbar — icona sole (dark) / luna (light), tooltip i18n |
| Variabili | Tutte le `--app-*` in `theme.css` hanno override nel blocco `:root:not(.p-dark)` |

#### Gravità (severity) — il colore come scorciatoia

I token `--app-severity-*` sono il colore con cui l'interfaccia dice **quanto è
grave**, nello stesso vocabolario dei `Tag :severity` di PrimeVue: `danger`,
`warn`, `info`, `success`, `secondary`, più `--app-severity-fill` (quanta tinta
prende uno sfondo acceso ma non invadente). Il BB che li consuma è
[`SelectButtonGravita`](../../../../frontend/src/core/components/SelectButtonGravita.vue).

⚠️ **`warn` è GIALLO e non arancio**, e non è una preferenza estetica: su una
resa **tenue** — un pallino, un chip non selezionato, un bordo — l'arancio si
legge come un rosso spento, e i due livelli che contano di più finiscono per
dare lo stesso segnale proprio dove il colore deve fare da scorciatoia
(rilievo in-app, 2026-08-21). Sui `Tag` a fondo pieno la distinzione regge:
quelli restano i colori di PrimeVue, e questi token governano la resa tenue,
che è l'unica dove il problema esiste.

⚠️ **In light mode scendono di tonalità**: le `-500` nascono per fondi scuri e
su bianco il giallo cede per primo — cedendo, riporterebbe esattamente il
difetto per cui era stato scelto.

**Regola**: nessun componente deve usare direttamente `--p-surface-700/800/900` per sfondi o bordi.
Usare sempre le variabili `--app-*` corrispondenti che si adattano automaticamente al modo attivo.
Per aggiungere un componente theme-aware: definire le variabili in `:root` (dark) e sovrascriverle
in `:root:not(.p-dark)` (light).

### `main.css` — classi utility globali

| Classe               | Scopo                                                     |
| -------------------- | --------------------------------------------------------- |
| `app-page`           | Wrapper root view (flex column, flex:1, overflow:hidden)  |
| `app-page-toolbar`   | Barra filtri + azioni (flex, space-between, wrap)         |
| `app-page-filters`   | Gruppo filtri (flex, wrap, gap)                           |
| `app-page-action`    | Pulsanti azione — responsive: solo icona sotto 1024px     |
| `app-datatable`      | DataTable compatta (font ridotto, padding, stripe, hover) |
| `app-drawer-content` | Wrapper contenuto drawer (gap via `--app-drawer-gap`)     |
| `app-drawer-section` | Separatore sezione nei drawer (bordo da theme.css)        |
| `app-form-footer`    | Footer Annulla/Salva (flex, justify-end). ⚠️ Fino al 2026-09-17 questa riga diceva `app-drawer-footer`, una classe che **non esiste** in nessun foglio: `ResoRigaForm` l'aveva copiata da qui e il suo footer non era allineato a destra. Il nome vero è quello di `FormFooter.vue` |
| `form-grid`          | Contenitore campi form (flex column, gap)                 |
| `form-field`         | Coppia label + input (flex column, gap ridotto)           |
| `form-grid-2col`     | Griglia 2 colonne responsive (1 col < 480px)              |
| `form-field-wide`    | Il campo a **tutta riga** dentro una griglia a 2/3 colonne (`grid-column: 1 / -1`). ⚠️ Usata nei template dal 2026-05, definita solo dal 17/09 |
| `app-tab-content`    | Wrapper contenuto tab per flex height                     |
| `app-text-muted`     | Testo sottotono (`--app-text-muted`): hint sotto i campi, note. ⛔ Non `text-color-secondary`: PrimeFlex non è installato, e fino al 17/09 nemmeno questa regola esisteva — il testo «sottotono» era testo normale |
| `font-bold`          | `font-weight: 600` (globale dal 17/09; prima viveva in uno `<style scoped>` e altrove non faceva niente) |
| `app-mono`           | `font-family: monospace` per un identificativo tecnico (codice, `tx_id`, IBAN). Globale dal 19/09: prima era riscritta in più `<style scoped>`, e in qualche punto come `.font-mono` di PrimeFlex |
| `mt-025`/`mt-05`/`mt-1` · `ml-05`/`mr-05` | Le sole utility di spaziatura. ⛔ `mt-3`, `mb-3`, `w-full`, `flex`, `gap-2`… sono PrimeFlex: non esistono qui e sono state tolte dai template il 17/09 |

⭐ **Una classe che non sta in nessun foglio non fa niente, e non lo dice.**
Prima di dire che una view è finita, il censimento delle classi statiche non
definite deve restare a **zero** (dal 2026-09-17, dopo tre passate: utility
PrimeFlex, variabili CSS della generazione precedente di PrimeVue, identificatori orfani):
`python3 scripts/check_classi_morte.py` (dalla root del repo; stampa l'elenco
e esce 1 se ne trova).

⛔ **E un NOME usato nel template ma non dichiarato nello `<script setup>` è
peggio di una classe morta: non fa niente finché i dati non lo toccano, poi
SOLLEVA.** Il compilatore lo traduce in `_ctx.<nome>` = `undefined`, la build
è verde, e `undefined.QUALCOSA` esplode nel render della prima riga che entra
in quel ramo — Vue svuota il sottoalbero e a video resta una lista bianca,
senza un errore per l'operatore. Successo il 2026-09-17 su `LottiLista.vue`:
`MANAGE_ICONS.ERRORE` (oggi `STATUS_ICONS.ERRORE`) senza import, dal 09/09; la scheda «Lotti del mese» si
rendeva e la scheda «Recuperi» no, perché solo lì c'era un lotto con
`ha_errori_gravi`, e l'etichetta accanto contava correttamente le righe che la
tabella non mostrava. Presidio: `vue/no-undef-properties` in `eslint.config.js`
(`npm run lint`, in CI), acceso quel giorno a zero segnalazioni.

**Nota responsive sotto 1024px**: i pulsanti del `FormFooter` (Annulla,
Chiudi, Salva) collassano automaticamente a icon-only via la classe
`app-form-footer-btn` (stessa logica di `.app-page-action`; ⚠️ fino al 17/09
questa riga scriveva `app-drawer-footer-btn`, che non esiste). Il componente
imposta `v-tooltip.top` con la label per garantire l'accessibilita'. La
modifica e' centralizzata in [`FormFooter.vue`](../../../../frontend/src/core/components/FormFooter.vue):
qualsiasi pulsante Annulla/Salva sparso fuori dal componente NON eredita
questo comportamento — pattern utile per individuare drawer non standard.

### Centralizzazione stile pulsanti (`main.css`)

Lo stile dei pulsanti azione e' centralizzato in `main.css` tramite classi `app-*-btn`.
Nessun componente deve definire colori o hover per pulsanti riga — usare sempre le classi globali.

| Classe | Colore | Scopo |
| --- | --- | --- |
| `app-action-btn` | Blu (`--app-btn-action-*`, dal 2026-08-27) | Azioni generiche nei form ("Aggiungi", "Gestisci" nei drawer) |
| `app-manage-btn` | Blu (info) | Pulsanti "Gestisci" nelle colonne DataTable (apre sub-drawer) |
| `app-delete-btn` | Rosso | Cestino elimina riga (DataTable e card) |
| `app-reload-btn` | Blu (`--app-btn-action-*`, dal 2026-08-27) | Refresh lista nella toolbar |

I pulsanti strutturali (Nuovo, Salva, Annulla) sono centralizzati tramite **componenti Vue**:

| Componente | Scopo |
| --- | --- |
| `PageActionsBar` | Barra azioni pagina/lista — responsive, controllo permessi su action e menu compatto |
| `NewButton` | Pulsante "Nuovo" specializzato legacy/non-toolbar |
| `FormFooter` | Footer Salva/Annulla nei drawer — Ctrl+S, readonly-aware |

### Icone: un nome di significato, in un punto solo

⛔ **Nessuna icona PrimeIcons si scrive a mano** (`'pi pi-...'`, `icon="pi pi-..."`,
`class="pi pi-..."`) fuori da `src/core/constants.js` e `src/core/navigation.js`
(censimento icone per significato, approvato da Tid il 2026-09-27). Il presidio è
[`src/core/icone.spec.js`](../../../../frontend/src/core/icone.spec.js). Fa due
controlli:

- fallisce se un letterale compare altrove;
- fallisce se una costante punta a un glifo che PrimeIcons non ha. Una classe
  inesistente non dà errore: l'icona semplicemente non c'è.

**Il nome dice il significato, non il disegno**: `STAMPA`, `SOSPENDI`, `RIPROVA`,
non `PRINT`, `PAUSE`, `REPLAY`. Due regole ne discendono:

- **due gesti diversi non portano lo stesso segno**. Esempi: `FILTRI` e `RICERCA`;
  `CORREZIONE` e `RIATTIVA`; `BLOCCATO` (fermo) e `VIETATO`/`CLOSE` (lucchetto);
- **lo stesso significato porta un segno solo**. Tutti i «sblocca» sono `SBLOCCA`,
  tutti gli «aggiungi» sono `ADD`.

Una voce che **porta** a una cosa con un'icona sua ripete l'icona della cosa
(`FATTURE`, `SOGGETTO`, `NAV_ICONS.PRATICHE`). Il generico `VAI_A` è solo un
ripiego.

| Gruppo | File | Che cosa |
| --- | --- | --- |
| `MANAGE_ICONS` | `constants.js` | **gesti** (azioni di riga, pulsanti, barre) e concetti di dominio senza voce di menu |
| `STATUS_ICONS` | `constants.js` | **stati ed esiti**, spie che non si cliccano: `VUOTO`, `TUTTO_OK`, `ERRORE`, `ATTESA`, `INFO`, `SI`/`NO`, `BLOCCATO`, `CARICAMENTO`, `VIETATO`, `NON_TROVATO`… |
| `RECAPITO_ICONS` | `constants.js` | icone di **campo** di una scheda (email, telefono, PEC, BIC) |
| `NAV_ICONS` | `navigation.js` | le **porte** dell'app (voci di menu, domini), con il nome della voce |
| `TIPO_RUOLO_ICONS` | `navigation.js` | il tipo di ruolo del soggetto; le chiavi sono i codici che arrivano dal BE |

```html
<!-- Pattern standard -->
<Button :icon="MANAGE_ICONS.CONTATTI" text rounded size="small" class="app-manage-btn"
  v-tooltip.bottom="t('contatto.gestisci_contatti')" @click.stop="emit('contatti', data)" />
<!-- Classe statica + icona: la classe resta statica, l'icona va in :class -->
<i class="percorso-handler" :class="STATUS_ICONS.AUTOMATICO" />
```

**Icona nuova**:

1. Si cerca il **significato** fra le chiavi e i loro commenti, non il disegno.
2. Se il significato manca, si aggiunge una chiave nel gruppo giusto. Il commento
   dice che cosa significa e da quale chiave vicina si distingue (`⛔ Non ...`).
3. Il glifo non dev'essere già usato da un'altra chiave con un significato diverso.

⚠️ **Le icone che arrivano dal DB** (`meta.icon` delle azioni disponibili dei
documenti) oggi sono glifi, non significati. Sono l'unica eccezione dichiarata nel
test, in attesa del brief DB.

Il colore resta responsabilita' della classe CSS standard (`app-manage-btn`,
`app-delete-btn`, ecc.). Per cambiare il colore di tutte le icone gestione si
modifica `.app-manage-btn` in `main.css`.

#### Pattern toggle dinamico: `EXPAND` / `COLLAPSE`

Per accordion, expansion row di DataTable, tree e qualsiasi azione che apre/chiude
contenuto, usare la coppia dinamica `MANAGE_ICONS.EXPAND` (`pi pi-chevron-down`,
stato collassato — invita ad aprire) e `MANAGE_ICONS.COLLAPSE` (`pi pi-chevron-up`,
stato espanso — invita a chiudere). Standard PrimeVue/Material allineato.

**Eccezione — expansion row di DataTable** (2026-09-27): il toggler di riga
PrimeVue usa `chevron-right` (chiusa) / `chevron-down` (aperta). Il toggle
«espandi tutte» della lista usa la **stessa** coppia, `MANAGE_ICONS.ROW_EXPAND` /
`MANAGE_ICONS.ROW_COLLAPSE`, così riga e lista portano lo stesso segno. Stessa
coppia per i gruppi annidati della sidebar (a sidebar chiusa, `ROW_EXPAND`
accanto all'icona del gruppo segnala che dentro ci sono altre voci) e per i toggler di riga scritti a mano
nei drawer (`isExpanded(data) ? ROW_COLLAPSE : ROW_EXPAND`). ⛔ Mai il glifo
`pi pi-chevron-*` cablato per un toggle di espansione.
`EXPAND`/`COLLAPSE` restano per accordion, pannelli e tree.

⛔ **Su una `<ListaConfigurabile>` il toggle «espandi tutte» NON si scrive in
pagina** (2026-09-18): è l'azione standard di `useListaAzioni`, accanto a
«Personalizza colonne» ed «Esporta», e compare da sé solo quando c'è qualcosa
da espandere (colonne ritirate o dettaglio inline). L'esempio qui sotto vale per
le superfici che non sono liste configurabili. I listini avevano il proprio
`toggle-all-versioni`: era la prima copia, ritirata alla seconda.

```js
// In toolbar globale (PageActionsBar) — toggle di tutte le righe
{
  key: 'toggle-all',
  kind: 'utility',
  label: allExpanded.value ? t('common.comprimi_tutte') : t('common.espandi_tutte'),
  icon: allExpanded.value ? MANAGE_ICONS.COLLAPSE : MANAGE_ICONS.EXPAND,
  command: toggleAll,
}

// In azione di riga (RowActionsMenu) — toggle di una singola riga
{
  key: 'toggle-row',
  // ⚠️ `common.*` non ha una coppia per la singola riga: le chiavi sono di
  //    dominio (es. `pratiche.percorso_comprimi` / `pratiche.percorso_espandi`)
  label: expanded[row.id] ? t('<dominio>.comprimi_riga') : t('<dominio>.espandi_riga'),
  icon: expanded[row.id] ? MANAGE_ICONS.COLLAPSE : MANAGE_ICONS.EXPAND,
  command: () => toggle(row),
}
```

**Regole**:

- Sempre dinamico (`isExpanded ? COLLAPSE : EXPAND`). Mai una sola icona statica
  per un toggle: l'utente perderebbe il feedback dello stato corrente.
- Non confondere `EXPAND`/`COLLAPSE` con `RELOAD` (`pi pi-refresh`): l'icona
  precedente `pi pi-history` era stata scelta per "cronologia versioni" ma in
  ruolo toggle veniva scambiata per refresh. Tenere `MANAGE_ICONS.VERSIONI`
  (`pi pi-history`) solo per uso decorativo dove rappresenta cronologia
  (es. header dell'expansion che mostra "Versioni storiche"), mai per toggle.

**Colonna azioni di riga** (pattern standard): i pulsanti `app-manage-btn` non si mettono piu'
direttamente in un `<template #body>` del `<Column>`. Usare sempre il building block
`RowActionsMenu` — gestisce automaticamente lo switch desktop inline / tablet kebab
tramite CSS, e accetta un array di azioni dichiarativo. Vedi sezione "Colonna azioni di riga"
nel pattern lista per l'API completa.

Per l'inventario completo di classi CSS, pulsanti e componenti, consultare il
[Catalogo Building Block Frontend](catalogo-building-block-frontend.md).

### Glifo vs controllo — icone decorative/indicative

Non tutte le icone sono pulsanti. Un'icona **decorativa/indicativa** (una freccia
di direzione, un `↩` di ramo, il glifo accanto a un titolo di sezione) **non deve
mai sembrare cliccabile**; un'icona **azione** deve esserlo senza ambiguità. La
distinzione si gioca sul **chrome, non sulla tinta**.

| | Icona **azione** (controllo) | Icona **glifo** (decorativa) |
| --- | --- | --- |
| Hit-area (padding/box) | sì | **no** — inline nel flusso |
| Hover | sì | **no** |
| `cursor` | `pointer` | `default` |
| Colore | **semantico saturo** via classe `app-*-btn` (blu azione e gestisci / rosso distruttivo / arancio cautela) | `--app-text-muted` |

**Regole**:

- **Il colore non è l'affordance principale: lo è il chrome.** Un glifo senza
  hit-area, senza hover e con `cursor: default` non viene letto come pulsante
  qualunque sia la sua tinta.
- **Mai un colore nuovo** (teal, viola, ecc.) per dire "non sono cliccabile":
  nella palette il colore È semantica, un 6° colore sarebbe l'unico senza
  significato e, per essere distinguibile, dovrebbe essere saturo → *avanza*
  invece di *arretrare*. Pacchiano per costruzione.
- **Mai uno sfondo/chip** per un glifo: è il segnale più forte di "sono un
  bottone" — l'opposto dell'obiettivo.
- Per il glifo usare `--app-text-muted` (arretra). **Attenzione**: ha lo stesso
  valore di `--app-btn-disabled-color`, quindi *da solo* direbbe "bottone
  disabilitato" — è il **chrome assente** a chiarire che è decorativo. La
  differenza `--app-text-color` vs `--app-text-muted` su un glifo piccolo
  (≈0.8rem) è impercettibile: non usarla come leva.
- **`opacity` non è un segnale semantico.** Non usarla per "attenuare" un
  elemento: si **somma** ai veli dei contenitori (es. `.app-readonly` a `0.85`
  nei drawer post-DRAFT → `0.85 × 0.75 ≈ 0.64`, area illeggibile) e smorza anche
  i **dati veri** dentro la riga (codici, Tag stato). Se un ramo/stato va
  segnalato, farlo con icona + label esplicita, non con `opacity`.

Primo consumatore: `LineagePassaggiContenuto` (corpo "Passaggi", in dialog dai
chip di `DocumentoCollegamentiBar`) — frecce direzione e `↩` ramo inverso come
glifi muted.

### ⭐ Dove vive il NOME di un'icona — la regola del 2 applicata al significato

> Decisa con Tid il **2026-09-02**, dopo che una revisione aveva proposto di
> portare **tutte** le icone scritte a mano dentro `MANAGE_ICONS`.

Le due sezioni sopra dicono *com'è fatta* un'icona (glifo o controllo) e *quali*
icone sono composite (le entità di dominio). Restava senza risposta la terza
domanda, ed è quella che si pone chi scrive una cella: **il nome dell'icona lo
scrivo sul posto o lo metto in una costante?**

**La regola, e non è nuova — è la regola del 2, applicata al *significato*:**

> Un'icona che porta un **senso ripetuto in più di un punto** è un **concetto**:
> va in `MANAGE_ICONS` e i consumatori la referenziano.
> Un'icona usata **una volta sola**, decorativa, resta **letterale sul posto**.

⛔ **La regola generale «ogni icona da `MANAGE_ICONS`» è stata VALUTATA E
RIFIUTATA**, e non per il costo delle modifiche — per il merito. Una costante
serve a dare un nome a un concetto: darlo a un glifo con **un solo lettore**
obbliga chi legge la pagina ad aprire un altro file per sapere cosa mostra, e
produce un nome che deriva dal suo unico uso alla prima modifica. *Una costante
con un consumatore solo non centralizza niente: sposta.*

⭐ **E il rischio vero non è la centralizzazione, è la DIVERGENZA DI
SIGNIFICATO.** Se «bloccato» si scrive a mano in sei punti, sei punti possono
derivare a sei icone diverse **per lo stesso stato** — e quello è un difetto che
l'operatore vede, che nessun test prende e che nessuno attribuisce alla causa.
È questo che la costante previene, non il numero di righe.

**Come si applica, in una domanda:**

| Chiedersi | Se sì | Se no |
| --- | --- | --- |
| «Questa icona dice una cosa che l'applicazione dice **anche altrove**?» | concetto → `MANAGE_ICONS`, e si sistemano **tutte** le occorrenze di quel senso | letterale sul posto |

⚠️ **Il criterio è il SENSO, non la stringa.** Due `pi pi-check` che significano
cose diverse (una «riga valida», l'altra «preset di default») sono **due** casi
da una volta, non un concetto da due: unirli sotto una costante sola creerebbe
un legame falso, e il giorno in cui una delle due cambia icona cambierebbe anche
l'altra.

⚠️ **E vale nei due versi**: una costante in `MANAGE_ICONS` che è rimasta con un
consumatore solo va **riportata sul posto**, non tenuta per simmetria.

**Come si misura il perimetro** (la misura trova i candidati, non decide la
regola — che reggerebbe identica con qualunque numero):

```bash
cd frontend
# icone scritte a mano nei template
grep -rho 'class="pi pi-[a-z0-9-]*"' src --include=*.vue | sort | uniq -c | sort -rn
# quante passano gia' dalla costante
grep -rho 'MANAGE_ICONS\.[A-Z_]*' src --include=*.vue --include=*.js | wc -l
```

Le icone usate una volta sola non sono candidate per costruzione; il perimetro
da guardare sono le **ripetute**, e solo quelle in cui la ripetizione è davvero
lo stesso senso.

⛔ **Non è una campagna da fare in un colpo.** Si consuma come l'inventario delle
liste: quando si tocca un file per altri motivi, e partendo dai sensi più
ripetuti.

### Iconografia di dominio — base documento + overlay-tipo

Le icone delle entità vendite (preventivi, offerte, ordini, ddt, resi,
contratti, fatture) sono **icone composite** definite in `main.css` come
`.app-nav-icon-<entita>` con due pseudo-elementi, e referenziate da `NAV_ICONS`
(`navigation.js`), **non** da PrimeIcons singole.

**Il principio** (deciso con Tid 2026-07-09): nessun glifo "si spiega da solo"
per un nome proprio (un `calculator` significa "calcolo" ovunque, non
"preventivo"). Il riconoscimento nasce da **famiglia coerente, differenziatore
ed etichetta** (l'icona ha sempre label o tooltip accanto). Quindi:

- **`::before` = base documento** (`pi-file` `\e958`) → il **marcatore di
  famiglia/area**: "questo è un documento vendite" (mai un glifo generico che
  potrebbe significare altro).
- **`::after` = overlay del TIPO** → il **differenziatore**, grande, dentro
  l'angolo in basso a destra del foglio, che è **aperto** come quello di
  `pi-file-edit` (Tid 2026-09-27; lo si ottiene ritagliando `pi-file` con
  `clip-path`, perché il font non ha un foglio aperto senza simbolo proprio).
  ⭐ Misure di base e simbolo in **una regola sola** per tutta la famiglia, in
  `main.css`: ogni documento dichiara solo il `content` del suo `::after`.

| Entità | Overlay | Glifo |
| --- | --- | --- |
| Preventivo | matita (bozza/proposta) | `pi-pencil` `\e942` |
| Offerta | tag (offerta commerciale) | `pi-tag` `\e95e` |
| Ordine | carrello | `pi-shopping-cart` `\e980` |
| DDT | camion (trasporto) | `pi-truck` `\ea00` |
| Reso | freccia-ritorno | `pi-arrow-circle-left` `\e91f` |
| Contratto | verificato (vincolante) | `pi-verified` `\ea02` |
| Fattura | euro (documento fiscale) | `pi-euro` `\e9bd` |

**Regole**:

- **L'overlay deve VARIARE per tipo, non essere condiviso.** L'errore da evitare
  (corretto qui): mettere lo **stesso** badge (l'euro) su tutte le entità a
  valore → il pezzo comune domina la lettura e le icone si assomigliano. Il
  pezzo che varia (l'overlay) è quello che deve distinguere; l'**euro resta solo
  su Fattura**, dove finalmente significa qualcosa di specifico.
  ⚠️ La regola vale **dentro la famiglia documento** (base `\e958`): su un'altra
  base l'euro è un altro segno. Listini e approvazioni prezzo lo portano come
  «prezzo», su basi proprie, e non collidono. La Fattura ha la base foglio
  **dal 2026-09-26** (decisione Tid): prima usava la ricevuta `\ea06`, la
  stessa di Clienti, e usciva dalla sua famiglia.
- **Due elementi, non tre.** Base (famiglia) + overlay (tipo). Non aggiungere un
  terzo marcatore "area": la base È già l'area → sarebbe solo ingombrante.
- **Niente collisioni di dominio/azione**: l'icona del dominio Vendite è il
  carrello **intero** (`pi-shopping-cart` pieno) → l'ordine usa il carrello come
  **badge** su documento, non collide. Mai `pi-replay`/`pi-refresh` per i Resi
  (si leggono come "ricarica").
- Nuova entità vendite: aggiungere `.app-nav-icon-<entita>` ai due selettori
  della regola di famiglia in `main.css`, più il suo `::after` con il solo
  `content` dell'overlay-tipo, e la chiave in `NAV_ICONS`. Mai una PrimeIcon
  singola generica. `icone.spec.js` fallisce se una classe composta delle
  costanti non ha le sue regole in `main.css`.

### Regole CSS per i componenti

- Sempre `<style scoped>` — mai globale (eccetto `main.css`)
- `:deep()` solo per override PrimeVue, mai per componenti custom
- **Nessun CSS scoped per layout form** — usare classi `main.css`
- Se serve un nuovo pattern layout, aggiungerlo a `main.css` come classe globale
- Mai hardcodare colori — usare variabili `--app-*`
- **Pulsanti riga**: usare le classi `app-*-btn` centralizzate, mai `severity` inline per edit/delete

---

## Sicurezza

### Autenticazione JWT

⛔ **Nessun token in `localStorage`** (dal 2026-09-28, [brief sicurezza](../work-done/brief-be-fe-sicurezza-header-token-mfa.md) §2).
Il **refresh** sta in un cookie `HttpOnly` che il JavaScript non vede: lo
scrivono e lo leggono il backend e il browser. L'**access** (10 minuti) vive solo
in memoria, in `core/sessione.js`. Al ricaricamento della pagina l'access non
c'è mai: la sessione si ritrova rinnovando dal cookie.

| Meccanismo            | Dove                                   | Descrizione                                                                           |
| --------------------- | -------------------------------------- | ------------------------------------------------------------------------------------- |
| Access in memoria     | `core/sessione.js`                     | Unica sede dell'access; reattivo (`accessTokenRef`)                                   |
| Route guard           | `router/index.js`                      | Rotte protette di default; `auth.ripristinaSessione()` prima di ogni rotta            |
| Rinnovo               | `core/api.js` `rinnovaAccess`          | Corpo vuoto + header `X-Requested-With`; il cookie lo porta il browser                |
| Una scheda alla volta | `core/sessione.js` `rinnovaCoordinato` | Lock del browser + `BroadcastChannel`: rinnova una scheda, le altre ricevono l'access |
| Accodamento           | `core/sessione.js`                     | Chiamate concorrenti della stessa scheda aspettano la stessa promise                  |
| Protezione loop       | `core/api.js`                          | Chiamate a `/token/` escluse dal rinnovo                                              |
| Redirect              | `LoginView`                            | Rotta originale salvata in `?redirect=`                                               |
| Obblighi              | `router/index.js`                      | Cambio password, poi secondo fattore: dal profilo (`obblighi_pendenti`), nell'ordine del cancello del backend |
| Motivo del ritorno    | `core/sessione.js` `MOTIVO_USCITA`     | `?reason=`: sessione scaduta o logout da un'altra scheda, ognuno con la sua frase     |
| Logout                | `stores/auth.js`                       | Backend cancella il cookie; `clearTokens()` pulisce; le altre schede escono           |

⭐ **Più schede.** Ogni rinnovo ruota il refresh e mette in blacklist il
precedente: due schede che rinnovano insieme presenterebbero lo stesso cookie,
e la seconda verrebbe buttata fuori. Il rinnovo gira quindi dentro un lock
(`navigator.locks`): una scheda alla volta, e il cookie (condiviso) è già
quello ruotato da chi è uscito dal lock. L'access nuovo si annuncia sul canale
`zeroerp-sessione`. Gli altri due eventi — **logout** (tutte le schede escono)
e **sessione nuova** (login o cambio emittente in un'altra scheda: questa
riparte dal boot) — li gestisce lo store `auth`. ⛔ Nessun altro modulo chiama
l'endpoint di refresh: passa da `rinnovaAccess`, altrimenti il coordinamento ha
un buco.

### Regole di sicurezza

- Mai accedere a `localStorage` direttamente — passa da `core/storage.js`; e
  ⛔ mai un token lì dentro
- Mai `window.location` per redirect — usare il router. ⭐ **Una sola eccezione
  dichiarata, e non è un redirect**: l'azione `ripartiDalBoot` di
  `stores/auth.js` fa `window.location.assign(...)` per **ripartire dal boot**.
  La usano due casi con la stessa esigenza: `cambiaEmittenteAttivo` (cambiare
  emittente cambia ciò che si vede ovunque) e l'apertura di una **sessione
  nuova in un'altra scheda** (login o cambio emittente: il cookie ora è di
  un'altra sessione). L'applicazione tiene stato in cache fuori dagli store
  (KeepAlive delle viste, cache di modulo dei lookup): solo un ricaricamento
  completo garantisce che non restino a video dati della sessione precedente.
  Un terzo caso passa dalla stessa azione, non scrive un secondo
  `window.location`
- Mai esporre dati sensibili in log, template o attributi HTML
- Mai costruire URL con interpolazione da input utente — usare parametri Axios

---

## Gestione errori API

I componenti **non gestiscono errori manualmente**. Il composable `useApiHandler` intercetta, estrae il messaggio dall'envelope backend e mostra il toast.

⛔ **L'interceptor axios di `core/api.js` non mostra toast** (rinnova il token, porta agli
obblighi pendenti). Un `try/catch` col `catch` vuoto «gestito dall'interceptor» inghiotte
l'errore: il 2026-10-23 ne sono stati corretti quattordici. `execute` accetta anche l'azione di uno
store, che restituisce il dato già estratto; un'azione che non restituisce niente dà `undefined`
al successo e `null` sull'errore.

```js
// Caricamento (toast solo su errore) — la funzione viene dal modulo api/
const data = await execute(() => listConfigRecords(rel, params))

// Salvataggio (toast su successo e errore)
const result = await execute(
  () => store.create(payload),
  { successMessage: t('notifications.save_success') }
)

// Polling silenzioso (nessun toast)
const sessioni = await execute(() => listSessioni(), { silent: true })
```

### ⭐ Campi in errore dal backend — `campiErrati` (dal 2026-08-08)

Quando il backend sa **quale campo** l'operatore deve correggere, lo dice:
l'envelope d'errore porta `error.fields`, un array di **nomi** (mai i valori —
vedi [api.md §Envelope risposte](../api.md)). `useApiHandler` li espone gia'
pronti da legare agli input:

```js
const { execute, loading, campiErrati } = useApiHandler()
```

```vue
<InputText v-model="form.codice" :invalid="campiErrati.includes('codice')" />
```

**Non sostituisce la validazione client**, la completa: `canSave` copre le
regole che il frontend conosce (obbligatorieta', formato), `campiErrati` copre
**quelle che stanno nel service** — unicita', coerenza fra entita', vincoli di
stato. Prima l'operatore leggeva «Campo 'ordinamento' non valido» nel toast e
doveva cercarselo da solo nel form.

| Regola | Perche' |
|---|---|
| si azzera a ogni `execute` | descrive l'**ultimo** errore, non la storia del drawer. Il campo resta rosso finche' non si riprova a salvare |
| si legge anche in `silent` | il chiamante puo' voler evidenziare senza toast |
| nessun messaggio sotto il campo | il testo sta gia' nel toast; ripeterlo sotto l'input e' rumore. Il bordo rosso dice *dove*, il toast dice *cosa* |
| il nome e' quello del **payload API**, non del `v-model` | se il form rinomina un campo, il legame va scritto a mano — `:invalid="campiErrati.includes('nome_api')"` |

**È lo standard, non un caso isolato**: dal 2026-08-08 i drawer lo legano. La regola per un drawer nuovo: se un campo del form ha lo
stesso nome della chiave che mandi nel payload, legalo — costa una riga e il
giorno in cui il service comincia a rifiutarlo l'operatore vede dove.

⚠️ **Non si lega tutto**: la lista dei nomi che il backend può davvero mandare è
finita (si ricava dai `context={"field": …}` e dalle chiavi passate ai
validator). Legare un campo fuori da quella lista non fa danno ma non fa niente:
è una riga che non decide.

✅ **Dal 2026-08-24 lo popolano anche gli errori nati in PL/pgSQL**, e la storia
merita una riga perché è un difetto che si vedeva solo dal lato che riceve. Il
canale del database (`RAISE … USING COLUMN`) viaggiava dall'08/08 ed era
valorizzato da quasi tutti i punti di sollevamento — ma il backend lo perdeva
**appena un service traduceva l'errore**, cioè quasi sempre. Il nome arrivava
all'envelope da una strada su cinque, e a video non si illuminava niente.
Ora la lettura è una sola (`diagnostica_db`) e il campo viaggia fino in fondo:
vedi [api.md §I cinque punti di traduzione](../api.md).

### ⭐ Il bersaglio dell'errore — `bersagli` (dal 2026-08-24)

`campiErrati` dice **quale campo correggere** nella pagina dove l'operatore già
si trova. Il **bersaglio** dice **a quale altra cosa deve andare** — ed è la
differenza fra evidenziare un input e disegnare un **gesto**.

```
messaggio:  «Non si può numerare il documento 835: la fattura che
             rettifica non è ancora numerata (documento 820).»
gesto:      [ Apri Fattura 820 ]
```

⭐ **Perché esiste**: all'operatore non serve il *nome* del record, gli serve
**arrivarci**. Un identificativo dentro una frase, per quanto umano, resta una
cosa da ricopiare a mano in un campo di ricerca.

**Non c'è niente da scrivere nei componenti.** Il gesto lo compone
`useApiHandler` e lo consegna al toast: tutti i file che usano `execute` lo
hanno già.

```js
// Serve solo a chi ha una superficie PROPRIA dove metterlo.
const { execute, bersagli } = useApiHandler()
```

| Regola | Perché |
|---|---|
| il toast con un gesto è **persistente** | un pulsante che sparisce dopo cinque secondi non è un gesto. `life: 0`, come `systemError` |
| bersaglio irraggiungibile → **nessun pulsante** | è un'**offerta**, non una promessa: permessi, area bloccata, tipo senza destinazione. Il messaggio si mostra lo stesso. ⛔ Mai un pulsante che porta in un vicolo cieco |
| mai su un errore **tecnico** | su un 500 l'operatore non ha niente da fare. Lo toglie il backend, in `_apply_policy` |
| al massimo **cinque** | oltre, non è più un gesto ma un elenco — e *quanti* sono lo dice già la frase |

**Le tre superfici, e il resolver è uno solo:**

| Da dove arriva l'errore | Chi disegna il gesto |
|---|---|
| envelope `error.targets` (una chiamata fallita) | il **toast**, via `useApiHandler` — automatico |
| `errore.targets` dentro un **200** del runner di pipeline | `useLottoAzioni`, stesso toast |
| `errore_bersagli` di una riga (giro **asincrono**, errore persistito) | `ErroreRigaInfo`, il popover dell'icona di riga |

⚠️ **Un resolver solo — `core/bersagli.js` — per tutte e tre.** Se divergessero,
lo stesso errore direbbe due cose diverse a seconda di come è arrivato a video.

⭐ **E la terza riga è quella che conta di più.** Un giro di fatturazione può
partire da solo — worker, batch notturno — e fallire quando davanti allo schermo
non c'è nessuno: chi legge quell'errore lo legge **ore dopo**, dall'icona di
riga. Il toast è il caso facile.

**Aggiungere un tipo raggiungibile** = una riga in `DESTINAZIONI`
(`core/bersagli.js`) più la sua etichetta `config.tipi_entita.<codice>` in
`it.json`/`en.json`. ⚠️ L'indirizzo i18n **lo dichiara il database**
(`config.tipi_entita.etichetta_key`): qui si ripete quella chiave, non se ne
inventa una — è lo stesso patto dei tre livelli già descritto sopra.

⚠️ **Oggi `TASK_RUN` non è raggiungibile**, ed è deliberato: è a catalogo perché
serve al giornale degli eventi, e nessuna schermata mostra un giro per id.

### ⭐ La soluzione — `hint`, cioè cosa fare adesso (dal 2026-09-09)

`campiErrati` dice **quale campo** correggere, il bersaglio dice **a quale altra
cosa** andare. La **soluzione** dice **cosa fare adesso** — ed è la terza metà,
quella che mancava.

```
messaggio:   «Non si può numerare il documento 835: la fattura che
              rettifica non è ancora numerata (documento 820).»
soluzione:   «Numerare prima i documenti che questo rettifica, poi ripetere.»
gesto:       [ Apri Fattura 820 ]
```

⭐ **La frase non la scrive il frontend, e nemmeno il backend**: è la `soluzione`
che il team DB scrive **a catalogo per ogni codice**, quindi è multilingua e
cambia con un seed. Viaggia nell'envelope come `error.hint`.

**Non c'è niente da scrivere nei componenti.** La estrae `useApiHandler` e la
consegna al toast, che la rende **sotto il messaggio** — esattamente come per il
gesto:

```js
// Serve solo a chi ha una superficie PROPRIA dove metterla.
const { execute, soluzione } = useApiHandler()
```

| Regola | Perché |
|---|---|
| va nel **`detail`** del toast, mai concatenata al messaggio | sono due frasi con due ruoli — cosa è successo, cosa fare — e il tema le rende una sotto l'altra con pesi diversi. Unirle produce un periodo unico in cui l'istruzione si perde dentro la diagnosi |
| il toast che la porta dura **di più** (`TOAST_DURATION.ERROR_CON_SOLUZIONE`) | la durata si calibra su **quanto c'è da leggere**, e qui il testo è il doppio. ⛔ Non è persistente come quello col gesto: la soluzione è a catalogo per ogni codice, e `life: 0` farebbe di **ogni** errore di dominio un toast da chiudere a mano |
| su un errore **tecnico** non arriva, e non è il frontend a deciderlo | lo toglie `_apply_policy` sui tre codici in cui il canale `HINT` non porta una soluzione a catalogo ma il testo che PostgreSQL scrive per lo sviluppatore. ⛔ Ri-deciderlo qui sarebbe una **seconda sede** della stessa regola |
| il **rifiuto confermabile** non la mostra, ed è voluto | lì la frase «cosa fare adesso» **è il dialog che sta comparendo** (`useForzaturaConfermata`): ripeterla sotto sarebbe dire due volte la stessa cosa |

⛔ **Chi chiama `notify.error(...)` a mano non ce l'ha**, ed è la stessa
asimmetria che già vale per il gesto: il canale è `execute`, e un secondo
percorso che legge l'envelope per conto proprio è la forma in cui i due
divergono. Se una schermata mostra un errore senza passare da `useApiHandler`,
la domanda da farsi è perché.

---

⚠️ **`ui_action`: un valore su sette, e gli altri sei sono SERVITI.**
`useApiHandler` lo espone come `azioneUi`; l'unico componente che ci ramifica è
`useForzaturaConfermata`, su `confirm_and_retry`. ⭐ **Non è una lacuna, ed è
dichiarato** (decisione di Tid, 2026-09-09): `highlight_form_fields` lo serve
`campiErrati`, `redirect_login` lo serve lo **status 401** in `core/api.js`, e i
restanti quattro li serve il **toast** — che ora porta anche la soluzione e, dove
c'è un bersaglio, il gesto. ⚠️ Prima di dare un comportamento al settimo vanno
rilette le righe di override, decise quando nessuno poteva verificarle a
video. Tabella completa: [api.md §Cosa cambia davvero lo status](../api.md).

---

## Modalita' sola lettura e accesso — pattern "protect"

### Principio

Le autorizzazioni utente prevedono tre livelli di accesso (`TUTTO`, `LETTURA`, `BLOCCATO`) su tre granularita' diverse. Tutti i form e le view devono supportare nativamente le modalita' ridotte senza duplicare componenti o creare varianti separate.

### Piramide permessi

| Livello | Cosa controlla | Trigger FE | Enforcement BE |
| --- | --- | --- | --- |
| **Area** (schema DB) | Accesso all'intero dominio | `useReadonlyMode(schemaDb)` + route guard su `BLOCCATO` | `ZeroERPPermission` via `area_funzionale` |
| **Azione processo** | Singola operazione (es. "genera fatture") | `action` su `PageActionsBar` / `FormFooter` | `permission_codename` sulla view |
| **Oggetto / model** (v2) | Singola entita' dentro un'area | `useReadonlyMode(schemaDb, modelName)` | `model_permission = (app_label, model_name)` sulla view |

### Composable `useReadonlyMode(schemaDb, modelName?)`

Il provider va chiamato nella View (parent della SearchTable e dei drawer). I figli iniettano con `useInjectReadonly()` / `useInjectBlocked()`.

```js
// Livello area (classico)
useReadonlyMode(READONLY_DOMAINS.ANAGRAFICHE)

// Livello oggetto (permessi v2) — richiede model_permission sulla view BE
useReadonlyMode(READONLY_DOMAINS.ANAGRAFICHE, READONLY_MODELS.CLIENTE)
```

Semantica di `isReadonly` / `isBlocked` dopo la risoluzione:

| Contesto | Livello risolto | `isReadonly` | `isBlocked` |
| --- | --- | --- | --- |
| Area | TUTTO | `false` | `false` |
| Area | LETTURA | `true` | `false` |
| Area | BLOCCATO | — (route guard interviene prima) | — |
| Oggetto | TUTTO | `false` | `false` |
| Oggetto | LETTURA | `true` | `false` |
| Oggetto | BLOCCATO | `true` | `true` |

A livello oggetto `BLOCCATO` implica anche `isReadonly` (l'utente non deve poter attivare form o inviare POST).

### Tecnica CSS "pannello protect"

Ispirata al formato protect AS/400: un unico overlay CSS blocca ogni interazione sul contenuto, senza toccare i componenti interni. Non si creano componenti `*ReadOnly.vue` separati.

```css
.app-readonly {
  pointer-events: none;     /* blocca ogni click, hover, focus */
  user-select: text;        /* permetti copia testo */
  opacity: 0.85;            /* feedback visivo: stai consultando */
}
```

Wrap del contenuto:

```vue
<div :class="{ 'app-readonly': isReadonly }">
  <!-- form, DataTable, drawer content — tutto normale -->
</div>
```

### Pattern LISTA — template standard

Ogni SearchTable con permessi livello oggetto segue questo schema:

```vue
<script setup>
import PageActionsBar from '@/core/components/PageActionsBar.vue'
import ReadonlyBadge from '@/core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '@/core/components/AccessoBloccatoPanel.vue'
import { useInjectBlocked } from '@/core/composables/useReadonlyMode'
import { MANAGE_ICONS } from '@/core/constants'
import { computed } from 'vue'

import FiltriLista from '@/core/components/FiltriLista.vue'
import ListaConfigurabile from '@/core/components/ListaConfigurabile.vue'
import { useListaConfigurabilePage } from '@/core/composables/useListaConfigurabilePage'

const isBlocked = useInjectBlocked()
// `pageActions` standard (ricarica, nuovo con `hideWhenReadonly`, …) li compone lo scaffolding
const { searchText, pageActions, perimetroBloccato, listaRef, ... } =
  useListaConfigurabilePage(store, { onNew: () => emit('new'), newTooltipKey: '...' })
</script>

<template>
  <div class="app-tab-content">
    <!-- BLOCCATO: pannello sostitutivo, niente toolbar ne' tabella -->
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
      <div class="app-page-toolbar">
        <FiltriLista :store="store" :inert="perimetroBloccato">
          <template #sempre>
            <InputText v-model="searchText" class="app-filter-w-lg" :placeholder="t('...')" />
          </template>
          <!-- altri filtri, legati con un binder -->
        </FiltriLista>
        <PageActionsBar :actions="pageActions">
          <template #suffix>
            <ReadonlyBadge />
          </template>
        </PageActionsBar>
      </div>
      <ListaConfigurabile ref="listaRef" codice="dominio.entita" ... />
    </template>
  </div>
</template>
```

Modello reale completo: `anagrafiche/components/FornitoriSearchTable.vue`.

**Regole operative liste**:

- ❌ **mai** `<Button icon="pi pi-refresh" ...>` inline — sempre `PageActionsBar`
- ❌ **mai** badge testuale "Sola lettura" custom — sempre `<ReadonlyBadge />`
- ✅ Ordine standard: `PageActionsBar` con `ReadonlyBadge` nello slot `suffix`
- ✅ `AccessoBloccatoPanel` sostituisce toolbar + lista (variante A, schermata protect). **Non** tenere toolbar visibile disabilitata.
- ✅ Refresh resta visibile in LETTURA; le azioni con `hideWhenReadonly` si nascondono; `ReadonlyBadge` si mostra solo su `isReadonly && !isBlocked`

### Stato permessi → UI della lista

Tabella riassuntiva di cosa vede l'operatore in base al livello risolto:

| Livello | Toolbar | Filtri | Refresh | Nuovo | ReadonlyBadge | Corpo lista |
| --- | --- | --- | --- | --- | --- | --- |
| TUTTO | visibile | attivi | visibile | visibile | nascosto | DataTable normale, Nuovo + modifica OK |
| LETTURA | visibile | attivi | visibile | nascosto | visibile | DataTable, riga apre drawer in consultazione |
| BLOCCATO (area) | — | — | — | — | — | l'utente non arriva alla pagina (route guard blocca + sidebar nasconde la voce) |
| BLOCCATO (oggetto) | nascosta | — | nascosto | nascosto | nascosto | `AccessoBloccatoPanel` — icona 🔒 + messaggio, niente DataTable |

### Modalita' BLOCCATA — dettaglio per liste (livello oggetto)

A differenza del BLOCCATO di area (dove il route guard impedisce la navigazione), il BLOCCATO di **livello oggetto** lascia raggiungere la pagina: l'operatore potrebbe avere `anagrafiche = TUTTO` ma `anagrafiche.cliente = BLOCCATO`. La view deve quindi auto-rilevare lo stato e mostrare la schermata sostitutiva.

**Comportamento atteso**:

- Non tentare alcuna fetch all'apertura: lasciare la store non inizializzata
- Non mostrare toolbar, filtri o tabella: sostituisci con `<AccessoBloccatoPanel />`
- Non mostrare badge `ReadonlyBadge`: il pannello comunica gia' piu' forte
- Nessun sub-drawer attivabile: l'utente non puo' cliccare righe (non esistono)
- Messaggio i18n standard: `common.accesso_negato_elenco` + `common.accesso_negato_hint`

**Implementazione minima** (gia' nel template standard sopra):

```vue
<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />
    <template v-else>
      <!-- toolbar + lista normali -->
    </template>
  </div>
</template>
```

**Cosa NON fare**:

- ❌ Non lasciare la toolbar visibile "grigia/disabilitata" sotto il pannello (variante B scartata: semanticamente ambigua)
- ❌ Non chiamare `store.fetchList()` sotto `onMounted` senza guard su `isBlocked`
- ❌ Non mostrare empty state generico (`SearchHint`) — il pannello bloccato e' piu' specifico
- ❌ Non usare banner inline + tabella vuota — la separazione toolbar/pannello rompe il pattern AS/400

### Pattern DRAWER — template standard

`DrawerTitle` include **automaticamente** il badge readonly via inject. Zero codice aggiuntivo per lo sviluppatore:

```vue
<script setup>
// Modifiche non salvate (BB useDrawerFormPreserve): fotografia a form pronto,
// conferma su ogni uscita, «Modifica» arancio nel titolo.
const { fissa, modificato, chiudiConConferma } =
  useDrawerFormPreserve(form, { visibile: () => props.visible })
const chiudi = () => chiudiConConferma(onClose)
// X, ESC e clic fuori escono come l'Annulla: lo STESSO `chiudi`.
const suVisibile = gestoreVisibile(emit, chiudi)
</script>

<Drawer :visible="visible" @update:visible="suVisibile">
  <template #header>
    <DrawerTitle
      :modificato="modificato"
      :action="isEdit ? t('common.edit') : t('common.new')"
      :title="t('...')"
      icon="pi pi-briefcase"
    />
    <!-- badge "Sola lettura" appare a destra automaticamente se readonly -->
  </template>

  <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
    <!-- form normale, disabled si propaga via .app-readonly -->
  </div>

  <FormFooter @save="onSave" @cancel="chiudi" />
  <!-- pulsante Salva nascosto automaticamente se readonly -->
</Drawer>
```

⛔ **Una via d'uscita sola** (2026-09-26): X, ESC, clic fuori e Annulla passano
dallo **stesso** `chiudi`, cablato con `gestoreVisibile(emit, chiudi)` — mai un
gestore `@update:visible` scritto a mano. Con due gestori la X e l'Annulla
finivano per emettere eventi diversi. La chiusura **dopo un salvataggio
riuscito** resta diretta (niente conferma: non c'è niente da perdere). Più form
nello stesso drawer, ciascuno col suo Salva → `unisciFotografie(...)`, una
domanda sola. Dettaglio: catalogo BB, voce `useDrawerFormPreserve`.

**Regole operative drawer**:

- ✅ Ogni drawer admin DEVE esporre prop `readonly` + leggere `useInjectReadonly()` con effetto cumulativo (`computed isReadOnlyEffective = props.readonly || isReadonly.value`)
- ✅ Usare sempre `DrawerTitle` nel `#header` — il badge si propaga automaticamente
- ❌ Non creare varianti `*ReadOnly.vue` separate
- ✅ Wrap del contenuto con `:class="{ 'app-readonly': isReadonly }"` per l'effetto protect
- ✅ `FormFooter` nasconde Salva in readonly; tasti di chiusura (X drawer, `.app-escape`) restano attivi

### Drawer autonomo vs drawer figlio puro

Un drawer puo' comportarsi in due modi rispetto ai permessi livello oggetto:

| Tipo | Dichiara scope proprio | Quando usare | Esempio |
| --- | --- | --- | --- |
| **Autonomo** | `useReadonlyMode(READONLY_DOMAINS.X, READONLY_MODELS.Y)` al setup | Il model e' catalogato in `config.area_model_overrides` (l'admin puo' bloccarlo singolarmente) | `ContiBancariDrawer` → `(READONLY_DOMAINS.ANAGRAFICHE, READONLY_MODELS.CONTO_BANCARIO)` |
| **Figlio puro** | solo `useInjectReadonly()` | Il model non e' nel catalogo, si eredita il readonly del parent | `IndirizzoDrawer`, `ContoBancarioForm` |

**Drawer autonomo — template**:

```js
// anagrafiche/components/ContiBancariDrawer.vue
import { useReadonlyMode, useInjectBlocked } from '@/core/composables/useReadonlyMode'
import { READONLY_DOMAINS, READONLY_MODELS } from '@/core/constants'

// Dichiara scope proprio (l'OR interno rispetta anche eredita' dal parent)
const { isReadonly } = useReadonlyMode(READONLY_DOMAINS.ANAGRAFICHE, READONLY_MODELS.CONTO_BANCARIO)
const isBlocked = useInjectBlocked()
```

```vue
<Drawer ...>
  <template #header>
    <DrawerTitle ... />  <!-- badge readonly automatico -->
  </template>

  <!-- Safety net: pannello se raggiunto bypassando l'azione di riga -->
  <AccessoBloccatoPanel v-if="isBlocked" />
  <div v-else class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
    <!-- contenuto normale -->
  </div>

  <FormFooter v-if="!isBlocked" @save="..." @cancel="..." />
</Drawer>
```

**Azione di riga che apre un drawer autonomo** — disabilita se oggetto bloccato (evita 403):

```js
import { useAuthStore } from '@/stores/auth'
const auth = useAuthStore()

function buildRowActions(data) {
  return [
    {
      key: 'conti-bancari',
      label: t('conti_bancari.gestisci_conti'),
      icon: MANAGE_ICONS.CONTI_BANCARI,
      disabled: auth.isObjectBlocked('anagrafiche', 'conto_bancario'),
      command: () => emit('conti-bancari', data),
    },
  ]
}
```

**Cosa succede se sbagli e metti `useReadonlyMode` su un drawer figlio puro?**
Nulla di rotto: `fn_resolve_livello_oggetto` fa fallback al livello area se il model non e' catalogato. Ma e' codice inutile che suggerisce una granularita' che non esiste — lascialo solo sui drawer veramente autonomi.

### Drawer di entita' con sub-drawer (catena readonly)

> **Regola d'oro**: il `readonly` non si calcola mai nei sub-drawer.
> Lo calcola il drawer di entita' (parent) e lo propaga via `provide(READONLY_KEY, ...)`.
> I sub-drawer (note, righe, utility, conti, ecc.) usano **solo** `useInjectReadonly()`
> senza nessuna logica locale.

I drawer di entita' (es. `ContrattoDrawer`, `PreventiviDrawer`) sono il **punto unico**
dove si combinano i 3 ingredienti del readonly:

1. **Permessi area/oggetto** dell'utente — via `useInjectReadonly()` dal provider della View
2. **Stato workflow** del documento (DRAFT vs stati post-DRAFT) — derivato da `detail.stato_codice*`
3. **Contesto** — `props.readonly` (split-view), `is_attiva=false` (revisione superseded), ecc.

Il computed risultante `isReadonly` viene `provide`-ato con `READONLY_KEY` ai sub-drawer,
che lo ricevono "gia' cotto" tramite `useInjectReadonly()`.

**Template drawer di entita' (parent provider)**:

```js
// ContrattoDrawer.vue / PreventiviDrawer.vue
import { computed, provide } from 'vue'
import { useInjectReadonly, READONLY_KEY } from '@/core/composables/useReadonlyMode'

const parentReadonly = useInjectReadonly()                  // (1) permessi area
const isWorkflowLocked = computed(                          // (2) stato post-DRAFT
  () => props.mode === 'edit'
     && detail.value
     && detail.value.stato_codice !== 'DRAFT',
)
const isSuperseded = computed(                              // (3) contesto entita'
  () => detail.value !== null && detail.value.is_attiva === false,
)

const isReadonly = computed(() =>
  parentReadonly.value
  || props.readonly
  || isWorkflowLocked.value
  || isSuperseded.value,
)
provide(READONLY_KEY, isReadonly)
```

**Template sub-drawer (figlio puro consumer)** — *zero* logica locale:

```js
// ContrattoRigheDrawer.vue / PreventivoNoteDrawer.vue / ContrattoNoteDrawer.vue
import { useInjectReadonly } from '@/core/composables/useReadonlyMode'

const isReadonly = useInjectReadonly()  // ← solo lettura. STOP.
```

**Anti-pattern (DA NON FARE) nel sub-drawer**:

```js
// ❌ NO: logica locale che ricalcola lo stato workflow
const parentReadonly = useInjectReadonly()
const isReadonly = computed(
  () => parentReadonly.value || props.contrattoStatoCodice !== 'DRAFT',
)
```

Perche' e' sbagliato:

- duplica la regola del modello UX in 2 posti (parent + figlio) — drift garantito
- nasconde una props (`contrattoStatoCodice`) che il sub-drawer non dovrebbe nemmeno conoscere
- se la regola cambia (es. CESSATO ammette modifica `meta`), va aggiornata in N posti
- rompe il pattern "Provider → Consumer" su cui si fonda il sistema permessi

Se il sub-drawer ha bisogno di un readonly diverso dal parent (caso raro: il padre e' editabile
ma il figlio no per ragioni di dominio), allora il **PARENT** estende il proprio `isReadonly`
con quella regola e la propaga. Il sub-drawer resta agnostico.

**Azioni di stato in drawer readonly** — i pulsanti di transizione (`Emetti`, `Accetta`,
`Cessa`, ecc.) restano cliccabili anche dentro `app-readonly` perche' `DrawerActionsBar`
applica automaticamente `.app-escape` a tutti i suoi pulsanti. Non filtrare la lista actions
per `isReadonly` (allineato a `ContrattoDrawer.drawerActions` / `PreventiviDrawer.drawerActions`):
la sicurezza e' garantita dal BE che rifiuta i comandi senza permesso.

**Azioni di processo su selezione righe → dialog, non pannello in coda** (2026-07-25,
decisione Tid). Le attività che generano un documento a valle selezionando righe
(evasione ordine → DDT, smistamento preventivo → ordine/commessa, crea reso da DDT,
ri-spedizione reso) si aprono da un **pulsante nella `DrawerActionsBar`** — con l'icona
del documento che si genera (`NAV_ICONS.DDT`, `NAV_ICONS.RESI`, `MANAGE_ICONS.SEND`) e
`kind: 'manage'` — e vivono in un `AppDialog` dedicato. Non più come pannello sempre
montato in fondo al drawer: allungava il contenuto e faceva la fetch delle righe anche a
chi non stava lavorando quel processo.

Regole del dialog d'azione:

- **fetch lazy** su `watch([visible, id])` — all'apertura e a **ogni riapertura** (i
  residui devono essere freschi dopo un'azione appena eseguita), mai al mount;
- **`:readonly` esplicito** = il readonly PURO del chiamante (permessi/split/superseded),
  NON quello combinato col lock-di-stato: il dialog è lanciato da un drawer post-DRAFT
  `app-readonly` e senza override `FormFooter` erediterebbe `readonly=true` nascondendo il
  pulsante di conferma — è la stessa ragione per cui il pannello, quando viveva nel
  drawer, stava in `app-escape` (vedi `AppDialog.readonly`);
- **`:close-only`** quando non c'è nulla da fare (readonly puro o nessuna riga
  lavorabile): il dialog resta consultabile come consuntivo;
- **chiusura a conferma riuscita**, con emit al drawer padre che ricarica detail e
  capability. Un lavoro parziale si riprende riaprendo il dialog.

Riferimento: `DdtResoDialog`, `OrdineEvasioneDialog`, `PreventiviSmistamentoDialog`.

**Esempi nel codice**:

| Drawer parent (provider) | Sub-drawer figli (consumer) | Cosa propaga |
| --- | --- | --- |
| `ContrattoDrawer` | `ContrattoRigheDrawer`, `ContrattoNoteDrawer` | parentReadonly + `stato_codice !== 'DRAFT'` |
| `PreventiviDrawer` | `PreventivoNoteDrawer`, `PreventiviRigheTable` | parentReadonly + `stato_codice_interno !== 'DRAFT'` + `is_attiva=false` |
| `SoggettoDrawer` | `IndirizziSoggettoDrawer`, `ContattiSoggettoDrawer` | solo parentReadonly (no workflow state) |

### Tasti di uscita

Come F12/F3 sui formati protect AS/400, i **pulsanti di chiusura** restano attivi anche in modalita' protect:

```css
.app-readonly .app-escape {       /* classe generica uscita */
  pointer-events: auto;
  cursor: pointer;
}
```

`app-escape` la porta il pulsante Annulla/Chiudi di `FormFooter` e la si mette su
ogni pannello-azione legittimo dentro un contenitore protect.

⚠️ **La X del drawer NON ha bisogno di una regola** (verificato 2026-09-18):
`app-readonly` sta sul wrapper del **contenuto** (`app-drawer-content`), e la
testa del `Drawer` — con la sua X — è **fuori** da quel wrapper. Fino a quel
giorno qui stavano due selettori in più, `.p-drawer-close` e `.p-dialog-close`,
che in PrimeVue non esistono (le classi sono `p-drawer-close-button` /
`p-dialog-close-button`): CSS morto che descriveva un meccanismo mai attivo. Il
dialog una X non ce l'ha più (§`AppDialog`, «Chrome»).

Regola: in sola lettura **si puo' solo chiudere/uscire**, mai aprire/creare/modificare.

### Impatto sui componenti

- **Non creare varianti read-only** di componenti esistenti — usare la classe `.app-readonly` sul container
- `DrawerTitle`: auto-include `ReadonlyBadge` a destra del titolo
- `FormFooter`: Salva nascosto se readonly (`v-if="!isReadonly"`)
- `PageActionsBar`: nasconde le azioni con `hideWhenReadonly`, mantiene il refresh in LETTURA e usa il kebab su touch/tablet/mobile
- `ReadonlyBadge`: visibile solo se readonly e non bloccato
- `AccessoBloccatoPanel`: sostituisce il contenuto lista se bloccato (livello oggetto)
- `DataTable` row-click: in sola lettura apre il drawer in modalita' consultazione (protect attivo)
- **Copia testo**: `user-select: text` garantisce che l'operatore possa sempre copiare dati con Ctrl+C

### Dove si usa

| Contesto | Trigger |
| --- | --- |
| Autorizzazioni utente area | LETTURA sull'area funzionale (schema DB) |
| Autorizzazioni utente oggetto (v2) | Override `config.user_override_oggetti` su `app_label.model_name` |
| Split view | Pannello secondario affiancato sempre in sola lettura (readonly propagato via provide) |

---

## Enum centralizzati cross-cutting (constants.js)

### Principio

Le **stringhe identificative** condivise tra producer e consumer (readonly area/model, chiavi cross-tab refresh) NON si scrivono mai come literal. Vivono come **costanti** in `src/core/constants.js` e si importano dove servono.

Rationale: un typo silenzioso (`'contratoo'` vs `'contratto'`) rompe il binding senza errori runtime — il producer emette, nessun consumer ascolta, auto-refresh morto. L'enum toglie il problema alla radice (IDE autocompletion + grep facile).

### I tre enum

```js
import { READONLY_DOMAINS, READONLY_MODELS, TAB_ENTITIES } from '@/core/constants'
```

| Enum | Scopo | Esempi |
| --- | --- | --- |
| `READONLY_DOMAINS` | Area (schema DB) passata come **primo arg** a `useReadonlyMode` | `AMM_SOFTWARE`, `ANAGRAFICHE`, `CATALOGO`, `CONFIG`, `DOCUMENTI`, `MAGAZZINO`, `PAGAMENTI`, `PRATICHE`, `STRUMENTI`, `VENDITE` (elenco completo al 2026-09-26; `PAGAMENTI` e' entrato quel giorno, prima le view di pagamenti passavano la stringa) |
| `READONLY_MODELS` | Model specifico (permessi v2) come **secondo arg** opzionale a `useReadonlyMode` | `CONTRATTO`, `CLIENTE`, `FORNITORE`, `ARTICOLO`, `UNITA_MISURA`, `CONTO_BANCARIO`, `SOGGETTO`, `PROMO_ARTICOLO` |
| `TAB_ENTITIES` | Chiave cross-tab per `emitDataChanged` + `useTabFreshness` / `onDataChanged` | `CONTRATTO`, `PRATICA`, `ARTICOLO`, `FORNITORE`, `PREVENTIVO`, `PROMO_ARTICOLI`, ... |

### Regola operativa

```js
// NO — literal vietato
useReadonlyMode('vendite', 'contratto')
emitDataChanged('contratto', id)
useTabFreshness(store, 'contratto')

// SI — costante
useReadonlyMode(READONLY_DOMAINS.VENDITE, READONLY_MODELS.CONTRATTO)
emitDataChanged(TAB_ENTITIES.CONTRATTO, id)
useTabFreshness(store, TAB_ENTITIES.CONTRATTO)
```

Il primo (literal) **funziona** ma non è mai accettato in PR di nuovo codice: il pattern enum è la **fonte di verità** per tutti i call site.

### Consumer cross-tab: due pattern

Entrambi validi, ambedue usano `TAB_ENTITIES`:

```js
// Pattern A — standard per SearchTable paginata
useTabFreshness(store, TAB_ENTITIES.CONTRATTO)
// Se un altro tab emette CONTRATTO, lo store fa fetchList() automatico

// Pattern B — hook custom (es. pannelli senza SearchTable, view di profilo)
const { onDataChanged } = useTabEvents()
onMounted(() => {
  onDataChanged('profilo-reparto', () => store.fetchList())
})
```

Pattern A è la default. Pattern B si usa quando la view non ha uno `store` standard con `fetchList` o quando serve un handler custom.

### Producer cross-tab

Sta **sempre** nello store, dopo ogni operazione di scrittura:

```js
// Store Pinia
async function create(payload) {
  const res = await api.create(payload)
  emitDataChanged(TAB_ENTITIES.CONTRATTO, res.data.data.id)  // emit post-write
  return res.data.data
}

async function update(id, payload) {
  const res = await api.update(id, payload)
  emitDataChanged(TAB_ENTITIES.CONTRATTO, id)
  return res.data.data
}
```

Entità **read-only** (es. log immutabili): non emettono mai, e nessun consumer deve ascoltarle.

⭐ **Un verbo che fa nascere un'altra entità avvisa le DUE entità, dallo store del
verbo.** Generare un DDT da un ordine scrive sull'ordine (residui, stato) *e* crea
il DDT; lo smistamento di un preventivo scrive sul preventivo *e* crea l'ordine.
L'azione dello store che chiama l'endpoint emette per entrambe:

```js
// store ordini
async function generaDdt(ordineId, righe = null) {
  const res = await generaDdtFromOrdine(ordineId, righe)
  emitDataChanged(TAB_ENTITIES.ORDINE, ordineId)
  if (res.data.data?.ddt_id) emitDataChanged(TAB_ENTITIES.DDT, res.data.data.ddt_id)
  return res.data.data
}
```

⛔ Mai l'emissione nella dialog o nel drawer che ha lanciato il verbo: un'altra
superficie che chiama lo stesso endpoint (un flusso di pratica, un'azione di
massa) non avviserebbe nessuno, e la lista dell'entità nata resterebbe ferma
senza errori. Fino al 2026-09-26 facevano così `OrdineEvasioneDialog` e
`PreventiviDrawer` (smistamento); `generaRiconsegna` dello store resi era già
nella forma giusta. Il `changed` del drawer resta: è il contratto verso chi lo
ha aperto, non l'avviso alle liste.

### Factory `createCrudStore`

Per gli store lista+CRUD (categorie clienti, promo articoli, matrici config,
clienti, articoli…) la factory `core/stores/createCrudStore.js` emette da sé
in `create`/`update`/`extraActions`. Basta passare `tabEntity`:

```js
export const useCategorieClientiStore = createCrudStore('amm-categorie-clienti', {
  api: { list, detail, create, update },
  tabEntity: TAB_ENTITIES.CATEGORIE_CLIENTI,  // la factory emette automaticamente
  orderBy: 'ordinamento',
  startsEmpty: false,
  // ...
})
```

Nessun `emitDataChanged` manuale necessario nei metodi. ⚠️ Fino al 2026-09-18
questa sezione descriveva `createCrudAdminStore` in `core/composables/`, con
`storeName`/`emitKey`/`defaultOrderBy`: quella factory è stata **eliminata il
2026-06-05** (convergenza B19 in `createCrudStore`), e un documento che nomina
un file inesistente manda a cercarlo.

### Aggiungere una nuova entità

1. Aggiungere la chiave in `constants.js`:

   ```js
   export const TAB_ENTITIES = {
     // ... esistenti
     NUOVA_ENTITA: 'nuova_entita',
   }
   ```

2. Nello store: `emitDataChanged(TAB_ENTITIES.NUOVA_ENTITA, id)` dopo ogni write
3. Nella SearchTable: `useTabFreshness(store, TAB_ENTITIES.NUOVA_ENTITA)`
4. Se serve permesso livello oggetto: aggiungere anche in `READONLY_MODELS` + dichiarare `model_permission = (app_label, model_name)` sulla view BE

### Naming

- `READONLY_MODELS` usa **singolare** snake_case (`contratto`, `promo_articolo`) — matcha `app_label.model_name` del BE Django per `ZeroERPPermission`.
- `TAB_ENTITIES` può usare **plurale** dove è più naturale per la feature (`promo_articoli`, `categorie_clienti`) — è una chiave FE-only, non vincolata al BE.
- `READONLY_DOMAINS` corrisponde 1:1 agli schema DB backend.

Una stessa parola può comparire in entrambi (es. `PROMO_ARTICOLO` singolare in `READONLY_MODELS` + `PROMO_ARTICOLI` plurale in `TAB_ENTITIES`): è volontario, i due ruoli sono distinti.

### Check pre-PR

- [ ] Zero literal `'schema_name'` in chiamate `useReadonlyMode`
- [ ] Zero literal in `emitDataChanged` / `useTabFreshness` / `onDataChanged`
- [ ] Se aggiunta una chiave all'enum, verificare che esista **sia un producer che un consumer** (altrimenti è orfana)
- [ ] Per entità read-only (log, audit): nessun `emitDataChanged`, nessun `useTabFreshness`

---

## Store Pinia — user-scoped + reset al logout

### Principio

Qualsiasi store Pinia che contenga **dati specifici dell'utente loggato** (filtri lista, cache di lookup user-aware, override personali, contesto selezionato, ecc.) DEVE dichiararsi `userScoped: true` come terzo parametro di `defineStore`. Il plugin `autoResetPlugin` (`src/core/pinia-plugins/auto-reset.js`) lo intercetta e:

1. al login successivo / al logout chiama `resetAllUserScopedStores()` da `auth.js`
2. per ogni store user-scoped invoca `clearUserState()` se esposto come action, altrimenti fa fallback su `$resetToInitial()` (snapshot dello state al primo init)

Razionale: senza questo flag uno stesso browser usato in sequenza da utenti diversi (caso "computer in ufficio condiviso") rischia che l'utente B veda i filtri / la cache / gli override dell'utente A. Bug di sicurezza silenzioso.

### Pattern store user-scoped

```js
export const useMyStore = defineStore('my-store', () => {
  const items = ref([])
  const filters = ref({ ... })

  function clearUserState() {
    // Solo se serve logica custom oltre al snapshot:
    // es. clear di Map/Set/cache module-level interna,
    // disconnect di BroadcastChannel, ecc.
    items.value = []
    filters.value = { ... }
  }

  return { items, filters, clearUserState }
}, {
  // Reset automatico al logout via autoResetPlugin.
  userScoped: true,
})
```

| Quando serve `clearUserState()` esplicito | Quando basta lo snapshot |
| --- | --- |
| Lo state contiene Map / Set / Date / function (non JSON-serializable) | State con primitives, oggetti/array piani |
| Lo store legge da localStorage all'init (snapshot fotografa già i dati utente); per `auth` vale per l'access in memoria di `core/sessione`, che lo snapshot non azzera | State puro in-memory |
| Servono side-effect aggiuntivi (chiudere BroadcastChannel, abortire fetch in volo) | Nessun side-effect |

### Pattern composable user-scoped (cache module-level)

I composable possono mantenere cache module-scope (es. `useGlobalLookup._cache`). Anche queste vanno azzerate al logout. Pattern:

```js
import { registerUserScopedResetter } from '@/core/pinia-plugins/auto-reset'

const _cache = new Map()
registerUserScopedResetter(() => _cache.clear())

export function useMioCompose() { ... }
```

`registerUserScopedResetter` accetta una function di reset ed è idempotente. Va chiamata al top-level del modulo (non dentro la setup function).

### Store globale `parameters` — cache condivisa per `config.parameters`

Single source of truth per i valori risolti (con override) dei parametri di sistema. Sostituisce la cache per-istanza che `useParameterDefaults` aveva pre-2026-05-02:

```js
import { useParametersStore } from '@/stores/parameters'

const params = useParametersStore()
await params.ensure(['DEFAULT_IVA_ID', 'DEFAULT_UTILITY'])  // single-flight per code
const iva = params.get('DEFAULT_IVA_ID')                     // sync getter, null se mancante
```

#### API

| Metodo | Scopo |
| --- | --- |
| `ensure(codes)` | Garantisce che i `codes` siano in cache. Single-flight per code: chiamate concorrenti convergono su una sola fetch. Idempotente. |
| `get(code)` | Sync getter del valore risolto. Ritorna `null` sia se non in cache sia se BE non ha valore. Per distinguere usare `has(code)`. |
| `has(code)` | True se il code è già stato fetchato (anche con valore `null`). |
| `invalidate(codes)` | Rimuove i `codes` dalla cache + broadcast cross-tab. La prossima `ensure` ri-fetcha. |
| `setOverride(code, value, scope)` | Upsert override personale o emittente + invalidate automatico del code. |
| `removeOverride(overrideId, code, scope)` | Delete override + invalidate. Il `code` serve per identificare cosa invalidare (l'API delete usa solo l'id). |

#### Cosa risolve rispetto al composable per-istanza

| Problema pre-2026-05-02 | Soluzione store |
| --- | --- |
| 4 drawer aperti = 4 fetch identiche per `DEFAULT_UTILITY` | Single-flight per code: 1 sola fetch |
| Admin cambia override → drawer mostrano valore vecchio finché non F5 | `setOverride` invalida la cache → tutti i computed reattivi si aggiornano |
| Cambio override in tab A non visibile in tab B | `BroadcastChannel('zeroerp-parameters')` propaga gli invalidate cross-tab |
| Cache parametri persiste tra utenti diversi sullo stesso browser | `userScoped: true` + `clearUserState()` azzera la cache al logout |

#### `useParameterDefaults` come thin wrapper

Il composable `useParameterDefaults` esiste ancora come API ergonomica per i drawer:

```js
const { defaults, load } = useParameterDefaults(['DEFAULT_IVA_ID', 'CATALOGO_BOM_DEFAULT_OBBLIGATORIO'])
await load()
form.iva_id = defaults.value.DEFAULT_IVA_ID   // string — convertire se serve
```

Internamente delega a `useParametersStore`: cache, single-flight, invalidation, cross-tab sync, reset al logout sono tutti gestiti dallo store. Il composable espone un computed `defaults` reattivo allo store.

#### Quando usare lo store direttamente vs il composable

- **Composable `useParameterDefaults`**: drawer/form che leggono N parametri all'apertura e li usano in `defaultForm()`. È la scelta di default.
- **Store `useParametersStore` direttamente**: pagine che fanno mutation di override (admin / impostazioni utente), o che devono reagire a invalidate cross-tab. Es. `useParameterSettings.saveOverride` delega a `store.setOverride` per ottenere invalidate gratis.

#### Convenzione codice_interno per parametri FK-surrogata

I parametri che referenziano tabelle di catalogo dotate di `codice_interno` (UNIQUE + immutabile via `script.trgfn_lock_columns`) stoccano il `codice_interno`, non l'id. La risoluzione codice→id è applicativa e va fatta lato FE incrociando il valore con la lookup della tabella target. Esempio: `DEFAULT_UTILITY` (codice_interno di `config.utilities`) risolto da [`useUtilityDefaultId`](../../../../frontend/src/core/composables/useUtilityDefaultId.js).

Vedi anche `linee-guida-sql §6b` per il principio generale e il framework DB `config.parameter_fk_surrogate`.

---

## Azioni processo — Livello 2 (pattern "action gate")

### Principio

Le azioni di processo controllano **singole operazioni** (es. "crea soggetto", "genera fatture") dentro un'area a cui l'operatore ha gia' accesso. Sono il livello di granularita' sotto TUTTO/LETTURA/BLOCCATO.

### Collocazione nel modello permessi

```
Livello 1: Area (TUTTO / LETTURA / BLOCCATO)  → sidebar + route guard + .app-readonly
Livello 2: Azione processo (abilitata / negata) → `action` su `PageActionsBar` / `FormFooter`
```

### Come funziona

L'endpoint `/me/` ritorna `azioni_abilitate: { codename: boolean }` per tutte le azioni attive. Lo store `auth.js` espone `isActionAllowed(codename)`.

I componenti `PageActionsBar` e `FormFooter` accettano una prop opzionale `action`:
- Se **assente** (default): il componente funziona come prima (solo check readonly)
- Se **presente**: il componente si nasconde se l'azione non e' abilitata

```vue
// Azione "Nuovo" visibile solo se l'azione e' abilitata
{ key: 'new', kind: 'primary', action: 'crea_soggetto', label: t('common.new'), command: onNew }

<!-- Footer Salva visibile solo se l'azione e' abilitata -->
<FormFooter action="modifica_soggetto" @save="..." @cancel="..." />
```

### Come aggiungere un'azione

1. **DB**: inserire riga in `config.azioni_processo` (seed CSV)
2. **Backend**: aggiungere `post_permission = "codename"` sulla view API
3. **Frontend**: aggiungere `action: 'codename'` sull'azione `PageActionsBar` o prop `action` su `FormFooter`
4. **Configurazione**: da Amm. Software → Profili reparto, abilitare per reparto

### Composable per casi avanzati

Per logica condizionale oltre ai componenti standard:

```js
import { useActionPermission } from '@/core/composables/useActionPermission'

const { isAllowed } = useActionPermission('genera_fatture_lotti')
// <Button v-if="isAllowed" ... />
```

### Regole

- Mai hardcodare codename nei componenti — usare costanti se ripetuti
- Il backend blocca sempre con 403 anche se il frontend non nasconde il bottone (defense-in-depth)
- ADMIN ha tutte le azioni abilitate — il check frontend lo gestisce automaticamente
- La prop `action` e' cumulativa con readonly: se readonly=true, il componente e' nascosto a prescindere

---

## Test — le tre altezze, e come si sceglie

> ⭐ **Dal 2026-09-23 si montano i componenti** (`@vue/test-utils` + `jsdom`,
> ok di Tid). Fino a quel giorno il frontend provava solo funzioni pure: quel
> confine ha presentato il conto tre volte in una settimana — rate, filtri di
> lista, barra del drawer di magazzino — e i filtri ne hanno pagati **due
> difetti in un giorno**, entrambi invisibili a qualunque funzione pura.

| Altezza | Ambiente | Vede | Costo |
| --- | --- | --- | --- |
| **funzione pura** (composable, utility) | node — il **default** | logica, calcoli, contratti di dato | il più basso: si scrive sempre per primo |
| **componente montato** (`// @vitest-environment jsdom`) | jsdom | che cosa **esiste** nel DOM: quali pulsanti, acceso/spento, dove sta un attributo | medio: vuole l'impalcatura, e parte più lento |
| **a video** | un browser vero, cioè una persona | come è **disegnato**: media query, ingombri, il telefono | il più alto, e non si automatizza oggi |

**La regola di scelta**: si scende di un'altezza solo quando quella sopra non
può vedere il difetto. ⛔ Un componente montato per provare un `if` che sta in
un composable è un test lento che prova la cosa sbagliata.

### Come si monta

```js
// @vitest-environment jsdom        ← in cima al file, prima di tutto
import { monta } from '../../../test/montaggio'

const w = monta(Componente, { prop: 'x' }, { provide: { [CHIAVE]: ref(true) } })
expect(w.findAll('button').map(b => b.text())).toContain('Conferma')
```

* **`frontend/test/montaggio.js`** è l'impalcatura: installa i plugin che
  `main.js` installa sull'app vera (Pinia, PrimeVue + i suoi servizi, i18n,
  la direttiva tooltip) e colma le lacune di jsdom (`matchMedia`). Vive
  **fuori da `src/`**: non è codice applicativo e non deve finire in un bundle.
* ⛔ **Il DOM non si accende globalmente**: chi ne ha bisogno lo dichiara in
  testa al proprio file. Accenderlo per tutti rallenterebbe i test puri — che
  sono la maggioranza — e nasconderebbe **quali** file toccano il DOM.
* ⭐ **Si monta il componente vero, si fingono solo i suoi contorni** (un'API,
  la config che arriva dal server). Un test che stubba ciò che deve provare
  prova lo stub.
* **`t` rende la chiave, non la frase**: le asserzioni parlano di *chiavi*
  i18n. Le frasi vivono nei `locales`, si riscrivono quando cambia il tono, e
  un test che le pinna diventa rosso per una virgola.
* ⚠️ **Le media query non si provano**: jsdom non calcola il CSS. La variante
  compatta sotto i 1024px resta materia di collaudo a video, e va detto invece
  che sottinteso.

### ⛔ Un test verde al primo colpo si prova per mutazione

Si rompe di proposito il codice sotto esame e si guarda se il test **diventa
rosso**. Un test che resta verde su un codice rotto non presidia niente.

🔴 **Non è teoria: è già servito due volte lo stesso giorno.** Sul mapper delle
azioni, quattro mutazioni su cinque venivano viste e la quinta no — il ramo
«motivo senza `reason_key`» non era coperto, e un dominio che perdesse la
chiave avrebbe mostrato un **tooltip vuoto** su un pulsante spento, cioè il
caso peggiore. Il test è nato da lì.

## Regole per il developer

1. Ogni componente e' autonomo — logica nei composables (di `core/` se generici, del dominio se parlano di un'entita')
2. Un componente non parla HTTP: l'URL di un endpoint vive in un modulo `api/` (del dominio o `core/api/`) o dietro uno store, e il componente chiama quella funzione dentro `execute` di `useApiHandler`. Mai `import api` in un `.vue` (presidio: `npm run guards` → `check-api-componenti.mjs`). ⚠️ Le pagine pubbliche della famiglia login (reset e cambio password) mostrano l'errore **nella card** e non in un toast: lì il `try/catch` resta, ma la chiamata passa comunque dal modulo `core/api/password.js`
3. Toast via `useNotify()` — mai `useToast()` direttamente
4. Dialog conferma via `useConfirmAction()` — mai `useConfirm()` direttamente; **sempre con `header`** (il nome dell'azione)
5. Drawer usano PrimeVue `Drawer` + `FormFooter` — mai pulsanti inline
6. Testi visibili via `$t()` — mai stringhe hardcoded
6-bis. Un test si scrive all'**altezza più bassa** che vede il difetto (§Test), e se passa al primo colpo si prova **per mutazione**
7. Nessun `console.log` in produzione
8. Un dominio importa un altro dominio solo nel verso delle FK; il verso opposto passa da un punto di estensione, e `core/` non importa mai un dominio (§«Confini fra domini»; presidio `check-confini-domini.mjs`)
9. Larghezze drawer da `constants.js` — mai hardcoded
10. Navigazione da `navigation.js` — mai duplicata
11. Paginazione/sort/search da `useSearchTable` — mai implementata manualmente
12. Inter-tab freshness di una lista da `useTabFreshness` — mai un `onDataChanged` scritto a mano accanto a uno store-lista. `useTabEvents` diretto solo per **emettere** (nello store, §«Producer cross-tab») o per il **Pattern B** (view senza store-lista standard, §«Consumer cross-tab»)
13. Stato drawer da `useDrawerState` — mai `ref(false)` + `ref('create')` separati
14. CSS layout da `main.css` — mai `<style scoped>` per layout form/pagina
15. Sola lettura da classe `.app-readonly` sul container — mai componenti duplicati
16. Azioni processo via `action` su `PageActionsBar`/`FormFooter` — mai `v-if` manuali per permessi
17. `ConfirmDialog` solo globale in `App.vue` — mai dentro Drawer (interferenza overlay)
18-bis. Un campo letto da un blob `capabilities.*` deve essere un campo che il database emette: il contratto si legge dalla doc auto-generata, non da un elenco ricopiato (presidio: `npm run guards` → `check-capability-contratto.mjs`). ⛔ Un refuso lì non rompe niente — lascia un pulsante spento che sembra una regola. ⛔ E il blob si legge **sotto `capabilities`** (via `useEntityCapabilities` o `capabilities.x`), mai `detail.can_x` / `detail.pdf`: la forma piatta è chiusa (api.md §«Il blob sta SOTTO `capabilities`», 2026-09-23) e lo stesso guard la conta
18. Dialog modali solo `AppDialog`, con `header`, **senza X** e senza `:closable` sul tag — il chrome è `DIALOG_CHROME`, un cambio di layout è una riga lì (presidio: `npm run guards` → `check-dialog-chrome.mjs`)

---

## Catalogo componenti e composable riutilizzabili

> Prima di creare un nuovo componente o composable, verificare se esiste gia' in questo catalogo.
> I componenti in `core/` sono generici e non importano mai un dominio (§«Confini fra domini», presidio `check-confini-domini.mjs`).

### Componenti UI (`core/components/`)

#### Layout e navigazione

| Componente | Scopo | Esempio d'uso |
| --- | --- | --- |
| `AppLayout` | Layout principale: sidebar + topbar + content area | router (layout radice) |
| `AppTopbar` | Topbar: azienda, titolo area, ricerca, sessioni, data | AppLayout |
| `AppSidebar` | Contenitore sidebar (logo + stato morfic) | AppLayout |
| `AppBreadcrumb` | Breadcrumb derivato da route meta | AppLayout |
| `ContentTabs` | Barra tab multi-entita con KeepAlive | AppLayout |
| `SidebarHome` | Sidebar stato HOME (lista domini L1) | AppSidebar |
| `SidebarDomain` | Sidebar stato DOMINIO (voci L2 + preferiti) | AppSidebar |
| `SidebarItem` | Voce sidebar riutilizzabile (icona + label) | SidebarHome |
| `LogoBrand` | Logo ZeroERP riutilizzabile | AppSidebar |
| `StatusPage` | Template pagina stato (errore, placeholder) | ErrorView |
| `SearchDrawer` | Ricerca universale soggetti per ruolo con row expansion | AppTopbar (Ctrl+K da AppLayout) |
| `SessioniAttivePanel` | Pannello sessioni attive in topbar | HomeView |

#### Infrastruttura drawer e liste

| Componente | Scopo | Props chiave | Esempio d'uso |
| --- | --- | --- | --- |
| `DrawerTitle` | Titolo standard drawer: azione sx + entita' centrata + badge readonly auto | `action`, `title`, `icon` | OperatoreDrawer |
| `FormFooter` | Footer drawer con Annulla/Salva, auto-hide Salva in readonly | `loading`, `disabled`, `action`, `closeOnly` | OperatoreDrawer |
| `PageActionsBar` | Barra azioni pagina/lista responsive. Gestisce azione primaria, utility inline desktop e kebab su touch/tablet/mobile | `actions`, `disabled`, `menuTooltip` | FornitoriSearchTable |
| `NewButton` | Pulsante specializzato legacy/non-toolbar. Nelle liste usare `PageActionsBar` | `tooltip`, `action` | TemplateVersioniSection |
| `ReadonlyBadge` | Badge grigio "Sola lettura", auto-visibile se `isReadonly && !isBlocked`, responsive (icona-only su mobile) | — | FornitoriSearchTable |
| `AccessoBloccatoPanel` | Pannello sostitutivo "Accesso negato a questo elenco" per BLOCCATO oggetto | — | FornitoriSearchTable |
| `RowActionsMenu` | Azioni di riga responsive: pulsanti inline su desktop, kebab `⋮` su tablet/touch. Se riceve `row` disabilita le azioni operative su record inattivi (`attivo=false` / `is_active=false`) salvo `allowWhenInactive` | `actions`, `row`, `tooltip`, `disabled`, `disableWhenInactive` | FornitoriSearchTable |
| `FiltriLista` | I FILTRI di una lista: in linea su desktop, in un drawer dal basso sotto i 1024px (o su un touch senza hover), con il segno di quanti ne sono attivi e «Pulisci filtri». Due slot: `#sempre` (la ricerca) e il default (gli altri filtri). ⚠️ I filtri dentro si legano con un **binder**, non con un `ref` a senso unico (§«Un filtro si lega con un binder») | `store` \| `segno`, `inert`, `titolo` | FornitoriSearchTable |
| `FiltroPeriodo` | Il PERIODO come UN filtro: i due estremi `data_da`/`data_a` resi insieme, una cella sola nella griglia del drawer | `periodo` (da `bindPeriodo`), `placeholderDa/A` | AuditLogView |
| `TagList` | Lista tag con overflow +N e tooltip | `items`, `labelField`, `maxVisible`, `severity` | SoggettiSearchTable |
| `AppDrawer` | **La sede del chrome dei drawer laterali**: testata, larghezza dalla scala, uscita con conferma, montaggio a fine animazione, corpo e readonly, footer fisso (§«Drawer (nuovo e modifica)») | `title`, `icon`, `action`, `width`, `modificato`, `confermaUscita`, `footer` | CanaleIncassoDrawer |

#### Building block form

| Componente | Scopo | Props chiave | Esempio d'uso |
| --- | --- | --- | --- |
| `AuthUserForm` | Form credenziali operatore | `form`, `isEdit` | OperatoreDrawer |

### Composable (`core/composables/`)

#### Infrastruttura liste e drawer

| Composable | Scopo | Esempio d'uso |
| --- | --- | --- |
| `useSearchTable` | Paginazione, sort, search debounce, applyFilters per DataTable lazy | useListaConfigurabilePage |
| `useDrawerState` | Stato drawer: visible, mode, itemId, itemData, openCreate(), editRow(), close() | EmittentiFiscaliListView |
| `useTabFreshness` | Refresh automatico lista su evento `dataChanged` | FornitoriSearchTable |
| `useTabEvents` | Event bus inter-tab per invalidazione dati | store `contratti` (emit); RepartiProfiloView (listen, Pattern B) |
| `useApiHandler` | Execute con loading, toast successo, gestione errori | DefinizioneEditorView |
| `useNotify` | Toast PrimeVue centralizzato — MAI importare useToast direttamente | useApiHandler |
| `useConfirmAction` | Dialogo conferma azione distruttiva | DefinizioneEditorView |
| `useConfirmCloseTab` | Conferma chiusura tab con modifiche non salvate | ContentTabs |
| `useKeyboardShortcuts` | Shortcut globali: Ctrl+K ricerca, Ctrl+W chiudi tab, Ctrl+Tab naviga | AppLayout |
| `usePagination` | Paginazione server-side locale (fuori da `useSearchTable`) | SearchDrawer |
| `useContrattoFiltriLista` | Il contratto che una lista offre ai suoi filtri: `chiaviFiltro`, `filtriDefault` (copia **profonda** e congelata), `filtriNeutri` e `azzeraFiltri`. Lo consuma `useListaStoreCore`, e lo adottano in tre righe gli store scritti a mano | useListaStoreCore |
| `useContrattoFiltriLocali` | Lo stesso contratto per una superficie **senza store-lista**: si dichiara `{ chiave: { rif, default } }` e tornano `segno` + `azzeraFiltri()`. Il default si **dichiara** (non si fotografa dal `ref`) e può essere una **funzione** quando si ricalcola («oggi») | DashboardBacklogView |
| `useStoreFilterBindings` | Il legame widget ↔ `store.filters`: `bindSelect`, `bindDate`, `bindPeriodo`, `bindToggle`, `bindLookup` | FornitoriSearchTable |

#### Lookup e autocomplete

| Composable | Scopo | Esempio d'uso |
| --- | --- | --- |
| `useLookup` | Caricamento lazy/eager di dati lookup con cache | OperatoriListView |
| `useLookupCodici` | Lookup **generico** di un `rel` nella cache condivisa: chiave (`<rel>` / `<rel>::no-obsoleti`) e fetch composte in un posto — mai scritte a mano (2026-09-19) | LookupSelect |
| `useLookupEtichettato` | Lookup del catalogo con l'**etichetta dichiarata dal DB** (`etichetta_key`, resa con `labelOrCode`): `etichetta(codice)` per le colonne + `opzioni` con la voce «tutti» — **non** un `LookupSelect`, che rende `descrizione` (2026-09-19, regola del 2) | GiornaleListView |
| `useServerAutocomplete` | Autocomplete con ricerca server debounce 300ms | ComuneAutocomplete |

#### Modalita sola lettura e azioni processo

| Composable | Scopo | Esempio d'uso |
| --- | --- | --- |
| `useReadonlyMode` | Provider: derive isReadonly da permessi area + provide | CategorieClientiListView |
| `useInjectReadonly` | Consumer: inject isReadonly dal provider padre | FormFooter |
| `useActionPermission` | Verifica se un'azione processo e' abilitata (computed reattivo) | LottiListView |

**Nota**: per i casi standard, usare `action` su `PageActionsBar`/`FormFooter` invece del composable diretto.

#### Ricerca universale

| Composable | Scopo | Esempio d'uso |
| --- | --- | --- |
| `useSearchDetail` | Fetch dettaglio soggetto per row expansion (livello 2) | SearchDetailTable |

### Building block di anagrafiche (`anagrafiche/components/`, `anagrafiche/composables/`)

Soggetto, indirizzi, contatti, conti bancari e geografia: fino al 2026-09-26 stavano in `core/`, che per usarli importava `anagrafiche` (frontend-standards §«Confini fra domini»). Gli altri domini li importano quando le loro tabelle puntano a quelle entita' (vendite, magazzino, pagamenti, pratiche, amministrazione).

#### Form

| Componente | Scopo | Props chiave | Esempio d'uso |
| --- | --- | --- | --- |
| `SoggettoForm` | Form universale PF/PG/ENTE con genera CF e validazione | `form`, `tipiSoggetto`, `isPF`, `showPartitaIva` | SoggettoDrawer |
| `ContattoForm` | Form contatto (nominativo, email, tel, pec, tipo, UO) | `form`, `tipiContatto`, `unitaOrganizzative` | ContattiSoggettoDrawer |
| `IndirizzoSoggettoForm` | Form indirizzo con barra multi-tipo, via_obj, check duplicato | composable props | SoggettoDrawer |
| `DatiSocietariForm` | Form dati societari (FG, REA, capitale, FE) | `form`, `formeGiuridiche`, `provinceLookup` | SoggettoDrawer |
| `ContoBancarioForm` | Form conto bancario: IBAN autocomplete, filiale, uso, date, flags | `form`, `usiDisponibili` | ContiBancariDrawer |

#### Autocomplete geografici

| Componente | Scopo | Props chiave | Esempio d'uso |
| --- | --- | --- | --- |
| `ComuneAutocomplete` | Autocomplete comune con ricerca server + initialItem | `modelValue`, `initialItem` | IndirizzoDrawer |
| `StradarioAutocomplete` | Autocomplete stradario filtrato per comune | `modelValue`, `comuneId` | IndirizzoDrawer |
| `StradarioGeneraleAutocomplete` | Autocomplete vie su stradario_generale (tutta Italia) | `modelValue` | IndirizzoDrawer (via nuova) |

#### Drawer dominio (gestione soggetto)

| Componente | Scopo | Esempio d'uso |
| --- | --- | --- |
| `IndirizziSoggettoDrawer` | Gestione indirizzi soggetto: multi-tipo, replace, auto-clone, addressNotFound | SoggettoDrawer |
| `ContattiSoggettoDrawer` | Gestione contatti soggetto: lista, CRUD, validazione email/PEC | SoggettoDrawer |
| `ContiBancariDrawer` | Gestione conti bancari soggetto: lista, CRUD, autocomplete IBAN/filiale | SoggettoDrawer |

#### Drawer e SearchTable geografici

| Componente | Scopo | Esempio d'uso |
| --- | --- | --- |
| `ComuneDrawer` + `ComuniSearchTable` | CRUD comuni | IndirizziView |
| `ProvinceDrawer` + `ProvinceSearchTable` | CRUD province | IndirizziView |
| `RegioniDrawer` + `RegioniSearchTable` | CRUD regioni | IndirizziView |
| `StatiDrawer` + `StatiSearchTable` | CRUD stati | IndirizziView |
| `ToponomasticaDrawer` + `ToponomasticaSearchTable` | CRUD toponomastica | IndirizziView |
| `CodiciPostaliDrawer` + `CodiciPostaliSearchTable` | CRUD codici postali | IndirizziView |
| `ConfigTablePanel` + `GenericConfigDrawer` | CRUD generico dei vocabolari della lista a DB `config.tabelle_gestibili` (`pannello`; metadata-driven: etichette i18n, FK→lookup, date) | ConfigView |

#### Building block dominio — soggetti e contatti

| Composable | Scopo | Esempio d'uso |
| --- | --- | --- |
| `useSoggettoForm` | Stato form soggetto PF/PG/ENTE, matrice indirizzi, validazione | SoggettoDrawer |
| `useContattoForm` | Stato form contatto con validazione email/PEC | ContattiSoggettoDrawer |
| `useContoBancarioForm` | Stato form conto bancario: IBAN autocomplete, filiale, uso, payload create/update | ContiBancariDrawer |
| `useDatiSocietariForm` | Stato form dati societari con policy forma giuridica | SoggettoDrawer |
| `useAuthUser` | Stato form credenziali + permessi operatore | OperatoreDrawer |

#### Building block dominio — indirizzi (gerarchia)

| Composable | Scopo | Esempio d'uso |
| --- | --- | --- |
| `useIndirizzoBase` | Composable condiviso: comune, via (via_obj unificato), CAP auto-set, civico, check duplicato, addressNotFound | IndirizzoDrawer |
| `useIndirizzoSoggettoForm` | Estende useIndirizzoBase: multi-tipo, libera, auto-clone, toPayloadArray | SoggettoDrawer |
| `useIndirizzoMultiTipo` | Barra tag tipo indirizzo con snapshot/restore per cambio tipo | useIndirizzoSoggettoForm |
| `useIndirizzoDuplicato` | Check duplicato indirizzo via API con exact_match + indirizzoWarnings | useIndirizzoBase |

### Utility (`core/utils/`)

| Utility | Scopo | Esempio d'uso |
| --- | --- | --- |
| `date.js` → `toDateString(d)` | Converte Date/string in 'YYYY-MM-DD' (ora locale, no bug UTC). ⛔ Mai `toISOString()` su una data del DatePicker: è la mezzanotte locale, in UTC diventa il giorno prima (la scadenza qualifica del fornitore si salvava così, corretto il 2026-10-04). Presidio: `core/utils/datePresidio.spec.js` (nessun `toISOString()` fuori da `date.js`) | TemplateVersioniSection |
| `segnoFiltri.js` → `segnoFiltri(filtri, chiavi, defaults, neutri)` | Il segno dei filtri attivi in una funzione pura → `{stato, conteggio, modificato}`: niente / numero grigio (solo default) / numero blu. ⭐ `modificato` esce perché «niente restringe» e «c'è qualcosa da riportare al default» sono due domande diverse, e i valori neutri le hanno separate: la seconda è ciò che tiene vivo «Pulisci filtri» | `FiltriLista` |
| `clonaFiltri.js` → `clonaValore` / `clonaFiltri` / `congelaProfondo` | Stacca un valore di filtro dal letterale che lo dichiara. ⛔ Lo spread e `Object.freeze` sono di **primo livello**: un default ad array resterebbe condiviso per riferimento, e il primo `push` del widget sposterebbe il metro insieme alla cosa misurata | `useContrattoFiltriLista` |

### Costanti (`core/constants.js`)

| Costante | Scopo |
| --- | --- |
| `DRAWER_WIDTH` | Larghezze drawer: SIMPLE, STANDARD, COMPLEX, WIDE, WIDE_PLUS, XLARGE (§«Larghezze standard») |
| `DATE_FORMAT` | Formato data PrimeVue DatePicker (`dd/mm/yy`). ⛔ Sede unica: ogni `DatePicker` lo riceve come `:date-format="DATE_FORMAT"`, e il locale di PrimeVue (`core/primevue-locale.js`) lo usa come default — fino al 2026-10-03 il letterale era scritto a mano in 27 punti. ⭐ Il selettore del **mese** (`view="month"`) riceve `MONTH_FORMAT` (`mm/yy`), mai `DATE_FORMAT` (mostrerebbe un giorno su un campo che non ne ha; regola del 2, 2026-10-04). Presidio: `core/utils/datePresidio.spec.js` (nessun formato letterale fuori da `constants.js`/`primevue-locale.js`) |
| `TOAST_DURATION` | Durata toast: SUCCESS, INFO, WARN, ERROR, ERROR_CON_SOLUZIONE, SYSTEM_ERROR, AZIONI (§«Notifiche») |
| `TABS` | Max tab aperti |
| `BREAKPOINTS` | Breakpoint responsive (MOBILE, TABLET) |
| `SHORTCUTS` | Shortcut tastiera (Ctrl+K, Ctrl+Tab, ecc.) |

### CSS globale (`assets/main.css`)

| Classe | Scopo |
| --- | --- |
| `.app-page` | Layout pagina full-height |
| `.app-tab-content` | Contenuto tab full-height |
| `.app-page-toolbar` | Toolbar con filtri + bottone nuovo |
| `.app-page-filters` | Container filtri nella toolbar — lo rende `FiltriLista`, non si scrive a mano |
| `.app-page-toolbar-start` | Zona sinistra della toolbar che filtri NON porta (titolo, pulsante «torna»). ⛔ Cancello a zero: un filtro qui dentro è un difetto |
| `.app-filter-w-sm\|md\|lg` | Le tre taglie di un filtro in linea (10 / 13 / 16rem) — al posto della larghezza nel tag |
| `.app-filtro-largo` | Leva per il filtro che a mezza riga non si legge: riga intera dentro il drawer |
| `.app-filtro-periodo` | I due estremi del periodo affiancati (`FiltroPeriodo`) |
| `.app-filtro-toggle` | Interruttore di filtro in linea (`FiltroToggle`) |
| `.app-datatable` | Stile DataTable (stripe, padding, paginator compatto) |
| `.app-drawer-content` | Layout contenuto drawer (flex column, gap) |
| `.app-drawer-section` | Separatore sezione nel drawer (h4 + border) |
| `.app-input-with-action` | Input con bottone azione affiancato (es. genera CF) |
| `.form-grid` | Griglia form a colonna singola |
| `.form-grid-2col` | Griglia form a 2 colonne (responsive) |
| `.form-field` | Campo form con label + input |
| `.app-readonly` | Overlay sola lettura: pointer-events none, opacity 0.85 |
| `.app-escape` | Escludi da readonly (pulsanti consultazione restano cliccabili) |
| `.app-empty-state` | Layout centrato per stati vuoti |
| `.app-loading` | Spinner loading centrato |
| `.app-action-btn` | Pulsante azione interno al form |
| `.app-field-error` | Messaggio errore campo |
| `.p-drawer-title` | Stile globale titolo drawer (centrato, verde) |

### Backend — Utility riutilizzabili

| Modulo | Scopo | Esempio d'uso |
| --- | --- | --- |
| `anagrafiche/services/_validators.py` | `require_str`, `optional_str`, `create_with_dedup`, `update_with_dedup` | Tutti i service anagrafiche |
| `anagrafiche/services/cf_validator_it.py` | Validazione congruenza CF + generazione CF (con omocodia) | SoggettiService |
| `core/utils/date.js` | `toDateString()` — conversione date frontend→backend | TemplateVersioniSection |
| `core/api/endpoint_helpers.py` | `handle_post_json` — wrapper POST con parsing + error handling | Tutte le view |
| `core/api/payload_validators.py` | `optional_int`, `optional_bool`, `paginated_envelope`, `parse_list_params` | Tutte le view |
| `core/services/error_manager.py` | `ErrorManager.require`, `ServiceError` | Tutti i service |

---

*ZeroERP Frontend Standards — ultimo aggiornamento 26 settembre 2026*
*Sviluppo Concentrico — anello esterno, radici nell'infrastruttura*
