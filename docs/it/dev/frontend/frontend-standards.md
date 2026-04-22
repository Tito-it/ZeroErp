# ZeroERP — Standard Frontend

> Questo documento definisce le regole di progettazione e sviluppo dell'interfaccia utente di ZeroERP.
> È vincolante per qualsiasi contributo al frontend. Le deroghe devono essere documentate e motivate.
>
> Aggiornato: 15 marzo 2026
>
> Vedi anche:
>
> * [Catalogo building block frontend](catalogo-building-block-frontend.md) — inventario completo componenti, composable, utility, classi CSS

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
- **Click riga** → apre drawer in edit (modifica = interazione principale)
- **Colonna azioni** riservata alle **azioni secondarie** (apri sub-drawer, disattiva, ecc.) — mai mettere la modifica tra le azioni: e' il click riga. Vedi sotto "Colonna azioni di riga".
- **Filtri** sopra la tabella nella toolbar, flex-wrap per responsive
- **Ricerca** con debounce 400ms (gestito da `useSearchTable`)
- **DataTable** sempre con: `lazy`, `removable-sort`, `striped-rows`, `scrollable`, `scrollHeight="flex"`

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

Lo switch e' realizzato da `@media (hover: none), (max-width: 1024px)` in `main.css`
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
      icon: MANAGE_ICONS.CONTRATTI,
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
  <Column :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
    <template #body="{ data }">
      <RowActionsMenu :actions="buildRowActions(data)" />
    </template>
  </Column>
</template>
```

**Formato azione:**

```js
{
  key: string,              // identificatore univoco
  label: string,            // testo (tradotto, visibile nel popup + tooltip inline)
  icon: string,             // classe PrimeIcons (es. 'pi pi-ban' o MANAGE_ICONS.X)
  severity?: 'primary' | 'warn' | 'danger', // opzionale (vedi tabella sotto)
  visible?: boolean,        // default true — azioni non applicabili si nascondono
  disabled?: boolean,       // default false — azione grigia ma presente
  command: () => void,      // handler click
}
```

**Severity — colore inline e popup:**

| Severity | Inline (desktop) | Popup (tablet/touch) | Uso tipico |
| --- | --- | --- | --- |
| `undefined` | Blu (`app-manage-btn`) | Neutro | Default: apri sub-drawer, clona, gestisci |
| `'primary'` | Verde (`app-action-btn`) | Neutro | State transition positiva (attiva, approva) |
| `'warn'` | Arancio (PrimeVue `severity="warn"`) | Neutro | Cautela (chiudi, blocca, scade) |
| `'danger'` | Rosso (`app-delete-btn`) | Rosso (`app-menu-item-danger`) | Distruttivo (elimina, disattiva) |

Solo `danger` differenzia anche nel popup: per le altre severity la label + icona bastano a distinguere l'azione.

**Convenzioni centralizzate (niente valori hardcoded nelle liste):**

| Cosa | Dove |
| --- | --- |
| Icona kebab | `MANAGE_ICONS.KEBAB` in `src/core/constants.js` |
| Stile bottone standard | `.app-manage-btn` in `main.css` |
| Stile bottone distruttivo | `.app-delete-btn` in `main.css` |
| Larghezza colonna (auto / 60px) | `.app-col-actions` in `main.css` (media query) |
| Voce menu distruttiva | `.app-menu-item-danger` in `main.css` (eredita `--app-btn-delete-*`) |
| Tooltip fallback kebab | `common.altre_azioni` ("Altre azioni") in `it.json` |
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

| Classe                     | Dove applicare                    | Scopo                                                                      |
| -------------------------- | --------------------------------- | -------------------------------------------------------------------------- |
| `app-page`                 | Div root della view               | Flex column, riempie altezza                                               |
| `app-page-toolbar`         | Contenitore filtri + azione       | Flex row, space-between                                                    |
| `app-page-filters`         | Gruppo filtri                     | Flex wrap                                                                  |
| `app-datatable`            | DataTable                         | Font compatto, padding ridotto, stripe, hover                              |
| `app-page-action`          | Pulsanti azione (via `NewButton`) | Responsive: solo icona su mobile                                           |
| `app-col-actions`          | `<Column>` azioni di riga         | Larghezza auto su desktop, 60px su tablet/touch (media query `<=1024px`)   |
| `app-row-actions-inline`   | Interno `RowActionsMenu`          | Wrapper pulsanti inline — visibile solo con hover + viewport `>=1024px`    |
| `app-row-actions-compact`  | Interno `RowActionsMenu`          | Wrapper kebab + menu popup — visibile su touch o viewport `<1024px`        |
| `app-menu-item-danger`     | Voce `Menu` PrimeVue              | Colore rosso per azioni distruttive — applicato via `severity: 'danger'`   |

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
│ ═══════ Modifica riga ═══════                           │
│ Articolo: [ART-001 ...] (disabled)                      │
│ UoM: [kWh ▼]         Tipo: [CANONE ▼]                   │
│ Prezzo: [25.50]       Qta: [1]                           │
│ Ordine: [10]                                             │
│                            [Annulla]  [Salva]            │
├─────────────────────────────────────────────────────────┤
│                                          [Chiudi]        │
└─────────────────────────────────────────────────────────┘
```

