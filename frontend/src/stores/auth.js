import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../core/api'

const TOKEN_KEY = 'access_token'
const REFRESH_KEY = 'refresh_token'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref(localStorage.getItem(TOKEN_KEY) || null)
  const refreshToken = ref(localStorage.getItem(REFRESH_KEY) || null)
  const user = ref(null)

  const isAuthenticated = computed(() => !!accessToken.value)

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

  async function login(username, password) {
    const response = await api.post('/auth/token/', { username, password })
    setTokens(response.data.access, response.data.refresh)
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
    login,
    logout,
    tryRefreshToken,
    clearTokens
  }
})
