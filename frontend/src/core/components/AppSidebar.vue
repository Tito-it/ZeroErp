<script setup>
// Scopo: sidebar morfica — mostra SidebarHome o SidebarDomain in base al dominio attivo.
// Gestisce header, toggle collapse e transizione tra stati.
// Prop drawer: istanza dentro il drawer overlay (mobile + tablet) — SEMPRE
// espansa, con le etichette, e senza il toggle in fondo. ⛔ Fino al
// 2026-09-21 era «mobile» e forzava il collasso a sole icone: sul touch non
// c'e' hover, quindi niente tooltip, e l'operatore doveva ricordare le icone.
import { computed, provide } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUiStore } from '../../stores/ui'
import { useNavigationStore } from '../../stores/navigation'
import SidebarHome from './SidebarHome.vue'
import SidebarDomain from './SidebarDomain.vue'
import LogoBrand from './LogoBrand.vue'

const props = defineProps({
  drawer: { type: Boolean, default: false }
})

const { t } = useI18n()
const ui = useUiStore()
const nav = useNavigationStore()

// `expand`: su tablet il rail e' compresso a forza (lo store ignora la
// preferenza) e «espandi» significa «apri il drawer coi nomi» — lo decide il
// layout, che il drawer lo possiede.
const emit = defineEmits(['navigate', 'expand'])

const isCollapsed = computed(() => !props.drawer && ui.effectiveSidebarCollapsed)

// Fornisce lo stato collapsed ai figli (SidebarItem, SidebarDomain)
// cosi' rispettano il mobile senza leggere direttamente lo store ui
provide('sidebarCollapsed', isCollapsed)

function onChildNavigate() {
  emit('navigate')
}

function onToggle() {
  if (ui.isTablet) emit('expand')
  else ui.toggleSidebar()
}
</script>

<template>
  <div class="app-sidebar-inner" :class="{ collapsed: isCollapsed }">
    <!-- Header: logo + titolo -->
    <div class="sidebar-header">
      <LogoBrand :showText="!isCollapsed" />
    </div>

    <!-- Contenuto morfico -->
    <nav class="sidebar-nav">
      <Transition name="sidebar-morph" mode="out-in">
        <SidebarHome
          v-if="!nav.currentDomain"
          key="home"
          @navigate="onChildNavigate"
        />
        <SidebarDomain
          v-else
          :key="nav.currentDomain"
          @navigate="onChildNavigate"
        />
      </Transition>
    </nav>

    <!-- Footer: toggle collapse (solo inline, non nel drawer) -->
    <div v-if="!drawer" class="sidebar-footer">
      <!-- A sidebar compressa il gesto e' «espandi»: il tooltip dice cosa fa il
           click, non lo stato attuale (rilievo in-app di Tid, 2026-09-18). -->
      <div class="sidebar-toggle" @click="onToggle"
        v-tooltip.right="isCollapsed ? t('nav.expand') : null"
      >
        <i :class="isCollapsed ? 'pi pi-angle-double-right' : 'pi pi-angle-double-left'"></i>
        <span v-if="!isCollapsed">{{ t('nav.collapse') }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.app-sidebar-inner {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--app-sidebar-border);
}

.collapsed .sidebar-header {
  justify-content: center;
  padding: 1rem 0.25rem;
}

.sidebar-nav {
  flex: 1;
  padding: 0.5rem;
  overflow-y: auto;
  min-height: 0;
}

.sidebar-footer {
  border-top: 1px solid var(--app-sidebar-border);
  padding: 0.5rem;
}

.sidebar-toggle {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  border-radius: var(--app-sidebar-item-radius);
  color: var(--app-sidebar-item-color);
  font-size: var(--app-font-size-sm);
  cursor: pointer;
  white-space: nowrap;
  transition: background var(--app-transition-fast);
}

.sidebar-toggle i {
  color: var(--app-icon-color);
}

.sidebar-toggle:hover i {
  color: inherit;
}

.collapsed .sidebar-toggle {
  justify-content: center;
  padding: 0.5rem 0.35rem;
}

.sidebar-toggle:hover {
  background: var(--app-sidebar-item-hover-bg);
}

/* Transizione morfica tra SidebarHome e SidebarDomain */
.sidebar-morph-enter-active,
.sidebar-morph-leave-active {
  transition: opacity 0.15s ease;
}

.sidebar-morph-enter-from,
.sidebar-morph-leave-to {
  opacity: 0;
}

/* Divider condiviso (usato direttamente in SidebarHome e SidebarDomain) */
:deep(.sidebar-divider) {
  height: 1px;
  background: var(--app-sidebar-border);
  margin: 0.25rem 0;
}
</style>
