# Split View — Tab Affiancate

> **Stato**: Pianificazione
> **Priorita'**: Bassa (feature futura)
> **Prerequisiti**: Nessun blocco tecnico

## Obiettivo

Permettere all'operatore di affiancare due tab aperte in una vista 50/50 (split view), per confrontare dati o copiare informazioni tra schede. Il **pannello secondario e' read-only** (solo visualizzazione): l'operatore lavora nel pannello primario e usa il secondario come riferimento.

## Analisi dello stato attuale

### Architettura tab corrente

| Componente | Ruolo |
| --- | --- |
| `AppLayout.vue` | Layout flex: sidebar + main (column: topbar, tabs-bar, content) |
| `ContentTabs.vue` | Barra tab orizzontale, un solo tab attivo alla volta |
| `useTabsStore` (Pinia) | Array tab, activeTabId, dirty, persistenza sessionStorage |
| `router-view` + `KeepAlive` | Renderizza UN solo componente, cachati fino a 10 |
| Router guard | Apre/attiva tab su navigazione |

### Vincolo principale

`<router-view>` di Vue Router renderizza **un solo componente** basato sulla route corrente. `KeepAlive` li tiene in memoria ma ne mostra solo uno. Per lo split view servono **due componenti visibili simultaneamente**.

## Approccio proposto — Sola lettura via provide/inject

### Ispirazione AS/400

Sull'AS/400 per rendere read-only un formato video bastava emettere un formato "protect" sopra — nessuna duplicazione di logica, stessa schermata, solo l'interazione bloccata.

### ~~Scartato: `pointer-events: none` su tutta la pagina~~

Il primo approccio era un CSS `pointer-events: none` globale sul pannello. **Scartato** perche' blocca l'intera pagina: paginazione, sort colonne, scroll DataTable, click su righe — non solo la scrittura. L'app ha gia' un meccanismo di sola lettura per operatori (livello LETTURA) che lascia la pagina navigabile.

### Approccio scelto: `provide(READONLY_KEY, true)` nel pannello split

Il `SplitReadonlyPanel` fa `provide(READONLY_KEY, ref(true))` — lo stesso meccanismo che `useReadonlyMode` usa per gli operatori con livello LETTURA. La pagina nel pannello secondario e' **completamente navigabile** (paginazione, sort, scroll, click riga per aprire dettaglio in drawer), ma le **azioni di scrittura sono bloccate**:

- `NewButton` si nasconde automaticamente (`useInjectReadonly()`)
- `DrawerFooter` si nasconde automaticamente (no Save/Cancel)
- I drawer form applicano `.app-readonly` (input non interattivi)

**Modifica chiave a `useReadonlyMode`**: aggiunto `inject` del parent READONLY_KEY con OR logico — se un parent (SplitReadonlyPanel) ha gia' fornito `readonly=true`, il valore si propaga anche se i permessi dell'operatore consentirebbero la scrittura.

```javascript
// useReadonlyMode.js — prima:
const isReadonly = computed(() => auth.isAreaReadonly(areaSchemaDb))

// useReadonlyMode.js — dopo:
const parentReadonly = inject(READONLY_KEY, ref(false))
const isReadonly = computed(() => parentReadonly.value || auth.isAreaReadonly(areaSchemaDb))
```

### Perche' questo approccio

| Alternativa | Pro | Contro |
| --- | --- | --- |
| Componenti `*Preview.vue` per dominio | Puliti | Un componente per ogni dominio, manutenzione doppia |
| Doppio router-view | Nativo | Vue Router non supporta route diverse in parallelo |
| iframe | Isolamento | Duplica stato app, auth, store |
| `pointer-events: none` globale | Zero config | Blocca TUTTA l'interazione (anche paginazione, scroll) |
| **provide/inject readonly (scelto)** | **Navigabile, zero duplicazione, funziona su ogni dominio** | **Serve component resolution dal router** |

### Come funziona

1. Il pannello secondario risolve il componente Vue dalla route della tab pinnata (`router.resolve()`)
2. Lo renderizza dentro un wrapper con classe `.split-readonly-panel`
3. Il CSS `pointer-events: none` blocca ogni interazione — come il formato protect AS/400
4. L'operatore puo' comunque **leggere tutto e copiare testo** (`user-select: text`)
5. Il componente e' vivo: se i dati cambiano nel primario, `useTabEvents` aggiorna anche il secondario

