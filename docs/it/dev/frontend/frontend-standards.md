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

### Empty state — liste che partono vuote (standard)

Le liste che possono selezionare troppi dati partono **vuote** e mostrano un placeholder
finche' l'utente non applica una ricerca (min 3 caratteri) o un filtro.

**Componenti coinvolti:**

| Elemento | Dove |
| --- | --- |
| `SearchHint.vue` | `core/components/` — placeholder riutilizzabile (icona search + messaggio) |
| `hasSearched` | Nello store Pinia — `ref(false)`, diventa `true` dopo il primo fetch |
| Guardia in `fetchList()` | Nello store — blocca la chiamata API se non ci sono filtri attivi |

**1. Store — aggiungere `hasSearched` e guardia in `fetchList()`:**

```js
const hasSearched = ref(false)

async function fetchList() {
  const f = filters.value
  const searchTerm = (f.search || '').trim()
  const hasFilters = f.filtro_1 != null || f.filtro_2 != null // adattare ai filtri reali

  // Search con meno di 3 caratteri e nessun filtro attivo → ignora
  if (searchTerm.length > 0 && searchTerm.length < 3 && !hasFilters) return
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
    const params = {}
    if (searchTerm.length >= 3) params.search = searchTerm
    // ... costruzione params ...
    const res = await listEntita(params)
    items.value = res.data.data.results
    totalRecords.value = res.data.data.count
    hasSearched.value = true
  } finally {
    loading.value = false
  }
}

// Esporre hasSearched nel return
return { items, totalRecords, loading, hasSearched, filters, fetchList, ... }
```

**2. SearchTable — placeholder + fetch condizionale:**

```vue
<script setup>
import { onMounted } from 'vue'
import SearchHint from '../../core/components/SearchHint.vue'

const { searchText, ... } = useSearchTable(store, { ... })

useTabFreshness(store, 'entita')
// La lista parte vuota — salvo che arrivi con search precaricata da URL/context.
onMounted(() => {
  if (searchText.value) {
    store.fetchList()
  }
})
</script>

<template>
  <!-- Placeholder: nessuna ricerca effettuata -->
  <SearchHint v-if="!store.hasSearched && !store.loading" />

  <DataTable v-show="store.hasSearched || store.loading" ...>
    ...
  </DataTable>
</template>
```

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

- **Due DatePicker**: "Dal" (`data_da`) e "Al" (`data_a`) nella toolbar filtri
- **Default `data_da`**: 1 gennaio dell'anno corrente - 1 (es. `2025-01-01` se oggi e' `2026-03-29`)
- **`data_a`**: null (nessun limite superiore di default)
- Il filtro si applica su `data_insert` (o colonna data apertura dedicata se esiste)
- Backend: `WHERE data_insert >= data_da::date AND data_insert < (data_a::date + INTERVAL '1 day')`
- Il tiebreaker `id` nell'ORDER BY garantisce paginazione deterministica

**Implementazione nello store:**

```js
const defaultDataDa = `${new Date().getFullYear() - 1}-01-01`

const filters = ref({
  // ... altri filtri ...
  data_da: defaultDataDa,
  data_a: null,
})
```

**Implementazione nella SearchTable:**

```html
<DatePicker v-model="dataDaFilter" :placeholder="t('common.data_da')"
  date-format="dd/mm/yy" show-icon show-button-bar style="width: 150px;"
  @date-select="onDataDaChange" @clear-click="onDataDaChange" />
```

Le chiavi i18n `common.data_da` ("Dal") e `common.data_a` ("Al") sono condivise da tutte le liste.

### Scorciatoie da tastiera (Keyboard Shortcuts)

Scorciatoie globali per operatori ERP power user. Due meccanismi:

**1. `useKeyboardShortcuts(shortcuts)` — composable generico**

Per shortcut che NON devono attivarsi dentro input/textarea/select (evita conflitti con la digitazione).

