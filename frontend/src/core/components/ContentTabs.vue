<script setup>
// Scopo: barra content tabs tipo browser — ogni pagina aperta diventa una tab.
// Le tab si restringono in proporzione quando non entrano (icona e chiusura
// fisse, cede solo il titolo); i controlli della barra stanno fuori dalla
// striscia che scorre, cosi' non escono mai dallo schermo.
// Su mobile la barra diventa un dropdown Select.
// Include bottone "Affianca" per split view read-only (solo desktop >= 1280px).
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Select from 'primevue/select'
import Popover from 'primevue/popover'
import { useTabsStore } from '../../stores/tabs'
import { useContextStore } from '../../stores/context'
import { useUiStore } from '../../stores/ui'
import { useConfirmAction } from '../composables/useConfirmAction'
import { useConfirmCloseTab } from '../composables/useConfirmCloseTab'
import { BREAKPOINTS, MANAGE_ICONS, TABS } from '../constants'
import { resolveTabDisplayLabel } from '../navigation'

const { t, te } = useI18n()
const router = useRouter()
const tabs = useTabsStore()
const context = useContextStore()
const ui = useUiStore()
const { closeTab } = useConfirmCloseTab()
const { confirmAction } = useConfirmAction()

// ⭐ La conferma della sostituzione oltre il limite (la chiede il guard del
//    router, vedi `stores/tabs`). La dialog NOMINA la scheda: «l'ultima» fa
//    cercare quale sia. ⚠️ Con modifiche non salvate e' rossa e lo dice,
//    come la X di chiusura (`useConfirmCloseTab`): sostituire e' chiudere.
watch(() => tabs.richiestaSostituzione, (richiesta) => {
  if (!richiesta) return
  const nome = tabLabel(richiesta.tab)
  const sporca = richiesta.tab.dirty === true
  confirmAction({
    header: t('tabs.sostituisci.titolo'),
    message: sporca
      ? t('tabs.sostituisci.messaggio_modifiche', { nome })
      : t('tabs.sostituisci.messaggio', { nome }),
    danger: sporca,
    acceptLabel: t('tabs.sostituisci.conferma'),
    acceptIcon: MANAGE_ICONS.CONFIRM,
    onAccept: () => richiesta.rispondi(true),
    onReject: () => richiesta.rispondi(false),
  })
})

// Schede rimanenti — visibile quando <= 5
const remainingTabs = computed(() => TABS.MAX_OPEN - tabs.tabs.length)
const remainingClass = computed(() => {
  const r = remainingTabs.value
  if (r <= 1) return 'remaining-red'
  if (r <= 3) return 'remaining-orange'
  return 'remaining-green'
})

const splitPopover = ref(null)

function tabLabel(tab) {
  return resolveTabDisplayLabel(tab, t, te)
}

const mobileTabOptions = computed(() =>
  tabs.tabs.map(tab => ({
    id: tab.id,
    label: tabLabel(tab),
  })),
)

// Split view disponibile solo su desktop largo con almeno 2 tab
const canSplit = computed(() =>
  ui.windowWidth >= BREAKPOINTS.DESKTOP_SPLIT && tabs.splittableTabs.length > 0
)

function handleTabClick(tab) {
  // Se si clicca la tab pinnata, fare swap (evita activeTabId === pinnedTabId)
  if (tabs.isSplit && tabs.pinnedTab?.id === tab.id) {
    tabs.swapPanels()
    router.push(tab.path)
    return
  }
  tabs.activateTab(tab.id)
  router.push(tab.path)
}

function handleCloseTab(tab, event) {
  event.stopPropagation()
  closeTab(tab)
}

function handleDropdownChange(tabId) {
  const tab = tabs.tabs.find(t => t.id === tabId)
  if (tab) {
    tabs.activateTab(tab.id)
    router.push(tab.path)
  }
}

function toggleSplitPopover(event) {
  if (tabs.isSplit) {
    tabs.closeSplit()
  } else {
    splitPopover.value?.toggle(event)
  }
}

function handlePinTab(tab) {
  tabs.pinTab(tab.id)
  splitPopover.value?.hide()
  // Navigazione alla tab attiva nel primario (potrebbe essere cambiata se si pinnava l'attiva)
  if (tabs.activeTab) router.push(tabs.activeTab.path)
}
</script>

