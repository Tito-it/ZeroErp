<script setup>
// Scopo: layout principale dell'applicazione — sidebar morfica, topbar, content tabs, breadcrumb, split view.
// Gestisce il layout responsive (desktop/tablet inline, mobile overlay drawer).
//
// ⭐ Il menu coi NOMI sul touch e' sempre il drawer (Tid, 2026-09-21). Il
//    pattern «solo icone + tooltip» si regge sull'hover, che sul touch non
//    esiste: fino a quel giorno il drawer mobile era compresso a sole icone
//    (senza guadagnare spazio: e' un layer sopra il contenuto) e su tablet il
//    rail era compresso a forza con un pulsante «espandi» che non faceva
//    nulla. Ora: mobile → l'hamburger apre il drawer ESPANSO; tablet → il rail
//    inline resta la scorciatoia e il suo pulsante «espandi» apre lo stesso
//    drawer; desktop → nessun drawer, la sidebar si espande inline.
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import Drawer from 'primevue/drawer'
import AppSidebar from './AppSidebar.vue'
import AppTopbar from './AppTopbar.vue'
import EmittenteAttivoDialog from './EmittenteAttivoDialog.vue'
import ContentTabs from './ContentTabs.vue'
import AppBreadcrumb from './AppBreadcrumb.vue'
import SplitReadonlyPanel from './SplitReadonlyPanel.vue'
import { useUiStore } from '../../stores/ui'
import { useTabsStore } from '../../stores/tabs'
import { useKeyboardShortcuts } from '../composables/useKeyboardShortcuts'
import { useConfirmCloseTab } from '../composables/useConfirmCloseTab'
import { SHORTCUTS, BREAKPOINTS } from '../constants'

const ui = useUiStore()
const tabs = useTabsStore()
const router = useRouter()
const { closeTab } = useConfirmCloseTab()

// Drawer di navigazione espanso (mobile + tablet, vedi intestazione).
const menuDrawerOpen = ref(false)

// Ripristina tab da sessionStorage al primo caricamento
onMounted(() => {
  tabs.restoreTabs()
})

// Naviga alla tab attiva dopo un cambio (usato dai shortcut)
function navigateToActiveTab() {
  const active = tabs.activeTab
  if (active) router.push(active.path)
}

// Chiude lo split automaticamente se la finestra scende sotto la soglia desktop
watch(() => ui.windowWidth, (w) => {
  if (w < BREAKPOINTS.DESKTOP_SPLIT && tabs.isSplit) tabs.closeSplit()
})

// Il drawer esiste solo sotto il desktop: se la finestra si allarga con il
// drawer aperto lo stato non deve restare «aperto» in attesa del prossimo
// restringimento.
watch(() => ui.isDesktop, (desktop) => {
  if (desktop) menuDrawerOpen.value = false
})

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
    // Sotto il desktop il gesto «apri/chiudi menu» e' il drawer: la
    // preferenza inline su tablet e' ignorata dallo store e sarebbe un no-op.
    action: () => {
      if (ui.isDesktop) ui.toggleSidebar()
      else menuDrawerOpen.value = !menuDrawerOpen.value
    }
  },
  {
    ...SHORTCUTS.GO_HOME,
    action: () => router.push('/')
  },
  {
    ...SHORTCUTS.SPLIT_SWAP,
    action: () => {
      if (!tabs.isSplit) return
      tabs.swapPanels()
      navigateToActiveTab()
    }
  },
  {
    ...SHORTCUTS.SPLIT_CLOSE,
    action: () => tabs.closeSplit()
  },
  {
    ...SHORTCUTS.AI_ASSISTANT,
    action: () => { if (ui.aiAvailable) ui.toggleAiDrawer() }
  }
])

function onDrawerNavigate() {
  menuDrawerOpen.value = false
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
      <AppSidebar @expand="menuDrawerOpen = true" />
    </aside>

    <!-- Mobile + tablet: il menu ESPANSO (icone + etichette) come drawer
         overlay. Su mobile e' l'unica sidebar, su tablet affianca il rail
         inline e si apre dal suo pulsante «espandi». Chiude su scelta di una
         voce o tap sulla maschera. -->
    <Drawer
      v-if="!ui.isDesktop"
      v-model:visible="menuDrawerOpen"
      position="left"
      :showCloseIcon="false"
      :pt="{
        root: { style: 'width: var(--app-sidebar-mobile-width)' },
        header: { style: 'display: none' },
        content: { style: 'padding: 0' }
      }"
    >
      <AppSidebar drawer @navigate="onDrawerNavigate" />
    </Drawer>

    <div class="app-main">
      <AppTopbar
        :show-hamburger="ui.isMobile"
        @toggle-menu="menuDrawerOpen = !menuDrawerOpen"
      />
      <!-- Prima scelta dell'emittente di lavoro: bloccante, e solo per chi
           non ha mai scelto (impersonazione di scope). Vive nel layout perche'
           deve comparire su qualunque rotta l'utente atterri dopo il login. -->
      <EmittenteAttivoDialog />
      <ContentTabs />
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
    </div>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  flex-direction: row;
  flex-wrap: nowrap;
  height: 100vh;
  min-height: 600px;
  overflow: hidden;
}

.app-sidebar {
  flex: 0 0 var(--app-sidebar-width);
  width: var(--app-sidebar-width);
  max-width: var(--app-sidebar-width);
  height: 100%;
  min-height: 0;
  background: var(--app-sidebar-bg);
  border-right: 1px solid var(--app-sidebar-border);
  overflow: hidden;
  transition: flex-basis var(--app-transition-normal), width var(--app-transition-normal), max-width var(--app-transition-normal);
}

.app-sidebar.collapsed {
  flex: 0 0 var(--app-sidebar-width-collapsed);
  width: var(--app-sidebar-width-collapsed);
  max-width: var(--app-sidebar-width-collapsed);
}

.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.app-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  min-height: 0;
}

/* Senza split: il pannello primario si comporta come prima */
.app-content:not(.split-active) .app-content-panel.primary {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: var(--app-content-padding);
  min-height: 0;
}

/* Split attivo: grid 50/50 */
.app-content.split-active {
  flex-direction: row;
  overflow: hidden;
}

.app-content.split-active .app-content-panel.primary {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding: var(--app-content-padding);
  min-width: 0;
}

@media (max-width: 767.98px) {
  .app-layout {
    min-height: 0;
  }

  .app-content:not(.split-active) .app-content-panel.primary {
    padding: 0.75rem;
  }
}
</style>
