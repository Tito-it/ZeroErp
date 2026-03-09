import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const SIDEBAR_KEY = 'sidebar_collapsed'
const TABLET_BREAKPOINT = 1024

export const useUiStore = defineStore('ui', () => {
  const sidebarCollapsed = ref(localStorage.getItem(SIDEBAR_KEY) === 'true')
  const windowWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1280)

  const isTablet = computed(() => windowWidth.value <= TABLET_BREAKPOINT)

  // Su tablet la sidebar è sempre collassata
  const effectiveSidebarCollapsed = computed(() => {
    return isTablet.value || sidebarCollapsed.value
  })

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
    localStorage.setItem(SIDEBAR_KEY, sidebarCollapsed.value)
  }

  function updateWindowWidth() {
    windowWidth.value = window.innerWidth
  }

  // Listener resize
  if (typeof window !== 'undefined') {
    window.addEventListener('resize', updateWindowWidth)
  }

  return { sidebarCollapsed, isTablet, effectiveSidebarCollapsed, toggleSidebar }
})
