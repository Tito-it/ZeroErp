<script setup>
// Scopo: sidebar morfica — mostra SidebarHome o SidebarDomain in base al dominio attivo.
// Gestisce header, toggle collapse, logout e transizione tra stati.
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useUiStore } from '../../stores/ui'
import { useNavigationStore } from '../../stores/navigation'
import SidebarHome from './SidebarHome.vue'
import SidebarDomain from './SidebarDomain.vue'
import LogoBrand from './LogoBrand.vue'

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()
const ui = useUiStore()
const nav = useNavigationStore()

const emit = defineEmits(['navigate'])

async function handleLogout() {
  await auth.logout()
  router.push({ name: 'login' })
}

function onChildNavigate() {
  emit('navigate')
}
</script>

<template>
  <div class="app-sidebar-inner" :class="{ collapsed: ui.effectiveSidebarCollapsed }">
    <!-- Header: logo + titolo -->
    <div class="sidebar-header">
      <LogoBrand :showText="!ui.effectiveSidebarCollapsed" />
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

    <!-- Footer: toggle + logout -->
    <div class="sidebar-footer">
      <div class="sidebar-toggle" @click="ui.toggleSidebar()"
        v-tooltip.right="ui.effectiveSidebarCollapsed ? t('nav.collapse') : null"
      >
        <i :class="ui.effectiveSidebarCollapsed ? 'pi pi-angle-right' : 'pi pi-angle-left'"></i>
        <span v-if="!ui.effectiveSidebarCollapsed">{{ t('nav.collapse') }}</span>
      </div>

      <div
        class="sidebar-user"
        @click="handleLogout"
        v-tooltip.right="ui.effectiveSidebarCollapsed ? t('auth.logout') : null"
      >
        <i class="pi pi-sign-out"></i>
        <span v-if="!ui.effectiveSidebarCollapsed">{{ t('auth.logout') }}</span>
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
  padding: 1rem 0.5rem;
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

.sidebar-user,
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

.sidebar-user i,
.sidebar-toggle i {
  color: var(--app-icon-color);
}

.sidebar-user:hover i,
.sidebar-toggle:hover i {
  color: inherit;
}

.collapsed .sidebar-user,
.collapsed .sidebar-toggle {
  justify-content: center;
  padding: 0.5rem;
}

.sidebar-user:hover,
.sidebar-toggle:hover {
  background: var(--app-sidebar-item-hover-bg);
}

.sidebar-toggle {
  margin-top: 2px;
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