### Regole del pattern

1. **Drawer largo**: usare `DRAWER_WIDTH.WIDE` (960px) per dare spazio alla lista + form
2. **Intestazione contesto**: in alto mostrare sempre i dati del parent (numero, cliente, stato, date). L'operatore deve sapere dove si trova senza tornare indietro. Tag stato allineato a destra
3. **Paginazione**: `paginator` con `rows="10"` e `rows-per-page-options="[10, 25]"`, `paginator-position="top"`, `data-key="id"`
4. **Pulsante Nuovo**: usare `NewButton` (componente standard), posizionato in alto a destra sopra la tabella come nelle liste principali
5. **Selezione riga**: `selection-mode="single"` + `v-model:selection`. Click riga popola il form in edit mode con `@row-select`
6. **Form dettaglio**: visibile SOLO quando attivo (Nuovo o click riga). Nascosto di default. Titolo "Nuova riga" o "Modifica riga"
7. **Articolo**: in create editabile (autocomplete), in edit disabled (immutabile)
8. **UoM**: filtrate per articolo via `listArticoloUom(articoloId)`, pre-seleziona la UoM base. Placeholder "Seleziona prima l'articolo" se nessun articolo scelto
9. **Salva/Annulla**: sempre in basso dopo il form. Salva crea o aggiorna, chiude form, emette `changed`. Annulla chiude form e deseleziona riga
10. **Elimina**: icona cestino sulla riga (`@click.stop` per non triggerare selezione). Se stavo editando quella riga, chiude il form
11. **`formMode`**: ref con 3 stati: `null` (nessun form), `'create'`, `'edit'`. Governa visibilita' e comportamento

### Riferimento implementativo

Primo caso: `ContrattoRigheDrawer.vue` (righe contratto pricing v5).

### Come applicare a una nuova sub-entita'

1. Copiare la struttura di `ContrattoRigheDrawer.vue` come base
2. Adattare le colonne DataTable e i campi del form
3. Passare le props contesto dal parent (numero/codice, cliente, stato, date)
4. Collegare le API CRUD (add/update/delete) allo store o direttamente
5. Mantenere `data-key="id"` + paginazione a 10 + `NewButton` + `@click.stop` sul cestino

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

### Componenti core e composable

Per l'inventario completo di componenti, composable, utility e classi CSS disponibili, consultare il [Catalogo Building Block Frontend](catalogo-building-block-frontend.md).

La checklist sopra resta il riferimento per decidere **dove** collocare un nuovo componente; il catalogo elenca **cosa** esiste gia'.

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

| Breakpoint | Dispositivo | Comportamento                                                                       |
| ---------- | ----------- | ----------------------------------------------------------------------------------- |
| >= 1024px  | Desktop     | Layout completo: sidebar inline, tutti i filtri visibili, azioni di riga inline     |
| 768-1023px | Tablet      | Pulsanti azione solo icona + tooltip, filtri flex-wrap, azioni di riga in kebab `⋮` |
| < 768px    | Mobile      | Sidebar overlay, padding ridotto, azioni di riga in kebab `⋮`                       |

Le classi responsive sono in `main.css` — nessun `@media` nei componenti scoped.
Il breakpoint mobile e' gestito dallo store `ui.js` (`isMobile`, `isTablet`).

Le azioni di riga (`RowActionsMenu`) usano in aggiunta `@media (hover: none)` per
intercettare i dispositivi touch indipendentemente dalla larghezza del viewport
(es. iPad Pro in landscape rende comunque il kebab perche' manca l'hover).

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

