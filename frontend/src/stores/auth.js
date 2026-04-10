import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../core/api'
import { DOMAINS } from '../core/navigation'
import { local, STORAGE_KEYS } from '../core/storage'
import { RUOLO_SISTEMA, LIVELLO_ACCESSO } from '../core/constants'
import { useNavigationStore } from './navigation'
import { useTabsStore } from './tabs'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref(local.get(STORAGE_KEYS.ACCESS_TOKEN))
  const refreshToken = ref(local.get(STORAGE_KEYS.REFRESH_TOKEN))

  // Profilo utente caricato dall'endpoint /me/
  // Struttura JSONB: { utente, ruolo_sistema, risorse_umane, soggetto, emittente, permessi_area, azioni_abilitate, deve_cambiare_password }
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
    const response = await api.post('/auth/token/', { username, password })
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

  // Domini visibili per l'utente corrente (filtra adminOnly in base a ruolo_sistema)
  const isAdmin = computed(() => user.value?.ruolo_sistema === RUOLO_SISTEMA.ADMIN)

  // Refactor operatore-emittenti (Q1): admin globale = ADMIN senza riga
  // in user_emittenti_fiscali. Il flag e' calcolato lato backend dalla
  // /core/me/ view. Per operatori e' sempre false.
  const isAdminGlobale = computed(() => !!user.value?.is_admin_globale)

  // Refactor operatore-emittenti: emittente fiscale 1-a-1 dell'utente
  // corrente. Per admin globale ritorna null perche' il blocco `emittente`
  // del profilo riflette il "gestore globale" (cascata fallback di
  // fn_get_user_profile) e NON l'emittente personale dell'utente.
  // Ritorna { id, codice, ragioneSociale } o null.
  const emittenteCorrente = computed(() => {
    if (isAdminGlobale.value) return null
    const ef = user.value?.emittente
    if (!ef) return null
    return {
      id: ef.emittente_fiscale_id ?? null,
      codice: ef.emittente_codice ?? null,
      ragioneSociale: ef.ragione_sociale_completa ?? ef.emittente_descrizione ?? null,
    }
  })

  // Scopo: Domini visibili: nasconde adminOnly per non-admin e BLOCCATO per tutti.
  // I domini adminOnly hanno gia' il loro guard — non applicare il check livello.
  const visibleDomains = computed(() => {
    return DOMAINS.filter(d => {
      if (d.adminOnly) return isAdmin.value
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

  // Scopo: Azione di processo abilitata? ADMIN ha tutto, default false.
  function isActionAllowed(codename) {
    if (isAdmin.value) return true
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
    isAdmin,
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