<template>
  <div v-if="tabs.tabs.length > 0" class="content-tabs">
    <!-- Desktop/Tablet: barra a due zone. La striscia delle tab e' l'unica
         parte che puo' scorrere; i controlli della barra (contatore, Affianca)
         stanno fuori da essa, cosi' restano a video qualunque sia il numero
         di tab aperte. -->
    <div v-if="ui.layoutMode !== 'mobile'" class="content-tabs-bar">
      <div class="content-tabs-strip">
        <div
          v-for="tab in tabs.tabs"
          :key="tab.id"
          class="content-tab"
          :class="{
            active: tabs.activeTabId === tab.id,
            pinned: tabs.isSplit && tabs.pinnedTab?.id === tab.id
          }"
          @click="handleTabClick(tab)"
        >
          <i v-if="tab.icon" :class="tab.icon" class="tab-icon"></i>
          <!-- Indicatore tab pinnata -->
          <i v-if="tabs.isSplit && tabs.pinnedTab?.id === tab.id" class="tab-pin-icon" :class="MANAGE_ICONS.TAB_FISSATA"></i>
          <!-- Il titolo e' l'unica parte della tab che si restringe: quando e'
               troncato il nome intero sta nel tooltip. Il delay evita che il
               tooltip compaia a ogni passaggio per cliccare una tab. -->
          <span
            class="tab-label"
            v-tooltip.top="{ value: tabLabel(tab), showDelay: 600 }"
          >{{ tabLabel(tab) }}</span>
          <!-- Indicatore dirty -->
          <span v-if="tab.dirty" class="tab-dirty-dot" v-tooltip.top="t('common.modifiche_non_salvate.indicatore')"></span>
          <!-- Indicatore contesto attivo -->
          <span
            v-else-if="tab.contextAware && context.hasContext"
            class="tab-context-dot"
            v-tooltip.top="t('context.filtered_by', { name: context.contextLabel })"
          ></span>
          <!-- Pulsante chiusura -->
          <i
            class="tab-close"
            :class="MANAGE_ICONS.CANCEL"
            @click="handleCloseTab(tab, $event)"
            v-tooltip.top="t('tabs.close')"
          ></i>
        </div>
      </div>

      <div class="content-tabs-controls">
        <!-- Contatore schede rimanenti -->
        <span
          v-if="remainingTabs <= 5"
          class="tab-remaining"
          :class="remainingClass"
          v-tooltip.top="t('tabs.remaining', { count: remainingTabs })"
        >{{ remainingTabs }}</span>

        <!-- Bottone Affianca / Chiudi split — icona verde coerente con app-action-btn -->
        <button
          v-if="canSplit"
          class="split-toggle-btn"
          :class="{ 'split-active': tabs.isSplit }"
          @click="toggleSplitPopover"
          v-tooltip.top="tabs.isSplit ? t('tabs.split_close') : t('tabs.split_open')"
        >
          <i :class="tabs.isSplit ? MANAGE_ICONS.CANCEL : MANAGE_ICONS.AFFIANCA"></i>
        </button>

        <!-- Popover con lista tab da affiancare -->
        <Popover ref="splitPopover" class="split-popover">
          <div class="split-popover-header">{{ t('tabs.split_select') }}</div>
          <div class="split-popover-list">
            <div
              v-for="tab in tabs.splittableTabs"
              :key="tab.id"
              class="split-popover-item"
              @click="handlePinTab(tab)"
            >
              <i v-if="tab.icon" :class="tab.icon" class="split-popover-icon"></i>
              <span>{{ tabLabel(tab) }}</span>
            </div>
          </div>
        </Popover>
      </div>
    </div>

    <!-- Mobile: dropdown -->
    <div v-else class="content-tabs-mobile">
      <Select
        :modelValue="tabs.activeTabId"
        :options="mobileTabOptions"
        optionLabel="label"
        optionValue="id"
        class="content-tabs-dropdown"
        @update:modelValue="handleDropdownChange"
      />
    </div>
  </div>
</template>

<style scoped>
.content-tabs {
  background: var(--app-toolbar-bg);
  border-bottom: 1px solid var(--app-toolbar-border);
  min-height: var(--app-toolbar-height);
}

.content-tabs-bar {
  display: flex;
  align-items: stretch;
  padding: 0 0.5rem;
}

/* Striscia delle tab: l'unica zona che scorre, e solo come rete di sicurezza
   (quando N tab al pavimento non entrano). `min-width: 0` e' obbligatorio:
   senza, un flex item con figli nowrap non si restringe sotto il contenuto e
   la striscia spingerebbe fuori i controlli. */
.content-tabs-strip {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  align-items: stretch;
  gap: 1px;
  overflow-x: auto;
  scrollbar-width: thin;
}

/* Controlli della barra (contatore, Affianca): fuori dalla striscia, quindi
   sempre a video qualunque sia il numero di tab aperte. */
.content-tabs-controls {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  margin-left: 0.5rem;
}