Unico punto di personalizzazione: sidebar, topbar, contenuto, card, drawer, AI widget, transizioni, tipografia.
Importato prima di `main.css` in `main.js`.

### Dark/Light mode

Il tema supporta dark e light mode tramite la classe `.p-dark` su `<html>`.

| Aspetto | Dettaglio |
| --- | --- |
| Selettore | `:root` = dark (default), `:root:not(.p-dark)` = light override |
| Store | `useUiStore().isDark` (ref), `toggleDarkMode()` (toggle + persist) |
| Persistenza | `localStorage` chiave `STORAGE_KEYS.DARK_MODE` |
| Pulsante | Topbar — icona sole (dark) / luna (light), tooltip i18n |
| Variabili | Tutte le `--app-*` in `theme.css` hanno override nel blocco `:root:not(.p-dark)` |

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
| `app-page-action`    | Pulsanti azione — responsive: solo icona su mobile        |
| `app-datatable`      | DataTable compatta (font ridotto, padding, stripe, hover) |
| `app-drawer-content` | Wrapper contenuto drawer (gap via `--app-drawer-gap`)     |
| `app-drawer-section` | Separatore sezione nei drawer (bordo da theme.css)        |
| `app-drawer-footer`  | Footer drawer Annulla/Salva (flex, justify-end)           |
| `form-grid`          | Contenitore campi form (flex column, gap)                 |
| `form-field`         | Coppia label + input (flex column, gap ridotto)           |
| `form-grid-2col`     | Griglia 2 colonne responsive (1 col < 480px)              |
| `app-tab-content`    | Wrapper contenuto tab per flex height                     |

### Centralizzazione stile pulsanti (`main.css`)

Lo stile dei pulsanti azione e' centralizzato in `main.css` tramite classi `app-*-btn`.
Nessun componente deve definire colori o hover per pulsanti riga — usare sempre le classi globali.

| Classe | Colore | Scopo |
| --- | --- | --- |
| `app-action-btn` | Verde (primary) | Azioni generiche nei form ("Aggiungi", "Gestisci" nei drawer) |
| `app-manage-btn` | Blu (info) | Pulsanti "Gestisci" nelle colonne DataTable (apre sub-drawer) |
| `app-edit-btn` | Verde (primary) | Matita modifica riga (DataTable e card) |
| `app-delete-btn` | Rosso | Cestino elimina riga (DataTable e card) |
| `app-reload-btn` | Verde | Refresh lista nella toolbar |

I pulsanti strutturali (Nuovo, Salva, Annulla) sono centralizzati tramite **componenti Vue**:

| Componente | Scopo |
| --- | --- |
| `NewButton` | Pulsante "Nuovo" nelle toolbar lista — responsive, controllo permessi |
| `DrawerFooter` | Footer Salva/Annulla nei drawer — Ctrl+S, readonly-aware |

### Centralizzazione icone gestione riga (`constants.js`)

Le icone dei pulsanti gestione nelle colonne DataTable sono centralizzate nella costante `MANAGE_ICONS`
in `src/core/constants.js`. Ogni lista che ha pulsanti per aprire sub-drawer (contatti, indirizzi,
conti bancari, UoM, BoM, note, conversioni) deve usare `:icon="MANAGE_ICONS.XXX"`, mai stringhe
hardcoded. Tutte le icone gestione riga usano la classe `app-manage-btn` (blu) — il colore
e' definito in un unico punto in `main.css`.

```html
<!-- Pattern standard -->
<Button :icon="MANAGE_ICONS.CONTATTI" text rounded size="small" class="app-manage-btn"
  v-tooltip.bottom="t('contatto.gestisci_contatti')" @click.stop="emit('contatti', data)" />
```

Per aggiungere una nuova icona gestione: inserire la chiave in `MANAGE_ICONS` e usarla nel componente.
Per cambiare il colore di tutte le icone gestione: modificare `.app-manage-btn` in `main.css`.

**Colonna azioni di riga** (pattern standard): i pulsanti `app-manage-btn` non si mettono piu'
direttamente in un `<template #body>` del `<Column>`. Usare sempre il building block
`RowActionsMenu` — gestisce automaticamente lo switch desktop inline / tablet kebab
tramite CSS, e accetta un array di azioni dichiarativo. Vedi sezione "Colonna azioni di riga"
nel pattern lista per l'API completa.

Per l'inventario completo di classi CSS, pulsanti e componenti, consultare il
[Catalogo Building Block Frontend](catalogo-building-block-frontend.md).

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

