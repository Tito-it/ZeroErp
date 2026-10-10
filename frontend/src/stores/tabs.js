// Scopo: gestione content tabs tipo browser — apertura, chiusura, stato dirty, persistenza, split view
import { defineStore } from 'pinia'
import { ref, computed, toRaw } from 'vue'
import { TABS } from '../core/constants'
import { session, STORAGE_KEYS } from '../core/storage'
import { DOMAIN_MENUS, flattenMenu, resolveTabIcon } from '../core/navigation'

let idCounter = 0

function generateId() {
  return `tab-${Date.now()}-${++idCounter}`
}

export const useTabsStore = defineStore('tabs', () => {
  const tabs = ref([])
  const activeTabId = ref(null)

  // ⭐ OLTRE IL LIMITE LA DECIMA SI SOSTITUISCE (Tid, 2026-09-30): le prime
  //    MAX_OPEN - 1 schede sono il tavolo di lavoro, l'ultima in fila e' la
  //    scheda di passaggio. Fino a quel giorno l'undicesima era bloccata con un
  //    toast, e l'operatore doveva cercare cosa chiudere e ripetere il clic.
  //    La domanda la pone il guard del router (l'unico che apre le schede);
  //    la conferma la mostra ContentTabs, perche' il guard non ha un
  //    componente in cui aprire una dialog: qui sta solo la richiesta in
  //    attesa, `{ tab, rispondi }`.
  const richiestaSostituzione = ref(null)

  // Chi ha modifiche non salvate, per tab: path → insieme delle sorgenti
  // (drawer) sporche. Una tab e' sporca finche' ALMENO UNA sua sorgente lo e':
  // con un flag solo, il primo drawer che salva lo abbasserebbe anche per
  // l'altro ancora aperto con le sue modifiche.
  const sorgentiSporche = new Map()

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

  function inferMenuKey(domain, path) {
    if (!domain || !DOMAIN_MENUS[domain]) return null
    return flattenMenu(DOMAIN_MENUS[domain])
      .find(item => item.to === path)?.key || null
  }

  function resolveCurrentIcon(domain, menuKey, path, fallback = null) {
    const resolvedMenuKey = menuKey || inferMenuKey(domain, path)
    return resolveTabIcon({ domain, menuKey: resolvedMenuKey }) || fallback || null
  }

  // Apre una tab (o attiva quella esistente per la stessa route)
  function openTab({ path, label, domain, menuKey, icon }) {
    const existing = tabs.value.find(t => t.path === path)
    if (existing) {
      let changed = false
      existing.domain = existing.domain || domain || null
      existing.menuKey = existing.menuKey || menuKey || inferMenuKey(existing.domain, path)
      const currentIcon = icon || resolveCurrentIcon(existing.domain, existing.menuKey, path, existing.icon)
      if (currentIcon && existing.icon !== currentIcon) {
        existing.icon = currentIcon
        changed = true
      }
      // Se la tab esistente e' quella pinnata nello split, chiudi lo split prima di attivarla
      if (isSplit.value && existing.id === pinnedTabId.value) {
        pinnedTabId.value = null
        changed = true
      }
      activeTabId.value = existing.id
      if (changed) persistTabs()
      return existing
    }
    // ⛔ Oltre il limite non si apre: chi arriva qui senza essere passato da
    //    `schedaDaSostituire` + `sostituisci` ha saltato la conferma.
    if (tabs.value.length >= TABS.MAX_OPEN) return null
    const tab = {
      id: generateId(),
      path,
      label: label || path.split('/').pop() || 'Pagina',
      domain: domain || null,
      menuKey: menuKey || inferMenuKey(domain, path),
      icon: icon || resolveCurrentIcon(domain, menuKey, path),
      dirty: false,
      contextAware: false,
      customLabel: false
    }
    tabs.value.push(tab)
    activeTabId.value = tab.id
    persistTabs()
    return tab
  }

  // Scopo: la scheda che l'apertura di `path` sostituirebbe — l'ultima in
  //        fila — o null se non serve sostituire niente (la scheda c'e' gia',
  //        o c'e' ancora posto).
  function schedaDaSostituire(path) {
    if (tabs.value.some(t => t.path === path)) return null
    if (tabs.value.length < TABS.MAX_OPEN) return null
    return tabs.value[tabs.value.length - 1]
  }

  // Scopo: chiede conferma della sostituzione a chi mostra la dialog
  //        (ContentTabs) e risponde true/false. Una richiesta ancora aperta
  //        quando ne arriva un'altra e' una navigazione abbandonata: risponde
  //        false, o la sua promessa resterebbe appesa per sempre.
  function chiediSostituzione(tab) {
    richiestaSostituzione.value?.rispondi(false)
    return new Promise((resolve) => {
      const richiesta = {
        tab,
        rispondi: (ok) => {
          // ⚠️ `toRaw`: il ref custodisce un PROXY reattivo, e `===` con
          //    l'oggetto originale e' sempre falso — la richiesta non si
          //    svuoterebbe mai.
          if (toRaw(richiestaSostituzione.value) === richiesta) richiestaSostituzione.value = null
          resolve(ok === true)
        },
      }
      richiestaSostituzione.value = richiesta
    })
  }

  // Rimuove una tab per id (senza conferma dirty — la conferma la gestisce il componente)
  function removeTab(tabId) {
    const idx = tabs.value.findIndex(t => t.id === tabId)
    if (idx === -1) return
    // Se la tab rimossa e' quella pinnata nello split, chiudi lo split (senza doppio persist)
    if (pinnedTabId.value === tabId) {
      pinnedTabId.value = null
    }
    sorgentiSporche.delete(tabs.value[idx].path)
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

  // Scopo: una sorgente (un drawer, via `useDrawerFormPreserve`) dice se ha
  //        modifiche non salvate; il flag `dirty` della tab ne e' la somma.
  //        Lo leggono il pallino di ContentTabs, la conferma di chiusura
  //        (`useConfirmCloseTab`) e l'avviso del cambio emittente.
  function segnalaModifiche(path, sorgente, sporca) {
    const insieme = sorgentiSporche.get(path) ?? new Set()
    if (sporca) insieme.add(sorgente)
    else insieme.delete(sorgente)
    if (insieme.size) sorgentiSporche.set(path, insieme)
    else sorgentiSporche.delete(path)
    const tab = tabs.value.find(t => t.path === path)
    if (tab) tab.dirty = insieme.size > 0
  }

  // Aggiorna la label di una tab
  function updateLabel(path, newLabel) {
    const tab = tabs.value.find(t => t.path === path)
    if (tab) {
      tab.label = newLabel
      tab.customLabel = true
      persistTabs()
    }
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
        menuKey: t.menuKey,
        icon: t.icon,
        customLabel: t.customLabel === true
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
        const domain = t.domain || null
        const menuKey = t.menuKey || inferMenuKey(domain, t.path)
        tabs.value.push({
          id: generateId(),
          path: t.path,
          label: t.label || t.path.split('/').pop() || 'Pagina',
          domain,
          menuKey,
          icon: resolveCurrentIcon(domain, menuKey, t.path, t.icon),
          dirty: false,
          contextAware: false,
          customLabel: t.customLabel === true
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
    sorgentiSporche.clear()
    tabs.value = []
    activeTabId.value = null
    pinnedTabId.value = null
    session.remove(STORAGE_KEYS.OPEN_TABS)
  }

  return {
    tabs,
    activeTabId,
    activeTab,
    // Sostituzione oltre il limite
    richiestaSostituzione,
    schedaDaSostituire,
    chiediSostituzione,
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
    segnalaModifiche,
    updateLabel,
    setContextAware,
    findByPath,
    hasDirtyTabs,
    restoreTabs,
    closeAll,
    // Reset user-scoped: alias di closeAll, invocato dal plugin autoReset al logout.
    // Esposto come action separata per rispettare il contratto del plugin
    // (`resetAllUserScopedStores` cerca `clearUserState` prima di $resetToInitial).
    clearUserState: closeAll
  }
}, {
  userScoped: true
})
