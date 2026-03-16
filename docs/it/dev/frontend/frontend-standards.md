# ZeroERP — Standard Frontend

> Questo documento definisce le regole di progettazione e sviluppo dell'interfaccia utente di ZeroERP.
> È vincolante per qualsiasi contributo al frontend. Le deroghe devono essere documentate e motivate.
>
> Aggiornato: 15 marzo 2026

---

## Stack tecnologico

| Componente | Versione | Ruolo                   |
| ---------- | -------- | ----------------------- |
| Vue.js     | 3.5.x    | Framework UI            |
| Vite       | 8.x      | Build tool e dev server |
| PrimeVue   | 4.5.x    | Libreria componenti     |
| PrimeIcons | latest   | Iconografia             |
| Pinia      | 3.x      | Gestione stato          |
| Vue Router | 5.x      | Navigazione             |
| vue-i18n   | 10.x     | Multilingua             |
| Axios      | latest   | Client HTTP             |
| Node.js    | 24 LTS   | Runtime di sviluppo     |

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
  router/             ← definizione rotte
  stores/             ← store Pinia globali (auth, ui, tabs, navigation, context)
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
```

`core/` e' l'equivalente frontend di `dbops` e `script`: nessun dominio lo chiama esplicitamente, ma tutti dipendono da lui.

---

## Principio di omogenita' UI

> **L'operatore deve sentirsi a casa in ogni schermata.**

Tutte le UI seguono gli stessi pattern visivi e comportamentali. Non esistono eccezioni per dominio.
Se un pattern viene migliorato, il miglioramento si applica a tutte le schermate — mai a una sola.

Le regole di consistenza sono:

1. **Un solo modo di fare ogni cosa** — lista, form, filtri, paginazione, notifiche
2. **Stesso layout ovunque** — toolbar + tabella + drawer, senza varianti
3. **Stessi componenti ovunque** — `NewButton`, `DrawerFooter`, `useSearchTable`, Tag per stati
4. **Stesse classi CSS ovunque** — `app-page`, `app-datatable`, `form-grid`, mai CSS scoped per layout
5. **Nessun testo hardcoded** — tutto via `$t()`, sempre
6. **Modifiche al pattern devono essere globali** — se cambi il paginator, cambi `useSearchTable` una volta e tutte le liste si aggiornano

---

## Layout generale

```
┌─────────────────────────────────────────────────────────┐
│                       TOPBAR (48px)                      │
├──────────┬──────────────────────────────────────────────┤
│          │  CONTENT TABS (tab aperti, multi-entita')    │
│          ├──────────────────────────────────────────────┤
│ SIDEBAR  │  BREADCRUMB                                  │
│ (240px)  ├──────────────────────────────────────────────┤
│          │                                              │
│          │           AREA CONTENUTO                     │
│          │                                              │
└──────────┴──────────────────────────────────────────────┘
```

### Sidebar sinistra

- Sempre visibile, collassabile (56px collassata, 240px espansa)
- Stato a tre fasi: HOME (domini L1) → DOMINIO (voci L2) → collassata (icone + tooltip)
- Preferenza persistita in localStorage
- Configurazione centralizzata in `core/navigation.js` — una sola fonte di verita'
- Logo e nome applicazione in cima, logout e comprimi in fondo
- Mobile (< 768px): overlay drawer invece di sidebar fissa

### Topbar

- Altezza fissa 48px
- Profilo utente con badge ruolo (ADMIN/OPERATIVO)
- Pulsante ricerca universale (Ctrl+K)
- Sessioni attive con pannello espandibile

### Content Tabs

- Barra tab sotto la topbar per navigazione multi-entita'
- Massimo 10 tab aperti (configurabile in `constants.js`)
- KeepAlive per preservare lo stato dei tab
- Shortcut: Ctrl+W chiude tab, Ctrl+Tab prossimo, Ctrl+Shift+Tab precedente
- Tab label derivata automaticamente da route meta via `resolveTabLabel()`

### Area contenuto

- Occupa tutto lo spazio rimanente (flex: 1)
- Padding uniforme (`--app-content-padding: 1rem`)
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

### Regole fisse

- **Paginazione SOPRA** la tabella (`paginatorPosition: 'top'`)
- **Indicatore pagina**: `1/5` con JumpToPageDropdown per salto diretto
- **Font compatto** sul paginator (`0.8rem`)
- **Pulsante Nuovo**: componente `NewButton` — label fisso `$t('common.new')`, tooltip contestuale
- **Click riga** → apre drawer in edit (no colonna azioni con icone)
- **Nessuna colonna azioni** — l'interazione e' tramite click riga
- **Filtri** sopra la tabella nella toolbar, flex-wrap per responsive
- **Ricerca** con debounce 400ms (gestito da `useSearchTable`)
- **DataTable** sempre con: `lazy`, `removable-sort`, `striped-rows`, `scrollable`, `scrollHeight="flex"`

### Classi CSS standard

| Classe             | Dove applicare                    | Scopo                                         |
| ------------------ | --------------------------------- | --------------------------------------------- |
| `app-page`         | Div root della view               | Flex column, riempie altezza                  |
| `app-page-toolbar` | Contenitore filtri + azione       | Flex row, space-between                       |
| `app-page-filters` | Gruppo filtri                     | Flex wrap                                     |
| `app-datatable`    | DataTable                         | Font compatto, padding ridotto, stripe, hover |
| `app-page-action`  | Pulsanti azione (via `NewButton`) | Responsive: solo icona su mobile              |

### Composable `useSearchTable(store)`

Centralizza debounce search, onPage, onSort e paginatorProps. Tutti i componenti lista lo usano:

```js
const { searchText, onPage, onSort, paginatorProps } = useSearchTable(store)
```

```html
<DataTable v-bind="paginatorProps" lazy @page="onPage" @sort="onSort" ...>
```

Nessun componente lista deve implementare onPage/onSort/debounce manualmente.

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

### Regole

- Usare PrimeVue `TabView` con `lazy` (carica il contenuto solo quando il tab e' attivo)
- Il div root della vista ha `class="app-page"` — il TabView si espande per riempire l'altezza
- Il componente dentro ogni TabPanel ha `class="app-tab-content"` per propagare il flex
- Ogni tab contiene un **SearchTable** riutilizzabile (non logica inline nella vista)
- I drawer sono dichiarati nella vista, fuori dal TabView

### CSS automatico

Le classi in `main.css` gestiscono la catena flex: `.app-page > .p-tabview > .p-tabview-panels > .p-tabview-panel > .app-tab-content` — tutto automatico, nessun CSS scoped necessario.

---

## Drawer (nuovo e modifica)

**Regola unica: qualsiasi form di inserimento o modifica si apre sempre in un drawer laterale destro.**

### Comportamento

- Si apre da destra con animazione slide
- La lista rimane visibile sullo sfondo
- Si chiude con: `ESC`, clic fuori, pulsante Annulla, o salvataggio riuscito
- Non e' possibile aprire due drawer contemporaneamente

### Larghezze standard (da `constants.js`)

| Tipo     | Larghezza | Esempio                            |
| -------- | --------- | ---------------------------------- |
| SIMPLE   | 480px     | Toponomastica, lookup, config      |
| STANDARD | 640px     | Indirizzi, anagrafiche             |
| COMPLEX  | 800px     | Pratiche, contratti                |
| WIDE     | 960px     | Ricerca universale, form complessi |

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
│   DrawerFooter                   │  ← componente riutilizzabile
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

### Componente `DrawerFooter`

Footer standard Annulla/Salva — mai duplicare i pulsanti inline:

```html
<DrawerFooter :loading="loading" :disabled="!canSave" @save="handleSave" @cancel="close" />
```

### Classi CSS form

| Classe               | Scopo                                                   |
| -------------------- | ------------------------------------------------------- |
| `app-drawer-content` | Wrapper contenuto drawer (flex column, gap)             |
| `form-grid`          | Contenitore campi (flex column, gap 0.75rem)            |
| `form-field`         | Coppia label + input (flex column, gap 0.25rem)         |
| `form-grid-2col`     | Griglia 2 colonne responsive (1 colonna sotto 480px)    |
| `app-drawer-footer`  | Footer fisso in basso (flex, justify-content: flex-end) |

---

## Componenti riutilizzabili (building block)

### Principio

Ogni sotto-area che potrebbe essere usata in piu' di un contesto deve essere un **componente autonomo** in `core/components/`. I componenti specifici di un solo dominio stanno in `<dominio>/components/`.

### Checklist prima di creare un componente

1. **Esiste gia'?** — controllare `core/components/` e `core/composables/`
2. **Servira' altrove?** — se si', collocare in `core/`; se no, in `<dominio>/components/`
3. **Props minimali** — esporre solo cio' che varia tra i contesti
4. **Emits chiari** — `@saved`, `@row-click`, `@new`, `update:modelValue`
5. **i18n** — tutti i testi tramite `$t()`, mai hardcoded
6. **Responsive** — testare su mobile (flex-wrap, no larghezze fisse)

### Componenti core gia' implementati

**Layout e navigazione:**

| Componente          | Scopo                                                  |
| ------------------- | ------------------------------------------------------ |
| `AppLayout.vue`     | Layout master: sidebar + topbar + tabs + contenuto     |
| `AppTopbar.vue`     | Topbar con profilo, ricerca, sessioni                  |
| `AppSidebar.vue`    | Sidebar morfica a 3 stati                              |
| `AppBreadcrumb.vue` | Breadcrumb derivato da route meta                      |
| `ContentTabs.vue`   | Barra tab multi-entita' con KeepAlive                  |
| `SearchDrawer.vue`  | Ricerca universale soggetti (WIDE)                     |
| `StatusPage.vue`    | Pagina stato riutilizzabile (errore, WIP, placeholder) |

**Form building block:**

| Componente                  | Scopo                                                  |
| --------------------------- | ------------------------------------------------------ |
| `SoggettoForm.vue`          | Form universale PF/PG/ENTE guidato da matrice DB       |
| `AuthUserForm.vue`          | Form credenziali (username, email, password)           |
| `ComuneAutocomplete.vue`    | Autocomplete comuni server-side                        |
| `StradarioAutocomplete.vue` | Autocomplete stradario filtrato per comune             |
| `NewButton.vue`             | Pulsante "+ Nuovo" con tooltip contestuale, responsive |
| `DrawerFooter.vue`          | Footer drawer Annulla/Salva standardizzato             |

**SearchTable (DataTable riutilizzabili):**

| Componente                     | Scopo                        | Riuso                   |
| ------------------------------ | ---------------------------- | ----------------------- |
| `ToponomasticaSearchTable.vue` | Lista toponomastica con CRUD | Tab gestione geografica |
| `ComuniSearchTable.vue`        | Lista comuni con creazione   | Tab gestione geografica |
| `ProvinceSearchTable.vue`      | Lista province con CRUD      | Tab gestione geografica |
| `RegioniSearchTable.vue`       | Lista regioni con CRUD       | Tab gestione geografica |
| `StatiSearchTable.vue`         | Lista stati con CRUD         | Tab gestione geografica |

**Drawer CRUD:**

| Componente                | Scopo                                     |
| ------------------------- | ----------------------------------------- |
| `ToponomasticaDrawer.vue` | CRUD toponomastica (SIMPLE)               |
| `ComuneDrawer.vue`        | Creazione comuni (SIMPLE)                 |
| `ProvinceDrawer.vue`      | CRUD province con select regione (SIMPLE) |
| `RegioniDrawer.vue`       | CRUD regioni con select stato (SIMPLE)    |
| `StatiDrawer.vue`         | CRUD stati con 6 campi (STANDARD)         |

---

## Composable centralizzati

| Composable                           | Scopo                                                        | Usato da                  |
| ------------------------------------ | ------------------------------------------------------------ | ------------------------- |
| `useSearchTable(store)`              | Debounce search, onPage, onSort, paginatorProps              | Tutti i SearchTable       |
| `useTabFreshness(store, entityType)` | Inter-tab refresh su data change + cleanup                   | Tutti i SearchTable       |
| `useDrawerState()`                   | Stato drawer reactive (visible, mode, itemId, itemData)      | Tutte le viste con drawer |
| `useApiHandler()`                    | Wrapper API con loading, toast automatici, error handling    | Tutti i componenti        |
| `useNotify()`                        | Toast centralizzati (success, error, systemError)            | Via useApiHandler         |
| `useLookup(fetchFn)`                 | Cache generica per lookup dropdown                           | Form con select           |
| `useServerAutocomplete(searchFn)`    | Ricerca server con debounce (min 2 char, 300ms)              | Autocomplete              |
| `useSoggettoForm(options)`           | State universale PF/PG/ENTE guidato da matrice DB            | SoggettoForm              |
| `useAuthUser()`                      | State credenziali con password match                         | AuthUserForm              |
| `usePagination()`                    | Stato paginazione server-side (legacy, usare useSearchTable) | SearchDrawer              |
| `useTabEvents()`                     | Event bus inter-tab (emitDataChanged, onDataChanged)         | Store + SearchTable       |
| `useConfirmAction()`                 | Dialog conferma azioni distruttive                           | Drawer con delete         |

---

## Pulsante Nuovo — `NewButton`

Il pulsante di creazione ha un comportamento standard su tutte le schermate:

```html
<NewButton :tooltip="t('indirizzi.nuovo_indirizzo')" @click="drawer.openCreate" />
```

- **Label fisso**: `$t('common.new')` → "Nuovo" (mai personalizzare il label)
- **Tooltip contestuale**: descrive l'azione specifica (es. "Nuovo Indirizzo", "Nuova Toponomastica")
- **Icona**: `pi pi-plus`
- **Responsive**: su tablet (< 1024px) mostra solo l'icona, il testo e' nel tooltip

---

## Tag stato (attivo/non attivo)

Quando una riga ha un campo `attivo`, lo stato si mostra con un `Tag` PrimeVue:

```html
<Tag :value="data.attivo ? t('indirizzi.attivo') : t('indirizzi.non_attivo')"
     :severity="data.attivo ? 'success' : 'warn'" />
```

Severita' standard: `success` = verde (attivo), `warn` = arancione (non attivo).
Mai usare colori diversi per lo stesso concetto.

---

## Responsive

| Breakpoint | Dispositivo | Comportamento                                            |
| ---------- | ----------- | -------------------------------------------------------- |
| >= 1024px  | Desktop     | Layout completo: sidebar inline, tutti i filtri visibili |
| 768-1023px | Tablet      | Pulsanti azione solo icona + tooltip, filtri flex-wrap   |
| < 768px    | Mobile      | Sidebar overlay, padding ridotto                         |

Le classi responsive sono in `main.css` — nessun `@media` nei componenti scoped.
Il breakpoint mobile e' gestito dallo store `ui.js` (`isMobile`, `isTablet`).

---

## Login

La schermata di login e' l'unica pagina senza sidebar e topbar.

- Centrata verticalmente e orizzontalmente
- Logo ZeroERP in cima
- Form con campi: **Username** e **Password**
- Pulsante **Accedi** (larghezza piena del form)
- Messaggio di errore inline (non toast)
- Nessun link "Registrati" — accesso solo su invito

---

## Conferma azioni distruttive

Qualsiasi azione irreversibile richiede un **dialog di conferma** centrato:

- Titolo + nome dell'elemento coinvolto
- Due pulsanti: **Annulla** (secondario) e **Conferma** (primario, rosso per distruttive)
- Il dialog si chiude solo tramite pulsanti — non con ESC o clic fuori
- Gestito da `useConfirmAction()` — mai creare dialog custom

---

## Notifiche

| Tipo               | Componente | Posizione      | Durata                         |
| ------------------ | ---------- | -------------- | ------------------------------ |
| Successo           | Toast      | Alto a destra  | 3 secondi                      |
| Errore operativo   | Toast      | Alto a destra  | 5 secondi (chiusura manuale)   |
| Errore validazione | Inline     | Sotto il campo | Fino a correzione              |
| Errore di sistema  | Toast      | Alto a destra  | Persistente (chiusura manuale) |

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

### Struttura chiavi

| Sezione                | Contenuto                                                        |
| ---------------------- | ---------------------------------------------------------------- |
| `common.*`             | Termini riutilizzabili (salva, annulla, cerca...)                |
| `nav.*`                | Label domini L1                                                  |
| `nav_menu.<dominio>.*` | Label voci L2                                                    |
| `indirizzi.*`          | Etichette gestione geografica (indirizzi, toponomastica, comuni) |
| `geo.*`                | Etichette province, regioni, stati                               |
| `amm.*`                | Etichette amministrazione software                               |
| `notifications.*`      | Messaggi toast                                                   |
| `errors.*`             | Messaggi pagine errore                                           |

Ogni nuova stringa va aggiunta **in entrambi i file** (`it.json` e `en.json`) contemporaneamente.

---

## Stili CSS

### Architettura a due livelli

| Livello  | Prefisso  | Fonte       | Ruolo                   |
| -------- | --------- | ----------- | ----------------------- |
| PrimeVue | `--p-*`   | Tema Aura   | Colori base, tipografia |
| ZeroERP  | `--app-*` | `theme.css` | Variabili applicative   |

I componenti usano **solo** `--app-*`. Mai `var(--p-*)` direttamente.

### `theme.css` — personalizzazione visiva

Unico punto di personalizzazione: sidebar, topbar, contenuto, card, drawer, transizioni, tipografia.
Importato prima di `main.css` in `main.js`.

### `main.css` — classi utility globali

| Classe               | Scopo                                                     |
| -------------------- | --------------------------------------------------------- |
| `app-page`           | Wrapper root view (flex column, flex:1, overflow:hidden)  |
| `app-page-toolbar`   | Barra filtri + azioni (flex, space-between, wrap)         |
| `app-page-filters`   | Gruppo filtri (flex, wrap, gap)                           |
| `app-page-action`    | Pulsanti azione — responsive: solo icona su mobile        |
| `app-datatable`      | DataTable compatta (font ridotto, padding, stripe, hover) |
| `app-drawer-content` | Wrapper contenuto drawer (flex column, gap)               |
| `app-drawer-footer`  | Footer drawer Annulla/Salva (flex, justify-end)           |
| `form-grid`          | Contenitore campi form (flex column, gap)                 |
| `form-field`         | Coppia label + input (flex column, gap ridotto)           |
| `form-grid-2col`     | Griglia 2 colonne responsive (1 col < 480px)              |
| `app-tab-content`    | Wrapper contenuto tab per flex height                     |

### Regole CSS per i componenti

- Sempre `<style scoped>` — mai globale (eccetto `main.css`)
- `:deep()` solo per override PrimeVue, mai per componenti custom
- **Nessun CSS scoped per layout form** — usare classi `main.css`
- Se serve un nuovo pattern layout, aggiungerlo a `main.css` come classe globale
- Mai hardcodare colori — usare variabili `--app-*`

---

## Sicurezza

### Autenticazione JWT

| Meccanismo      | Dove              | Descrizione                               |
| --------------- | ----------------- | ----------------------------------------- |
| Route guard     | `router/index.js` | Tutte le rotte protette di default        |
| Token refresh   | `core/api.js`     | Interceptor su 401, retry automatico      |
| Accodamento     | `core/api.js`     | Richieste durante refresh accodate        |
| Protezione loop | `core/api.js`     | Chiamate a `/token/` escluse dal refresh  |
| Redirect        | `LoginView`       | Rotta originale salvata in `?redirect=`   |
| Logout          | `stores/auth.js`  | `clearTokens()` pulisce tutta la sessione |

### Regole di sicurezza

- Mai accedere a `localStorage` direttamente — usare `useAuthStore()`
- Mai `window.location` per redirect — usare il router
- Mai esporre dati sensibili in log, template o attributi HTML
- Mai costruire URL con interpolazione da input utente — usare parametri Axios

---

## Gestione errori API

I componenti **non gestiscono errori manualmente**. Il composable `useApiHandler` intercetta, estrae il messaggio dall'envelope backend e mostra il toast.

```js
// Caricamento (toast solo su errore)
const data = await execute(() => api.get('/endpoint/', { params }))

// Salvataggio (toast su successo e errore)
const result = await execute(
  () => store.create(payload),
  { successMessage: t('notifications.save_success') }
)

// Polling silenzioso (nessun toast)
const status = await execute(() => api.get('/status/'), { silent: true })
```

---

## Regole per il developer

1. Ogni componente e' autonomo — logica nei composables di `core/`
2. Chiamate API passano da `useApiHandler` — mai `api.get/post` nei componenti
3. Toast via `useNotify()` — mai `useToast()` direttamente
4. Dialog conferma via `useConfirmAction()` — mai `useConfirm()` direttamente
5. Drawer usano PrimeVue `Drawer` + `DrawerFooter` — mai pulsanti inline
6. Testi visibili via `$t()` — mai stringhe hardcoded
7. Nessun `console.log` in produzione
8. Componenti di dominio non importano da altri domini — solo da `core/`
9. Larghezze drawer da `constants.js` — mai hardcoded
10. Navigazione da `navigation.js` — mai duplicata
11. Paginazione/sort/search da `useSearchTable` — mai implementata manualmente
12. Inter-tab freshness da `useTabFreshness` — mai `useTabEvents` direttamente
13. Stato drawer da `useDrawerState` — mai `ref(false)` + `ref('create')` separati
14. CSS layout da `main.css` — mai `<style scoped>` per layout form/pagina

---

*ZeroERP Frontend Standards — rev. 5 (15 marzo 2026)*
*Sviluppo Concentrico — anello esterno, radici nell'infrastruttura*