/* Le tab si restringono in proporzione alla loro larghezza naturale
   (flex-basis auto): un titolo lungo cede piu' di uno corto. Il pavimento e'
   un valore esplicito e non `auto`: per un flex item `min-width: auto` vale
   il min-content, che include il titolo intero — la tab non si stringerebbe
   mai. 5.5rem = parti fisse (~3.75rem: padding, icona, gap, chiusura) piu'
   ~4 caratteri di titolo; sotto, la striscia scorre. `overflow: hidden`
   garantisce che, in caso di pin + pallino insieme, niente sbordi sulla tab
   accanto. */
.content-tab {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex: 0 1 auto;
  min-width: 5.5rem;
  overflow: hidden;
  padding: 0.45rem 0.6rem;
  font-size: var(--app-font-size-sm);
  color: var(--app-topbar-breadcrumb-color);
  cursor: pointer;
  white-space: nowrap;
  border-bottom: 2px solid transparent;
  transition: background var(--app-transition-fast), color var(--app-transition-fast), border-color var(--app-transition-fast);
}

/* Icona, pin, pallini e chiusura non si restringono mai: e' il titolo l'unica
   parte che cede. */
.tab-icon,
.tab-pin-icon,
.tab-dirty-dot,
.tab-context-dot,
.tab-close {
  flex-shrink: 0;
}

.content-tab:hover {
  background: var(--app-toolbar-tab-hover-bg);
  color: var(--app-topbar-breadcrumb-active-color);
}

.content-tab.active {
  color: var(--app-topbar-breadcrumb-active-color);
  border-bottom-color: var(--app-accent-color);
}

.tab-icon {
  font-size: 0.8rem;
  color: var(--app-icon-color);
}

.content-tab.active .tab-icon {
  color: inherit;
}

/* Separatore verticale verde tra tab */
.content-tab + .content-tab {
  border-left: 1px solid color-mix(in srgb, var(--app-accent-color) 35%, transparent);
}

/* Il titolo: tetto a 150px come prima, e `min-width: 0` perche' possa cedere
   fino al pavimento della tab (con ellissi). */
.tab-label {
  flex: 0 1 auto;
  min-width: 0;
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tab-dirty-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--app-warning-color);
}

.tab-context-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--p-blue-400);
}

.tab-close {
  font-size: 0.65rem;
  padding: 0.15rem;
  border-radius: 3px;
  opacity: 0;
  transition: opacity var(--app-transition-fast), background var(--app-transition-fast);
}

.content-tab:hover .tab-close {
  opacity: 0.6;
}

.tab-close:hover {
  opacity: 1 !important;
  background: var(--app-sidebar-item-hover-bg);
}

/* Tab pinnata nello split */
.content-tab.pinned {
  border-bottom-color: var(--app-split-color);
}

.tab-pin-icon {
  font-size: 0.6rem;
  color: var(--app-split-color);
}

/* Contatore schede rimanenti */
.tab-remaining {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 1.3rem;
  height: 1.3rem;
  margin: auto 0.3rem;
  padding: 0 0.3rem;
  font-size: 0.7rem;
  font-weight: 700;
  border-radius: 4px;
  line-height: 1;
}

.tab-remaining.remaining-green {
  color: var(--p-green-400);
  background: color-mix(in srgb, var(--p-green-400) 15%, transparent);
}

.tab-remaining.remaining-orange {
  color: #fff;
  background: var(--app-warning-color);
}

.tab-remaining.remaining-red {
  color: #fff;
  background: var(--app-severity-danger);
}

/* Bottone Affianca / Chiudi split — icona verde, sfondo neutro (come app-action-btn) */
.split-toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.85rem;
  height: 1.85rem;
  margin: auto 0.4rem;
  font-size: 0.95rem;
  color: var(--app-accent-color);
  background: transparent;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: color var(--app-transition-fast), background var(--app-transition-fast);
}

.split-toggle-btn:hover {
  color: var(--p-primary-700);
  background: var(--p-primary-50);
}

.split-toggle-btn.split-active {
  color: var(--p-red-500);
}

.split-toggle-btn.split-active:hover {
  color: var(--p-red-600);
  background: var(--p-red-50);
}

/* Popover selettore tab per split */
:deep(.split-popover) {
  min-width: 200px;
  max-width: 320px;
}

.split-popover-header {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--app-topbar-breadcrumb-color);
  padding: 0.4rem 0.6rem;
  border-bottom: 1px solid var(--app-toolbar-border);
}

.split-popover-list {
  padding: 0.25rem 0;
}

.split-popover-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.45rem 0.6rem;
  font-size: var(--app-font-size-sm);
  cursor: pointer;
  transition: background var(--app-transition-fast);
}

.split-popover-item:hover {
  background: var(--app-toolbar-tab-hover-bg);
}

.split-popover-icon {
  font-size: 0.8rem;
  color: var(--app-icon-color);
}

/* Mobile dropdown */
.content-tabs-mobile {
  padding: 0.4rem 0.75rem;
}

.content-tabs-dropdown {
  width: 100%;
}
</style>