## Modalita' sola lettura e accesso — pattern "protect"

### Principio

Le autorizzazioni utente prevedono tre livelli di accesso (`TUTTO`, `LETTURA`, `BLOCCATO`) su tre granularita' diverse. Tutti i form e le view devono supportare nativamente le modalita' ridotte senza duplicare componenti o creare varianti separate.

### Piramide permessi

| Livello | Cosa controlla | Trigger FE | Enforcement BE |
| --- | --- | --- | --- |
| **Area** (schema DB) | Accesso all'intero dominio | `useReadonlyMode(schemaDb)` + route guard su `BLOCCATO` | `ZeroERPPermission` via `area_funzionale` |
| **Azione processo** | Singola operazione (es. "genera fatture") | prop `action` su `NewButton` / `DrawerFooter` | `permission_codename` sulla view |
| **Oggetto / model** (v2) | Singola entita' dentro un'area | `useReadonlyMode(schemaDb, modelName)` | `model_permission = (app_label, model_name)` sulla view |

### Composable `useReadonlyMode(schemaDb, modelName?)`

Il provider va chiamato nella View (parent della SearchTable e dei drawer). I figli iniettano con `useInjectReadonly()` / `useInjectBlocked()`.

```js
// Livello area (classico)
useReadonlyMode('anagrafiche')

// Livello oggetto (permessi v2) — richiede model_permission sulla view BE
useReadonlyMode('anagrafiche', 'cliente')
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
import ReadonlyBadge from '@/core/components/ReadonlyBadge.vue'
import ReloadButton from '@/core/components/ReloadButton.vue'
import NewButton from '@/core/components/NewButton.vue'
import AccessoBloccatoPanel from '@/core/components/AccessoBloccatoPanel.vue'
import { useInjectBlocked } from '@/core/composables/useReadonlyMode'

const isBlocked = useInjectBlocked()
</script>

<template>
  <div class="app-tab-content">
    <!-- BLOCCATO: pannello sostitutivo, niente toolbar ne' tabella -->
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
      <div class="app-page-toolbar">
        <div class="app-page-filters">
          <!-- input search, filtri -->
        </div>
        <div class="app-page-actions">
          <ReadonlyBadge />
          <ReloadButton @click="reload" />
          <NewButton :tooltip="..." @click="emit('new')" />
        </div>
      </div>
      <DataTable ... />
    </template>
  </div>
</template>
```

**Regole operative liste**:

- ❌ **mai** `<Button icon="pi pi-refresh" ...>` inline — sempre `<ReloadButton @click="reload" />`
- ❌ **mai** badge testuale "Sola lettura" custom — sempre `<ReadonlyBadge />`
- ✅ Ordine fisso in `app-page-actions`: `ReadonlyBadge → ReloadButton → NewButton`
- ✅ `AccessoBloccatoPanel` sostituisce toolbar + DataTable (variante A, schermata protect). **Non** tenere toolbar visibile disabilitata.
- ✅ `ReloadButton` si nasconde solo su `isBlocked` (serve anche in LETTURA); `NewButton` si nasconde su `isReadonly`; `ReadonlyBadge` si mostra solo su `isReadonly && !isBlocked`

### Stato permessi → UI della lista

Tabella riassuntiva di cosa vede l'operatore in base al livello risolto:

| Livello | Toolbar | Filtri | ReloadButton | NewButton | ReadonlyBadge | Corpo lista |
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
      <!-- toolbar + DataTable normali -->
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
<Drawer :visible="visible" @update:visible="...">
  <template #header>
    <DrawerTitle
      :action="isEdit ? t('common.edit') : t('common.new')"
      :title="t('...')"
      icon="pi pi-briefcase"
    />
    <!-- badge "Sola lettura" appare a destra automaticamente se readonly -->
  </template>

  <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
    <!-- form normale, disabled si propaga via .app-readonly -->
  </div>

  <DrawerFooter @save="onSave" @cancel="onCancel" />
  <!-- pulsante Salva nascosto automaticamente se readonly -->
</Drawer>
```

**Regole operative drawer**:

- ✅ Ogni drawer admin DEVE esporre prop `readonly` + leggere `useInjectReadonly()` con effetto cumulativo (`computed isReadOnlyEffective = props.readonly || isReadonly.value`)
- ✅ Usare sempre `DrawerTitle` nel `#header` — il badge si propaga automaticamente
- ❌ Non creare varianti `*ReadOnly.vue` separate
- ✅ Wrap del contenuto con `:class="{ 'app-readonly': isReadonly }"` per l'effetto protect
- ✅ `DrawerFooter` nasconde Salva in readonly; tasti di chiusura (X drawer, `.app-escape`) restano attivi

