# ZeroERP — Layout, Menu e Navigazione

**Sottotitolo**: Architettura sidebar morfica con dominio attivo e sottomenu a tab  
**Data**: Marzo 2026  
**Stack**: Vue 3.5 + PrimeVue 4.5 + Pinia  
**Stato**: Da implementare

> ⚠️ **Documento di progetto di marzo 2026, in parte superato.** Le sezioni
> 10.1, 10.9, 10.13 e 10.15 sono state **riscritte sullo stato del codice il
> 2026-09-26**, quando `AppToolbar.vue`, `useTabLabel`, `useLoading` e
> `useDirtyState` — i pezzi che quelle sezioni progettavano — sono stati
> ritirati perche' nessun file li usava. Per il resto la fonte e'
> [frontend-standards](../../frontend/frontend-standards.md) con il
> [catalogo BB](../../frontend/catalogo-building-block-frontend.md).

---

## Indice

1. [Contesto e Obiettivo](#1-contesto-e-obiettivo)
2. [Pattern di Navigazione: Sidebar Morfica](#2-pattern-di-navigazione-sidebar-morfica)
3. [Gestione dei Sottomenu](#3-gestione-dei-sottomenu)
4. [Struttura dei Componenti Vue](#4-struttura-dei-componenti-vue)
5. [Store Pinia — navigation.js](#5-store-pinia--navigationjs)
6. [Routing Vue Router](#6-routing-vue-router)
7. [Breadcrumb](#7-breadcrumb)
8. [Pagine con Tab — Template](#8-pagine-con-tab--template)
9. [Home — Stato Attuale e Visione Futura](#9-home--stato-attuale-e-visione-futura)
10. [Note architetturali](#10-note-architetturali--integrazione-con-frontend-esistente)
11. [Riepilogo Attività di Sviluppo](#11-riepilogo-attività-di-sviluppo)
12. [Checklist Implementazione](#12-checklist-implementazione)
13. [Decisioni di progetto](#13-decisioni-di-progetto)

---

## 1. Contesto e Obiettivo

ZeroERP è un gestionale ERP usato da operatori con profili diversi: alcuni lavorano su un'unica area (es. sempre fatturazione), altri saltano tra più domini nella stessa sessione. Il sistema permessi esclude automaticamente dalla navigazione le aree non autorizzate.

L'obiettivo di questo documento è definire l'architettura di navigazione frontend: come sono organizzati sidebar, menu e sottomenu, con quale pattern di interazione e come si strutturano le pagine interne.

> **Decisione fondamentale**: nessuna pagina intermedia di "card sottomenu". Il click su una voce di menu apre direttamente il programma — non una schermata di orientamento.

---

## 2. Pattern di Navigazione: Sidebar Morfica

Il pattern adottato è la **sidebar morfica a dominio**: una singola sidebar che cambia contenuto in base al dominio selezionato. Non esistono card intermedie come navigazione strutturale.

### 2.1 Struttura generale dello schermo

```
┌─────────────────────────┬─────────────────────────────────────────┐
│  Sidebar (morfica)      │  Content area                           │
│  220px                  │  flex-1                                 │
│                         │                                         │
│  [stato: HOME]          │  ┌─────────────────────────────────┐   │
│  ──────────────         │  │ Breadcrumb                      │   │
│  🏠 Home (link diretto) │  │ Dominio  >  Voce  >  Sotto-voce │   │
│  ──────────────         │  └─────────────────────────────────┘   │
│  👥 Anagrafiche         │                                         │
│  📋 Pratiche            │  [ Contenuto pagina attiva ]            │
│  💰 Vendite             │                                         │
│  ⚙️  Configurazione     │                                         │
│  🔑 Amm. Software      │                                         │
│     (solo ADMIN)        │                                         │
└─────────────────────────┴─────────────────────────────────────────┘
```

### 2.2 Stato HOME della sidebar

Quando nessun dominio è selezionato, la sidebar mostra le voci di primo livello — i domini funzionali con icona e label. È lo stato iniziale al caricamento dell'app e quello a cui si torna cliccando ← Home.

```
Sidebar — stato HOME
─────────────────────────
  🏠  Home          (link diretto alla dashboard)
  ─────────────────
  👥  Anagrafiche
  📋  Pratiche
  💰  Vendite
  ⚙️   Configurazione
  🔑  Amm. Software     ← visibile solo se ruolo_sistema = ADMIN
```

### 2.3 Stato DOMINIO della sidebar

Quando si seleziona un dominio, la sidebar si trasforma: mostra il menu specifico del dominio. In cima appare sempre il pulsante **← Home** che riporta allo stato HOME.

```
Sidebar — stato DOMINIO (esempio: Anagrafiche)
──────────────────────────────────────────────
  ← Home                  ← sempre in cima, fisso
  ──────────────────
  ANAGRAFICHE              ← titolo dominio (non cliccabile)
  ──────────────────
  👤  Clienti         ●   ← voce attiva evidenziata
  🏢  Fornitori
  👷  Risorse Umane
  🏛️   Emittenti Fiscali
  📊  Statistiche
```

### 2.4 Comportamento delle interazioni

| Azione utente | Risultato |
| --- | --- |
| Click su dominio (es. Anagrafiche) da HOME | Sidebar si trasforma, mostra menu Anagrafiche. Content apre la **pagina preferita** dell'utente per quel dominio, oppure la pagina default di sistema. |
| Click su ← Home nella sidebar di dominio | Sidebar torna allo stato HOME. Content naviga alla dashboard. |
| Click su voce del menu (es. Clienti) | Content area carica la pagina Clienti. Voce evidenziata nella sidebar. |
| Click su voce gia attiva | Nessuna azione (gia sul posto). |
| Refresh pagina | La sidebar si riapre sul dominio corretto in base alla route attiva. |
| Navigazione via breadcrumb | La sidebar non cambia. Il breadcrumb aggiorna la posizione nel content. |

---

## 3. Gestione dei Sottomenu

> **Principio chiave**: la sidebar conosce solo le voci di primo livello del dominio. I sottomenu vivono **dentro la pagina** come tab orizzontali. La sidebar non cresce mai in profondità.

### 3.1 Regola dei tre livelli

La navigazione si articola sempre su tre livelli precisi, con responsabilità separate:

```
Livello 1 — Sidebar HOME     : Dominio (Anagrafiche, Vendite, ...)
Livello 2 — Sidebar DOMINIO  : Entità  (Clienti, Fornitori, ...)
Livello 3 — Tab nella pagina : Sezione (Lista, Statistiche, Impostazioni, ...)

Oltre il terzo livello → tab annidati o filtri/toggle dentro il content della tab.
```

### 3.2 Struttura della pagina con tab

Ogni pagina di entità gestisce i propri sottomenu come `TabView` PrimeVue. L'aggiunta di una nuova tab non richiede alcuna modifica alla sidebar.

```
Content area — pagina Clienti
──────────────────────────────────────────────────────────────
Anagrafiche  >  Clienti                     ← breadcrumb
──────────────────────────────────────────────────────────────
[ Lista ]  [ Statistiche ● ]  [ Impostazioni ]  ← TabView
──────────────────────────────────────────────────────────────

  [ contenuto tab Statistiche ]

```

### 3.3 Quarto livello: navigazione interna alla tab

Se una tab ha a sua volta sottosezioni (es. Statistiche → Per area / Per periodo), queste si gestiscono con navigazione interna alla tab — mai nella sidebar.

```
Content area — Clienti > Statistiche
──────────────────────────────────────────────────────────────
Anagrafiche  >  Clienti  >  Statistiche        ← breadcrumb
──────────────────────────────────────────────────────────────
[ Lista ]  [ Statistiche ● ]  [ Impostazioni ]  ← tab L3
──────────────────────────────────────────────────────────────
  Sub-navigazione dentro Statistiche:
  • Per area geografica  ●
  • Per periodo
  • Per agente
──────────────────────────────────────────────────────────────
  [ grafico per area ]
```

### 3.4 Quando toccare la sidebar vs quando no

| Modifica                                        | Tocchi la sidebar?    | Dove si interviene              |
| ----------------------------------------------- | --------------------- | ------------------------------- |
| Aggiungi tab "Contratti" a Clienti              | No                    | Solo `ClientiView.vue`          |
| Aggiungi sub-sezione a Statistiche              | No                    | Solo `ClientiStatsView.vue`     |
| Aggiungi "Agenti" come nuova entità Anagrafiche | Sì — una riga         | `menus.js`, config Anagrafiche  |
| Aggiungi nuovo dominio "Magazzino"              | Sì — una icona + menu | `menus.js` + icona sidebar HOME |
| Rinomina una voce                               | Sì — una stringa      | `menus.js`                      |

---

## 4. Struttura dei Componenti Vue

### 4.1 Albero dei componenti

```
App.vue
  └── AppLayout.vue
        ├── AppSidebar.vue          ← sidebar morfica
        │     ├── SidebarHome.vue   ← stato HOME (lista domini)
        │     └── SidebarDomain.vue ← stato DOMINIO (menu specifico)
        └── AppContent.vue
              ├── AppBreadcrumb.vue ← breadcrumb automatico da route
              └── <router-view />   ← pagine
```

### 4.2 File e responsabilità

| File                   | Responsabilità                                                                       |
| ---------------------- | ------------------------------------------------------------------------------------ |
| `AppLayout.vue`        | Contenitore principale. Divide schermo in sidebar + content. Nessuna logica.         |
| `AppSidebar.vue`       | Legge `currentDomain` dallo store. Renderizza `SidebarHome` o `SidebarDomain`.       |
| `SidebarHome.vue`      | Lista delle icone dominio. Click → imposta `currentDomain` e naviga alla prima voce. |
| `SidebarDomain.vue`    | Riceve il menu del dominio attivo come prop. Mostra ← Home + voci con `PanelMenu`.   |
| `AppBreadcrumb.vue`    | Genera breadcrumb automaticamente dalla route `meta.breadcrumb`.                     |
| `stores/navigation.js` | `currentDomain`, `menus` per dominio, azioni `setDomain` / `clearDomain`.            |

### 4.3 Struttura cartelle

```
src/
  components/
    layout/
      AppLayout.vue
      AppSidebar.vue
      AppBreadcrumb.vue
      sidebar/
        SidebarHome.vue
        SidebarDomain.vue
  stores/
    navigation.js      ← currentDomain + menus config
    auth.js            ← ruolo_sistema, domini visibili
  views/
    HomeView.vue
    anagrafiche/
      ClientiView.vue
      FornitoriView.vue
      ...
    vendite/
      FattureView.vue
      ...
    amm-software/      ← solo ADMIN
      UtentiView.vue
      RepartiView.vue
```

---

<a id="5-store-pinia--navigationjs"></a>
## 5. Store Pinia — navigation.js

Lo store centralizza due cose: qual è il dominio attivo (`currentDomain`) e la configurazione dei menu per ogni dominio. Aggiungere voci o domini è solo questione di editare l'oggetto `menus`.

### 5.1 Struttura dello store

```javascript
// stores/navigation.js
import { defineStore } from 'pinia'

export const useNavigationStore = defineStore('navigation', {
  state: () => ({
    currentDomain: null,  // null = HOME | 'anagrafiche' | 'vendite' | ...
  }),

  getters: {
    currentMenu: (state) => menus[state.currentDomain] ?? [],
    isHome: (state) => state.currentDomain === null,
  },

  actions: {
    setDomain(domain) { this.currentDomain = domain },
    clearDomain()     { this.currentDomain = null },
  }
})
```

### 5.2 Configurazione menu

Ogni dominio è un array di voci con `label`, `icon`, `route`. I sotto-voci nella sidebar (se necessari) si aggiungono con `items` — `PanelMenu` li gestisce nativamente.

```javascript
const menus = {
  anagrafiche: [
    { label: 'Clienti',          icon: 'pi pi-users',       route: '/anagrafiche/clienti' },
    { label: 'Fornitori',        icon: 'pi pi-building',    route: '/anagrafiche/fornitori' },
    { label: 'Risorse Umane',    icon: 'pi pi-id-card',     route: '/anagrafiche/risorse-umane' },
    { label: 'Emittenti Fiscali',icon: 'pi pi-landmark',    route: '/anagrafiche/emittenti' },
  ],
  vendite: [
    { label: 'Fatture',          icon: 'pi pi-file-invoice',route: '/vendite/fatture' },
    { label: 'Ordini',           icon: 'pi pi-shopping-cart',route: '/vendite/ordini' },
    { label: 'Statistiche',      icon: 'pi pi-chart-bar',   route: '/vendite/statistiche' },
  ],
  // ... altri domini
}
```

### 5.3 Domini visibili per ruolo

La sidebar HOME mostra solo i domini autorizzati per l'utente, filtrati da `ruolo_sistema` e aree funzionali letti dall'endpoint `GET /api/v1/core/me/` al boot dell'app.

```javascript
// stores/auth.js
visibleDomains: (state) => {
  const all      = ['anagrafiche', 'pratiche', 'vendite', 'config']
  const adminOnly = ['amm-software']
  const visible  = all.filter(d => state.aree_autorizzate.includes(d))
  if (state.ruolo_sistema === 'ADMIN') visible.push(...adminOnly)
  return visible
}
```

---

## 6. Routing Vue Router

### 6.1 Struttura delle route

Ogni route ha `meta.domain` (per ripristinare la sidebar al refresh) e `meta.breadcrumb` (per il breadcrumb automatico).

```javascript
// router/index.js
{
  path: '/anagrafiche/clienti',
  name: 'clienti',
  component: () => import('@/views/anagrafiche/ClientiView.vue'),
  meta: {
    domain: 'anagrafiche',
    breadcrumb: ['Anagrafiche', 'Clienti'],
    requiresAuth: true,
  }
},
```

### 6.2 Navigation guard — ripristino sidebar

Al cambio di route (es. dopo refresh o navigazione diretta da URL), il guard legge `meta.domain` e imposta il dominio corretto nello store.

```javascript
router.beforeEach((to, from, next) => {
  const nav = useNavigationStore()
  if (to.meta.domain) {
    nav.setDomain(to.meta.domain)
  } else {
    nav.clearDomain()  // Home e pagine senza dominio
  }
  next()
})
```

---

## 7. Breadcrumb

Il breadcrumb è generato automaticamente dalla `meta` della route attiva. Non richiede logica manuale nelle pagine.

```
Route: /anagrafiche/clienti
meta.breadcrumb: ['Anagrafiche', 'Clienti']

  Anagrafiche  >  Clienti

────────────────────────────────────
Con tab attiva (gestita dalla pagina):

  Anagrafiche  >  Clienti  >  Statistiche
```

Il terzo segmento (tab attiva) viene aggiornato dalla pagina tramite un composable `useTabBreadcrumb()`:

```javascript
// ClientiView.vue
const { setTabCrumb } = useTabBreadcrumb()
watch(activeTab, (tab) => setTabCrumb(tab.label))
```

---

<a id="8-pagine-con-tab--template"></a>
## 8. Pagine con Tab — Template

Tutte le pagine di entità seguono lo stesso template. Le tab si aggiungono senza toccare nulla fuori dal file della pagina stessa.

### 8.1 Template standard

```vue
<template>
  <div class="page-container">
    <TabView v-model:activeIndex="activeTab" @tab-change="onTabChange">
      <TabPanel header="Lista">
        <ClientiLista />
      </TabPanel>
      <TabPanel header="Statistiche">
        <ClientiStatistiche />
      </TabPanel>
      <TabPanel header="Impostazioni">
        <ClientiImpostazioni />
      </TabPanel>
      <!-- Aggiungere tab qui senza modificare nulla altrove -->
    </TabView>
  </div>
</template>
```

### 8.2 Gestione breadcrumb da tab

```vue
<script setup>
import { ref } from 'vue'
import { useTabBreadcrumb } from '@/composables/useTabBreadcrumb'

const activeTab = ref(0)
const tabs = ['Lista', 'Statistiche', 'Impostazioni']
const { setTabCrumb } = useTabBreadcrumb()

function onTabChange(e) {
  setTabCrumb(tabs[e.index])
}
</script>
```

---

<a id="9-home--stato-attuale-e-visione-futura"></a>
## 9. Home — Stato Attuale e Visione Futura

### 9.1 Stato attuale → transizione

La home attualmente mostra:

- Benvenuto + nome utente (rimane invariato)
- Griglia con 9 card di navigazione ai domini
- Pannello sessioni attive (rimane invariato)

**In questa fase** la griglia delle 9 card di navigazione viene sostituita con **4 card placeholder** con icona "lavori in corso" (`pi pi-wrench`) e label generiche (`Dash 1`, `Dash 2`, `Dash 3`, `Dash 4`). La navigazione ai domini ora vive nella sidebar morfica, quindi le card sulla home cambiano ruolo: diventeranno widget KPI/dashboard in futuro.

```
HomeView.vue — stato transitorio
──────────────────────────────────────────────────────────────
  Benvenuto, [Nome]                    ← invariato
──────────────────────────────────────────────────────────────
  🔧 Dash 1        🔧 Dash 2        🔧 Dash 3        🔧 Dash 4
  (lavori in corso) (lavori in corso) (lavori in corso) (lavori in corso)
──────────────────────────────────────────────────────────────
  [ Sessioni attive ]                  ← invariato
──────────────────────────────────────────────────────────────
```

### 9.2 Visione futura

La home diventerà una **dashboard personalizzata per utente**, composta da card configurabili. Ogni card rappresenta un KPI, un'attività importante o un accesso rapido scelto dall'utente stesso (preferiti).

Le card mostreranno dati filtrati per l'utente corrente (es. solo le sue pratiche, i suoi emittenti autorizzati). La progettazione di dettaglio è rimandata a una fase successiva.

---

<a id="10-note-architetturali--integrazione-con-frontend-esistente"></a>
## 10. Note architetturali — Integrazione con frontend esistente

### 10.1 Content tabs, azioni di pagina e tab di livello 3 — come convivono
> Riscritta il 2026-09-26 sullo stato del codice. Il progetto di marzo
> prevedeva una barra di layout, `AppToolbar.vue`, alimentata da
> `route.meta.actions`: non e' mai entrata in uso ed e' stata ritirata.

La gerarchia visiva e' su tre livelli, con responsabilita' separate:

```text
┌─────────────────────────────────────────────────────────────┐
│ Content tabs (L2 — pagine aperte tipo browser)              │
│ [ Clienti ]  [ Fatture ]  [ Ordini ]                        │
├─────────────────────────────────────────────────────────────┤
│ Pagina                                                      │
│   PageActionsBar (azioni della pagina: «Nuovo», «Esporta»…) │
│   Tabs L3, se la pagina ha sezioni                          │
│   [ contenuto ]                                             │
└─────────────────────────────────────────────────────────────┘
```

| Livello | Componente | Cosa mostra | Chi lo gestisce |
| --- | --- | --- | --- |
| Content tabs | `ContentTabs.vue` | Pagine aperte (tipo browser) | `stores/tabs.js` |
| Azioni di pagina | `PageActionsBar.vue` | Azione primaria, utility inline, secondarie nel menu (su mobile tutto tranne la primaria va nel kebab) | la **pagina**, che le dichiara |
| Tab L3 (sezioni) | `Tabs` PrimeVue | Sezioni dentro la pagina | la pagina |

⭐ Le azioni stanno **nella pagina**, non nel layout: le conosce solo chi sa
che cosa la pagina fa, e una barra di layout guidata da `route.meta` le avrebbe
separate dal codice che le esegue. Per le liste la toolbar e' quella di
`<ListaConfigurabile>` (frontend-standards §«Lista standard»).

### 10.2 Convivenza navigation.js (config) e stores/navigation.js (store)

- `src/core/navigation.js` — **già esiste**, contiene `DOMAINS` e `SIDEBAR_ITEMS` (config statica, icone, route)
- `stores/navigation.js` — **da creare**, store Pinia con `currentDomain` e azioni `setDomain`/`clearDomain`

Lo store *consuma* la config statica. La config statica viene estesa con la struttura `menus` per dominio (voci di secondo livello). Nessun conflitto.

### 10.3 Responsive e sidebar collassata

L'attuale `stores/ui.js` gestisce `sidebarCollapsed` con auto-collasso a 1024px. La sidebar morfica deve rispettare questo comportamento:

- **Sidebar collassata, stato HOME**: mostra solo icone domini (come oggi)
- **Sidebar collassata, stato DOMINIO**: mostra solo icone delle voci del dominio + icona ← Home
- **Tooltip**: al hover su icona in stato collassato, mostra label (già implementato)

### 10.4 SearchDrawer e contesto globale

La ricerca globale (SearchDrawer) e il context chip nella topbar sono indipendenti dalla sidebar morfica. Non servono modifiche: la ricerca si apre sopra il content, il contesto resta nella topbar. La sidebar morfica non interagisce con il contesto globale.

### 10.5 Tab multiple tipo browser (content tabs)

L'area content supporta **tab multiple tipo browser**: ogni pagina aperta diventa una tab nell'area content, e l'utente puo' passare dall'una all'altra senza perdere lo stato.

```text
Toolbar / Content tabs
──────────────────────────────────────────────────────────────
  [ Clienti ]  [ Fattura #127 ● ]  [ Ordine #45 ]  [ + ]
──────────────────────────────────────────────────────────────
  [ contenuto della tab attiva ]
```

#### Comportamento

| Azione | Risultato |
| --- | --- |
| Click su voce sidebar | Apre una nuova tab (o attiva la tab se gia' aperta) |
| Click su tab esistente | Switcha alla tab, stato preservato |
| Click su X nella tab | Chiude la tab (con conferma se ci sono modifiche non salvate) |
| Refresh pagina | Le tab aperte vengono ripristinate (persiste in sessionStorage) |

#### Note di design

- Le tab sono **a livello di content area**, non a livello di browser — il layout (sidebar + topbar) resta fisso
- Lo stato di ogni tab (filtri, scroll, form in corso) viene preservato tramite `<KeepAlive>` di Vue o store dedicato
- Limite massimo di tab aperte configurabile (es. 10) per evitare degrado performance
- Le tab possono appartenere a **domini diversi**: aprire Clienti e poi Fatture non chiude la tab Clienti
- La sidebar morfica segue la tab attiva: se switchi su una tab di un altro dominio, la sidebar si aggiorna

### 10.6 Pagina default per dominio

Quando l'utente clicca su un dominio nella sidebar HOME, il sistema apre automaticamente una **pagina default**. La pagina default segue questa priorita':

1. **Preferita utente** — se l'utente ha impostato una pagina preferita per quel dominio, si apre quella
2. **Default di sistema** — altrimenti si apre la prima voce del menu del dominio (configurata in `DOMAIN_MENUS`)

#### Persistenza preferiti

I preferiti utente per dominio si salvano in `localStorage` (chiave: `domain_default_{domainKey}`). In futuro potranno essere sincronizzati lato server (es. `config.user_preferences`).

```javascript
// Esempio struttura preferiti in localStorage
{
  "domain_default_anagrafiche": "/anagrafiche/clienti",
  "domain_default_vendite": "/vendite/fatture",
  // se manca → usa la prima voce di DOMAIN_MENUS
}
```

#### Come si imposta la pagina preferita

Nella sidebar di dominio, accanto alla voce attiva, compare un'icona stella (o pin). Click sulla stella → la voce diventa la preferita per quel dominio. Un solo preferito per dominio.

### 10.7 Deep linking e content tabs

Quando un utente accede direttamente a un URL (es. `/vendite/fatture/127` da bookmark o link condiviso), il sistema deve:

1. Leggere `meta.domain` dalla route → impostare `currentDomain` (sidebar si aggiorna)
2. Creare automaticamente una content tab per quella route
3. Se la tab era gia' aperta (stessa route), attivarla invece di duplicarla

La chiave di unicita' di una tab e' la **route path completa** (es. `/vendite/fatture/127`). Due fatture diverse = due tab diverse. La stessa fattura aperta due volte = una sola tab.

```javascript
// stores/tabs.js — logica openTab
function openTab(route) {
  const existing = tabs.find(t => t.path === route.path)
  if (existing) {
    activeTabId.value = existing.id
    return
  }
  // crea nuova tab
  tabs.push({ id: generateId(), path: route.path, label: route.meta.tabLabel || route.meta.breadcrumb?.at(-1), domain: route.meta.domain })
  activeTabId.value = tabs.at(-1).id
}
```

Il router guard `beforeEach` chiama `openTab()` ad ogni navigazione — questo gestisce sia il click dalla sidebar sia il deep link diretto.

### 10.8 Inter-tab freshness (invalidazione dati tra tab)

Scenario: l'operatore modifica un cliente nella tab "Cliente Rossi", poi switcha sulla tab "Lista Clienti". La lista deve mostrare i dati aggiornati.

Best practice: **event bus leggero** tramite composable `useTabEvents`.

```javascript
// composables/useTabEvents.js
import { ref } from 'vue'

const listeners = ref(new Map())

export function useTabEvents() {
  // Emetti evento quando i dati cambiano
  function emitDataChanged(entityType, entityId) {
    const event = { type: 'data-changed', entityType, entityId, timestamp: Date.now() }
    listeners.value.forEach((cb) => cb(event))
  }

  // Ascolta eventi (ogni tab si registra)
  function onDataChanged(callback) {
    const id = Symbol()
    listeners.value.set(id, callback)
    return () => listeners.value.delete(id)  // cleanup
  }

  return { emitDataChanged, onDataChanged }
}
```

Pattern d'uso nelle pagine:

- **Pagina dettaglio** (es. `ClienteDetail`): dopo un salvataggio chiama `emitDataChanged('cliente', clienteId)`
- **Pagina lista** (es. `ClientiList`): ascolta `onDataChanged` e quando riceve un evento con `entityType === 'cliente'`, ri-esegue la query (solo se la tab e' attiva o al prossimo `tabActivated`)
- **Ottimizzazione**: il refresh avviene solo quando la tab diventa attiva (non in background), tramite un flag `stale` che viene controllato al `tabActivated`

> **Nota**: il context store (ricerca universale) e' **globale** — non e' per-tab. Se l'utente ha selezionato un contesto (es. "Cliente Rossi"), tutte le tab che supportano il filtro per contesto lo applicano. Questo e' coerente: il contesto rappresenta "su chi sto lavorando ora", non "cosa ho aperto".

### 10.9 Label dinamiche nelle content tabs
> Riscritta il 2026-09-26 sullo stato del codice. Il progetto di marzo
> prevedeva `useTabLabel` per rinominare la tab con il dato caricato
> («Fattura #127»): non e' mai entrato in uso ed e' stato ritirato.

La label di una content tab e' **quella della rotta**: `resolveTabLabel` in
`core/navigation.js`, dalla `meta` della rotta, alla sua apertura. Non cambia
col contenuto, e oggi non ne ha bisogno: un'entita' specifica (una fattura, un
cliente) **non apre una pagina**, si apre nel **drawer** sopra la lista, e il
drawer porta il proprio titolo (`DrawerTitle`, `DrawerContextHeader`). La tab
resta «Fatture» perche' la pagina e' la lista delle fatture.

⚠️ `stores/tabs.js` espone ancora `updateLabel(path, label)`, senza nessun
chiamante. Se nascera' una pagina di dettaglio con rotta propria (oggi l'unica
con un `:id` e' l'editor delle definizioni di workflow), il punto d'aggancio e'
quello.

### 10.10 Pagine errore (404, 403)

| Errore | Dove si renderizza | Comportamento |
| --- | --- | --- |
| 404 — route inesistente | Content tab dedicata "Pagina non trovata" | Mostra messaggio + link alla home. La tab si puo' chiudere. |
| 403 — dominio non autorizzato | Content tab dedicata "Accesso negato" | Messaggio: "Non hai i permessi per accedere a quest'area". La sidebar non mostra il dominio (filtrato da `visibleDomains`), ma l'utente potrebbe digitare l'URL. |
| 403 — entita' non autorizzata | Gestito dalla pagina stessa | L'API ritorna 403, la pagina mostra un `Message` PrimeVue inline. La tab resta aperta. |
| Errore di rete / 500 | Toast globale (gia' implementato in `useApiHandler`) | Non crea tab di errore. Il toast persistente notifica l'utente. |

Componenti: `NotFoundView.vue` e `ForbiddenView.vue` — pagine semplici, renderizzate dentro una content tab come qualsiasi altra pagina.

```javascript
// router — catch-all
{ path: '/:pathMatch(.*)*', name: 'not-found', component: NotFoundView, meta: { breadcrumb: ['Pagina non trovata'] } }
```

### 10.11 Layout responsive e mobile

#### Breakpoint e comportamento

| Breakpoint | Sidebar | Content tabs | Topbar |
| --- | --- | --- | --- |
| > 1024px (desktop) | Visibile, espandibile/collassabile | Barra tab visibile | Completa |
| 768–1024px (tablet) | Collassata automaticamente (solo icone) | Barra tab visibile, label abbreviate | Compatta |
| < 768px (mobile) | Nascosta, si apre come drawer overlay | Dropdown select al posto della barra tab | Hamburger + titolo pagina |

#### Soluzione tecnica: 3 stati gestiti da `stores/ui.js`

Lo store `ui.js` gia' gestisce `sidebarCollapsed` e `windowWidth`. Si estende con un computed `layoutMode` che guida tutto il layout:

```javascript
// stores/ui.js — estensione
getters: {
  layoutMode: (state) => {
    if (state.windowWidth < 768)  return 'mobile'
    if (state.windowWidth < 1024) return 'tablet'
    return 'desktop'
  },
  // sidebar visibile come elemento inline (non overlay)
  sidebarInline: (state) => state.layoutMode !== 'mobile',
  // sidebar aperta come drawer overlay (solo mobile)
  sidebarOverlay: (state) => state.layoutMode === 'mobile',
}
```

#### Sidebar: 3 modalita'

```text
DESKTOP (> 1024px)              TABLET (768-1024px)           MOBILE (< 768px)
┌──────────┬──────────┐    ┌────┬───────────────┐    ┌───────────────────┐
│ Sidebar  │ Content  │    │ ☰  │   Content     │    │ ☰  Titolo pagina  │
│ 220px    │ flex-1   │    │60px│   flex-1      │    ├───────────────────┤
│ espansa  │          │    │icon│               │    │   Content 100%    │
│          │          │    │only│               │    │                   │
└──────────┴──────────┘    └────┴───────────────┘    └───────────────────┘
                                                      ↓ hamburger click
                                                     ┌────────┬──────────┐
                                                     │Sidebar │ (overlay)│
                                                     │drawer  │ scuro    │
                                                     │280px   │ backdrop │
                                                     └────────┴──────────┘
```

Implementazione sidebar mobile:

- Usare il componente PrimeVue `Drawer` (ex `Sidebar`) con `position="left"` e `modal=true`
- Il drawer si apre al click sul pulsante hamburger nella topbar
- Al click su una voce del menu, il drawer si chiude automaticamente e il content naviga
- Il drawer contiene gli stessi componenti `SidebarHome`/`SidebarDomain` — nessuna duplicazione

```vue
<!-- AppLayout.vue — logica condizionale -->
<template>
  <!-- Desktop/Tablet: sidebar inline -->
  <aside v-if="ui.sidebarInline" class="app-sidebar">
    <AppSidebar />
  </aside>

  <!-- Mobile: sidebar come drawer overlay -->
  <Drawer v-else v-model:visible="mobileMenuOpen" position="left"
          :pt="{ root: { style: 'width: 280px' } }">
    <AppSidebar @navigate="mobileMenuOpen = false" />
  </Drawer>
</template>
```

#### Content tabs: barra vs dropdown

- **Desktop/Tablet**: `ContentTabs.vue` mostra la barra tab orizzontale (come descritto in sez. 10.5)
- **Mobile**: la barra tab viene sostituita da un `Select` PrimeVue con la lista delle tab aperte. L'utente seleziona la tab dal dropdown.

```vue
<!-- ContentTabs.vue — adattivo -->
<template>
  <!-- Desktop/Tablet: barra tab -->
  <div v-if="ui.layoutMode !== 'mobile'" class="content-tabs-bar">
    <div v-for="tab in tabs" :key="tab.id" class="content-tab" ...>
      {{ tab.label }}
    </div>
  </div>

  <!-- Mobile: dropdown -->
  <Select v-else v-model="activeTabId" :options="tabs"
          optionLabel="label" optionValue="id"
          class="content-tabs-dropdown" />
</template>
```

#### Topbar mobile

Su mobile la topbar si semplifica:

- **Sinistra**: pulsante hamburger (apre il drawer sidebar)
- **Centro**: titolo della pagina attiva (da `route.meta.breadcrumb` ultimo segmento)
- **Destra**: icona ricerca (apre SearchDrawer)
- Il context chip, la data e il logo emittente si nascondono (accessibili dal drawer o dalla pagina)

#### CSS: variabili e breakpoint dal tema

Tutti i breakpoint sono definiti come variabili CSS in `theme.css`, cosi' ogni componente puo' usarli senza hardcodare valori:

```css
/* theme.css — breakpoint e variabili responsive */
:root {
  --app-breakpoint-mobile: 768px;
  --app-breakpoint-tablet: 1024px;

  --app-sidebar-width: 220px;
  --app-sidebar-collapsed-width: 60px;
  --app-sidebar-mobile-width: 280px;

  --app-topbar-height: 48px;
  --app-topbar-mobile-height: 44px;
}
```

I componenti usano `@media` con queste soglie (o il getter `layoutMode` dallo store per la logica JS). Non servono librerie CSS esterne — i breakpoint sono pochi e ben definiti.

> **Nota implementativa**: nello Sprint 1, la struttura CSS deve gia' usare queste variabili e i componenti devono usare `v-if="ui.layoutMode"` per la logica condizionale. Il comportamento mobile completo (drawer, dropdown tabs, topbar semplificata) si implementa nello Sprint 1 insieme al resto — tanto non c'e' produzione da proteggere e costa poco farlo subito se la struttura e' gia' predisposta.

### 10.12 Keyboard shortcuts

Gli operatori ERP sono power user. Le scorciatoie da tastiera accelerano il lavoro quotidiano.

| Shortcut | Azione |
| --- | --- |
| `Ctrl+K` | Apri ricerca universale (SearchDrawer) |
| `Ctrl+Tab` | Tab successiva |
| `Ctrl+Shift+Tab` | Tab precedente |
| `Ctrl+W` | Chiudi tab corrente (con conferma se dirty) |
| `Ctrl+B` | Toggle sidebar espansa/collassata |
| `Ctrl+Home` | Vai alla Home |
| `Esc` | Chiudi drawer/dialog attivo |

Implementazione: composable `useKeyboardShortcuts` registrato in `AppLayout.vue`. Usa `@keydown` sul documento con event delegation. Le scorciatoie sono configurabili (costanti in `constants.js`) e disattivabili quando un input ha il focus.

```javascript
// composables/useKeyboardShortcuts.js
import { onMounted, onUnmounted } from 'vue'

export function useKeyboardShortcuts(shortcuts) {
  function handler(e) {
    // non intercettare se il focus e' su input/textarea/contenteditable
    if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return
    if (e.target.isContentEditable) return

    for (const s of shortcuts) {
      if (s.ctrl === e.ctrlKey && s.shift === (e.shiftKey || false) && s.key === e.key) {
        e.preventDefault()
        s.action()
        return
      }
    }
  }
  onMounted(() => document.addEventListener('keydown', handler))
  onUnmounted(() => document.removeEventListener('keydown', handler))
}
```

### 10.13 Loading states e transizioni
> Riscritta il 2026-09-26 sullo stato del codice. Il progetto di marzo
> prevedeva `useLoading` (skeleton al primo caricamento, ProgressBar ai
> successivi): non e' mai entrato in uso ed e' stato ritirato.

Lo stato di caricamento **non ha un composable proprio**: sta dove sta la
chiamata.

| Contesto | Chi tiene lo stato | Dove appare |
| --- | --- | --- |
| Chiamata di un componente | il `loading` di `useApiHandler` (lo stesso `execute` che gestisce errori e toast) | sul controllo che l'ha lanciata: pulsante, drawer, pannello |
| Lista | lo store della lista (`useListaStoreCore`) | il `loading` della DataTable |
| Salvataggio form | il `loading` di `useApiHandler` | il pulsante Salva (`FormFooter`) |
| Apertura drawer | `useDrawerContentReady` | il contenuto pesante monta a fine animazione, per non rimbalzare |
| Cambio dominio sidebar | nessuno | istantaneo |

Principio invariato: **mai bloccare l'intera UI**, il caricamento e' sempre
localizzato nel componente che lo aspetta. Gli skeleton non si usano.

### 10.14 Contesto globale (ricerca universale) e interazione con tab/domini

Il context store (`stores/context.js`) rappresenta il **soggetto/entita' su cui l'operatore sta lavorando**. E' globale e trasversale a tutte le tab e domini.

#### Regole di interazione

| Scenario | Comportamento |
| --- | --- |
| Contesto attivo + apro lista Clienti | La lista filtra automaticamente per il soggetto in contesto (se applicabile) |
| Contesto attivo + apro Fatture | La lista fatture filtra per il cliente/fornitore in contesto |
| Contesto attivo + apro pagina che non supporta il filtro | Nessun effetto — il chip resta visibile ma la pagina lo ignora |
| Rimuovo il contesto (click X sul chip) | Tutte le tab rimuovono il filtro e mostrano dati completi |
| Cambio contesto | Tutte le tab attive che supportano il filtro si aggiornano (via `watch` sul context store) |
| Switch tab | Il contesto **non cambia** — e' globale, non per-tab |

#### Implementazione nelle pagine

Ogni pagina che supporta il filtro per contesto usa un pattern standard:

```javascript
// pattern standard per pagine context-aware
import { useContextStore } from '@/stores/context'
import { watch } from 'vue'

const context = useContextStore()

// Query reattiva: si aggiorna quando cambia il contesto
const queryParams = computed(() => ({
  ...paginationParams,
  soggetto_ruolo_id: context.soggettoRuoloId || undefined,
}))

// Watch per refresh automatico quando il contesto cambia
watch(() => context.soggettoRuoloId, () => {
  resetPagination()
  fetchData()
})
```

#### Indicatore visivo nelle tab

Quando il contesto e' attivo, le tab che lo supportano mostrano un **indicatore** (es. un piccolo dot colorato nella label della tab) per segnalare che i dati sono filtrati. Questo evita confusione: l'operatore sa che sta vedendo dati parziali.

```text
Content tabs con contesto attivo
──────────────────────────────────────────────────────────────
  [ Clienti 🔵 ]  [ Fatture 🔵 ]  [ Impostazioni ]
                                    ↑ non supporta contesto
──────────────────────────────────────────────────────────────
```

### 10.15 Dirty state e conferma chiusura tab
> Riscritta il 2026-09-26 sullo stato del codice. Il progetto di marzo
> prevedeva `useDirtyState`, che alzava il flag `dirty` della tab dalla
> pagina: non e' mai entrato in uso ed e' stato ritirato.

🟡 **In corso dal 2026-09-26 — scelta A di Tid: lo scrittore parte dai drawer.**

Fino a quel giorno i lettori c'erano (flag `dirty` in `stores/tabs.js`,
pallino in `ContentTabs.vue`, conferma di chiusura in `useConfirmCloseTab`,
avviso «N schede con modifiche» nel cambio emittente) e lo scrittore no:
nessuno alzava il flag, e nessun errore lo segnalava.

⚠️ `useDirtyState` non aveva mai trovato un consumatore perche' le modifiche
non vivono nella **pagina**: vivono nel **drawer** aperto sopra la lista. Lo
scrittore quindi sta nei drawer:

* la fotografia del form di `useDrawerFormPreserve` risponde anche «ci sono
  modifiche non salvate?» (`modificato`);
* con l'opzione `visibile` il drawer lo dice alla sua tab
  (`tabs.segnalaModifiche(path, sorgente, sporca)`): una tab e' sporca finche'
  almeno un suo drawer aperto ha modifiche; chiudere o salvare abbassa il
  segnale;
* ⭐ la protezione vera sta **alla chiusura del drawer** (`chiudiConConferma`):
  con il drawer aperto il velo copre tab e topbar, e il primo clic sulla X di
  una tab chiudeva il drawer — cioe' abbandonava le modifiche — prima di
  arrivare alla tab (prova in-app di Tid, 2026-09-26). Chiudere un drawer con
  modifiche chiede «Chiudi senza salvare?»; la scritta «Modifica» del titolo
  e' arancio finche' c'e' qualcosa da salvare;
* collegati (2026-09-26, due giri; il primo provato in-app da Tid): tutti i drawer
  con un form da salvare, i form inline sotto una lista, i form a elenco e
  quelli spezzati su piu' campi, i drawer generici (`EntityFormDrawer`,
  `GenericConfigDrawer`, `AppDrawer`). Fuori: le AppDialog (piccoli form di
  conferma), e il drawer del lotto di vendite, che non ha un form.

### Sprint 1 — Tutta l'infrastruttura di navigazione

**Obiettivo**: costruire tutto in un colpo — store, content tabs, sidebar morfica, routing, composable di supporto, pagine errore, home, breadcrumb, placeholder. Nessuna produzione da proteggere.

**1a. Store e config**

- [ ] Creare `stores/navigation.js` (store Pinia: `currentDomain`, `setDomain`, `clearDomain`)
- [ ] Estendere `core/navigation.js` con `DOMAIN_MENUS` — config voci L2 per ogni dominio
  - `amm-software` con 4 voci placeholder:
    `Operatori`, `Profili Reparto`, `Permessi`, `Audit Log` — tutte con icona `pi pi-wrench`
  - Gli altri domini: voci vuote o placeholder fino all'implementazione
- [ ] Aggiungere `visibleDomains` getter a `stores/auth.js` (filtra su `ruolo_sistema` e aree da `/core/me/`)
- [ ] Store Pinia `stores/tabs.js` — gestione content tabs (id, path, label, dominio, stato dirty)

**1b. Content tabs (struttura tipo browser)**

- [ ] Componente `ContentTabs.vue` — barra tab orizzontale sopra il content
- [ ] Integrazione con `<router-view>` + `<KeepAlive>` per preservare stato tab inattive
- [ ] Deep linking: URL diretto crea tab automaticamente; unicita' per route path (sez. 10.7)
- [ ] Click su voce sidebar → apre nuova tab (o attiva tab esistente se gia' aperta)
- [ ] Chiusura tab con X (conferma se dirty)
- [ ] Persistenza tab aperte in `sessionStorage` (ripristino al refresh)
- [ ] Limite massimo tab configurabile (es. 10)
- [ ] Indicatore contesto attivo (dot colorato) sulle tab context-aware (sez. 10.14)

**1c. Sidebar morfica**

- [ ] Refactor `AppSidebar.vue` → sidebar morfica (switch `SidebarHome` / `SidebarDomain`)
- [ ] Implementare `SidebarHome.vue` (lista domini, click → `setDomain` + naviga a pagina default)
- [ ] Implementare `SidebarDomain.vue` (pulsante ← Home + titolo dominio + voci con icone)
- [ ] La sidebar segue la tab attiva: switch su tab di altro dominio → sidebar si aggiorna
- [ ] Sidebar collassata: solo icone + tooltip (coerente con comportamento attuale)
- [ ] Icona stella/pin nella sidebar per impostare pagina preferita per dominio

**1d. Routing, pagine errore, pagina default**

- [ ] Router guard (`beforeEach`): legge `meta.domain` → imposta `currentDomain` + chiama `openTab()`
- [ ] Logica pagina default per dominio: preferita utente (localStorage) oppure prima voce menu
- [ ] Route catch-all 404 → `NotFoundView.vue` (renderizzata in content tab)
- [ ] Route guard 403 → `ForbiddenView.vue` (per URL digitati di domini non autorizzati)
- [ ] Route: `/amm-software` e sotto-route → pagine placeholder

**1e. Composable di supporto**

- ~~`useTabLabel.js` — aggiorna label dinamica della tab corrente (sez. 10.9)~~ ritirato il 2026-09-26
- [ ] `useTabEvents.js` — event bus inter-tab per invalidazione dati (sez. 10.8)
- [ ] `useKeyboardShortcuts.js` — scorciatoie tastiera registrate in AppLayout (sez. 10.12)
- ~~`useDirtyState.js` — traccia modifiche non salvate per conferma chiusura tab~~ ritirato il 2026-09-26

**1f. Home, breadcrumb, pagine placeholder**

- [ ] `HomeView.vue`: sostituire griglia 9 domini con 4 card placeholder (`Dash 1..4`, icona `pi pi-wrench`)
- [ ] Implementare `AppBreadcrumb.vue` (generato da route `meta.breadcrumb`)
- [ ] Creare composable `useTabBreadcrumb.js`
- [ ] Aggiungere `meta.domain` e `meta.breadcrumb` a tutte le route
- [ ] `PlaceholderView.vue` riutilizzabile (titolo + lista funzionalita' in arrivo come props)
- [ ] Pagine placeholder per Amm. Software (vedi sezione 12.1) e per gli altri domini

### Sprint 2 — Area Amm. Software completa

**Obiettivo**: prima area funzionante end-to-end, dal backend al frontend.

- [ ] Implementare backend e frontend Amministrazione Utenti (vedi WIP `amministrazione-utenti.md`)
- [ ] Route `/amm-software/operatori` e `/amm-software/profili-reparto` con pagine reali
- [ ] Sostituire icone `pi pi-wrench` con icone definitive per Amm. Software
- [ ] Verificare: inter-tab freshness funziona (modifica utente → lista si aggiorna)

### Sprint 3 — Domini operativi e dashboard

**Obiettivo**: popolare i domini con contenuto reale e attivare la dashboard home.

- [ ] Popolare `DOMAIN_MENUS` per i domini operativi (anagrafiche, vendite, ecc.)
- [ ] Creare route e pagine per ogni dominio (partendo da quelli con backend gia' pronto)
- [ ] Dashboard home: sostituire card placeholder con widget KPI reali
- [ ] Layout mobile: sidebar overlay + content tabs dropdown (sotto 768px)

---

### 12.1 Pagina Amm. Software — contenuto iniziale

Quando si clicca su "Amm. Software" dalla sidebar HOME (o su una delle 4 voci WIP), la pagina nel content area mostra un placeholder informativo:

```text
Content area — Amm. Software (stato WIP)
──────────────────────────────────────────────────────────────
  Amm. Software                                ← breadcrumb
──────────────────────────────────────────────────────────────

  ┌──────────────────────────────────────────┐
  │  🔧  Area in costruzione                  │
  │                                          │
  │  Le funzionalita' di amministrazione     │
  │  software sono in fase di sviluppo.      │
  │                                          │
  │  Prossimamente:                          │
  │  • Gestione operatori                    │
  │  • Profili reparto                       │
  │  • Configurazione permessi               │
  │  • Audit e sessioni                      │
  └──────────────────────────────────────────┘

```

Questo layout si può implementare come un semplice componente `PlaceholderView.vue` riutilizzabile per tutte le pagine non ancora sviluppate — riceve come prop il titolo e la lista delle funzionalità in arrivo.

---

## 13. Decisioni di progetto

| # | Decisione | Scelta | Motivazione |
| --- | --- | --- | --- |
| D1 | Sidebar: pattern di navigazione | Sidebar morfica a dominio (HOME/DOMINIO) | Scalabile, pulita, nessuna pagina intermedia |
| D2 | Sottomenu | Tab nella pagina (livello 3), mai nella sidebar | La sidebar non cresce in profondita; aggiunta tab = solo nel file pagina |
| D3 | Home card | 4 placeholder dashboard (non navigazione) | La navigazione vive nella sidebar; le card serviranno per KPI |
| D4 | Prima sidebar morfica | Amm. Software (4 voci WIP) | Dominio isolato, solo ADMIN, buon test del pattern morfico |
| D5 | Naming area admin | "Amministrazione Software" (label breve: "Amm. Software") | Distingue dall'amministrazione aziendale/contabile |
| D6 | Config menus | Estensione `navigation.js` con `DOMAIN_MENUS` | Unica fonte di verita per navigazione; lo store Pinia la consuma |
| D7 | Pagine non sviluppate | `PlaceholderView.vue` riutilizzabile | Evita pagine bianche; comunica cosa arrivera |
| D8 | Responsive sidebar morfica | Collassata = solo icone (come oggi), con tooltip | Coerente con comportamento esistente `stores/ui.js` |
| D9 | Tab multiple tipo browser | Content area con tab aperte, switch senza perdere stato | Operatori ERP lavorano su piu entita contemporaneamente |
| D10 | Pagina default per dominio | Preferita utente (localStorage) oppure prima voce menu | L'utente abituale va sempre alla stessa pagina; il nuovo ha un default sensato |
| D11 | Deep linking | URL diretto crea tab automaticamente; unicita' per route path | Bookmark e link condivisi funzionano senza configurazione |
| D12 | Inter-tab freshness | Event bus `useTabEvents` + refresh lazy al `tabActivated` | Evita query inutili in background; dati freschi quando serve |
| D13 | Contesto globale | Globale (non per-tab); le tab context-aware filtrano via `watch` | Il contesto e' "su chi lavoro", non "cosa ho aperto" |
| D14 | Indicatore contesto nelle tab | Dot colorato sulle tab che filtrano per contesto attivo | L'operatore sa che sta vedendo dati parziali |
| D15 | Pagine errore | 404/403 renderizzati come content tab chiudibile | Coerente con il modello tab; nessun fullscreen takeover |
| D16 | Layout mobile | Sidebar overlay + content tabs come dropdown sotto 768px | Usabilita' tablet/magazzino; incluso nello Sprint 1 |
| D17 | Keyboard shortcuts | Composable `useKeyboardShortcuts` in AppLayout | Power user ERP; disattivato quando input ha focus |
| D18 | Loading pattern | Skeleton per primo caricamento, ProgressBar per operazioni successive | Loading localizzato nella tab, mai bloccante l'intera UI |
| D19 | Dirty state tab | Composable `useDirtyState` + flag in store tabs + conferma chiusura | Previene perdita dati; indicatore visivo su tab con modifiche. ⚠️ Mai attivo: vedi §10.15 |
