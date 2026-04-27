import axios from 'axios'
import router from '../router'
import { local, STORAGE_KEYS } from './storage'
import { resolveCanaleLogin } from './constants'
import i18n from './i18n'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Interceptor request — aggiunge il token JWT e la lingua UI corrente
api.interceptors.request.use(config => {
  const token = local.get(STORAGE_KEYS.ACCESS_TOKEN)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  // Propaga la lingua corrente come Accept-Language standard HTTP.
  // Il middleware BE UserLanguageMiddleware legge questo header per
  // settare la GUC `myapp.user_language`; fallback DB 'it'.
  const locale = i18n?.global?.locale?.value
  if (locale) {
    config.headers['Accept-Language'] = locale
  }
  return config
})

// Interceptor response — token refresh automatico + redirect login
// Esclude login/refresh per admin|portale|shop: un 401 su queste rotte
// NON deve riprovare un refresh (loop). Lista estensibile in un unico posto.
const TOKEN_ENDPOINTS_RE = /\/(admin|portale|shop)\/token\//
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
      TOKEN_ENDPOINTS_RE.test(originalRequest.url ?? '')
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
      // §8.5.2: endpoint refresh risolto dinamicamente dal canale salvato.
      // La store `auth` persiste `LOGIN_CHANNEL`; qui lo leggiamo da storage
      // per evitare la dipendenza circolare api → store → api.
      // Fallback ADMIN per sessioni pre-multi-face senza key persistita.
      const canale = resolveCanaleLogin(local.get(STORAGE_KEYS.LOGIN_CHANNEL))
      const response = await axios.post(
        `${api.defaults.baseURL}${canale.refreshPath}`,
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
  // NB: LOGIN_CHANNEL non viene rimosso — conserva la preferenza utente
  // per il prossimo login manuale (stesso pattern di `clearTokens`).
  // Usa il router per evitare page reload; preserva la rotta per redirect post-login
  const currentPath = router.currentRoute?.value?.fullPath
  router.push({
    name: 'login',
    query: currentPath && currentPath !== '/login' ? { redirect: currentPath } : {}
  })
}

export default api
