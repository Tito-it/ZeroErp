import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const SIDEBAR_KEY = 'sidebar_collapsed'
const TABLET_BREAKPOINT = 1024

export const useUiStore = defineStore('ui', () => {
  const storedValue = localStorage.getItem(SIDEBAR_KEY)
  const windowWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1280)

  const isTablet = computed(() => windowWidth.value <= TABLET_BREAKPOINT)

  // Se non c'è preferenza salvata e siamo su tablet, parte collassata
  const sidebarCollapsed = ref(storedValue !== null ? storedValue === 'true' : isTablet.value)

  // Su tablet la sidebar parte collassata, ma l'utente può espanderla
  const effectiveSidebarCollapsed = computed(() => {
    return sidebarCollapsed.value
  })

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
    localStorage.setItem(SIDEBAR_KEY, sidebarCollapsed.value)
  }

  function updateWindowWidth() {
    const wasTablet = isTablet.value
    windowWidth.value = window.innerWidth
    // Collassa automaticamente quando si entra in modalità tablet
    if (!wasTablet && isTablet.value) {
      sidebarCollapsed.value = true
    }
  }

  // Listener resize
  if (typeof window !== 'undefined') {
    window.addEventListener('resize', updateWindowWidth)
  }

  return { sidebarCollapsed, isTablet, effectiveSidebarCollapsed, toggleSidebar }
})
