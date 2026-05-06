import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../core/api'
import { DOMAINS } from '../core/navigation'
import { local, STORAGE_KEYS } from '../core/storage'
import {
  RUOLO_APPLICATIVO,
  LIVELLO_ACCESSO,
  CANALE_LOGIN,
  resolveCanaleLogin
} from '../core/constants'
import { resetAllUserScopedStores } from '../core/pinia-plugins/auto-reset'
import { syncUserLanguage } from '../core/i18n'
import { useUiStore } from './ui'
import { isJwtExpired } from '../core/jwt'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref(local.get(STORAGE_KEYS.ACCESS_TOKEN))
  const refreshToken = ref(local.get(STORAGE_KEYS.REFRESH_TOKEN))

  // §8.5.2: canale di login corrente. Restored da localStorage al boot
  // (sopravvive al page reload), default ADMIN per sessioni pre-multi-face
  // e per retrocompat. Determina quale endpoint `/{admin|portale|shop}/token/`
  // usare per login + refresh.
  const loginChannel = ref(
    local.get(STORAGE_KEYS.LOGIN_CHANNEL) || CANALE_LOGIN.ADMIN.key
  )

  // Profilo utente caricato dall'endpoint /me/
  // Struttura JSONB: { utente, is_super_admin, ruolo_applicativo,
  // risorse_umane, soggetto, emittente, permessi_area, azioni_abilitate,
  // deve_cambiare_password, is_admin_globale }
  const user = ref(null)

  // Flag cambio password obbligatorio (impostato al login se deve_cambiare_password = true)
  const passwordChangeRequired = ref(false)

  // Validita' temporale dei token (firma non verificata client-side).
  // Il leeway 5s evita race su clock skew browser/server al limite della
  // scadenza. Reattivi: cambiano automaticamente quando setTokens/clearTokens
  // aggiornano gli ref. Il computed `isAuthenticated` considera l'utente
  // operativo se almeno il refreshToken e' ancora valido (l'access scaduto
  // sara' rigenerato dal refresh proattivo nel router guard o dall'interceptor
  // 401 in api.js).
  const accessTokenValid = computed(() =>
    !!accessToken.value && !isJwtExpired(accessToken.value, 5_000)
  )
  const refreshTokenValid = computed(() =>
    !!refreshToken.value && !isJwtExpired(refreshToken.value, 5_000)
  )
  const isAuthenticated = computed(
    () => accessTokenValid.value || refreshTokenValid.value
  )

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

  // Scopo: Memorizza il canale di login scelto. Chiamato da `login()`;
  // separato per consentire test/debug di imposta canale senza fare login.
  function setLoginChannel(canaleKey) {
    const canale = resolveCanaleLogin(canaleKey)
    loginChannel.value = canale.key
    local.set(STORAGE_KEYS.LOGIN_CHANNEL, canale.key)
  }

  // Scopo: azzera lo stato auth di questo store (tokens + user + flag).
  //        Esposto come `clearUserState` (contratto autoReset plugin):
  //        il reset centralizzato al logout lo invoca durante l'iterazione
  //        degli store user-scoped. Non tocca gli altri store — di quelli
  //        si occupa il plugin iterando.
  //
  //        Il canale di login NON viene pulito: dopo il logout il
  //        LoginView riusa la stessa selezione (ADMIN/PORTALE/SHOP) e
  //        `setLoginChannel` lo sovrascrivera' al prossimo login.
  function clearAuthTokensOnly() {
    accessToken.value = null
    refreshToken.value = null
    user.value = null
    passwordChangeRequired.value = false
    local.remove(STORAGE_KEYS.ACCESS_TOKEN)
    local.remove(STORAGE_KEYS.REFRESH_TOKEN)
  }

  // Scopo: azzera lo stato utente completo dell'intera app.
  //        Unico punto di pulizia post-logout: delega a
  //        `resetAllUserScopedStores()` che itera tutti gli store
  //        marcati `userScoped: true` e chiama il loro `clearUserState`
  //        (o fallback $resetToInitial). Include auth stesso.
  //        Chiamato da `logout()` e dal flow 401/refresh-fallito.
  function clearTokens() {
    resetAllUserScopedStores()
  }

  async function fetchProfile() {
    try {
      const response = await api.get('/core/me/')
      user.value = response.data.data
      if (!user.value) {
        throw new Error('Profilo vuoto: risposta API senza dati utente')
      }
      // Applica preferenze personali dell'utente (tema + lingua UI).
      // Chiavi localStorage user-scoped: evita che la scelta di un altro
      // utente sullo stesso browser persista al login successivo.
      const uid = user.value.utente?.id ?? null
      if (uid != null) {
        useUiStore().syncUserPreferences(uid)
        syncUserLanguage(uid)
      }
    } catch (err) {
      user.value = null
      throw err
    }
  }

  // Scopo: Login multi-canale (§8.5.2). `canaleKey` opzionale per retrocompat:
  // se omesso, usa la key gia' salvata (default ADMIN). Il canale determina
  // quale endpoint token chiamare (`/admin/token/` | `/portale/token/` |
  // `/shop/token/`) e viene persistito per il successivo refresh.
  async function login(username, password, canaleKey) {
    if (canaleKey) {
      setLoginChannel(canaleKey)
    }
    const canale = resolveCanaleLogin(loginChannel.value)
    const response = await api.post(canale.tokenPath, { username, password })
    setTokens(response.data.access, response.data.refresh)
    // Controlla flag cambio password dal backend
    passwordChangeRequired.value = !!response.data.password_change_required
    try {
      await fetchProfile()
    } catch (err) {
      clearTokens()
      throw err
    }
  }

  async function tryRefreshToken() {
    if (!refreshToken.value) return false
    try {
      // Il refresh usa il canale correntemente salvato: stesso namespace
      // del login originale. Coerente con il guard cross-namespace del BE
      // (`AuditTokenRefreshView`, §8.3.5) che rifiuta refresh di veste
      // incompatibile col path.
      const canale = resolveCanaleLogin(loginChannel.value)
      const response = await api.post(canale.refreshPath, {
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

  // Multi-face auth Stage B: i nuovi campi nativi di /me/.
  // - isSuperAdmin: true se l'utente ha binding al profilo SUPER_ADMIN
  //   (profilo id 9100). Sostituisce il legacy `isAdmin` mantenuto come
  //   alias per retrocompat.
  // - ruoloApplicativo: categoria dell'identita' attiva
  //   (OPERATORE | CLIENTE_PORTALE | FORNITORE_PORTALE | SHOP_CUSTOMER |
  //    API_CLIENT | DISABILITATO | null).
  const isSuperAdmin = computed(() => user.value?.is_super_admin === true)
  const ruoloApplicativo = computed(() => user.value?.ruolo_applicativo || null)

  // §8.5.3: id dell'identita attiva del JWT corrente. Post-§8.3.6 il /me/
  // espone il blocco `identita` con la veste risolta dal claim. Consumer:
  // FE che devono passare `identita_id` a endpoint che ne hanno bisogno
  // (es. flussi cross-veste in PR-C), o mostrare la veste corrente in UI.
  const identitaId = computed(() => user.value?.identita?.id || null)

  // Alias legacy. Nuovi consumer usino isSuperAdmin direttamente.
  const isAdmin = isSuperAdmin

  // Helpers ortogonali per namespace multi-face. Utili per router guard,
  // navigazione condizionale e feature flag lato UI.
  const isOperatoreInterno = computed(
    () => ruoloApplicativo.value === RUOLO_APPLICATIVO.OPERATORE
  )
  const isClientePortale = computed(
    () => ruoloApplicativo.value === RUOLO_APPLICATIVO.CLIENTE_PORTALE
  )
  const isFornitorePortale = computed(
    () => ruoloApplicativo.value === RUOLO_APPLICATIVO.FORNITORE_PORTALE
  )
  const isShopCustomer = computed(
    () => ruoloApplicativo.value === RUOLO_APPLICATIVO.SHOP_CUSTOMER
  )

  // Refactor operatore-emittenti (Q1): admin globale = ADMIN senza riga
  // in user_emittenti_fiscali. Il flag e' calcolato lato backend dalla
  // /core/me/ view. Per operatori e' sempre false.
  const isAdminGlobale = computed(() => !!user.value?.is_admin_globale)

  // Refactor operatore-emittenti: emittente fiscale 1-a-1 dell'utente
  // corrente. Per admin globale ritorna null perche' il blocco `emittente`
  // del profilo riflette il "gestore globale" (cascata fallback di
  // fn_get_user_profile) e NON l'emittente personale dell'utente.
  //
  // Esposte DUE chiavi FK distinte perche' il modello le differenzia:
  //   - id                → anagrafiche.emittenti_fiscali.id (PK reale, usato
  //     ad es. da pratiche.emittente_fiscale_id)
  //   - soggettoRuoloId   → anagrafiche.soggetti_ruoli.id (usato ad es. da
  //     vendite.listini.emittente_soggetto_ruolo_id)
  // La differenza non e' ovvia dal nome e va rispettata. Vedi
  // feedback_emittente_pk_vs_soggetto_ruolo.md.
  const emittenteCorrente = computed(() => {
    if (isAdminGlobale.value) return null
    const ef = user.value?.emittente
    if (!ef) return null
    return {
      id: ef.emittente_fiscale_id ?? null,
      // Il blocco `emittente` e' il merge tra i campi `emittente_*` e l'output
      // di fn_get_soggetto_dati_by_ruolo, che espone il ruolo come
      // `soggetto_ruolo_id` (senza prefisso). E' la PK verso soggetti_ruoli.
      soggettoRuoloId: ef.soggetto_ruolo_id ?? null,
      codice: ef.emittente_codice ?? null,
      ragioneSociale: ef.ragione_sociale_completa ?? ef.emittente_descrizione ?? null,
    }
  })

  // Scopo: Domini visibili. Filtri applicati:
  //   - adminOnly: solo SUPER_ADMIN (es. Amm. Software).
  //   - non adminOnly: solo operatori interni (OPERATORE). I portali e lo
  //     shop hanno namespace dedicati /portale/ e /shop/ e non vedono i
  //     domini operativi.
  //   - BLOCCATO: nascosto a tutti (tranne SUPER_ADMIN via bypass DB).
  // I domini adminOnly hanno il loro guard — non applicare il check livello.
  const visibleDomains = computed(() => {
    return DOMAINS.filter(d => {
      if (d.adminOnly) return isSuperAdmin.value
      if (!isOperatoreInterno.value) return false
      if (d.schemaDb && isAreaBlocked(d.schemaDb)) return false
      return true
    })
  })

  // Mappa permessi area: { anagrafiche: 'TUTTO', vendite: 'LETTURA', ... }
  // Popolata da /me/ campo permessi_area (fn_get_user_permissions_map)
  const permessiArea = computed(() => user.value?.permessi_area || {})

  // Livello accesso per area funzionale (TUTTO | LETTURA | BLOCCATO).
  // SUPER_ADMIN ha bypass totale su tutte le aree (pattern identico a isActionAllowed).
  function getLivelloArea(schemaDb) {
    if (isSuperAdmin.value) return LIVELLO_ACCESSO.TUTTO
    return permessiArea.value[schemaDb] || LIVELLO_ACCESSO.BLOCCATO
  }

  // Scopo: Area in sola lettura? (livello LETTURA)
  function isAreaReadonly(schemaDb) {
    return getLivelloArea(schemaDb) === LIVELLO_ACCESSO.LETTURA
  }

  // Scopo: Area bloccata? (livello BLOCCATO — nessun accesso)
  function isAreaBlocked(schemaDb) {
    return getLivelloArea(schemaDb) === LIVELLO_ACCESSO.BLOCCATO
  }

  // Mappa override oggetto: { 'anagrafiche.conto_bancario': 'BLOCCATO', ... }
  // Popolata da /me/ campo permessi_oggetto (fn_get_user_object_permissions_map)
  const permessiOggetto = computed(() => user.value?.permessi_oggetto || {})

  // Scopo: Livello accesso per singolo model (override oggetto con fallback area).
  function getLivelloOggetto(schemaDb, modelName) {
    const key = `${schemaDb}.${modelName}`
    if (permessiOggetto.value[key]) return permessiOggetto.value[key]
    return getLivelloArea(schemaDb)
  }

  // Scopo: Model in sola lettura? (override LETTURA o fallback area LETTURA)
  function isObjectReadonly(schemaDb, modelName) {
    return getLivelloOggetto(schemaDb, modelName) === LIVELLO_ACCESSO.LETTURA
  }

  // Scopo: Model bloccato? (override BLOCCATO o fallback area BLOCCATO)
  function isObjectBlocked(schemaDb, modelName) {
    return getLivelloOggetto(schemaDb, modelName) === LIVELLO_ACCESSO.BLOCCATO
  }

  // Mappa azioni abilitate: { genera_fatture_lotti: true, reset_lotto_draft: false, ... }
  // Popolata da /me/ campo azioni_abilitate (fn_get_user_actions_map)
  const azioniAbilitate = computed(() => user.value?.azioni_abilitate || {})

  // Scopo: Azione di processo abilitata? SUPER_ADMIN ha bypass totale, default false.
  function isActionAllowed(codename) {
    if (isSuperAdmin.value) return true
    return azioniAbilitate.value[codename] === true
  }

  // Scopo: Getter per determinare se l'operatore deve cambiare password.
  const mustChangePassword = computed(() =>
    passwordChangeRequired.value || !!user.value?.deve_cambiare_password
  )

  return {
    accessToken,
    refreshToken,
    user,
    isAuthenticated,
    accessTokenValid,
    refreshTokenValid,
    isSuperAdmin,
    isAdmin,  // alias legacy di isSuperAdmin
    ruoloApplicativo,
    identitaId,
    isOperatoreInterno,
    isClientePortale,
    isFornitorePortale,
    isShopCustomer,
    isAdminGlobale,
    emittenteCorrente,
    mustChangePassword,
    passwordChangeRequired,
    displayName,
    visibleDomains,
    permessiArea,
    getLivelloArea,
    isAreaReadonly,
    isAreaBlocked,
    permessiOggetto,
    getLivelloOggetto,
    isObjectReadonly,
    isObjectBlocked,
    azioniAbilitate,
    isActionAllowed,
    setTokens,
    loginChannel,
    setLoginChannel,
    login,
    logout,
    tryRefreshToken,
    clearTokens,
    fetchProfile,
    // Contratto plugin autoReset: clearUserState e` la primitiva che il
    // reset centralizzato chiama sullo store auth. Delega alla pulizia
    // tokens-only (no ricorsione su resetAllUserScopedStores, che e' il
    // chiamante). Equivalente al vecchio clearTokens pre-refactor.
    clearUserState: clearAuthTokensOnly
  }
}, {
  userScoped: true
})
