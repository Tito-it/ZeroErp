// Scopo: gestione content tabs tipo browser — apertura, chiusura, stato dirty, persistenza, split view
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { TABS } from '../core/constants'
import { session, STORAGE_KEYS } from '../core/storage'

let idCounter = 0

function generateId() {
  return `tab-${Date.now()}-${++idCounter}`
}

export const useTabsStore = defineStore('tabs', () => {
  const tabs = ref([])
  const activeTabId = ref(null)

  // --- Split view state ---
  const pinnedTabId = ref(null)

  // Tab attiva corrente
  const activeTab = computed(() =>
    tabs.value.find(t => t.id === activeTabId.value) || null
  )

  // Tab pinnata nel pannello secondario (split view)
  const pinnedTab = computed(() =>
    tabs.value.find(t => t.id === pinnedTabId.value) || null
  )

  // Split attivo (derivato: pinnedTabId presente e tab ancora esistente)
  const isSplit = computed(() => pinnedTab.value !== null)

  // Tab disponibili per il popover "Affianca" (tutte tranne l'attiva)
  const splittableTabs = computed(() =>
    tabs.value.filter(t => t.id !== activeTabId.value)
  )

  // Apre una tab (o attiva quella esistente per la stessa route)
  function openTab({ path, label, domain, icon }) {
    const existing = tabs.value.find(t => t.path === path)
    if (existing) {
      // Se la tab esistente e' quella pinnata nello split, chiudi lo split prima di attivarla
      if (isSplit.value && existing.id === pinnedTabId.value) {
        pinnedTabId.value = null
      }
      activeTabId.value = existing.id
      return existing
    }
    // Limite massimo tab
    if (tabs.value.length >= TABS.MAX_OPEN) {
      // Chiudi la tab piu' vecchia non-dirty (esclusa attiva e pinnata)
      const closable = tabs.value.find(t =>
        !t.dirty && t.id !== activeTabId.value && t.id !== pinnedTabId.value
      )
      if (closable) removeTab(closable.id)
    }
    const tab = {
      id: generateId(),
      path,
      label: label || path.split('/').pop() || 'Pagina',
      domain: domain || null,
      icon: icon || null,
      dirty: false,
      contextAware: false
    }
    tabs.value.push(tab)
    activeTabId.value = tab.id
    persistTabs()
    return tab
  }

  // Rimuove una tab per id (senza conferma dirty — la conferma la gestisce il componente)
  function removeTab(tabId) {
    const idx = tabs.value.findIndex(t => t.id === tabId)
    if (idx === -1) return
    // Se la tab rimossa e' quella pinnata nello split, chiudi lo split (senza doppio persist)
    if (pinnedTabId.value === tabId) {
      pinnedTabId.value = null
    }
    tabs.value.splice(idx, 1)
    // Se era la tab attiva, attiva la piu' vicina
    if (activeTabId.value === tabId) {
      const next = tabs.value[Math.min(idx, tabs.value.length - 1)]
      activeTabId.value = next ? next.id : null
    }
    persistTabs()
  }

  // Attiva una tab specifica
  function activateTab(tabId) {
    const tab = tabs.value.find(t => t.id === tabId)
    if (tab) activeTabId.value = tabId
  }

  // Attiva la tab successiva (ciclica)
  function activateNextTab() {
    if (tabs.value.length <= 1) return
    const idx = tabs.value.findIndex(t => t.id === activeTabId.value)
    const next = (idx + 1) % tabs.value.length
    activeTabId.value = tabs.value[next].id
  }

  // Attiva la tab precedente (ciclica)
  function activatePrevTab() {
    if (tabs.value.length <= 1) return
    const idx = tabs.value.findIndex(t => t.id === activeTabId.value)
    const prev = (idx - 1 + tabs.value.length) % tabs.value.length
    activeTabId.value = tabs.value[prev].id
  }

  // Imposta flag dirty su una tab
  function setDirty(path, isDirty) {
    const tab = tabs.value.find(t => t.path === path)
    if (tab) tab.dirty = isDirty
  }

  // Aggiorna la label di una tab
  function updateLabel(path, newLabel) {
    const tab = tabs.value.find(t => t.path === path)
    if (tab) tab.label = newLabel
  }

  // Segna una tab come context-aware
  function setContextAware(path, isAware) {
    const tab = tabs.value.find(t => t.path === path)
    if (tab) tab.contextAware = isAware
  }

  // Trova la tab per path
  function findByPath(path) {
    return tabs.value.find(t => t.path === path) || null
  }

  // Controlla se ci sono tab dirty
  function hasDirtyTabs() {
    return tabs.value.some(t => t.dirty)
  }

  // --- Split view methods ---

  // Pinna una tab nel pannello secondario read-only
  function pinTab(tabId) {
    const tab = tabs.value.find(t => t.id === tabId)
    if (!tab) return
    // Servono almeno 2 tab per lo split (una nel primario, una nel secondario)
    if (tabs.value.length < 2) return
    // Se si pinna la tab attiva, sposta il primario sulla prima tab disponibile
    if (tabId === activeTabId.value) {
      const other = tabs.value.find(t => t.id !== tabId)
      if (!other) return
      activeTabId.value = other.id
    }
    pinnedTabId.value = tabId
    persistTabs()
  }

  // Chiude lo split view
  function closeSplit() {
    pinnedTabId.value = null
    persistTabs()
  }

  // Scambia pannello primario e secondario
  function swapPanels() {
    if (!isSplit.value) return
    const prevActive = activeTabId.value
    activeTabId.value = pinnedTabId.value
    pinnedTabId.value = prevActive
    persistTabs()
  }

  // Persistenza in sessionStorage
  function persistTabs() {
    try {
      const data = tabs.value.map(t => ({
        path: t.path,
        label: t.label,
        domain: t.domain,
        icon: t.icon
      }))
      const payload = {
        tabs: data,
        activeTabPath: activeTab.value?.path || null
      }
      // Salva stato split solo se attivo
      if (isSplit.value && pinnedTab.value) {
        payload.splitPinnedPath = pinnedTab.value.path
      }
      session.set(STORAGE_KEYS.OPEN_TABS, JSON.stringify(payload))
    } catch { /* sessionStorage pieno o non disponibile */ }
  }

  // Ripristina tab da sessionStorage (senza scrivere persistTabs ad ogni openTab)
  function restoreTabs() {
    try {
      const raw = session.get(STORAGE_KEYS.OPEN_TABS)
      if (!raw) return
      const data = JSON.parse(raw)
      if (!Array.isArray(data.tabs)) return
      // Costruisce le tab direttamente senza passare da openTab (evita N persistTabs)
      for (const t of data.tabs) {
        const existing = tabs.value.find(x => x.path === t.path)
        if (existing) continue
        tabs.value.push({
          id: generateId(),
          path: t.path,
          label: t.label || t.path.split('/').pop() || 'Pagina',
          domain: t.domain || null,
          icon: t.icon || null,
          dirty: false,
          contextAware: false
        })
      }
      // Ripristina tab attiva
      if (data.activeTabPath) {
        const restored = tabs.value.find(x => x.path === data.activeTabPath)
        if (restored) activeTabId.value = restored.id
      } else if (tabs.value.length > 0) {
        activeTabId.value = tabs.value[0].id
      }
      // Ripristina split view se salvato
      if (data.splitPinnedPath) {
        const pinned = tabs.value.find(x => x.path === data.splitPinnedPath)
        if (pinned && pinned.id !== activeTabId.value) {
          pinnedTabId.value = pinned.id
        }
      }
    } catch { /* JSON corrotto, ignoriamo */ }
  }

  // Chiudi tutte le tab (usato per logout)
  function closeAll() {
    tabs.value = []
    activeTabId.value = null
    pinnedTabId.value = null
    session.remove(STORAGE_KEYS.OPEN_TABS)
  }

  return {
    tabs,
    activeTabId,
    activeTab,
    // Split view
    pinnedTab,
    isSplit,
    splittableTabs,
    pinTab,
    closeSplit,
    swapPanels,
    // Tab operations
    openTab,
    removeTab,
    activateTab,
    activateNextTab,
    activatePrevTab,
    setDirty,
    updateLabel,
    setContextAware,
    findByPath,
    hasDirtyTabs,
    restoreTabs,
    closeAll
  }
})
