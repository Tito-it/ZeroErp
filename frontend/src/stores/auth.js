import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../core/api'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref(localStorage.getItem('access_token') || null)
  const refreshToken = ref(localStorage.getItem('refresh_token') || null)
  const user = ref(null)

  const isAuthenticated = computed(() => !!accessToken.value)

  async function login(username, password) {
    const response = await api.post('/token/', { username, password })
    accessToken.value = response.data.access
    refreshToken.value = response.data.refresh
    localStorage.setItem('access_token', accessToken.value)
    localStorage.setItem('refresh_token', refreshToken.value)
  }

  function logout() {
    accessToken.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  return { accessToken, refreshToken, user, isAuthenticated, login, logout }
})
