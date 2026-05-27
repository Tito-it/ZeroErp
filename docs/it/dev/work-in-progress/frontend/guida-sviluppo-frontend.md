# Guida Sviluppo Frontend — ZeroERP

**Stack**: Vue 3.5 + Vite 8 + PrimeVue 4.5 + Pinia 3 + Vue Router 5 + vue-i18n 10
**Runtime**: Node.js 24 LTS (nvm)
**Data**: Marzo 2026 (aggiornato 18 marzo)
**Complementare a**: `docs/it/dev/frontend/frontend-standards.md` (regole vincolanti e catalogo componenti)

---

## Indice

1. [Struttura cartelle](#1-struttura-cartelle)
2. [Componenti Vue — convenzioni](#2-componenti-vue--convenzioni)
3. [Composable — pattern e catalogo](#3-composable--pattern-e-catalogo)
4. [Store Pinia](#4-store-pinia)
5. [Navigazione e routing](#5-navigazione-e-routing)
6. [API client — come aggiungere endpoint](#6-api-client--come-aggiungere-endpoint)
7. [Pattern SearchTable + Drawer](#7-pattern-searchtable--drawer)
8. [Pattern Building Block Form](#8-pattern-building-block-form)
9. [Modalita sola lettura](#9-modalita-sola-lettura)
10. [Internazionalizzazione (i18n)](#10-internazionalizzazione-i18n)
11. [CSS e theming](#11-css-e-theming)
12. [Storage e persistenza](#12-storage-e-persistenza)
13. [Pattern ricorrenti](#13-pattern-ricorrenti)
14. [Aggiungere un nuovo dominio](#14-aggiungere-un-nuovo-dominio)
15. [Build e verifica](#15-build-e-verifica)

---

## 1. Struttura cartelle

```
frontend/src/
├── core/                           # Moduli condivisi cross-dominio
│   ├── components/                 # 40+ componenti UI condivisi
│   │   ├── App*.vue                # Layout: AppLayout, AppTopbar, AppSidebar, AppToolbar, AppBreadcrumb, AppDrawer
│   │   ├── Sidebar*.vue            # SidebarHome, SidebarDomain, SidebarItem
│   │   ├── Content*.vue            # ContentTabs
│   │   ├── Search*.vue             # SearchDrawer
│   │   ├── *Form.vue               # Building block: SoggettoForm, ContattoForm, IndirizzoSoggettoForm, DatiSocietariForm, AuthUserForm
│   │   ├── *Autocomplete.vue       # ComuneAutocomplete, StradarioAutocomplete, StradarioGeneraleAutocomplete
│   │   ├── *Drawer.vue             # Drawer geografici: ComuneDrawer, ProvinceDrawer, RegioniDrawer, StatiDrawer, ToponomasticaDrawer, CodiciPostaliDrawer
│   │   ├── *SearchTable.vue        # SearchTable geografiche: ComuniSearchTable, ProvinceSearchTable, RegioniSearchTable, StatiSearchTable, ToponomasticaSearchTable, CodiciPostaliSearchTable
│   │   ├── GenericConfigDrawer.vue # Drawer generico per 67 tabelle config
│   │   ├── ConfigTablePanel.vue    # Pannello config con tab dinamici
│   │   ├── IndirizziSoggettoDrawer.vue  # Gestione indirizzi soggetto (multi-tipo, replace, auto-clone)
│   │   ├── ContattiSoggettoDrawer.vue   # Gestione contatti soggetto
│   │   ├── FormFooter.vue        # Footer drawer con auto-hide readonly
│   │   ├── DrawerTitle.vue         # Titolo drawer
│   │   ├── NewButton.vue           # Pulsante Nuovo con auto-hide readonly
│   │   ├── PaginationInfo.vue      # Info paginazione
│   │   ├── TagList.vue             # Lista tag
│   │   ├── LogoBrand.vue           # Logo riutilizzabile
│   │   └── StatusPage.vue          # Template pagina stato
│   ├── composables/                # 24 composable (use*.js)
│   ├── views/                      # HomeView, LoginView, PlaceholderView, ErrorView
│   ├── api.js                      # Istanza Axios con interceptor token
│   ├── apiCore.js                  # Endpoint core: lookup, search, stradario, CAP
│   ├── constants.js                # Costanti UI: DRAWER_WIDTH, TOAST_DURATION, PAGINATION, BREAKPOINTS, SHORTCUTS
│   ├── i18n.js                     # Istanza vue-i18n
│   ├── navigation.js               # Fonte unica: DOMAINS, DOMAIN_MENUS, resolveTabLabel
│   └── storage.js                  # Layer localStorage/sessionStorage
├── anagrafiche/                    # Dominio attivo
│   ├── api/anagrafiche.js          # Endpoint anagrafiche: soggetti, contatti, indirizzi, ruoli, CF/PIVA
│   ├── components/                 # SoggettoDrawer, SoggettiSearchTable, IndirizzoDrawer, IndirizziSearchTable
│   ├── stores/                     # soggetti, indirizzi, comuni, province, regioni, stati, toponomastica, codiciPostali
│   └── views/                      # SoggettiView, IndirizziView
├── stores/                         # Store Pinia globali: auth, context, navigation, tabs, ui
├── locales/                        # it.json, en.json
├── router/index.js                 # Rotte + navigation guard
└── main.js                         # Bootstrap app
```

**Regola**: i moduli dominio vanno in `src/<dominio>/` (es. `src/anagrafiche/`). Il core e' solo per codice condiviso cross-dominio. I building block form (`*Form.vue`) stanno in core perche' riusabili da piu' domini.

---

<a id="2-componenti-vue--convenzioni"></a>
## 2. Componenti Vue — convenzioni

### Stile obbligatorio

- **`<script setup>`** — sempre Composition API, mai Options API
- **Commento `// Scopo:`** in testa allo script — una riga che descrive il ruolo del componente
- **Props tipizzate** con `defineProps()` — sempre `type` e `default`/`required`
- **Emit dichiarati** con `defineEmits()`

### Naming file

| Tipo | Pattern | Esempio |
|------|---------|---------|
| Layout | `App*.vue` | `AppTopbar.vue`, `AppSidebar.vue` |
| Sidebar | `Sidebar*.vue` | `SidebarHome.vue`, `SidebarItem.vue` |
| Dettaglio ricerca | `*Detail.vue` | `ClienteDetail.vue` |
| Vista | `*View.vue` | `SoggettiView.vue`, `IndirizziView.vue` |
| Drawer | `*Drawer.vue` | `SoggettoDrawer.vue`, `ComuneDrawer.vue` |
| SearchTable | `*SearchTable.vue` | `SoggettiSearchTable.vue` |
| Form building block | `*Form.vue` | `SoggettoForm.vue`, `ContattoForm.vue` |
| Autocomplete | `*Autocomplete.vue` | `ComuneAutocomplete.vue` |
| Composable | `use*.js` | `useSearchTable.js`, `useDrawerState.js` |
| Store | `<nome>.js` in `stores/` | `auth.js`, `soggetti.js` |

### CSS ownership

- `<style scoped>` — sempre
- `:deep()` consentito **solo** per override componenti PrimeVue
- Mai `:deep()` per stilizzare componenti custom figli

---

<a id="3-composable--pattern-e-catalogo"></a>
## 3. Composable — pattern e catalogo

### Dove

Tutti i composable condivisi in **`src/core/composables/`**.

### Catalogo completo

Per l'inventario completo dei composable disponibili (infrastruttura, lookup, building block dominio), consultare il [Catalogo Building Block Frontend](../../frontend/catalogo-building-block-frontend.md#composables-srccorecomposables).

### Regola toast

```javascript
// CORRETTO
import { useNotify } from '../composables/useNotify'
const notify = useNotify()
notify.success('Salvato')

// SBAGLIATO — mai importare useToast direttamente
import { useToast } from 'primevue/usetoast'
```

---

## 4. Store Pinia

### Stile obbligatorio — setup function

```javascript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useMyStore = defineStore('my-store', () => {
  const value = ref(null)
  const derived = computed(() => /* ... */)
  function doAction() { /* ... */ }
  return { value, derived, doAction }
})
```

### Store globali (src/stores/)

| Store | Responsabilita | Persistito |
|-------|---------------|------------|
| `auth` | Login, token, profilo utente, `permessiArea`, `getLivelloArea()`, `isAreaReadonly()` | Token in localStorage |
| `ui` | Sidebar collapsed, search drawer | Sidebar in localStorage |
| `navigation` | Dominio attivo | No |
| `tabs` | Tab aperti, tab attivo | Tab in localStorage |
| `context` | Contesto globale (soggetto selezionato dalla ricerca) | No |

### Store dominio (src/anagrafiche/stores/)

Un file per entita: `soggetti.js`, `indirizzi.js`, `comuni.js`, `province.js`, ecc.
Pattern: `fetchList()`, `fetchDetail()`, `create()`, `update()` — delegano a `api/anagrafiche.js`.

### Comunicazione

- Stato condiviso: store Pinia
- **Mai** `window.dispatchEvent(new CustomEvent(...))` — usare ref/computed nello store

---

## 5. Navigazione e routing

### Fonte unica: `navigation.js`

```javascript
export const DOMAINS = [
  { key: 'anagrafiche', icon: 'pi pi-users', to: '/anagrafiche' },
  { key: 'vendite', icon: 'pi pi-shopping-cart', to: '/vendite' },
  // ...
  { key: 'amm-software', icon: 'pi pi-lock', to: '/amm-software', adminOnly: true },
]

export const DOMAIN_MENUS = {
  'anagrafiche': [
    { key: 'soggetti', icon: 'pi pi-id-card', to: '/anagrafiche/soggetti' },
    { key: 'indirizzi', icon: 'pi pi-map-marker', to: '/anagrafiche/indirizzi' },
  ],
  'config': [
    { key: 'tabelle', icon: 'pi pi-table', to: '/config/tabelle' },
  ],
  // ...
}

export function resolveTabLabel(meta, t) {
  const { domain, menuKey } = meta
  if (menuKey) return t(`nav_menu.${domain}.${menuKey}`)
  if (domain && domain !== 'home') return t(`nav.${domain}`)
  return null
}
```

### Route meta — campi riconosciuti

| Campo | Tipo | Obbligatorio | Scopo |
|-------|------|:---:|--------|
| `domain` | string | Si | Identifica dominio; guida sidebar, breadcrumb, tab |
| `menuKey` | string | No | Voce L2; usato per tab label e breadcrumb |
| `errorKey` | string | No | Solo pagine errore |
| `public` | boolean | No | `true` solo su `/login` |

### Navigation guard (sequenza)

1. Rotte pubbliche (login)
2. Redirect a login se non autenticato
3. Fetch profilo se mancante
4. Guard admin per `amm-software`
5. Impostazione dominio attivo
6. Apertura tab (escluso home e errore)

---

<a id="6-api-client--come-aggiungere-endpoint"></a>
## 6. API client — come aggiungere endpoint

### Struttura file API

```
src/core/api.js          # Istanza Axios con interceptor (token, refresh, 401 redirect)
src/core/apiCore.js      # Endpoint condivisi: lookup, search, stradario, CAP
src/anagrafiche/api/anagrafiche.js  # Endpoint dominio anagrafiche
```

### Pattern per aggiungere un endpoint

```javascript
// src/anagrafiche/api/anagrafiche.js
import api from '../../core/api'

// Lista paginata
export function listSoggetti(params) {
  return api.get('/api/v1/anagrafiche/soggetti/', { params })
}

// Dettaglio
export function getSoggetto(id) {
  return api.get(`/api/v1/anagrafiche/soggetti/${id}/`)
}

// Creazione
export function createSoggetto(data) {
  return api.post('/api/v1/anagrafiche/soggetti/', data)
}

// Aggiornamento parziale
export function updateSoggetto(id, data) {
  return api.patch(`/api/v1/anagrafiche/soggetti/${id}/`, data)
}
```

### Aggiungere un nuovo dominio API

1. Creare `src/<dominio>/api/<dominio>.js`
2. Importare `api` da `../../core/api`
3. Esportare funzioni per ogni endpoint
4. Usarle nello store o direttamente nei composable

---

<a id="7-pattern-searchtable--drawer"></a>
## 7. Pattern SearchTable + Drawer

Questo e' il pattern principale per tutte le schermate CRUD. Esempio: Soggetti.

### View (provider + composizione)

```javascript
// SoggettiView.vue
import { useReadonlyMode } from '@/core/composables/useReadonlyMode'
const { isReadonly } = useReadonlyMode('anagrafiche')  // provide readonly per tutti i figli
```

La View contiene: SearchTable + Drawer. La SearchTable gestisce la lista, il Drawer gestisce il form.

### SearchTable (useSearchTable)

```javascript
// SoggettiSearchTable.vue
const { rows, totalRecords, loading, pagination, fetchList, onPage, onSort } = useSearchTable({
  fetchFn: (params) => listSoggetti(params),
  defaultSort: { field: 'ragione_sociale_completa', order: 1 },
})
```

Espone: `rows`, `totalRecords`, `loading`, `pagination`, `fetchList()`, `onPage()`, `onSort()`.
La DataTable PrimeVue si lega a questi.

### Drawer (useDrawerState)

```javascript
// SoggettoDrawer.vue
const { visible, mode, editId, openCreate, openEdit, close } = useDrawerState()
```

Espone: `visible`, `mode` (create/edit), `editId`, `openCreate()`, `openEdit(id)`, `close()`.

### FormFooter (auto-hide readonly)

```vue
<FormFooter :loading="loading" :disabled="!canSave" @save="onSave" @cancel="close" />
```

Si nasconde automaticamente in modalita sola lettura (inject readonly).

### NewButton (auto-hide readonly)

```vue
<NewButton :label="t('soggetti.nuovo')" @click="drawer.openCreate()" />
```

Si nasconde automaticamente in modalita sola lettura.

---

## 8. Pattern Building Block Form

I building block sono composable + componente Vue accoppiati. Ogni BB gestisce un sotto-dominio atomico.

### Architettura

```
useXxxForm.js    → stato reattivo, validazione, reset, populate
XxxForm.vue      → template con binding al form del composable
```

### Esempio: IndirizzoSoggettoForm

```javascript
// Nel drawer che usa il form:
const indirizzo = useIndirizzoSoggettoForm()

// Il composable espone:
indirizzo.form           // reactive con tutti i campi
indirizzo.canSave        // computed: validazione OK
indirizzo.validate()     // errori espliciti
indirizzo.reset()        // pulisci tutto
indirizzo.toPayloadArray() // genera payload per backend (multi-tipo con snapshot)
indirizzo.addressNotFound  // computed: indirizzo non trovato in DB
indirizzo.indirizzoWarnings // ref: messaggi dal check duplicato
```

### Gerarchia composable indirizzo

```
useIndirizzoBase        → comune, via (via_obj unificato), CAP, civico, check duplicato
  ├── useIndirizzoSoggettoForm  → estende base + multi-tipo, libera, auto-clone
  │     └── useIndirizzoMultiTipo  → barra tag tipo, snapshot/restore
  └── IndirizzoDrawer (standalone)  → usa base direttamente per CRUD indirizzi_dettaglio
```

### Regola via_obj

Un unico campo `form.via_obj` per la via selezionata, sia da StradarioAutocomplete (via esistente) che da StradarioGeneraleAutocomplete (via nuova). Il flag `form.via_nuova` controlla solo quale autocomplete mostrare. Il payload usa `stradario_id` se presente nell'oggetto, altrimenti `toponomastica_id + descrizione_via`.

---

## 9. Modalita sola lettura

### Architettura provide/inject

```javascript
// View (provider):
import { useReadonlyMode } from '@/core/composables/useReadonlyMode'
const { isReadonly } = useReadonlyMode('anagrafiche')

// Drawer (consumer):
import { useInjectReadonly } from '@/core/composables/useReadonlyMode'
const isReadonly = useInjectReadonly()
```

### Componenti auto-hide

- **FormFooter**: inietta readonly, si nasconde con `v-if="!isReadonly"`
- **NewButton**: inietta readonly, si nasconde con `v-if="!isReadonly"`

### CSS protect

```vue
<div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
```

`.app-readonly` blocca `pointer-events` ma permette `user-select: text`.
Pulsanti di consultazione (es. "Gestisci Contatti") usano classe `app-escape` per restare cliccabili.

---

## 10. Internazionalizzazione (i18n)

### Regola fondamentale

**Ogni testo visibile all'utente usa `t()` o `$t()`** — zero stringhe hardcoded.

### Convenzioni chiavi

| Prefisso | Uso |
|----------|-----|
| `nav.*` | Label dominio L1 |
| `nav_menu.<domain>.*` | Label voci menu L2 |
| `common.*` | Etichette comuni (salva, annulla, cerca) |
| `placeholder.<domain_menuKey>.*` | Titolo e features placeholder |
| `notifications.*` | Messaggi toast |
| `errors.*` | Titoli pagine errore |
| `context.*` | Tooltip e label contesto globale |
| `soggetti.*`, `indirizzi.*`, `geo.*`, `amm.*` | Etichette dominio-specifiche |

### Istanza condivisa

```javascript
import i18n from '../core/i18n'
const t = i18n.global.t  // usabile fuori dai componenti (es. router)
```

---

## 11. CSS e theming

### Architettura variabili

1. **PrimeVue** (`--p-*`): gestite dal tema, non modificare
2. **App** (`--app-*`): definite in `theme.css`, costruite sopra `--p-*`

### Classi globali (main.css)

| Classe | Scopo |
|--------|-------|
| `app-page` | Container pagina con padding |
| `app-datatable` | DataTable con stile uniforme |
| `app-drawer-content` | Contenuto drawer con padding |
| `app-drawer-section` | Sezione separata nel drawer |
| `form-grid` | Griglia form responsive |
| `form-grid-2col` | Griglia 2 colonne |
| `form-field` | Campo form con label + input |
| `app-readonly` | Overlay sola lettura |
| `app-escape` | Escludi da readonly (pulsanti consultazione) |
| `app-input-with-action` | Input con pulsante affiancato |

### Regole

- `<style scoped>` — sempre
- `:deep()` solo per override PrimeVue
- Mai `!important` (tranne override PrimeVue documentato)
- Breakpoint: `BREAKPOINTS.MOBILE: 768`, `BREAKPOINTS.TABLET: 1024`

---

## 12. Storage e persistenza

### Layer centralizzato

```javascript
import { local, STORAGE_KEYS } from '../core/storage'

local.get(STORAGE_KEYS.SIDEBAR_COLLAPSED)
local.set(STORAGE_KEYS.SIDEBAR_COLLAPSED, true)
```

**Mai** accedere direttamente a `localStorage.getItem()`. Aggiungere nuove chiavi in `STORAGE_KEYS`.

---

## 13. Pattern ricorrenti

### Costanti UI

Tutte in `src/core/constants.js`:

```javascript
import { DRAWER_WIDTH, TOAST_DURATION, PAGINATION, SHORTCUTS } from '../core/constants'
```

### Cleanup listener con HMR

```javascript
if (typeof window !== 'undefined') {
  window.addEventListener('resize', handler, { passive: true })
  if (import.meta.hot) {
    import.meta.hot.dispose(() => window.removeEventListener('resize', handler))
  }
}
```

### Placeholder automatici

`PlaceholderView.vue` deriva la chiave i18n da `route.meta`:

```
domain: 'amm-software', menuKey: 'operatori'
→ chiave: placeholder.amm_software_operatori.title / .features
```

---

## 14. Aggiungere un nuovo dominio

Checklist completa per aggiungere un dominio (es. "logistica"):

### 1. navigation.js

```javascript
// DOMAINS
{ key: 'logistica', icon: 'pi pi-truck', to: '/logistica' }

// DOMAIN_MENUS
'logistica': [
  { key: 'spedizioni', icon: 'pi pi-send', to: '/logistica/spedizioni' }
]
```

### 2. i18n (locales/it.json, en.json)

```json
{
  "nav": { "logistica": "Logistica" },
  "nav_menu": { "logistica": { "spedizioni": "Spedizioni" } }
}
```

### 3. Rotte (router/index.js)

Per domini placeholder: automatico. Per viste dedicate:

```javascript
const domainsWithRoutes = new Set(['amm-software', 'anagrafiche', 'config', 'logistica'])

// rotta figlia
{
  path: 'logistica/spedizioni',
  name: 'logistica-spedizioni',
  component: () => import('../logistica/views/SpedizioniView.vue'),
  meta: { domain: 'logistica', menuKey: 'spedizioni' }
}
```

### 4. API client

Creare `src/logistica/api/logistica.js` con le funzioni endpoint.

### 5. Store

Creare `src/logistica/stores/spedizioni.js` con fetchList/create/update.

### 6. Componenti

- `src/logistica/views/SpedizioniView.vue` — usa `useReadonlyMode('logistica')`
- `src/logistica/components/SpedizioniSearchTable.vue` — usa `useSearchTable`
- `src/logistica/components/SpedizioneDrawer.vue` — usa `useDrawerState`

### 7. Verifica

```bash
cd frontend && npx vite build
```

---

## 15. Build e verifica

### Comandi

```bash
nvm use
cd frontend && npx vite build      # Build produzione
cd frontend && npx vite dev         # Dev server
```

### Checklist pre-commit

- [ ] Build senza errori
- [ ] Nessuna stringa hardcoded nei template (usa `t()`)
- [ ] Nessun `useToast()` diretto (usa `useNotify()`)
- [ ] Nessun `localStorage` diretto (usa `storage.js`)
- [ ] Nessun `CustomEvent` per comunicazione (usa store Pinia)
- [ ] CSS scoped, nessun `:deep()` su componenti custom
- [ ] Nuove costanti in `constants.js`, non valori magici inline
- [ ] Composable in `core/composables/`
- [ ] Drawer usa `useDrawerState` + `FormFooter`
- [ ] Lista usa `useSearchTable` + `NewButton`
- [ ] View con area funzionale usa `useReadonlyMode`
