<script setup>
// Scopo: layout principale dell'applicazione — sidebar morfica, topbar, content tabs, breadcrumb.
// Gestisce il layout responsive (desktop/tablet inline, mobile overlay drawer).
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Drawer from 'primevue/drawer'
import AppSidebar from './AppSidebar.vue'
import AppTopbar from './AppTopbar.vue'
import ContentTabs from './ContentTabs.vue'
import AppBreadcrumb from './AppBreadcrumb.vue'
import { useUiStore } from '../../stores/ui'
import { useTabsStore } from '../../stores/tabs'
import { useKeyboardShortcuts } from '../composables/useKeyboardShortcuts'
import { useConfirmCloseTab } from '../composables/useConfirmCloseTab'
import { SHORTCUTS } from '../constants'

const ui = useUiStore()
const tabs = useTabsStore()
const router = useRouter()
const { closeTab } = useConfirmCloseTab()

const mobileMenuOpen = ref(false)

// Ripristina tab da sessionStorage al primo caricamento
onMounted(() => {
  tabs.restoreTabs()
})

// Naviga alla tab attiva dopo un cambio (usato dai shortcut)
function navigateToActiveTab() {
  const active = tabs.activeTab
  if (active) router.push(active.path)
}

// Scorciatoie da tastiera globali
useKeyboardShortcuts([
  {
    ...SHORTCUTS.SEARCH,
    action: () => ui.openSearchDrawer()
  },
  {
    ...SHORTCUTS.NEXT_TAB,
    action: () => { tabs.activateNextTab(); navigateToActiveTab() }
  },
  {
    ...SHORTCUTS.PREV_TAB,
    action: () => { tabs.activatePrevTab(); navigateToActiveTab() }
  },
  {
    ...SHORTCUTS.CLOSE_TAB,
    action: () => closeTab(tabs.activeTab)
  },
  {
    ...SHORTCUTS.TOGGLE_SIDEBAR,
    action: () => ui.toggleSidebar()
  },
  {
    ...SHORTCUTS.GO_HOME,
    action: () => router.push('/')
  }
])

function onMobileNavigate() {
  mobileMenuOpen.value = false
}
</script>

<template>
  <div class="app-layout">
    <!-- Desktop/Tablet: sidebar inline -->
    <aside
      v-if="ui.sidebarInline"
      class="app-sidebar"
      :class="{ collapsed: ui.effectiveSidebarCollapsed }"
    >
      <AppSidebar />
    </aside>

    <!-- Mobile: sidebar come drawer overlay -->
    <Drawer
      v-else
      v-model:visible="mobileMenuOpen"
      position="left"
      :pt="{ root: { style: 'width: 280px' } }"
    >
      <AppSidebar @navigate="onMobileNavigate" />
    </Drawer>

    <div class="app-main">
      <AppTopbar
        :show-hamburger="ui.isMobile"
        @toggle-menu="mobileMenuOpen = !mobileMenuOpen"
      />
      <ContentTabs />
      <main class="app-content">
        <AppBreadcrumb />
        <router-view v-slot="{ Component }">
          <KeepAlive :max="10">
            <component :is="Component" :key="$route.path" />
          </KeepAlive>
        </router-view>
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  min-height: 600px;
  overflow: hidden;
}

.app-sidebar {
  width: var(--app-sidebar-width);
  min-width: var(--app-sidebar-width);
  height: 100%;
  min-height: 0;
  background: var(--app-sidebar-bg);
  border-right: 1px solid var(--app-sidebar-border);
  overflow: hidden;
  transition: width var(--app-transition-normal), min-width var(--app-transition-normal);
}

.app-sidebar.collapsed {
  width: var(--app-sidebar-width-collapsed);
  min-width: var(--app-sidebar-width-collapsed);
}

.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.app-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--app-content-padding);
}

@media (max-width: 767px) {
  .app-layout {
    min-height: 0;
  }

  .app-content {
    padding: 0.75rem;
  }
}
</style>
