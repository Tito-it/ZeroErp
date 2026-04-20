import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../core/api'
import { DOMAINS } from '../core/navigation'
import { local, STORAGE_KEYS } from '../core/storage'
import { RUOLO_APPLICATIVO, LIVELLO_ACCESSO } from '../core/constants'
import { useNavigationStore } from './navigation'
import { useTabsStore } from './tabs'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref(local.get(STORAGE_KEYS.ACCESS_TOKEN))
  const refreshToken = ref(local.get(STORAGE_KEYS.REFRESH_TOKEN))

  // Profilo utente caricato dall'endpoint /me/
  // Struttura JSONB: { utente, is_super_admin, ruolo_applicativo, ruolo_sistema (legacy),
  // risorse_umane, soggetto, emittente, permessi_area, azioni_abilitate,
  // deve_cambiare_password, is_admin_globale }
  const user = ref(null)

  // Flag cambio password obbligatorio (impostato al login se deve_cambiare_password = true)
  const passwordChangeRequired = ref(false)

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
    passwordChangeRequired.value = false
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
    const response = await api.post('/admin/token/', { username, password })
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
      const response = await api.post('/admin/token/refresh/', {
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

  // Livello accesso per area funzionale (TUTTO | LETTURA | BLOCCATO)
  function getLivelloArea(schemaDb) {
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
    isSuperAdmin,
    isAdmin,  // alias legacy di isSuperAdmin
    ruoloApplicativo,
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
    login,
    logout,
    tryRefreshToken,
    clearTokens,
    fetchProfile
  }
})