```text
+------------------------------------------------------------------+
| AppTopbar                                                        |
+------------------------------------------------------------------+
| Tab1 | Tab2 *attiva* | Tab3 | Tab4  ·············  [⫏ Affianca] |
+------------------------------------------------------------------+
|                          |  [sola lettura]                       |
|   Pannello Primario      |   Pannello Secondario (pinnato)       |
|   (router-view)          |   (stesso componente, CSS protect)    |
|   Tab2 - interattivo     |   Tab1 - read-only overlay            |
|                          |                                       |
+------------------------------------------------------------------+
```

## Piano di implementazione

### Fase 1 — Store: stato split view

**File**: `stores/tabs.js` (estensione)

Nuovi campi stato:

```javascript
const splitMode = ref(false)       // split attivo/disattivo
const pinnedTabId = ref(null)      // ID della tab pinnata nel pannello secondario
```

Nuovi metodi:

```javascript
pinTab(tabId)       // splitMode=true, pinnedTabId=tabId, attiva altra tab nel primario
closeSplit()        // splitMode=false, pinnedTabId=null
swapPanels()        // scambia activeTabId <-> pinnedTabId + router.push

// Computed
pinnedTab            // computed: tab object della tab pinnata
isSplit              // computed: splitMode === true
```

Persistenza: estendere `persistTabs()` / `restoreTabs()` per salvare `splitMode` + `pinnedTabPath`.

### Fase 2 — ContentTabs.vue: bottone "Affianca" e controlli split

#### Scelta UX: bottone sulla barra tab (non hover su singola tab)

L'approccio iniziale prevedeva un'icona pin su hover di ogni tab non attiva. Scartato perche':

- Hover-dipendente: non funziona su touch/tablet
- Target piccolo, poco discoverable
- L'operatore deve sapere *prima* che la funzione esiste

**Approccio scelto**: bottone "Affianca" posizionato a **destra della barra ContentTabs**, allineato alla fine della riga tab. L'azione e' nel contesto giusto (barra tab = gestione tab) ed e' sempre visibile.

```text
[Soggetti X] [Config X] [Fatture X]  ···················  [⫏ Affianca]
                                                            ^-- visibile solo su desktop >= 1280px
```

#### Flusso interazione

1. **Attivare split**: click su "Affianca" → si apre un **Popover PrimeVue** con la lista delle tab aperte (esclusa quella attiva). Ogni voce mostra icona + label della tab.
2. **Selezionare tab**: click su una voce del popover → `tabs.pinTab(tabId)` → split attivato, tab selezionata nel pannello secondario read-only.
3. **Stato split attivo**: il bottone "Affianca" diventa **"Chiudi split"** (icona `pi pi-times` o `pi pi-window-minimize`), colore accent per feedback visivo. Il pannello secondario ha anche il suo header con X per chiudere.
4. **Disattivare split**: click su "Chiudi split" nella barra tab OPPURE click su "X" nell'header del pannello secondario OPPURE shortcut.
5. **Tab pinnata**: nella barra tab la tab pinnata mostra un indicatore visivo (icona pin `pi pi-thumbtack`, bordo accent) per distinguerla dalle altre.

#### Visibilita' responsive

Il bottone "Affianca" si mostra **solo su desktop >= 1280px** tramite CSS media query. Su tablet e mobile non appare — lo split non ha senso su schermi piccoli. Se lo split e' attivo e la finestra scende sotto 1280px, `closeSplit()` automatico (watcher su viewport).

#### Requisito minimo

Il popover si mostra solo se ci sono **almeno 2 tab aperte** (serve una tab da affiancare). Con una sola tab il bottone e' disabilitato o nascosto.

### Fase 3 — AppLayout.vue: layout split

Modificare `.app-content` per supportare grid a 2 colonne quando split e' attivo:

```vue
<main class="app-content" :class="{ 'split-active': tabs.isSplit }">
  <!-- Pannello primario (sempre presente) -->
  <div class="app-content-panel primary">
    <AppBreadcrumb />
    <router-view v-slot="{ Component }">
      <KeepAlive :max="10">
        <component :is="Component" :key="$route.path" />
      </KeepAlive>
    </router-view>
  </div>

  <!-- Pannello secondario read-only (solo se split attivo) -->
  <SplitReadonlyPanel v-if="tabs.isSplit" />
</main>
```

**CSS**:

```css
.app-content.split-active {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
}

.app-content-panel {
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  min-width: 0;
}

/* Responsive: solo desktop largo */
@media (max-width: 1280px) {
  .app-content.split-active {
    grid-template-columns: 1fr;
  }
}
```

### Fase 4 — SplitReadonlyPanel.vue: sola lettura via provide/inject

Componente core — risolve il componente dalla route della tab pinnata, fornisce `READONLY_KEY = true` via provide/inject. La pagina resta navigabile, le azioni di scrittura sono bloccate dai componenti stessi (NewButton, DrawerFooter, drawer form).

```vue
<script setup>
import { computed, ref, provide } from 'vue'
import { useRouter } from 'vue-router'
import { useTabsStore } from '@/stores/tabs'
import { READONLY_KEY, BLOCKED_KEY } from '../composables/useReadonlyMode'

const router = useRouter()
const tabs = useTabsStore()

// Forza readonly su tutti i componenti figli (come livello LETTURA per operatori)
provide(READONLY_KEY, ref(true))
provide(BLOCKED_KEY, ref(false))

const pinnedComponent = computed(() => {
  if (!tabs.pinnedTab) return null
  const resolved = router.resolve(tabs.pinnedTab.path)
  const match = resolved.matched[resolved.matched.length - 1]
  return match?.components?.default || null
})
</script>

<template>
  <div class="split-secondary-panel">
    <div class="split-panel-header">
      <i :class="tabs.pinnedTab?.icon" />
      <span>{{ tabs.pinnedTab?.label }}</span>
      <span class="split-readonly-badge">Sola lettura</span>
      <button @click="tabs.swapPanels()"><i class="pi pi-arrows-h" /></button>
      <button @click="tabs.closeSplit()"><i class="pi pi-times" /></button>
    </div>
    <!-- Pagina navigabile: paginazione, sort, scroll, click riga OK -->
    <!-- Scrittura bloccata: NewButton nascosto, DrawerFooter nascosto, form readonly -->
    <div class="split-panel-content">
      <component :is="pinnedComponent" :key="tabs.pinnedTab?.path" />
    </div>
  </div>
</template>
```

**Modifica necessaria a `useReadonlyMode`**: il composable deve rispettare il readonly del parent con OR logico, altrimenti la View nel pannello split sovrascrive il provide con il proprio valore (basato sui permessi operatore).

```javascript
// useReadonlyMode.js
const parentReadonly = inject(READONLY_KEY, ref(false))
const isReadonly = computed(() => parentReadonly.value || auth.isAreaReadonly(areaSchemaDb))

.split-panel-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0.75rem;
  border-bottom: 1px solid var(--app-border-color);
  border-left: 2px solid var(--app-border-color);
}

.split-panel-header button {
  pointer-events: auto;  /* i bottoni header restano cliccabili! */
}
</style>
```

**Nota chiave**: l'header (swap, chiudi) ha `pointer-events: auto` — resta interattivo sopra il pannello protect. Solo il contenuto della view e' bloccato.

### Fase 5 — Keyboard shortcuts

| Shortcut | Azione |
| --- | --- |
| `Ctrl+Shift+S` | Toggle split: pinna tab attiva, attiva la successiva nel primario |
| `Ctrl+Shift+Arrow` | Swap pannelli |
| `Ctrl+Shift+W` | Chiudi split |