```js
import { useKeyboardShortcuts } from '../composables/useKeyboardShortcuts'
useKeyboardShortcuts([
  { key: 'F5', ctrl: false, action: () => reload() },
])
```

Usato da: `useSearchTable` (F5 ricarica lista).

**2. Listener diretto `window.addEventListener('keydown')` — per shortcut che devono funzionare SEMPRE**

Per shortcut come Ctrl+S che devono attivarsi anche dentro un campo input.

```js
function onKeydown(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault()
    emit('save')
  }
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
```

Usato da: `DrawerFooter` (Ctrl+S salva).

**Shortcut attive:**

| Shortcut | Contesto | Azione | Componente |
|----------|----------|--------|------------|
| `F5` | Lista (DataTable) | Ricarica lista senza reload browser | `useSearchTable` |
| `Ctrl+S` | Drawer (qualsiasi) | Salva — rispetta disabled/loading/readonly | `DrawerFooter` |
| `Esc` | Drawer PrimeVue | Chiude drawer (nativo PrimeVue `dismissable`) | Drawer |
| `Ctrl+K` | Globale | Apre ricerca universale | `AppTopbar` |

**Regole:**
- `useKeyboardShortcuts` per shortcut che NON devono interferire con la digitazione
- Listener diretto per shortcut che devono funzionare SEMPRE (Ctrl+S, Ctrl+K)
- Sempre `e.preventDefault()` per evitare l'azione default del browser
- Sempre cleanup in `onUnmounted`

---

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

### Dove collocare un componente

| Criterio | Collocazione | Esempio |
| --- | --- | --- |
| Entita' config condivisa (tabelle `config.*`) usata o potenzialmente usabile da 2+ domini | `core/components/` | ToponomasticaSearchTable, ComuniSearchTable, ProvinceDrawer |
| Componente di layout, form o UI generico | `core/components/` | NewButton, DrawerFooter, SoggettoForm |
| Logica specifica di un solo dominio | `<dominio>/components/` | IndirizzoDrawer (via nuova + stradario), UtentePermessiTab |

**Eccezione documentata**: i componenti geografici (toponomastica, comuni, province, regioni, stati)
stanno in `core/components/` anche se importano stores da `anagrafiche/stores/`.
Questo perche' sono entita' config condivise che il backend serve da `anagrafiche` per
organizzazione, ma concettualmente sono cross-dominio (qualsiasi modulo potrebbe aver bisogno
di un filtro per comune o provincia). L'alternativa — duplicarli per dominio — violerebbe
il principio di riuso.

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

## Modalita' sola lettura (pattern "protect")

### Principio

Le autorizzazioni utente prevedono la **sola lettura** come livello di accesso. Tutti i form e le view devono essere progettati per supportare nativamente la modalita' read-only, senza duplicare componenti o creare varianti separate.

### Tecnica CSS "pannello protect"

Ispirata al formato protect AS/400: un unico overlay CSS blocca ogni interazione sulla view, senza toccare i componenti interni. Non si creano componenti `*ReadOnly.vue` separati.

```css
.app-readonly {
  pointer-events: none;     /* blocca ogni click, hover, focus */
  user-select: text;        /* permetti copia testo */
  opacity: 0.85;            /* feedback visivo: stai consultando */
}
```

### Come applicare

Ogni view/drawer che supporta la sola lettura wrappa il contenuto con la classe condizionale:

```vue
<div :class="{ 'app-readonly': isReadonly }">
  <!-- form, DataTable, drawer content — tutto normale -->
</div>
```

