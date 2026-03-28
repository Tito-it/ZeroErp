<script setup>
// Scopo: pannello secondario read-only per split view — risolve il componente Vue
// dalla route della tab pinnata e lo renderizza in modalita' sola lettura.
// Usa lo stesso meccanismo provide/inject di useReadonlyMode: NewButton si nasconde,
// DrawerFooter si nasconde, drawer form diventano readonly — ma la pagina resta
// navigabile (paginazione, sort, scroll, click riga per dettaglio).
import { computed, ref, provide } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useTabsStore } from '../../stores/tabs'
import { READONLY_KEY, BLOCKED_KEY } from '../composables/useReadonlyMode'

const { t } = useI18n()
const router = useRouter()
const tabs = useTabsStore()

// Forza readonly su tutti i componenti figli via provide/inject
// (stesso meccanismo di useReadonlyMode per operatori con livello LETTURA)
provide(READONLY_KEY, ref(true))
provide(BLOCKED_KEY, ref(false))

// Risolve il componente Vue associato alla route della tab pinnata
const pinnedComponent = computed(() => {
  if (!tabs.pinnedTab) return null
  const resolved = router.resolve(tabs.pinnedTab.path)
  if (!resolved.matched.length) return null
  const match = resolved.matched[resolved.matched.length - 1]
  return match?.components?.default || null
})

function handleSwap() {
  tabs.swapPanels()
  if (tabs.activeTab) router.push(tabs.activeTab.path)
}
</script>

<template>
  <div v-if="pinnedComponent" class="split-secondary-panel">
    <!-- Header pannello secondario -->
    <div class="split-panel-header">
      <i v-if="tabs.pinnedTab?.icon" :class="tabs.pinnedTab.icon" class="split-panel-icon"></i>
      <span class="split-panel-label">{{ tabs.pinnedTab?.label }}</span>
      <span class="split-readonly-badge">{{ t('tabs.split_readonly') }}</span>
      <div class="split-panel-actions">
        <button
          class="split-panel-btn"
          @click="handleSwap"
          v-tooltip.top="t('tabs.split_swap')"
        >
          <i class="pi pi-arrows-h"></i>
        </button>
        <button
          class="split-panel-btn"
          @click="tabs.closeSplit()"
          v-tooltip.top="t('tabs.split_close')"
        >
          <i class="pi pi-times"></i>
        </button>
      </div>
    </div>

    <!-- Contenuto: pagina navigabile, scrittura bloccata via provide readonly -->
    <div class="split-panel-content">
      <component :is="pinnedComponent" :key="tabs.pinnedTab?.path" />
    </div>
  </div>
</template>

<style scoped>
.split-secondary-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  border-left: 2px solid var(--app-toolbar-border);
}

.split-panel-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0.75rem;
  background: var(--app-toolbar-bg);
  border-bottom: 1px solid var(--app-toolbar-border);
  min-height: var(--app-toolbar-height);
}

.split-panel-icon {
  font-size: 0.8rem;
  color: var(--app-icon-color);
}

.split-panel-label {
  font-size: var(--app-font-size-sm);
  font-weight: 500;
  color: var(--app-topbar-breadcrumb-active-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.split-readonly-badge {
  font-size: 0.65rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  background: color-mix(in srgb, var(--p-orange-400) 15%, transparent);
  color: var(--p-orange-500);
  padding: 0.15rem 0.45rem;
  border-radius: 3px;
  white-space: nowrap;
}

.split-panel-actions {
  margin-left: auto;
  display: flex;
  gap: 0.25rem;
}

.split-panel-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.6rem;
  height: 1.6rem;
  font-size: 0.75rem;
  color: var(--app-topbar-breadcrumb-color);
  background: transparent;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  transition: background var(--app-transition-fast), color var(--app-transition-fast);
}

.split-panel-btn:hover {
  background: var(--app-toolbar-tab-hover-bg);
  color: var(--app-topbar-breadcrumb-active-color);
}

/* Feedback visivo leggero: il pannello secondario e' leggermente desaturato */
.split-panel-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--app-content-padding);
  min-height: 0;
  opacity: 0.9;
  filter: saturate(0.8);
}
</style>