Registrare in `AppLayout.vue` (dove ci sono gia' Ctrl+Tab, Ctrl+W, ecc.)

### Fase 6 — Resize handle (v2, opzionale)

Divider draggabile tra i due pannelli per regolare proporzione (60/40, 70/30). Preferenza salvata in localStorage.

## Gestione casi limite

### Tasti di uscita nel pannello protect (F12/F3 dell'AS/400)

Il `pointer-events: none` blocca tutto, ma alcuni elementi **devono restare attivi** — come F12 (indietro) e F3 (uscita) nei formati protect AS/400. In CSS si ottiene con `pointer-events: auto` sui selettori specifici:

- **X di chiusura drawer/dialog** (`.p-drawer-close`, `.p-dialog-close`) — l'operatore deve poter chiudere un drawer aperto nel pannello protect
- **X di chiusura tab** (`.tab-close`) — se la tab nel pannello protect ha un drawer aperto, deve poterlo chiudere
- **Classe generica `.split-escape`** — da aggiungere a qualsiasi elemento che deve restare cliccabile

Regola: nel pannello protect **si puo' solo chiudere/uscire**, mai aprire/creare/modificare.

### Chiusura tab pinnata

Se l'utente chiude una tab che e' pinnata nello split -> `closeSplit()` automatico nel metodo `removeTab()`.

### Responsive

Split view disponibile SOLO su desktop >= 1280px. Watcher su `ui.layoutMode`: se scende sotto soglia -> `closeSplit()` automatico.

### useRoute() nel pannello secondario

Il componente nel pannello 2 non ha una route attiva nel router. `useRoute()` ritornera' la route del primario. Per la maggior parte delle view questo non e' un problema perche':

- Le SearchTable caricano dati via API, non da route params
- I drawer si aprono su eventi, non su route

Se una view specifica dipende da route params (es. `/soggetti/:id`), si puo' passare il path come provide/inject. Ma nella v1 lo split funziona gia' bene con le view lista.

### KeepAlive

Il componente pinnato nel pannello 2 e' una **nuova istanza** (non la stessa del KeepAlive primario) perche' viene renderizzato da `<component :is>` diretto, fuori dal `<KeepAlive>` del router-view. Non c'e' conflitto.

### Aggiornamento dati

Se l'operatore modifica un soggetto nel pannello primario, il pannello secondario (es. lista soggetti) si aggiorna via `useTabFreshness` + `useTabEvents.onDataChanged()` — pattern gia' esistente.

## Stima effort

| Fase | Complessita' | Note |
| --- | --- | --- |
| 1. Store split | Bassa | 3-4 metodi, persistenza |
| 2. ContentTabs UI | Bassa | Bottone "Affianca" + Popover selettore tab |
| 3. AppLayout grid | Bassa | CSS grid condizionale |
| 4. SplitReadonlyPanel | **Bassa** | Un componente, CSS protect |
| 5. Shortcuts | Bassa | Pattern gia' in uso |
| 6. Resize handle | Media | v2 |

**Complessita' complessiva: BASSA.** Nessun componente da duplicare per dominio. Il "formato protect" CSS funziona su qualsiasi view presente e futura senza modifiche.

## Confronto approcci

| Aspetto | Preview per dominio | CSS Protect (scelto) |
| --- | --- | --- |
| Componenti da creare | 1 per ogni dominio | 1 solo (`SplitReadonlyPanel`) |
| Manutenzione | Ogni nuova view richiede un Preview | Zero — funziona automaticamente |
| Fedelta' visiva | Approssimata (DataTable semplificata) | Identica alla view originale |
| Interazione | Nessuna | Nessuna (pointer-events: none) |
| Copia testo | Da implementare | Gratis (user-select: text) |
| Effort totale | Medio (cresce con i domini) | Basso (fisso) |

## Decisioni prese

1. **UX attivazione split**: bottone "Affianca" sulla barra ContentTabs (destra) + Popover con lista tab. Scartato: icona pin su hover singola tab (hover-dipendente, poco discoverable).
2. **Responsive**: split view solo desktop >= 1280px. Tablet e mobile esclusi.

## Decisioni aperte

1. **Resize handle subito o v2?** Consiglio v2 — prima validare che lo split base funzioni.
2. **Drag and drop tab per pinnare?** UX bella ma complessa — v2.
3. **Pannello interattivo in futuro?** Se il read-only protect si dimostra utile e gli operatori chiedono di piu', si puo' rimuovere il `pointer-events: none` e affrontare i problemi di useRoute/dirty state. Ma il protect copre il 90% dei casi d'uso (consultazione/confronto).
