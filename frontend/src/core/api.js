import axios from 'axios'
import router from '../router'
import { local, STORAGE_KEYS } from './storage'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Interceptor request — aggiunge il token JWT ad ogni chiamata
api.interceptors.request.use(config => {
  const token = local.get(STORAGE_KEYS.ACCESS_TOKEN)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Interceptor response — token refresh automatico + redirect login
let isRefreshing = false
let pendingRequests = []

function onRefreshSuccess(newToken) {
  pendingRequests.forEach(cb => cb(newToken))
  pendingRequests = []
}

function onRefreshFailure(err) {
  pendingRequests.forEach(cb => cb(null, err))
  pendingRequests = []
}

api.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config

    // Evita loop infinito sulle chiamate di refresh/login
    if (
      error.response?.status !== 401 ||
      originalRequest._retry ||
      originalRequest.url?.includes('/auth/token/')
    ) {
      return Promise.reject(error)
    }

    // Tenta il refresh del token
    const refreshToken = local.get(STORAGE_KEYS.REFRESH_TOKEN)
    if (!refreshToken) {
      redirectToLogin()
      return Promise.reject(error)
    }

    if (isRefreshing) {
      // Accoda la richiesta in attesa del refresh in corso
      return new Promise((resolve, reject) => {
        pendingRequests.push((newToken, err) => {
          if (err) return reject(err)
          originalRequest.headers.Authorization = `Bearer ${newToken}`
          resolve(api(originalRequest))
        })
      })
    }

    originalRequest._retry = true
    isRefreshing = true

    try {
      const response = await axios.post(
        `${api.defaults.baseURL}/auth/token/refresh/`,
        { refresh: refreshToken },
        { headers: { 'Content-Type': 'application/json' } }
      )
      const newToken = response.data.access
      local.set(STORAGE_KEYS.ACCESS_TOKEN, newToken)
      originalRequest.headers.Authorization = `Bearer ${newToken}`
      onRefreshSuccess(newToken)
      return api(originalRequest)
    } catch (refreshError) {
      onRefreshFailure(refreshError)
      redirectToLogin()
      return Promise.reject(refreshError)
    } finally {
      isRefreshing = false
    }
  }
)

function redirectToLogin() {
  local.remove(STORAGE_KEYS.ACCESS_TOKEN)
  local.remove(STORAGE_KEYS.REFRESH_TOKEN)
  // Usa il router per evitare page reload; preserva la rotta per redirect post-login
  const currentPath = router.currentRoute?.value?.fullPath
  router.push({
    name: 'login',
    query: currentPath && currentPath !== '/login' ? { redirect: currentPath } : {}
  })
}

export default api
