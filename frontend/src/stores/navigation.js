// Scopo: gestione stato sidebar morfica — dominio attivo e menu corrente
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { DOMAINS, DOMAIN_MENUS } from '../core/navigation'
import { local, domainFavoriteKey } from '../core/storage'

export const useNavigationStore = defineStore('navigation', () => {
  // Dominio attivo (null = stato HOME)
  const currentDomain = ref(null)

  // Mappa reattiva delle pagine preferite per dominio (sincronizzata con localStorage)
  const favorites = ref(loadFavorites())

  // Menu L2 del dominio attivo
  const currentMenu = computed(() => {
    if (!currentDomain.value) return []
    return DOMAIN_MENUS[currentDomain.value] || []
  })

  // Config del dominio attivo (icona, label key, ecc.)
  const currentDomainConfig = computed(() => {
    if (!currentDomain.value) return null
    return DOMAINS.find(d => d.key === currentDomain.value) || null
  })

  // Imposta il dominio attivo
  function setDomain(domainKey) {
    currentDomain.value = domainKey
  }

  // Torna allo stato HOME
  function clearDomain() {
    currentDomain.value = null
  }

  // Pagina default per un dominio: preferita utente > prima voce menu > route base dominio
  function getDefaultRoute(domainKey) {
    const favorite = favorites.value[domainKey]
    if (favorite) return favorite
    const menu = DOMAIN_MENUS[domainKey] || []
    if (menu.length > 0) return menu[0].to
    const domain = DOMAINS.find(d => d.key === domainKey)
    return domain?.to || null
  }

  // Salva pagina preferita per un dominio
  function setFavorite(domainKey, routePath) {
    favorites.value = { ...favorites.value, [domainKey]: routePath }
    local.set(domainFavoriteKey(domainKey), routePath)
  }

  // Rimuovi pagina preferita per un dominio
  function clearFavorite(domainKey) {
    const copy = { ...favorites.value }
    delete copy[domainKey]
    favorites.value = copy
    local.remove(domainFavoriteKey(domainKey))
  }

  // Controlla se una route e' la preferita per il dominio corrente (reattivo)
  function isFavorite(routePath) {
    if (!currentDomain.value) return false
    return favorites.value[currentDomain.value] === routePath
  }

  // Carica preferiti da localStorage all'avvio
  function loadFavorites() {
    const result = {}
    for (const domain of DOMAINS) {
      const val = local.get(domainFavoriteKey(domain.key))
      if (val) result[domain.key] = val
    }
    return result
  }

  // Reset completo al logout: dominio attivo + preferiti localStorage
  function clearAll() {
    currentDomain.value = null
    for (const domain of DOMAINS) {
      local.remove(domainFavoriteKey(domain.key))
    }
    favorites.value = {}
  }

  return {
    currentDomain,
    currentMenu,
    currentDomainConfig,
    setDomain,
    clearDomain,
    getDefaultRoute,
    setFavorite,
    clearFavorite,
    clearAll,
    isFavorite,
    // Reset user-scoped: alias di clearAll (pulisce domain + favoriti
    // localStorage), invocato dal plugin autoReset al logout.
    clearUserState: clearAll
  }
}, {
  userScoped: true
})
