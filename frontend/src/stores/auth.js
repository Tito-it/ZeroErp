import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../core/api'
import { DOMAINS } from '../core/navigation'
import { local, STORAGE_KEYS } from '../core/storage'
import { useNavigationStore } from './navigation'
import { useTabsStore } from './tabs'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref(local.get(STORAGE_KEYS.ACCESS_TOKEN))
  const refreshToken = ref(local.get(STORAGE_KEYS.REFRESH_TOKEN))

  // Profilo utente caricato dall'endpoint /me/
  // Struttura JSONB: { utente, ruolo_sistema, risorse_umane, soggetto, emittente }
  const user = ref(null)

  const isAuthenticated = computed(() => !!accessToken.value)

  // Nome visualizzato: priorità soggetto.nome > utente.first_name > username
  const displayName = computed(() => {
    if (!user.value) return ''
    const soggetto = user.value.soggetto
    if (soggetto?.nome) {
      return [soggetto.nome, soggetto.cognome].filter(Boolean).join(' ')
    }
    const utente = user.value.utente
    if (utente?.first_name || utente?.last_name) {
      return [utente.first_name, utente.last_name].filter(Boolean).join(' ')
    }
    return utente?.username || ''
  })

  function setTokens(access, refresh) {
    accessToken.value = access
    refreshToken.value = refresh
    local.set(STORAGE_KEYS.ACCESS_TOKEN, access)
    local.set(STORAGE_KEYS.REFRESH_TOKEN, refresh)
  }

  function clearTokens() {
    accessToken.value = null
    refreshToken.value = null
    user.value = null
    local.remove(STORAGE_KEYS.ACCESS_TOKEN)
    local.remove(STORAGE_KEYS.REFRESH_TOKEN)
    useTabsStore().closeAll()
    useNavigationStore().clearAll()
  }

  async function fetchProfile() {
    try {
      const response = await api.get('/core/me/')
      user.value = response.data.data
      if (!user.value) {
        throw new Error('Profilo vuoto: risposta API senza dati utente')
      }
    } catch (err) {
      user.value = null
      throw err
    }
  }

  async function login(username, password) {
    const response = await api.post('/auth/token/', { username, password })
    setTokens(response.data.access, response.data.refresh)
    await fetchProfile()
  }

  async function tryRefreshToken() {
    if (!refreshToken.value) return false
    try {
      const response = await api.post('/auth/token/refresh/', {
        refresh: refreshToken.value
      })
      setTokens(response.data.access, refreshToken.value)
      return true
    } catch {
      clearTokens()
      return false
    }
  }

  async function logout() {
    // Invalida la sessione lato server prima di pulire i token
    if (refreshToken.value) {
      try {
        await api.post('/auth/logout/', { refresh: refreshToken.value })
      } catch {
        // Se il logout server fallisce, procedi comunque con la pulizia locale
      }
    }
    clearTokens()
  }

  // Domini visibili per l'utente corrente (filtra adminOnly in base a ruolo_sistema)
  const isAdmin = computed(() => user.value?.ruolo_sistema === 'ADMIN')

  const visibleDomains = computed(() => {
    return DOMAINS.filter(d => !d.adminOnly || isAdmin.value)
  })

  return {
    accessToken,
    refreshToken,
    user,
    isAuthenticated,
    isAdmin,
    displayName,
    visibleDomains,
    login,
    logout,
    tryRefreshToken,
    clearTokens,
    fetchProfile
  }
})
