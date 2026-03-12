// Scopo: traccia modifiche non salvate in una content tab.
// Sincronizza il flag dirty con lo store tabs e gestisce beforeunload del browser.
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useTabsStore } from '../../stores/tabs'

export function useDirtyState() {
  const dirty = ref(false)
  const tabs = useTabsStore()
  const route = useRoute()

  // Sincronizza il flag dirty con lo store tabs
  watch(dirty, (val) => {
    tabs.setDirty(route.path, val)
  })

  function markDirty() {
    dirty.value = true
  }

  function markClean() {
    dirty.value = false
  }

  // Guard browser: beforeunload per evitare perdita dati su refresh/chiusura browser
  function beforeUnload(e) {
    if (dirty.value) {
      e.preventDefault()
      e.returnValue = ''
    }
  }

  onMounted(() => window.addEventListener('beforeunload', beforeUnload))
  onUnmounted(() => {
    window.removeEventListener('beforeunload', beforeUnload)
    tabs.setDirty(route.path, false)
  })

  return { dirty, markDirty, markClean }
}
