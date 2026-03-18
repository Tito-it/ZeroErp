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

## Approccio proposto — Tecnica "Pannello Protect"

### Ispirazione AS/400

Sull'AS/400 per rendere read-only un formato video bastava emettere un formato "protect" sopra — nessuna duplicazione di logica, stessa schermata, solo l'interazione bloccata. In termini OOP: mettere tutto sopra un pannello e impostare il pannello come readonly.

### Equivalente CSS: `pointer-events: none`

In Vue/CSS il concetto e' identico: **non duplichiamo la view, renderizziamo lo stesso componente wrappato in un overlay che blocca ogni interazione**.

```css
.split-readonly-panel {
  pointer-events: none;     /* blocca OGNI click, hover, focus */
  user-select: text;        /* ma permetti copia testo (Ctrl+C) */
  opacity: 0.85;            /* feedback visivo "stai guardando" */
  filter: saturate(0.7);    /* leggermente desaturato */
}
```

**Una riga CSS** (`pointer-events: none`) e tutto il contenuto diventa read-only: bottoni, form, input, drawer, DataTable, tutto. Zero componenti Preview da creare, zero duplicazione.

### Perche' questo approccio

| Alternativa | Pro | Contro |
| --- | --- | --- |
| Componenti `*Preview.vue` per dominio | Puliti | Un componente per ogni dominio, manutenzione doppia |
| Doppio router-view | Nativo | Vue Router non supporta route diverse in parallelo |
| iframe | Isolamento | Duplica stato app, auth, store |
| **Stesso componente + CSS protect** | **Zero duplicazione, funziona su ogni dominio automaticamente** | **Serve component resolution dal router** |

### Come funziona

1. Il pannello secondario risolve il componente Vue dalla route della tab pinnata (`router.resolve()`)
2. Lo renderizza dentro un wrapper con classe `.split-readonly-panel`
3. Il CSS `pointer-events: none` blocca ogni interazione — come il formato protect AS/400
4. L'operatore puo' comunque **leggere tutto e copiare testo** (`user-select: text`)
5. Il componente e' vivo: se i dati cambiano nel primario, `useTabEvents` aggiorna anche il secondario

```
+------------------------------------------------------------------+
| AppTopbar                                                        |
+------------------------------------------------------------------+
| Tab1 [pin]  | Tab2 *attiva* | Tab3        | Tab4                 |
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

### Fase 2 — ContentTabs.vue: controlli split

Aggiungere per ogni tab un'**azione pin** visibile su hover (icona `pi pi-window-maximize`):

```
[Soggetti X] [Config [pin] X] [Fatture X]
                      ^-- hover su tab NON attiva: appare icona pin
```

**Interazione UX**:

- **Attivare split**: click sull'icona pin di una tab NON attiva -> pinnata a destra, attiva resta a sinistra
- **Disattivare split**: click su "X" nell'header del pannello secondario (o shortcut)
- **Tab pinnata**: indicatore visivo (icona pin fissa, bordo accent)

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

### Fase 4 — SplitReadonlyPanel.vue: il "formato protect"

Componente core — risolve il componente dalla route della tab pinnata e lo renderizza con CSS protect:

```vue
<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useTabsStore } from '@/stores/tabs'

const router = useRouter()
const tabs = useTabsStore()

const pinnedComponent = computed(() => {
  if (!tabs.pinnedTab) return null
  const resolved = router.resolve(tabs.pinnedTab.path)
  const match = resolved.matched[resolved.matched.length - 1]
  return match?.components?.default || null
})
</script>

<template>
  <div class="app-content-panel secondary">
    <!-- Header con label e chiudi -->
    <div class="split-panel-header">
      <i :class="tabs.pinnedTab?.icon" />
      <span>{{ tabs.pinnedTab?.label }}</span>
      <span class="split-readonly-badge">Sola lettura</span>
      <button @click="tabs.swapPanels()">
        <i class="pi pi-arrows-h" />
      </button>
      <button @click="tabs.closeSplit()">
        <i class="pi pi-times" />
      </button>
    </div>

    <!-- IL FORMATO PROTECT: stessa view, interazione bloccata -->
    <!-- Eccezione: i bottoni .split-escape restano cliccabili (come F12/F3 su AS/400) -->
    <div class="split-readonly-panel">
      <component :is="pinnedComponent" :key="tabs.pinnedTab?.path" />
    </div>
  </div>
</template>

<style scoped>
.split-readonly-panel {
  pointer-events: none;      /* protect globale */
  user-select: text;         /* permetti copia testo */
  opacity: 0.85;
  filter: saturate(0.7);
  flex: 1;
  overflow-y: auto;
  border-left: 2px solid var(--app-border-color);
}

/* "F12/F3" — elementi che restano attivi dentro il pannello protect */
.split-readonly-panel :deep(.tab-close),         /* X chiudi tab */
.split-readonly-panel :deep(.p-dialog-close),     /* X chiudi dialog */
.split-readonly-panel :deep(.p-drawer-close),     /* X chiudi drawer */
.split-readonly-panel :deep(.split-escape) {      /* classe generica escape */
  pointer-events: auto;
  cursor: pointer;
}

.split-readonly-badge {
  font-size: 0.7rem;
  background: var(--app-warning-light);
  color: var(--app-warning-dark);
  padding: 2px 8px;
  border-radius: 4px;
}

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
| 2. ContentTabs UI | Bassa | Icona pin su hover |
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

## Decisioni aperte

1. **Resize handle subito o v2?** Consiglio v2 — prima validare che lo split base funzioni.
2. **Drag and drop tab per pinnare?** UX bella ma complessa — v2.
3. **Pannello interattivo in futuro?** Se il read-only protect si dimostra utile e gli operatori chiedono di piu', si puo' rimuovere il `pointer-events: none` e affrontare i problemi di useRoute/dirty state. Ma il protect copre il 90% dei casi d'uso (consultazione/confronto).
