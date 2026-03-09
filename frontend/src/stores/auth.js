import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../core/api'

const TOKEN_KEY = 'access_token'
const REFRESH_KEY = 'refresh_token'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref(localStorage.getItem(TOKEN_KEY) || null)
  const refreshToken = ref(localStorage.getItem(REFRESH_KEY) || null)

  // Profilo utente caricato dall'endpoint /me/
  // Struttura attesa: { username, first_name, last_name, emittente: { id, codice, descrizione } }
  const user = ref(null)

  const isAuthenticated = computed(() => !!accessToken.value)

  const displayName = computed(() => {
    if (!user.value) return ''
    const { first_name, last_name, username } = user.value
    if (first_name || last_name) {
      return [first_name, last_name].filter(Boolean).join(' ')
    }
    return username || ''
  })

  function setTokens(access, refresh) {
    accessToken.value = access
    refreshToken.value = refresh
    localStorage.setItem(TOKEN_KEY, access)
    localStorage.setItem(REFRESH_KEY, refresh)
  }

  function clearTokens() {
    accessToken.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_KEY)
  }

  async function fetchProfile() {
    try {
      const response = await api.get('/core/me/')
      user.value = response.data.data
    } catch {
      // Endpoint non ancora disponibile — nessun errore visibile
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

  function logout() {
    clearTokens()
  }

  return {
    accessToken,
    refreshToken,
    user,
    isAuthenticated,
    displayName,
    login,
    logout,
    tryRefreshToken,
    clearTokens,
    fetchProfile
  }
})