Il flag `isReadonly` viene derivato dalle autorizzazioni utente (permesso di scrittura assente sul dominio/entita').

### Tasti di uscita

Come F12/F3 sui formati protect AS/400, i **pulsanti di chiusura** restano attivi anche in modalita' protect:

```css
.app-readonly :deep(.p-drawer-close),    /* X chiudi drawer */
.app-readonly :deep(.p-dialog-close),    /* X chiudi dialog */
.app-readonly :deep(.app-escape) {       /* classe generica uscita */
  pointer-events: auto;
  cursor: pointer;
}
```

Regola: in sola lettura **si puo' solo chiudere/uscire**, mai aprire/creare/modificare.

### Impatto sui componenti

- **Non creare varianti read-only** di componenti esistenti — usare la classe `.app-readonly` sul container
- **DrawerFooter**: in sola lettura il footer (Annulla/Salva) non viene renderizzato (`v-if="!isReadonly"`)
- **NewButton**: in sola lettura non viene renderizzato (`v-if="!isReadonly"`)
- **DataTable row-click**: in sola lettura apre il drawer in modalita' consultazione (protect attivo)
- **Copia testo**: `user-select: text` garantisce che l'operatore possa sempre copiare dati con Ctrl+C

### Dove si usa

| Contesto | Trigger |
| --- | --- |
| Autorizzazioni utente | Permesso di scrittura assente sul dominio |
| Split view (futuro) | Pannello secondario affiancato sempre in sola lettura |

---

## Azioni processo — Livello 2 (pattern "action gate")

### Principio

Le azioni di processo controllano **singole operazioni** (es. "crea soggetto", "genera fatture") dentro un'area a cui l'operatore ha gia' accesso. Sono il livello di granularita' sotto TUTTO/LETTURA/BLOCCATO.

### Piramide permessi

```
Livello 1: Area (TUTTO / LETTURA / BLOCCATO)  → sidebar + route guard + .app-readonly
Livello 2: Azione processo (abilitata / negata) → prop action su NewButton / DrawerFooter
```

### Come funziona

L'endpoint `/me/` ritorna `azioni_abilitate: { codename: boolean }` per tutte le azioni attive. Lo store `auth.js` espone `isActionAllowed(codename)`.

I componenti `NewButton` e `DrawerFooter` accettano una prop opzionale `action`:
- Se **assente** (default): il componente funziona come prima (solo check readonly)
- Se **presente**: il componente si nasconde se l'azione non e' abilitata

```vue
<!-- Pulsante "Nuovo" visibile solo se l'azione e' abilitata -->
<NewButton action="crea_soggetto" :tooltip="t('...')" @click="..." />

<!-- Footer Salva visibile solo se l'azione e' abilitata -->
<DrawerFooter action="modifica_soggetto" @save="..." @cancel="..." />
```

### Come aggiungere un'azione

1. **DB**: inserire riga in `config.azioni_processo` (seed CSV)
2. **Backend**: aggiungere `post_permission = "codename"` sulla view API
3. **Frontend**: aggiungere prop `action="codename"` su `NewButton` o `DrawerFooter`
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
15. Sola lettura da classe `.app-readonly` sul container — mai componenti duplicati
16. Azioni processo via prop `action` su `NewButton`/`DrawerFooter` — mai `v-if` manuali per permessi
17. `ConfirmDialog` solo globale in `App.vue` — mai dentro Drawer (interferenza overlay)

---

## Catalogo componenti e composable riutilizzabili

> Prima di creare un nuovo componente o composable, verificare se esiste gia' in questo catalogo.
> I componenti in `core/` sono cross-dominio e non devono importare da domini specifici.

### Componenti UI (`core/components/`)

#### Layout e navigazione

| Componente | Scopo | Usato da |
| --- | --- | --- |
| `AppLayout` | Layout principale: sidebar + topbar + content area | root |
| `AppTopbar` | Topbar: azienda, titolo area, ricerca, sessioni, data | AppLayout |
| `AppSidebar` | Contenitore sidebar (logo + stato morfic) | AppLayout |
| `AppToolbar` | Toolbar meta-driven con tab e azioni | View con tab |
| `AppBreadcrumb` | Breadcrumb derivato da route meta | AppLayout |
| `ContentTabs` | Barra tab multi-entita con KeepAlive | AppLayout |
| `SidebarHome` | Sidebar stato HOME (lista domini L1) | AppSidebar |
| `SidebarDomain` | Sidebar stato DOMINIO (voci L2 + preferiti) | AppSidebar |
| `SidebarItem` | Voce sidebar riutilizzabile (icona + label) | SidebarHome, SidebarDomain |
| `LogoBrand` | Logo ZeroERP riutilizzabile | AppSidebar, LoginView |
| `StatusPage` | Template pagina stato (errore, placeholder) | ErrorView, PlaceholderView |
| `SearchDrawer` | Ricerca universale soggetti per ruolo con row expansion | AppLayout (Ctrl+K) |
| `SessioniAttivePanel` | Pannello sessioni attive in topbar | AppTopbar |

#### Infrastruttura drawer e liste

| Componente | Scopo | Props chiave | Usato da |
| --- | --- | --- | --- |
| `DrawerTitle` | Titolo standard drawer: azione sx + entita' centrata | `action`, `title` | Tutti i drawer |
| `DrawerFooter` | Footer drawer con Annulla/Salva, auto-hide in readonly | `loading`, `disabled` | Tutti i drawer |
| `NewButton` | Pulsante "Nuovo" nella toolbar, auto-hide in readonly | `tooltip` | Tutte le SearchTable |
| `PaginationInfo` | Info paginazione (es. "1-50 di 1234") | `pagination` | SearchTable |
| `TagList` | Lista tag con overflow +N e tooltip | `items`, `labelField`, `maxVisible`, `severity` | Ruoli in lista soggetti |
| `AppDrawer` | Drawer generico con header + footer + slot body | `title`, `width` | Utility wrapper |

#### Building block form

| Componente | Scopo | Props chiave | Usato da |
| --- | --- | --- | --- |
| `SoggettoForm` | Form universale PF/PG/ENTE con genera CF e validazione | `form`, `tipiSoggetto`, `isPF`, `showPartitaIva` | SoggettoDrawer, UtenteDrawer |
| `ContattoForm` | Form contatto (nominativo, email, tel, pec, tipo, UO) | `form`, `tipiContatto`, `unitaOrganizzative` | ContattiSoggettoDrawer |
| `IndirizzoSoggettoForm` | Form indirizzo con barra multi-tipo, via_obj, check duplicato | composable props | IndirizziSoggettoDrawer |
| `DatiSocietariForm` | Form dati societari (FG, REA, capitale, FE) | `form`, `formeGiuridiche`, `provinceLookup` | SoggettoDrawer |
| `ContoBancarioForm` | Form conto bancario: IBAN autocomplete, filiale, uso, date, flags | `form`, `usiDisponibili` | ContiBancariDrawer |
| `AuthUserForm` | Form credenziali operatore | `form`, `isEdit` | UtenteDrawer |

#### Autocomplete

| Componente | Scopo | Props chiave | Usato da |
| --- | --- | --- | --- |
| `ComuneAutocomplete` | Autocomplete comune con ricerca server + initialItem | `modelValue`, `initialItem` | IndirizzoDrawer, IndirizzoSoggettoForm |
| `StradarioAutocomplete` | Autocomplete stradario filtrato per comune | `modelValue`, `comuneId` | IndirizzoDrawer, IndirizzoSoggettoForm |
| `StradarioGeneraleAutocomplete` | Autocomplete vie su stradario_generale (tutta Italia) | `modelValue` | IndirizzoDrawer (via nuova) |

#### Drawer dominio (gestione soggetto)

| Componente | Scopo | Usato da |
| --- | --- | --- |
| `IndirizziSoggettoDrawer` | Gestione indirizzi soggetto: multi-tipo, replace, auto-clone, addressNotFound | SoggettoDrawer |
| `ContattiSoggettoDrawer` | Gestione contatti soggetto: lista, CRUD, validazione email/PEC | SoggettoDrawer |
| `ContiBancariDrawer` | Gestione conti bancari soggetto: lista, CRUD, autocomplete IBAN/filiale | SoggettoDrawer |

#### Drawer e SearchTable geografici

| Componente | Scopo | Usato da |
| --- | --- | --- |
| `ComuneDrawer` + `ComuniSearchTable` | CRUD comuni | IndirizziView |
| `ProvinceDrawer` + `ProvinceSearchTable` | CRUD province | IndirizziView |
| `RegioniDrawer` + `RegioniSearchTable` | CRUD regioni | IndirizziView |
| `StatiDrawer` + `StatiSearchTable` | CRUD stati | IndirizziView |
| `ToponomasticaDrawer` + `ToponomasticaSearchTable` | CRUD toponomastica | IndirizziView |
| `CodiciPostaliDrawer` + `CodiciPostaliSearchTable` | CRUD codici postali | IndirizziView |
| `ConfigTablePanel` + `GenericConfigDrawer` | CRUD generico 67 tabelle config | ConfigView |

### Composable (`core/composables/`)

#### Infrastruttura liste e drawer

| Composable | Scopo | Usato da |
| --- | --- | --- |
| `useSearchTable` | Paginazione, sort, search debounce, applyFilters per DataTable lazy | Tutte le SearchTable |
| `useDrawerState` | Stato drawer: visible, mode, itemId, itemData, openCreate(), editRow(), close() | Tutte le View con drawer |
| `useTabFreshness` | Refresh automatico lista su evento `dataChanged` | Tutte le SearchTable |
| `useTabEvents` | Event bus inter-tab per invalidazione dati | Store (emit), SearchTable (listen) |
| `useTabLabel` | Risoluzione label tab da route meta | ContentTabs |
| `useApiHandler` | Execute con loading, toast successo, gestione errori | Tutti i drawer |
| `useNotify` | Toast PrimeVue centralizzato — MAI importare useToast direttamente | useApiHandler |
| `useConfirmAction` | Dialogo conferma azione distruttiva | UtenteDrawer, delete |
| `useConfirmCloseTab` | Conferma chiusura tab con modifiche non salvate | ContentTabs |
| `useDirtyState` | Traccia modifiche non salvate (form dirty) | ContentTabs |
| `useLoading` | Stato loading generico (ref + toggle) | Componenti vari |
| `useKeyboardShortcuts` | Shortcut globali: Ctrl+K ricerca, Ctrl+W chiudi tab, Ctrl+Tab naviga | AppLayout |
| `usePagination` | Paginazione server-side (usato internamente da useSearchTable) | useSearchTable |

#### Lookup e autocomplete

| Composable | Scopo | Usato da |
| --- | --- | --- |
| `useLookup` | Caricamento lazy/eager di dati lookup con cache | Form con select/dropdown |
| `useServerAutocomplete` | Autocomplete con ricerca server debounce 300ms | ComuneAutocomplete, StradarioAutocomplete, StradarioGeneraleAutocomplete |

#### Building block dominio — soggetti e contatti

| Composable | Scopo | Usato da |
| --- | --- | --- |
| `useSoggettoForm` | Stato form soggetto PF/PG/ENTE, matrice indirizzi, validazione | SoggettoDrawer, UtenteDrawer |
| `useContattoForm` | Stato form contatto con validazione email/PEC | ContattiSoggettoDrawer |
| `useContoBancarioForm` | Stato form conto bancario: IBAN autocomplete, filiale, uso, payload create/update | ContiBancariDrawer |
| `useDatiSocietariForm` | Stato form dati societari con policy forma giuridica | SoggettoDrawer |
| `useAuthUser` | Stato form credenziali + permessi operatore | UtenteDrawer |

#### Building block dominio — indirizzi (gerarchia)

| Composable | Scopo | Usato da |
| --- | --- | --- |
| `useIndirizzoBase` | Composable condiviso: comune, via (via_obj unificato), CAP auto-set, civico, check duplicato, addressNotFound | IndirizzoDrawer, useIndirizzoSoggettoForm |
| `useIndirizzoSoggettoForm` | Estende useIndirizzoBase: multi-tipo, libera, auto-clone, toPayloadArray | IndirizziSoggettoDrawer |
| `useIndirizzoMultiTipo` | Barra tag tipo indirizzo con snapshot/restore per cambio tipo | useIndirizzoSoggettoForm |
| `useIndirizzoDuplicato` | Check duplicato indirizzo via API con exact_match + indirizzoWarnings | useIndirizzoBase |

#### Modalita sola lettura e azioni processo

| Composable | Scopo | Usato da |
| --- | --- | --- |
| `useReadonlyMode` | Provider: derive isReadonly da permessi area + provide | View (SoggettiView, IndirizziView, ConfigTablePanel) |
| `useInjectReadonly` | Consumer: inject isReadonly dal provider padre | NewButton, DrawerFooter, tutti i Drawer |
| `useActionPermission` | Verifica se un'azione processo e' abilitata (computed reattivo) | Componenti dominio con logica condizionale avanzata |

**Nota**: per i casi standard, usare la prop `action` su `NewButton`/`DrawerFooter` invece del composable diretto.

#### Ricerca universale

| Composable | Scopo | Usato da |
| --- | --- | --- |
| `useSearchDetail` | Fetch dettaglio soggetto per row expansion (livello 2) | SearchDrawer |

### Utility (`core/utils/`)

| Utility | Scopo | Usato da |
| --- | --- | --- |
| `date.js` → `toDateString(d)` | Converte Date/string in 'YYYY-MM-DD' (ora locale, no bug UTC) | SoggettoForm, SoggettoDrawer |

### Costanti (`core/constants.js`)

| Costante | Scopo |
| --- | --- |
| `DRAWER_WIDTH` | Larghezze drawer: SIMPLE, STANDARD, COMPLEX, WIDE |
| `DATE_FORMAT` | Formato data PrimeVue DatePicker (`dd/mm/yy`) |
| `TOAST_DURATION` | Durata toast: SUCCESS, ERROR, SYSTEM_ERROR |
| `PAGINATION` | Default righe e opzioni righe/pagina |
| `TABS` | Max tab aperti |
| `BREAKPOINTS` | Breakpoint responsive (MOBILE, TABLET) |
| `SHORTCUTS` | Shortcut tastiera (Ctrl+K, Ctrl+Tab, ecc.) |

### CSS globale (`assets/main.css`)

| Classe | Scopo |
| --- | --- |
| `.app-page` | Layout pagina full-height |
| `.app-tab-content` | Contenuto tab full-height |
| `.app-page-toolbar` | Toolbar con filtri + bottone nuovo |
| `.app-page-filters` | Container filtri nella toolbar |
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

| Modulo | Scopo | Usato da |
| --- | --- | --- |
| `anagrafiche/services/_validators.py` | `require_str`, `optional_str`, `create_with_dedup`, `update_with_dedup` | Tutti i service anagrafiche |
| `anagrafiche/services/cf_validator_it.py` | Validazione congruenza CF + generazione CF (con omocodia) | SoggettiService |
| `core/utils/date.js` | `toDateString()` — conversione date frontend→backend | SoggettoForm, SoggettoDrawer |
| `core/api/endpoint_helpers.py` | `handle_post_json` — wrapper POST con parsing + error handling | Tutte le view |
| `core/api/payload_validators.py` | `optional_int`, `optional_bool`, `paginated_envelope`, `parse_list_params` | Tutte le view |
| `core/services/error_manager.py` | `ErrorManager.require`, `ServiceError` | Tutti i service |

---

*ZeroERP Frontend Standards — rev. 9 (25 marzo 2026)*
*Sviluppo Concentrico — anello esterno, radici nell'infrastruttura*
