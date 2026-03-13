<script setup>
// Scopo: barra content tabs tipo browser — ogni pagina aperta diventa una tab.
// Su mobile la barra diventa un dropdown Select.
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Select from 'primevue/select'
import { useTabsStore } from '../../stores/tabs'
import { useContextStore } from '../../stores/context'
import { useUiStore } from '../../stores/ui'
import { useConfirmCloseTab } from '../composables/useConfirmCloseTab'

const { t } = useI18n()
const router = useRouter()
const tabs = useTabsStore()
const context = useContextStore()
const ui = useUiStore()
const { closeTab } = useConfirmCloseTab()

function handleTabClick(tab) {
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
</script>

<template>
  <div v-if="tabs.tabs.length > 0" class="content-tabs">
    <!-- Desktop/Tablet: barra tab orizzontale -->
    <div v-if="ui.layoutMode !== 'mobile'" class="content-tabs-bar">
      <div
        v-for="tab in tabs.tabs"
        :key="tab.id"
        class="content-tab"
        :class="{ active: tabs.activeTabId === tab.id }"
        @click="handleTabClick(tab)"
      >
        <i v-if="tab.icon" :class="tab.icon" class="tab-icon"></i>
        <span class="tab-label">{{ tab.label }}</span>
        <!-- Indicatore dirty -->
        <span v-if="tab.dirty" class="tab-dirty-dot" v-tooltip.top="t('tabs.close_confirm_title')"></span>
        <!-- Indicatore contesto attivo -->
        <span
          v-else-if="tab.contextAware && context.hasContext"
          class="tab-context-dot"
          v-tooltip.top="t('context.filtered_by', { name: context.contextLabel })"
        ></span>
        <!-- Pulsante chiusura -->
        <i
          class="pi pi-times tab-close"
          @click="handleCloseTab(tab, $event)"
          v-tooltip.top="t('tabs.close')"
        ></i>
      </div>
    </div>

    <!-- Mobile: dropdown -->
    <div v-else class="content-tabs-mobile">
      <Select
        :modelValue="tabs.activeTabId"
        :options="tabs.tabs"
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
  gap: 1px;
  padding: 0 0.5rem;
  overflow-x: auto;
  scrollbar-width: thin;
}

.content-tab {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.45rem 0.6rem;
  font-size: var(--app-font-size-sm);
  color: var(--app-topbar-breadcrumb-color);
  cursor: pointer;
  white-space: nowrap;
  border-bottom: 2px solid transparent;
  transition: background var(--app-transition-fast), color var(--app-transition-fast), border-color var(--app-transition-fast);
}

.content-tab:hover {
  background: var(--app-toolbar-tab-hover-bg);
  color: var(--app-topbar-breadcrumb-active-color);
}

.content-tab.active {
  color: var(--app-topbar-breadcrumb-active-color);
  border-bottom-color: var(--p-primary-color);
}

.tab-icon {
  font-size: 0.8rem;
}

.tab-label {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tab-dirty-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--p-orange-400);
  flex-shrink: 0;
}

.tab-context-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--p-blue-400);
  flex-shrink: 0;
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

/* Mobile dropdown */
.content-tabs-mobile {
  padding: 0.4rem 0.75rem;
}

.content-tabs-dropdown {
  width: 100%;
}
</style>
