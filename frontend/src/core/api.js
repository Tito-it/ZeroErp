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

    const nonAutorizzato = error.response?.status === 401
    const rottaDiToken = TOKEN_ENDPOINTS_RE.test(originalRequest?.url ?? '')

    // ⛔ Un 401 su una richiesta GIA' RITENTATA non è «niente da fare»: vuol
    //    dire che il token appena rinfrescato è stato rifiutato lo stesso —
    //    sessione revocata, identità disattivata, veste cambiata. Fino al
    //    2026-09-04 si usciva di qui con un `reject` e basta: l'operatore
    //    restava sulla pagina, ogni gesto rispondeva «utente non connesso» e
    //    al login non ci arrivava nessuno. Ora si va al login come per il
    //    refresh fallito: il caso è lo stesso, cambia solo da dove si scopre.
    // ⚠️ Le rotte di token restano fuori: là un 401 è «credenziali sbagliate»
    //    e si è già sulla pagina di login.
    if (nonAutorizzato && originalRequest?._retry && !rottaDiToken) {
      await redirectToLogin()
      return Promise.reject(error)
    }

    // Evita loop infinito sulle chiamate di refresh/login
    if (!nonAutorizzato || originalRequest?._retry || rottaDiToken) {
      return Promise.reject(error)
    }

    // Tenta il refresh del token
    const refreshToken = local.get(STORAGE_KEYS.REFRESH_TOKEN)
    if (!refreshToken) {
      await redirectToLogin()
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
      await redirectToLogin()
      return Promise.reject(refreshError)
    } finally {
      isRefreshing = false
    }
  }
)

// Scopo: chiude la sessione morta e porta al login.
//
// 🔴 IL PUNTO CHE MANCAVA, ed è la causa del difetto «resto sulla home vuota e
//    al login ci arrivo solo ricaricando» (rilievo di Tid, 2026-09-04).
//    Lo stato di autenticazione vive in DUE posti: `localStorage` e i ref dello
//    store Pinia, che dal localStorage sono stati letti UNA volta sola alla
//    creazione. Qui si ripuliva **solo il localStorage**, quindi lo store
//    continuava a tenere in memoria i due token.
//    ⇒ `isAuthenticated` (che li legge dalla memoria e guarda solo la loro
//    SCADENZA) restava **vero**: una sessione uccisa dal server — refresh
//    blacklistato, identità revocata — ha token non ancora scaduti per data.
//    ⇒ Il `router.push` qui sotto finiva sul guard `if (to.name === 'login' &&
//    auth.isAuthenticated) return { name: 'home' }` e veniva **rimandato alla
//    home**. Da lì ogni chiamata rispondeva 401 e il login era irraggiungibile;
//    solo un ricarico — che rilegge il localStorage ormai vuoto — lo sbloccava.
// ⇒ Si azzera lo stato DOVE VIVE: `clearTokens()` dello store, che pulisce i
//    ref, il localStorage e gli store user-scoped (niente dati del vecchio
//    utente in memoria). Il localStorage lo tocca lui, non più questa funzione.
//
// ⚠️ Import DINAMICO, e non è un vezzo: `stores/auth` importa `api`, quindi un
//    import statico chiuderebbe il ciclo api → auth → api. Qui il modulo serve
//    solo a runtime, quando entrambi sono già valutati.
// ⚠️ Se l'import fallisse, si ripiega sulla vecchia pulizia del solo
//    localStorage: meglio una sessione mezza chiusa che un'eccezione dentro un
//    interceptor, che si mangerebbe anche il redirect.
async function redirectToLogin() {
  try {
    const { useAuthStore } = await import('../stores/auth')
    useAuthStore().clearTokens()
  } catch {
    local.remove(STORAGE_KEYS.ACCESS_TOKEN)
    local.remove(STORAGE_KEYS.REFRESH_TOKEN)
  }
  // NB: LOGIN_CHANNEL non viene rimosso — conserva la preferenza utente
  // per il prossimo login manuale (stesso pattern di `clearTokens`).
  // Usa il router per evitare page reload; preserva la rotta per redirect post-login.
  // `reason=session_expired` viene letto da LoginView per mostrare un messaggio
  // esplicito invece di una pagina muta (UX: l'utente capisce che e' caduta
  // la sessione e non sta avendo un bug).
  const rottaCorrente = router.currentRoute?.value
  // ⚠️ Se si e' gia' sul login non si spinge una seconda navigazione: con piu'
  //    chiamate in volo che prendono 401 insieme, ognuna passerebbe di qui e
  //    vue-router respingerebbe le repliche come «navigazione ridondante» —
  //    promise rifiutate che nessuno raccoglie, cioe' rumore in console su un
  //    percorso che sta gia' funzionando.
  if (rottaCorrente?.name === 'login') return

  const currentPath = rottaCorrente?.fullPath
  const query = { reason: 'session_expired' }
  if (currentPath && currentPath !== '/login') {
    query.redirect = currentPath
  }
  // ⚠️ `catch` sul push: una navigazione respinta da un guard (o superata da
  //    un'altra) rifiuta la promise, e qui dentro nessuno la aspetta.
  return router.push({ name: 'login', query }).catch(() => {})
}

export default api