### Drawer autonomo vs drawer figlio puro

Un drawer puo' comportarsi in due modi rispetto ai permessi livello oggetto:

| Tipo | Dichiara scope proprio | Quando usare | Esempio |
| --- | --- | --- | --- |
| **Autonomo** | `useReadonlyMode('schema', 'model')` al setup | Il model e' catalogato in `config.area_model_overrides` (l'admin puo' bloccarlo singolarmente) | `ContiBancariDrawer` → `('anagrafiche', 'conto_bancario')` |
| **Figlio puro** | solo `useInjectReadonly()` | Il model non e' nel catalogo, si eredita il readonly del parent | `IndirizzoDrawer`, `ContoBancarioForm` |

**Drawer autonomo — template**:

```js
// ContiBancariDrawer.vue
import { useReadonlyMode, useInjectBlocked } from '@/core/composables/useReadonlyMode'

// Dichiara scope proprio (l'OR interno rispetta anche eredita' dal parent)
const { isReadonly } = useReadonlyMode('anagrafiche', 'conto_bancario')
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

  <DrawerFooter v-if="!isBlocked" @save="..." @cancel="..." />
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
- `DrawerTitle`: auto-include `ReadonlyBadge` a destra del titolo
- `DrawerFooter`: Salva nascosto se readonly (`v-if="!isReadonly"`)
- `NewButton`: si nasconde se readonly
- `ReloadButton`: si nasconde solo se bloccato (livello oggetto)
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
| `READONLY_DOMAINS` | Area (schema DB) passata come **primo arg** a `useReadonlyMode` | `VENDITE`, `ANAGRAFICHE`, `CATALOGO`, `AMM_SOFTWARE`, `CONFIG`, `PRATICHE` |
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

Il primo (literal) **funziona** ma non è mai accettato in PR di nuovo codice: il pattern enum è la **fonte di verità** sparsa in ~125 call site.

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

### Factory `createCrudAdminStore`

Per gli store admin CRUD standard (categorie clienti, promo articoli, matrici config) esiste una factory in `core/composables/createCrudAdminStore.js` che gestisce automaticamente emit in create/update. Basta passare `emitKey`:

```js
export const useCategorieClientiStore = createCrudAdminStore({
  storeName: 'amm-categorie-clienti',
  api: { list, get, create, update },
  defaultOrderBy: 'ordinamento',
  emitKey: TAB_ENTITIES.CATEGORIE_CLIENTI,  // la factory emette automaticamente
  // ...
})
```

Nessun `emitDataChanged` manuale necessario nei metodi.

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

## Azioni processo — Livello 2 (pattern "action gate")

### Principio

Le azioni di processo controllano **singole operazioni** (es. "crea soggetto", "genera fatture") dentro un'area a cui l'operatore ha gia' accesso. Sono il livello di granularita' sotto TUTTO/LETTURA/BLOCCATO.

### Collocazione nel modello permessi

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
| `DrawerTitle` | Titolo standard drawer: azione sx + entita' centrata + badge readonly auto | `action`, `title`, `icon` | Tutti i drawer |
| `DrawerFooter` | Footer drawer con Annulla/Salva, auto-hide Salva in readonly | `loading`, `disabled`, `action`, `closeOnly` | Tutti i drawer |
| `NewButton` | Pulsante "Nuovo" toolbar, auto-hide in readonly | `tooltip`, `action` | Tutte le SearchTable |
| `ReloadButton` | Pulsante refresh toolbar, auto-hide solo se `isBlocked` (livello oggetto) | — | Tutte le SearchTable |
| `ReadonlyBadge` | Badge grigio "Sola lettura", auto-visibile se `isReadonly && !isBlocked`, responsive (icona-only su mobile) | — | Toolbar liste + `DrawerTitle` |
| `AccessoBloccatoPanel` | Pannello sostitutivo "Accesso negato a questo elenco" per BLOCCATO oggetto | — | SearchTable con `v-if="isBlocked"` |
| `RowActionsMenu` | Azioni di riga responsive: pulsanti inline su desktop, kebab `⋮` su tablet/touch | `actions`, `tooltip`, `disabled` | Tutte le SearchTable con azioni secondarie |
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
