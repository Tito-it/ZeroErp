# Guida Sviluppo Frontend — ZeroERP

**Stack**: Vue 3.5 + Vite 7 + PrimeVue 4.5 + Pinia 3 + Vue Router 5 + vue-i18n 10
**Runtime**: Node.js 24 LTS (nvm)
**Data**: Marzo 2026

---

## Indice

1. [Struttura cartelle](#1-struttura-cartelle)
2. [Componenti Vue — convenzioni](#2-componenti-vue--convenzioni)
3. [Composable — pattern e collocazione](#3-composable--pattern-e-collocazione)
4. [Store Pinia](#4-store-pinia)
5. [Navigazione e routing](#5-navigazione-e-routing)
6. [Internazionalizzazione (i18n)](#6-internazionalizzazione-i18n)
7. [CSS e theming](#7-css-e-theming)
8. [Storage e persistenza](#8-storage-e-persistenza)
9. [Pattern ricorrenti](#9-pattern-ricorrenti)
10. [Aggiungere un nuovo dominio](#10-aggiungere-un-nuovo-dominio)
11. [Build e verifica](#11-build-e-verifica)

---

## 1. Struttura cartelle

```
frontend/src/
├── core/                         # Moduli condivisi cross-dominio
│   ├── components/               # Componenti UI condivisi
│   │   ├── AppLayout.vue         # Layout principale (sidebar + topbar + content)
│   │   ├── AppTopbar.vue         # Topbar con azienda, titolo area, ricerca, data
│   │   ├── AppSidebar.vue        # Contenitore sidebar (logo + stato morfic)
│   │   ├── AppBreadcrumb.vue     # Breadcrumb derivato da route meta
│   │   ├── ContentTabs.vue       # Barra tab multi-entita con KeepAlive
│   │   ├── SidebarHome.vue       # Sidebar stato HOME (lista domini)
│   │   ├── SidebarDomain.vue     # Sidebar stato DOMINIO (voci L2 + preferiti)
│   │   ├── SidebarItem.vue       # Voce sidebar riutilizzabile (icona + label)
│   │   ├── LogoBrand.vue         # Logo ZeroERP riutilizzabile (sidebar + login)
│   │   ├── SearchDrawer.vue      # Drawer ricerca universale
│   │   ├── StatusPage.vue        # Template pagina stato (errore, placeholder)
│   │   └── details/              # Componenti dettaglio ricerca
│   ├── composables/              # Hook riutilizzabili (use*)
│   │   ├── useNotify.js          # Toast centralizzato (success, error, systemError)
│   │   ├── useApiHandler.js      # Wrapper chiamate API con loading/error
│   │   ├── usePagination.js      # Logica paginazione server-side
│   │   ├── useConfirmAction.js   # Dialog conferma con ConfirmDialog PrimeVue
│   │   ├── useConfirmCloseTab.js # Conferma chiusura tab con modifiche non salvate
│   │   ├── useDirtyState.js      # Tracking stato "dirty" di un form
│   │   ├── useKeyboardShortcuts.js # Shortcut globali (Ctrl+K, Ctrl+W, ecc.)
│   │   ├── useLoading.js         # Stato loading generico
│   │   ├── useSearchDetail.js    # Logica dettaglio da ricerca universale
│   │   ├── useTabEvents.js       # Eventi bus per tab
│   │   └── useTabLabel.js        # Risoluzione label tab
│   ├── views/                    # Viste condivise
│   │   ├── HomeView.vue          # Homepage con griglia domini
│   │   ├── LoginView.vue         # Pagina login
│   │   ├── PlaceholderView.vue   # Placeholder per aree non sviluppate
│   │   ├── ErrorView.vue         # 404 / 403
│   │   ├── NotFoundView.vue      # Alias 404
│   │   └── ForbiddenView.vue     # Alias 403
│   ├── api.js                    # Istanza Axios con interceptor token
│   ├── constants.js              # Costanti UI (drawer width, toast, breakpoint)
│   ├── i18n.js                   # Istanza vue-i18n
│   ├── navigation.js             # Fonte unica domini, menu L2, resolveTabLabel
│   └── storage.js                # Layer localStorage/sessionStorage
├── stores/                       # Store Pinia
│   ├── auth.js                   # Autenticazione, profilo, token
│   ├── context.js                # Contesto globale (soggetto selezionato)
│   ├── navigation.js             # Dominio attivo
│   ├── tabs.js                   # Tab aperti, persistenza
│   └── ui.js                     # Layout (sidebar, breakpoint, search drawer)
├── locales/                      # File i18n
│   ├── it.json
│   └── en.json
├── router/index.js               # Definizione rotte + navigation guard
└── main.js                       # Bootstrap app
```

**Regola**: i moduli dominio (futuri) vanno in `src/<dominio>/` (es. `src/vendite/`). Il core e' solo per codice condiviso cross-dominio.

---

## 2. Componenti Vue — convenzioni

### Stile obbligatorio

- **`<script setup>`** — sempre Composition API, mai Options API
- **Commento `// Scopo:`** in testa allo script — una riga che descrive il ruolo del componente
- **Props tipizzate** con `defineProps()` — sempre `type` e `default`/`required`
- **Emit dichiarati** con `defineEmits()`

### Riutilizzo ed estrazione

- Un pattern ripetuto in 2+ componenti → estrarre in componente condiviso in `core/components/`
- Esempio: `LogoBrand.vue` (usato in AppSidebar + LoginView), `SidebarItem.vue` (usato in SidebarHome + SidebarDomain)
- Il componente estratto **possiede i propri stili** (scoped) — mai usare `:deep()` dal parent per stilizzare figli riutilizzabili

### CSS ownership

- Ogni componente possiede i propri stili con `<style scoped>`
- `:deep()` e' consentito **solo** per override di componenti PrimeVue (es. `.p-datatable`)
- Mai usare `:deep()` per stilizzare componenti custom figli — spostare gli stili nel figlio

### Naming file

| Tipo | Pattern | Esempio |
|------|---------|---------|
| Componente layout | `App*.vue` | `AppTopbar.vue`, `AppSidebar.vue` |
| Componente sidebar | `Sidebar*.vue` | `SidebarHome.vue`, `SidebarItem.vue` |
| Componente dettaglio | `*Detail.vue` | `ClienteDetail.vue` |
| Vista | `*View.vue` | `HomeView.vue`, `PlaceholderView.vue` |
| Composable | `use*.js` | `useNotify.js`, `usePagination.js` |
| Store | `<nome>.js` in `stores/` | `auth.js`, `tabs.js` |

---

## 3. Composable — pattern e collocazione

### Dove

Tutti i composable condivisi vivono in **`src/core/composables/`**. Mai mettere file `use*.js` direttamente in `core/`.

### Struttura tipo

```javascript
import { ref, computed } from 'vue'

export function useMyComposable(options) {
  // stato reattivo
  const data = ref(null)
  const loading = ref(false)

  // logica
  async function fetchData() { /* ... */ }

  // esponi solo cio' che serve
  return { data, loading, fetchData }
}
```

### Composable disponibili

| Composable | Scopo | Note |
|------------|-------|------|
| `useNotify` | Toast uniformi | Usa `useToast()` internamente — i componenti NON devono importare `useToast` direttamente |
| `useApiHandler` | Wrapper API con loading/error | Gestisce errori con `useNotify` |
| `usePagination` | Paginazione server-side | Legge default da `constants.js` |
| `useConfirmAction` | Dialog conferma | Wrappa `useConfirm()` PrimeVue |
| `useSearchDetail` | Dettaglio da ricerca | Logica fetch dettaglio per SearchDrawer |
| `useDirtyState` | Form dirty tracking | Per warning chiusura tab |
| `useConfirmCloseTab` | Conferma chiusura tab dirty | Combina dirty + confirm |
| `useKeyboardShortcuts` | Shortcut globali | Legge da `SHORTCUTS` in `constants.js` |

### Regola toast

**Mai** importare `useToast` da PrimeVue nei componenti. Usare sempre `useNotify()`:

```javascript
// CORRETTO
import { useNotify } from '../composables/useNotify'
const notify = useNotify()
notify.success('Salvato')
notify.error('Errore nel salvataggio')

// SBAGLIATO
import { useToast } from 'primevue/usetoast'
const toast = useToast()
toast.add({ severity: 'success', summary: 'Salvato', life: 3000 })
```

---

## 4. Store Pinia

### Stile obbligatorio

Tutti gli store usano la **setup function** (non l'oggetto options):

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

### Store esistenti

| Store | Responsabilita | Stato persistito |
|-------|---------------|------------------|
| `auth` | Login, token, profilo utente, permessi | Token in localStorage |
| `ui` | Sidebar collapsed, layout mode, search drawer | Sidebar in localStorage |
| `navigation` | Dominio attivo | No |
| `tabs` | Tab aperti, tab attivo | Tab in localStorage |
| `context` | Contesto globale (soggetto selezionato) | No |

### Comunicazione fra componenti

- Per stato condiviso: usare uno store Pinia
- **Mai** `window.dispatchEvent(new CustomEvent(...))` — usare ref/computed nello store
- Esempio: il search drawer usa `ui.searchDrawerVisible` e `ui.openSearchDrawer()`, non un evento custom

---

## 5. Navigazione e routing

### Fonte unica: `navigation.js`

Il file `src/core/navigation.js` e' la **fonte unica di verita** per:

- **`DOMAINS`**: array dei domini con key, icona, path
- **`DOMAIN_MENUS`**: voci menu L2 per ogni dominio
- **`resolveTabLabel(meta, t)`**: risolve la label per tab, breadcrumb e titolo pagina

```javascript
// navigation.js
export function resolveTabLabel(meta, t) {
  const { domain, menuKey } = meta
  if (menuKey) return t(`nav_menu.${domain}.${menuKey}`)
  if (domain && domain !== 'home') return t(`nav.${domain}`)
  return null
}
```

**Questa funzione e' usata da**: router guard (tab label), AppTopbar (titolo area), AppBreadcrumb (breadcrumb).

### Route meta — campi riconosciuti

Ogni route autenticata **deve** avere `meta.domain`. Gli altri campi sono opzionali:

| Campo | Tipo | Obbligatorio | Scopo |
|-------|------|:---:|--------|
| `domain` | string | Si | Identifica dominio; guida sidebar, breadcrumb, tab |
| `menuKey` | string | No | Voce L2 del dominio; usato per tab label e breadcrumb |
| `errorKey` | string | No | Solo pagine errore: `'not_found'` \| `'forbidden'` |
| `errorIcon` | string | No | Icona PrimeIcon per pagine errore |
| `public` | boolean | No | `true` solo su `/login`; salta guard autenticazione |

**Non aggiungere altri campi meta** senza necessita verificata. In particolare:
- La **label tab/breadcrumb** si deriva da `domain` + `menuKey` via `resolveTabLabel()` — non serve un campo dedicato
- La **chiave placeholder** si deriva da `domain_menuKey` (con hyphen → underscore) — non serve `placeholderKey`

### Struttura rotte

```javascript
// router/index.js
{
  path: 'amm-software/operatori',
  name: 'amm-software-operatori',
  component: () => import('../core/views/PlaceholderView.vue'),
  meta: { domain: 'amm-software', menuKey: 'operatori' }
}
```

### Navigation guard

Il guard in `router/index.js` gestisce in sequenza:
1. Rotte pubbliche (login)
2. Redirect a login se non autenticato
3. Fetch profilo se mancante
4. Guard admin per `amm-software`
5. Impostazione dominio attivo in `navigation` store
6. Apertura tab (escluso home e pagine errore)

---

## 6. Internazionalizzazione (i18n)

### Regola fondamentale

**Ogni testo visibile all'utente usa `t()` o `$t()`** — zero stringhe hardcoded nei template.

### Organizzazione chiavi

```json
{
  "nav": {
    "anagrafiche": "Anagrafiche",
    "vendite": "Vendite"
  },
  "nav_menu": {
    "amm-software": {
      "operatori": "Operatori",
      "permessi": "Permessi"
    }
  },
  "placeholder": {
    "amm_software_operatori": {
      "title": "Gestione Operatori",
      "features": ["Lista operatori", "Modifica profili"]
    }
  },
  "notifications": {
    "save_success": "Salvato con successo",
    "generic_error": "Si e' verificato un errore"
  },
  "errors": {
    "not_found_title": "Pagina non trovata",
    "forbidden_title": "Accesso negato"
  }
}
```

### Convenzioni chiavi

| Prefisso | Uso |
|----------|-----|
| `nav.*` | Label dominio L1 |
| `nav_menu.<domain>.*` | Label voci menu L2 |
| `placeholder.<domain_menuKey>.*` | Titolo e features placeholder |
| `notifications.*` | Messaggi toast |
| `errors.*` | Titoli pagine errore |
| `context.*` | Tooltip e label contesto globale |

### Istanza condivisa

L'istanza i18n e' in `src/core/i18n.js` — importabile anche fuori dai componenti (es. nel router):

```javascript
import i18n from '../core/i18n'
const t = i18n.global.t
```

---

## 7. CSS e theming

### Architettura variabili

Due livelli di variabili CSS:

1. **PrimeVue** (`--p-*`): gestite dal tema PrimeVue, non modificare direttamente
2. **App** (`--app-*`): variabili applicative definite in `theme.css`, costruite sopra `--p-*`

```css
/* theme.css — esempio */
:root {
  --app-topbar-height: 48px;
  --app-sidebar-width: 240px;
  --app-sidebar-collapsed-width: 56px;
  --app-topbar-bg: var(--p-surface-0);
  --app-sidebar-item-color: var(--p-text-muted-color);
  --app-transition-fast: 0.15s ease;
}
```

### Regole CSS

- Usare `<style scoped>` — sempre
- Preferire variabili `--app-*` per valori ripetuti
- Mai `!important` (tranne override PrimeVue documentato)
- `:deep()` solo per componenti PrimeVue, mai per componenti custom
- Breakpoint responsive: usare le costanti da `constants.js` (`BREAKPOINTS.MOBILE: 768`, `BREAKPOINTS.TABLET: 1024`)

---

## 8. Storage e persistenza

### Layer centralizzato

Tutto l'accesso a `localStorage`/`sessionStorage` passa da `src/core/storage.js`:

```javascript
import { local, STORAGE_KEYS } from '../core/storage'

local.get(STORAGE_KEYS.SIDEBAR_COLLAPSED)
local.set(STORAGE_KEYS.SIDEBAR_COLLAPSED, true)
```

**Mai** accedere direttamente a `localStorage.getItem()` nei componenti o store. Aggiungere nuove chiavi in `STORAGE_KEYS`.

### Chiavi registrate

| Chiave | Scopo | Storage |
|--------|-------|---------|
| `access_token` | JWT access token | localStorage |
| `refresh_token` | JWT refresh token | localStorage |
| `sidebar_collapsed` | Stato sidebar | localStorage |
| `open_tabs` | Tab aperti (array) | localStorage |

---

## 9. Pattern ricorrenti

### Costanti UI

Tutte le costanti UI vivono in `src/core/constants.js`. Non duplicare valori magici nei componenti:

```javascript
import { DRAWER_WIDTH, TOAST_DURATION, PAGINATION, SHORTCUTS } from '../core/constants'
```

### Cleanup listener con HMR

Per listener globali (resize, keydown) negli store/composable:

```javascript
if (typeof window !== 'undefined') {
  window.addEventListener('resize', handler, { passive: true })
  if (import.meta.hot) {
    import.meta.hot.dispose(() => window.removeEventListener('resize', handler))
  }
}
```

### Placeholder automatici

`PlaceholderView.vue` deriva automaticamente la chiave i18n da `route.meta`:

```
domain: 'amm-software', menuKey: 'operatori'
→ chiave: 'amm_software_operatori'
→ i18n: placeholder.amm_software_operatori.title / .features
```

Non serve passare prop ne' aggiungere campi meta extra.

---

## 10. Aggiungere un nuovo dominio

Checklist completa per aggiungere un dominio (es. "logistica"):

### 1. `navigation.js`

```javascript
// DOMAINS — aggiungere entry
{ key: 'logistica', icon: 'pi pi-truck', to: '/logistica' }

// DOMAIN_MENUS — aggiungere array (anche vuoto)
'logistica': [
  { key: 'spedizioni', icon: 'pi pi-send', to: '/logistica/spedizioni' }
]
```

### 2. Chiavi i18n (`locales/it.json` e `locales/en.json`)

```json
{
  "nav": { "logistica": "Logistica" },
  "nav_menu": { "logistica": { "spedizioni": "Spedizioni" } },
  "placeholder": {
    "logistica_spedizioni": {
      "title": "Gestione Spedizioni",
      "features": ["Tracciamento spedizioni", "Gestione corrieri"]
    }
  }
}
```

### 3. Rotte (`router/index.js`)

Se il dominio ha solo pagine placeholder, non serve nulla — `domainPlaceholderRoutes()` genera automaticamente la rotta base.

Per voci L2 con pagine dedicate:

```javascript
// Aggiungere 'logistica' a domainsWithRoutes nel router
const domainsWithRoutes = new Set(['amm-software', 'logistica'])

// Aggiungere rotte figlie
{
  path: 'logistica/spedizioni',
  name: 'logistica-spedizioni',
  component: () => import('../core/views/PlaceholderView.vue'),
  meta: { domain: 'logistica', menuKey: 'spedizioni' }
}
```

### 4. Verifica

```bash
cd frontend && ./node_modules/.bin/vite build
```

Controllare che il build passi senza errori e che il nuovo dominio appaia nella sidebar.

---

## 11. Build e verifica

### Comandi

```bash
# Attivare Node (se necessario)
nvm use

# Build produzione
cd frontend && ./node_modules/.bin/vite build

# Dev server
cd frontend && ./node_modules/.bin/vite dev
```

### Checklist pre-commit frontend

- [ ] Build senza errori
- [ ] Nessuna stringa hardcoded nei template (usa `t()`)
- [ ] Nessun `useToast()` diretto (usa `useNotify()`)
- [ ] Nessun `localStorage` diretto (usa `storage.js`)
- [ ] Nessun `CustomEvent` per comunicazione (usa store Pinia)
- [ ] CSS scoped, nessun `:deep()` su componenti custom
- [ ] Nuove costanti in `constants.js`, non valori magici inline
- [ ] Composable in `core/composables/`, non in `core/`
