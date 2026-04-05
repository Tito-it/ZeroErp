import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { BREAKPOINTS } from '../core/constants'
import { local, STORAGE_KEYS } from '../core/storage'

export const useUiStore = defineStore('ui', () => {
  const storedValue = local.get(STORAGE_KEYS.SIDEBAR_COLLAPSED)
  const windowWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1280)

  // Layout mode: mobile / tablet / desktop
  const layoutMode = computed(() => {
    if (windowWidth.value < BREAKPOINTS.MOBILE) return 'mobile'
    if (windowWidth.value < BREAKPOINTS.TABLET) return 'tablet'
    return 'desktop'
  })

  const isTablet = computed(() => layoutMode.value === 'tablet')
  const isMobile = computed(() => layoutMode.value === 'mobile')
  const isDesktop = computed(() => layoutMode.value === 'desktop')

  // La sidebar inline si mostra solo su desktop e tablet (su mobile e' overlay/drawer)
  const sidebarInline = computed(() => layoutMode.value !== 'mobile')

  // Se non c'e' preferenza salvata e siamo su tablet, parte collassata
  const sidebarCollapsed = ref(
    storedValue !== null ? storedValue === 'true' : !isDesktop.value
  )

  // Su tablet la sidebar e' sempre collassata, indipendentemente dalla preferenza
  const effectiveSidebarCollapsed = computed(() =>
    isTablet.value ? true : sidebarCollapsed.value
  )

  // Search drawer — stato condiviso tra AppLayout (shortcut) e AppTopbar (pulsante)
  const searchDrawerVisible = ref(false)

  function openSearchDrawer() { searchDrawerVisible.value = true }

  // AI assistant drawer — stato condiviso tra AppTopbar (pulsante) e shortcut
  const aiDrawerVisible = ref(false)
  const aiAvailable = ref(false)

  // Dark/Light mode — persistito in localStorage, applicato su <html> class
  const storedDarkMode = local.get(STORAGE_KEYS.DARK_MODE)
  const isDark = ref(storedDarkMode !== null ? storedDarkMode === 'true' : true)

  // Applica la classe al DOM all'inizializzazione
  function _applyDarkMode() {
    if (isDark.value) {
      document.documentElement.classList.add('p-dark')
    } else {
      document.documentElement.classList.remove('p-dark')
    }
  }
  _applyDarkMode()

  function toggleDarkMode() {
    isDark.value = !isDark.value
    local.set(STORAGE_KEYS.DARK_MODE, isDark.value)
    _applyDarkMode()
  }

  function openAiDrawer() { aiDrawerVisible.value = true }
  function toggleAiDrawer() { aiDrawerVisible.value = !aiDrawerVisible.value }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
    local.set(STORAGE_KEYS.SIDEBAR_COLLAPSED, sidebarCollapsed.value)
  }

  function updateWindowWidth() {
    const prevMode = layoutMode.value
    windowWidth.value = window.innerWidth
    // Collassa automaticamente quando si passa a tablet
    if (prevMode === 'desktop' && layoutMode.value === 'tablet') {
      sidebarCollapsed.value = true
    }
  }

  // Listener resize con cleanup HMR
  if (typeof window !== 'undefined') {
    window.addEventListener('resize', updateWindowWidth, { passive: true })
    if (import.meta.hot) {
      import.meta.hot.dispose(() => window.removeEventListener('resize', updateWindowWidth))
    }
  }

  return {
    windowWidth,
    layoutMode,
    isTablet,
    isMobile,
    isDesktop,
    sidebarInline,
    sidebarCollapsed,
    effectiveSidebarCollapsed,
    searchDrawerVisible,
    openSearchDrawer,
    aiDrawerVisible,
    aiAvailable,
    openAiDrawer,
    toggleAiDrawer,
    toggleSidebar,
    isDark,
    toggleDarkMode
  }
})
