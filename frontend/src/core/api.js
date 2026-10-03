import axios from 'axios'
import { routerApp } from './routerApp'
import { local, STORAGE_KEYS } from './storage'
import { resolveCanaleLogin } from './constants'
import { MOTIVO_USCITA, azzeraAccess, getAccessToken, rinnovaCoordinato } from './sessione'
import i18n from './i18n'
import { extractApiErrorCode } from './utils/apiError'

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
  return config
})

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

// Scopo: chiude la sessione morta e porta al login.
//
// 🔴 IL PUNTO CHE MANCAVA, ed è la causa del difetto «resto sulla home vuota e
//    al login ci arrivo solo ricaricando» (rilievo di Tid, 2026-09-04).
//    Lo stato di autenticazione viveva in DUE posti: `localStorage` e i ref
//    dello store Pinia, che dal localStorage erano stati letti UNA volta sola
//    alla creazione. Qui si ripuliva **solo il localStorage**, quindi lo store
//    continuava a tenere in memoria i due token. (Dal 2026-09-28 i token non
//    stanno più in localStorage: l'access vive solo in `core/sessione`.)
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
// ⚠️ Se l'import fallisse, si ripiega sul solo azzeramento dell'access in
//    memoria: meglio una sessione mezza chiusa che un'eccezione dentro un
//    interceptor, che si mangerebbe anche il redirect.
// Esportata: la usa anche lo store `auth` quando un'altra scheda chiude la
// sessione (logout), per arrivare al login per la stessa strada, col suo
// motivo (`MOTIVO_USCITA` in `core/sessione`).
export async function redirectToLogin(motivo = MOTIVO_USCITA.SESSIONE_SCADUTA) {
  try {
    const { useAuthStore } = await import('../stores/auth')
    useAuthStore().clearTokens()
  } catch {
    azzeraAccess()
  }
  // NB: LOGIN_CHANNEL non viene rimosso — conserva la preferenza utente
  // per il prossimo login manuale (stesso pattern di `clearTokens`).
  // Usa il router per evitare page reload; preserva la rotta per redirect post-login.
  // `reason=<motivo>` viene letto da LoginView per mostrare un messaggio
  // esplicito invece di una pagina muta (UX: l'utente capisce perché è
  // uscito e non pensa a un bug).
  const rottaCorrente = routerApp().currentRoute?.value
  // ⚠️ Se si e' gia' sul login non si spinge una seconda navigazione: con piu'
  //    chiamate in volo che prendono 401 insieme, ognuna passerebbe di qui e
  //    vue-router respingerebbe le repliche come «navigazione ridondante» —
  //    promise rifiutate che nessuno raccoglie, cioe' rumore in console su un
  //    percorso che sta gia' funzionando.
  if (rottaCorrente?.name === 'login') return

  const currentPath = rottaCorrente?.fullPath
  const query = { reason: motivo }
  if (currentPath && currentPath !== '/login') {
    query.redirect = currentPath
  }
  // ⚠️ `catch` sul push: una navigazione respinta da un guard (o superata da
  //    un'altra) rifiuta la promise, e qui dentro nessuno la aspetta.
  return routerApp().push({ name: 'login', query }).catch(() => {})
}

// Scopo: il freno della credenziale scattato su una password chiesta DENTRO
//        la sessione (cambio password, configurazione del secondo fattore):
//        il backend ha chiuso questa sessione, e si va al login col motivo.
//        true se era questo il caso; il chiamante, altrimenti, mostra l'errore.
// ⚠️ Solo `E_UTENTE_BLOCCATO`: e' il solo freno che chiude la sessione
//    (`password_con_freno.py`). `E_LOGIN_ATTESA` rallenta e basta.
export function seSessioneChiusaDalFreno(err) {
  if (extractApiErrorCode(err) !== 'E_UTENTE_BLOCCATO') return false
  redirectToLogin(MOTIVO_USCITA.FRENO_PASSWORD)
  return true
}

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
// ⚠️ Import dinamico per la stessa ragione di `redirectToLogin` (ciclo api →
//    auth → api).
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
