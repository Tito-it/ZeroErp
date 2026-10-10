// Scopo: gestione stato sidebar morfica — dominio attivo e menu corrente
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { DOMAINS, DOMAIN_MENUS, flattenMenu } from '../core/navigation'
import { local, domainFavoriteKey, userScopedKey } from '../core/storage'

const FAVORITES_PER_DOMAIN_MAX = 4

export const useNavigationStore = defineStore('navigation', () => {
  // Dominio attivo (null = stato HOME)
  const currentDomain = ref(null)

  // ID utente corrente per persistere preferiti personali senza leak cross-user.
  const currentUserId = ref(null)

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

  // Scopo: risolve la chiave storage user-scoped per il preferito di un dominio.
  // Ritorna null se non c'e' utente in sessione: in quel caso la persistenza e'
  // disabilitata (vedi persistDomainFavorites). Mai usare la chiave base globale
  // come fallback: e' condivisa tra utenti sullo stesso browser e diventa
  // veicolo di leak cross-user (un secondo utente vedrebbe i preferiti del primo).
  function favoriteStorageKey(domainKey) {
    if (currentUserId.value == null) return null
    return userScopedKey(domainFavoriteKey(domainKey), currentUserId.value)
  }

  // Pagina default per un dominio: primo preferito utente > prima voce menu > route base dominio
  function getDefaultRoute(domainKey) {
    const domainFavorites = favorites.value[domainKey]
    if (Array.isArray(domainFavorites) && domainFavorites.length > 0) {
      return domainFavorites[0]
    }
    // ⚠️ La prima voce con una rotta: un GRUPPO (voce con `children`) non ne
    //    ha una sua, e il suo `to` assente mandava il dominio a `undefined`.
    const primaVoce = flattenMenu(DOMAIN_MENUS[domainKey]).find(item => item.to)
    if (primaVoce) return primaVoce.to
    const domain = DOMAINS.find(d => d.key === domainKey)
    return domain?.to || null
  }

  // Scopo: persiste l'array ordinato dei preferiti di un dominio.
  // Guard: senza utente in sessione la scrittura e' vietata, altrimenti i
  // preferiti finirebbero nella chiave globale del browser e diventerebbero
  // visibili al prossimo utente che si logga (leak cross-user).
  function persistDomainFavorites(domainKey, domainFavorites) {
    const key = favoriteStorageKey(domainKey)
    if (!key) return
    if (!Array.isArray(domainFavorites) || domainFavorites.length === 0) {
      local.remove(key)
      return
    }
    local.set(key, JSON.stringify(domainFavorites))
  }

  // Scopo: normalizza l'array rimuovendo valori non validi e duplicati.
  function normalizeFavoritesList(list) {
    const seen = new Set()
    const result = []
    for (const path of Array.isArray(list) ? list : []) {
      if (typeof path !== 'string' || !path || seen.has(path)) continue
      seen.add(path)
      result.push(path)
    }
    return result
  }

  // Aggiunge una pagina preferita per un dominio. Ritorna false se cap raggiunto.
  function addFavorite(domainKey, routePath) {
    if (!domainKey || !routePath) return false
    const current = getDomainFavorites(domainKey)
    if (current.includes(routePath)) return true
    if (current.length >= FAVORITES_PER_DOMAIN_MAX) return false
    const next = [...current, routePath]
    favorites.value = { ...favorites.value, [domainKey]: next }
    persistDomainFavorites(domainKey, next)
    return true
  }

  // Rimuove una pagina preferita da un dominio.
  function removeFavorite(domainKey, routePath) {
    if (!domainKey || !routePath) return
    const current = getDomainFavorites(domainKey)
    const next = current.filter(path => path !== routePath)
    const copy = { ...favorites.value }
    if (next.length > 0) {
      copy[domainKey] = next
    } else {
      delete copy[domainKey]
    }
    favorites.value = copy
    persistDomainFavorites(domainKey, next)
  }

  // Toggle preferito: add se assente, remove se presente. Ritorna false se cap raggiunto.
  function toggleFavorite(domainKey, routePath) {
    if (isFavoriteOfDomain(domainKey, routePath)) {
      removeFavorite(domainKey, routePath)
      return true
    }
    return addFavorite(domainKey, routePath)
  }

  // Riordina i preferiti di un dominio usando solo route valide e uniche.
  function reorderFavorites(domainKey, newOrder) {
    if (!domainKey) return
    const next = normalizeFavoritesList(newOrder)
    const copy = { ...favorites.value }
    if (next.length > 0) {
      copy[domainKey] = next
    } else {
      delete copy[domainKey]
    }
    favorites.value = copy
    persistDomainFavorites(domainKey, next)
  }

  // Preferiti raw del dominio, senza filtro permessi.
  function getDomainFavorites(domainKey) {
    return normalizeFavoritesList(favorites.value[domainKey])
  }

  // Preferiti raw aggregati, in ordine dominio e poi ordine interno.
  function getAllFavorites() {
    return DOMAINS.flatMap(domain =>
      getDomainFavorites(domain.key).map(path => ({
        domain: domain.key,
        path
      }))
    )
  }

  // Controlla se una route e' preferita in almeno un dominio.
  function isFavorite(routePath) {
    return Object.values(favorites.value).some(domainFavorites =>
      normalizeFavoritesList(domainFavorites).includes(routePath)
    )
  }

  // Controlla se una route e' preferita per uno specifico dominio.
  function isFavoriteOfDomain(domainKey, routePath) {
    return getDomainFavorites(domainKey).includes(routePath)
  }

  // Compatibilita' con vecchi caller: imposta un solo preferito come lista a 1 elemento.
  function setFavorite(domainKey, routePath) {
    reorderFavorites(domainKey, routePath ? [routePath] : [])
  }

  // Compatibilita' con vecchi caller: rimuove tutti i preferiti del dominio.
  function clearFavorite(domainKey) {
    reorderFavorites(domainKey, [])
  }

  // Scopo: i path delle voci di menu di un dominio, cioe' gli unici che un
  //        preferito puo' essere (lo crea la stella di una voce, `SidebarDomain`).
  function vociDelDominio(domainKey) {
    return new Set(flattenMenu(DOMAIN_MENUS[domainKey]).map(item => item.to).filter(Boolean))
  }

  // Carica preferiti da localStorage. Senza userId niente da caricare.
  // ⛔ Un preferito salvato su una voce poi RITIRATA dal menu si scarta qui:
  //    `getDefaultRoute` mette il primo preferito davanti alla prima voce, e
  //    un path che non e' piu' una pagina apriva il dominio su «non trovato»
  //    (Amm. Software, voce «Permessi» ritirata il 2026-10-06). Il localStorage
  //    sopravvive ai rilasci: il menu di oggi e' la sola fonte di cosa vale.
  // NB: storica versione di questa funzione faceva fallback sulla chiave base
  // globale come "legacy migration". E' stata RIMOSSA perche' la chiave base
  // e' condivisa tra utenti sullo stesso browser, quindi un secondo utente
  // ereditava i preferiti del primo (leak cross-user). Conseguenza: eventuali
  // preferiti salvati pre-fix nella chiave globale sono persi — accettiamo
  // il trade-off in cambio della sicurezza.
  function loadFavorites(userId = currentUserId.value) {
    const result = {}
    if (userId == null) return result
    for (const domain of DOMAINS) {
      const scopedKey = userScopedKey(domainFavoriteKey(domain.key), userId)
      const raw = local.get(scopedKey)
      if (!raw) continue
      let parsed
      try {
        parsed = JSON.parse(raw)
      } catch {
        parsed = raw
      }
      const list = (Array.isArray(parsed)
        ? normalizeFavoritesList(parsed)
        : normalizeFavoritesList([parsed])
      ).filter(path => vociDelDominio(domain.key).has(path))
      if (list.length > 0) result[domain.key] = list
    }
    return result
  }

  // Sincronizza preferiti personali dopo login/restore profilo.
  // ⛔ Fino al 2026-09-12 qui (e in `clearUserState`) girava a OGNI login un
  //    `purgeLegacyBaseKeys()` che cancellava dal localStorage le chiavi
  //    globali di prima del fix user-scoped: un meccanismo «difensivo» che
  //    serviva dati che questo codice non scrive piu' da mesi
  //    (analisi-software-per-dati-morti §2.4). Tolto: chi ha un browser
  //    pre-fix con residui globali non li vede — erano il difetto, non un
  //    dato — perche' `loadFavorites` legge SOLO le chiavi user-scoped.
  function syncUserFavorites(userId) {
    currentUserId.value = userId ?? null
    favorites.value = loadFavorites(currentUserId.value)
  }

  // Reset completo esplicito: dominio attivo + preferiti localStorage dell'utente corrente.
  function clearAll() {
    currentDomain.value = null
    for (const domain of DOMAINS) {
      const key = favoriteStorageKey(domain.key)
      if (key) local.remove(key)
    }
    favorites.value = {}
  }

  // Reset al logout: azzera lo stato in memoria preservando i preferiti
  // user-scoped in localStorage (verranno ricaricati al login successivo
  // dello stesso utente).
  function clearUserState() {
    currentDomain.value = null
    favorites.value = {}
    currentUserId.value = null
  }

  return {
    currentDomain,
    currentUserId,
    currentMenu,
    currentDomainConfig,
    setDomain,
    clearDomain,
    getDefaultRoute,
    addFavorite,
    removeFavorite,
    toggleFavorite,
    reorderFavorites,
    getDomainFavorites,
    getAllFavorites,
    isFavoriteOfDomain,
    setFavorite,
    clearFavorite,
    clearAll,
    syncUserFavorites,
    isFavorite,
    clearUserState
  }
}, {
  userScoped: true
})
