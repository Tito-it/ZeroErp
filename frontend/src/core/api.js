import axios from 'axios'
import { routerApp } from './routerApp'
import { local, STORAGE_KEYS } from './storage'
import { resolveCanaleLogin } from './constants'
import { getAccessToken, rinnovaCoordinato } from './sessione'
import { redirectToLogin } from './uscitaSessione'
import i18n from './i18n'
import { extractApiErrorCode } from './utils/apiError'
import { generateIdempotencyKey } from './utils/idempotency'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// L'header che il backend pretende sul rinnovo, autenticato dal solo cookie:
// un form o un link di un altro sito non può mandarlo (anti-CSRF). Il nome e
// il valore sono quelli di `apps/core/api/refresh_cookie.py`; li confronta
// `test_auth_views.test_nome_cookie_e_header_uguali_nei_tre_linguaggi`.
const ANTI_CSRF_HEADER = 'X-Requested-With'
const ANTI_CSRF_VALORE = 'XMLHttpRequest'

// Interceptor request — aggiunge il token JWT (in memoria, `core/sessione`) e
// la lingua UI corrente
api.interceptors.request.use(config => {
  const token = getAccessToken()
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
  applicaIdempotencyKey(config)
  return config
})

// Scopo: ⭐ L'`Idempotency-Key` su ogni chiamata che scrive, in un punto solo
//        (decisione di Tid del 2026-10-20, brief-be-verifica-documentazione-api
//        §A5). Il backend la pretende su ogni POST che scrive
//        (`_ApiViewBase.initial`), e alcuni endpoint anche su PATCH/PUT/DELETE:
//        la si mette su tutti e quattro i metodi, dove non serve e' ignorata.
// Note: ⛔ Una key per CHIAMATA, la stessa granularita' delle 69 copie di
//       `generateIdempotencyKey()` che sostituisce (regola del 2, ok di Tid): il
//       rinnovo dopo un 401 rimanda la stessa `config`, quindi la stessa key.
//       ⚠️ Una key gia' presente vince: chi la genera di proposito (una per
//       GESTO, riusata nei reinvii) la passa negli header e resta sua — e' il
//       mestiere di `useChiaveGesto`, per i gesti irreversibili che un
//       timeout non deve far eseguire due volte.
const METODI_CHE_SCRIVONO = new Set(['post', 'put', 'patch', 'delete'])

export function applicaIdempotencyKey(config) {
  if (!METODI_CHE_SCRIVONO.has((config.method || 'get').toLowerCase())) return config
  const headers = config.headers || {}
  const presente = typeof headers.has === 'function'
    ? headers.has('Idempotency-Key')
    : Object.keys(headers).some(k => k.toLowerCase() === 'idempotency-key')
  if (!presente) {
    if (typeof headers.set === 'function') headers.set('Idempotency-Key', generateIdempotencyKey())
    else headers['Idempotency-Key'] = generateIdempotencyKey()
  }
  config.headers = headers
  return config
}

// Scopo: rinnova l'access dal cookie HttpOnly del refresh (brief sicurezza
//        §2, dal 2026-09-28). Il corpo è vuoto: il browser manda il cookie da
//        solo (stesso origin), e il backend risponde col solo `access`, dopo
//        aver ruotato il refresh nel cookie. QUANDO chiamarlo — una volta per
//        scheda, una scheda alla volta — lo decide `rinnovaCoordinato`.
//        L'endpoint è quello del canale di login (`LOGIN_CHANNEL`, che resta
//        in localStorage: non è un segreto).
export function rinnovaAccess() {
  return rinnovaCoordinato(async () => {
    const canale = resolveCanaleLogin(local.get(STORAGE_KEYS.LOGIN_CHANNEL))
    const response = await api.post(canale.refreshPath, null, {
      headers: { [ANTI_CSRF_HEADER]: ANTI_CSRF_VALORE }
    })
    return response.data.access
  })
}

// Interceptor response — token refresh automatico + redirect login
// Esclude login/refresh per admin|portale|shop: un 401 su queste rotte
// NON deve riprovare un refresh (loop). Lista estensibile in un unico posto.
const TOKEN_ENDPOINTS_RE = /\/(admin|portale|shop)\/token\//

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

    if (CODICI_OBBLIGO_PENDENTE.has(extractApiErrorCode(error))) {
      await portaAllObbligo()
      return Promise.reject(error)
    }

    // Evita loop infinito sulle chiamate di refresh/login
    if (!nonAutorizzato || originalRequest?._retry || rottaDiToken) {
      return Promise.reject(error)
    }

    // Rinnova e riprova. Le richieste che prendono 401 insieme aspettano la
    // STESSA promise di rinnovo (`rinnovaCoordinato`): la vecchia coda
    // `pendingRequests` era questo, scritto a mano.
    originalRequest._retry = true
    try {
      const nuovo = await rinnovaAccess()
      originalRequest.headers.Authorization = `Bearer ${nuovo}`
      return api(originalRequest)
    } catch (refreshError) {
      await redirectToLogin()
      return Promise.reject(refreshError)
    }
  }
)

// L'uscita dalla sessione (`redirectToLogin`, `seSessioneChiusaDalFreno`) vive
// in `core/uscitaSessione.js`: non e' trasporto, e chi la chiama — una vista —
// non deve avere in mano il client (guard `check-api-componenti`).

// I 403 del cancello degli obblighi del backend (`apps/core/api/cancello_obblighi.py`):
// la credenziale ha un obbligo da chiudere prima di ogni altra richiesta.
const CODICI_OBBLIGO_PENDENTE = new Set(['E_CAMBIO_PASSWORD_RICHIESTO', 'E_TOTP_CONFIGURAZIONE_RICHIESTA'])

// Le pagine che chiudono un obbligo: da lì un 403 del cancello non riporta
// altrove (ci si è già).
const ROTTE_DEGLI_OBBLIGHI = new Set(['change-password', 'sicurezza'])

let portaAllObbligoInCorso = null

// Scopo: un obbligo nato A SESSIONE APERTA — l'amministratore accende
//        l'obbligo o spegne il device, un reparto passa a «richiede il secondo
//        fattore», il secondo fattore spento da un'altra scheda. Il profilo
//        letto al login non lo sa, e senza questo ogni chiamata rispondeva 403
//        finché non si ricaricava la pagina. Si rilegge il profilo e si rifà la
//        navigazione corrente: è il guard del router a scegliere la pagina
//        (una regola sola, quella di `obblighi_pendenti`).
// ⚠️ Una sola volta per volta: con più chiamate in volo che prendono il 403
//    insieme, aspettano tutte la stessa promise.
// ⚠️ Import dinamico: `stores/auth` importa `api`, e un import statico
//    chiuderebbe il ciclo api → auth → api.
function portaAllObbligo() {
  if (!portaAllObbligoInCorso) {
    portaAllObbligoInCorso = (async () => {
      const rottaCorrente = routerApp().currentRoute?.value
      if (ROTTE_DEGLI_OBBLIGHI.has(rottaCorrente?.name)) return
      try {
        const { useAuthStore } = await import('../stores/auth')
        await useAuthStore().fetchProfile()
      } catch {
        return
      }
      // `force`: la stessa rotta, rinavigata perché il guard la rivaluti.
      await routerApp().push({ path: rottaCorrente?.fullPath ?? '/', force: true }).catch(() => {})
    })().finally(() => {
      portaAllObbligoInCorso = null
    })
  }
  return portaAllObbligoInCorso
}

export default api
