import { defineStore } from 'pinia'
import { ref } from 'vue'

const SIDEBAR_KEY = 'sidebar_collapsed'

export const useUiStore = defineStore('ui', () => {
  const sidebarCollapsed = ref(localStorage.getItem(SIDEBAR_KEY) === 'true')

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
    localStorage.setItem(SIDEBAR_KEY, sidebarCollapsed.value)
  }

  return { sidebarCollapsed, toggleSidebar }
})
