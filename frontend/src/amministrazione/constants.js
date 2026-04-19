// Scopo: costanti e helper del modulo Amm. Software.
// Enum: re-export da core/constants (fonte unica di verita').
// Builder opzioni per Select centralizzati (zero duplicazione).

// Re-export enum da core — usati anche da stores/auth.js e test.
export { RUOLO_SISTEMA, LIVELLO_ACCESSO } from '../core/constants'
import { RUOLO_SISTEMA, LIVELLO_ACCESSO } from '../core/constants'

// --- Tipo ruolo per SoggettoResolver ---
export const TIPO_RUOLO_CODICE = {
  RIS_UMANA: 'RIS_UMANA'
}

// Scopo: Costruisce le opzioni ruolo LEGACY per Select.
// Usato ancora da PermessiRiepilogoView (legacy). Nuovi consumer operatori
// usino buildFilterSuperAdminOptions + buildFilterStatoOptions.
// includeAll: aggiunge "Tutti" (per filtri lista) e "Disabilitato".
export function buildRuoloOptions(t, { includeAll = false } = {}) {
  const opts = [
    { label: t('amm.ruolo_admin'), value: RUOLO_SISTEMA.ADMIN },
    { label: t('amm.ruolo_operativo'), value: RUOLO_SISTEMA.OPERATIVO }
  ]
  if (includeAll) {
    opts.unshift({ label: t('amm.ruolo_all'), value: null })
    opts.push({ label: t('amm.ruolo_disabilitato'), value: RUOLO_SISTEMA.DISABILITATO })
  }
  return opts
}

// Scopo: Opzioni filtro SUPER_ADMIN per toolbar lista operatori.
// Valori tri-state: null = tutti, true = solo SUPER_ADMIN, false = escludi.
// Il BE accetta il param is_super_admin come bool opzionale.
export function buildFilterSuperAdminOptions(t) {
  return [
    { label: t('amm.filter_super_admin_tutti'), value: null },
    { label: t('amm.filter_super_admin_si'), value: true },
    { label: t('amm.filter_super_admin_no'), value: false }
  ]
}

// Scopo: Opzioni filtro stato operatore per toolbar. Tri-state
// null/true/false mappato direttamente su is_active del BE.
export function buildFilterStatoOptions(t) {
  return [
    { label: t('amm.stato_all'), value: null },
    { label: t('amm.stato_attivo'), value: true },
    { label: t('amm.stato_inattivo'), value: false }
  ]
}

// Scopo: Costruisce le opzioni livello accesso per Select.
export function buildLivelloOptions(t) {
  return [
    { label: t('amm.livello_tutto'), value: LIVELLO_ACCESSO.TUTTO },
    { label: t('amm.livello_lettura'), value: LIVELLO_ACCESSO.LETTURA },
    { label: t('amm.livello_bloccato'), value: LIVELLO_ACCESSO.BLOCCATO }
  ]
}

// Scopo: Costruisce le opzioni tipo tabella audit per Select filtro.
export function buildAuditTabellaOptions(t) {
  return [
    { label: t('amm.audit_tabella_tutti'), value: null },
    { label: t('amm.audit_tabella_override_aree'), value: 'user_override_aree' },
    { label: t('amm.audit_tabella_override_azioni'), value: 'user_override_azioni' },
    { label: t('amm.audit_tabella_emittenti'), value: 'user_emittenti_fiscali' },
    { label: t('amm.audit_tabella_ruolo'), value: 'risorse_umane_auth_user' },
    { label: t('amm.audit_tabella_profilo_aree'), value: 'profili_reparto_aree' },
    { label: t('amm.audit_tabella_profilo_azioni'), value: 'profili_reparto_azioni' }
  ]
}

// --- Arrotondamento importi ---
// Valori allineati al CHECK constraint DB (anagrafiche.emittenti_fiscali_utilities
// e anagrafiche.emittenti_fiscali.rounding_policy):
//   IN ('UP','DOWN','HALF_UP','HALF_DOWN')
// Le label sono codici tecnici (no traduzione: identificano l'algoritmo IEEE).
export const ROUNDING_METHODS = [
  { label: 'HALF_UP', value: 'HALF_UP' },
  { label: 'HALF_DOWN', value: 'HALF_DOWN' },
  { label: 'UP', value: 'UP' },
  { label: 'DOWN', value: 'DOWN' }
]

// Lista flat dei codici, comoda quando serve solo l'enum (es. <Select :options>).
export const ROUNDING_METHOD_VALUES = ROUNDING_METHODS.map(m => m.value)

// Range decimali allineato al CHECK constraint DB
// (chk_emittenti_fiscali_utilities_arrotondamento_dec).
export const ROUNDING_DECIMALI_RANGE = { MIN: 0, MAX: 6 }

// --- Email log stati ---
export const EMAIL_LOG_STATO = {
  PENDING: 'PENDING',
  SENT: 'SENT',
  FAILED: 'FAILED',
  RETRY: 'RETRY'
}

// Scopo: Costruisce le opzioni stato email log per Select filtro.
export function buildEmailLogStatoOptions(t) {
  return [
    { label: t('amm.email_stato_tutti'), value: null },
    { label: t('amm.email_stato_sent'), value: EMAIL_LOG_STATO.SENT },
    { label: t('amm.email_stato_failed'), value: EMAIL_LOG_STATO.FAILED },
    { label: t('amm.email_stato_pending'), value: EMAIL_LOG_STATO.PENDING },
    { label: t('amm.email_stato_retry'), value: EMAIL_LOG_STATO.RETRY }
  ]
}

// Scopo: Restituisce la severity PrimeVue per uno stato email log.
export function getEmailLogStatoSeverity(stato) {
  if (stato === EMAIL_LOG_STATO.SENT) return 'success'
  if (stato === EMAIL_LOG_STATO.FAILED) return 'danger'
  if (stato === EMAIL_LOG_STATO.RETRY) return 'warn'
  return 'info' // PENDING
}

// --- Severity mapping riusabili ---

// Scopo: Restituisce la severity PrimeVue per un livello accesso.
export function getLivelloSeverity(livello) {
  if (livello === LIVELLO_ACCESSO.TUTTO) return 'success'
  if (livello === LIVELLO_ACCESSO.LETTURA) return 'warn'
  return 'danger'
}

// Scopo: Restituisce la label i18n per un livello accesso.
export function getLivelloLabel(t, livello) {
  if (livello === LIVELLO_ACCESSO.TUTTO) return t('amm.livello_tutto')
  if (livello === LIVELLO_ACCESSO.LETTURA) return t('amm.livello_lettura')
  return t('amm.livello_bloccato')
}

// Scopo: Restituisce la severity PrimeVue per un ruolo sistema.
export function getRuoloSeverity(ruolo) {
  if (ruolo === RUOLO_SISTEMA.ADMIN) return 'warn'
  if (ruolo === RUOLO_SISTEMA.DISABILITATO) return 'danger'
  return 'info'
}

// Scopo: Restituisce la severity PrimeVue per un tipo operazione audit.
export function getAuditOpSeverity(tipo) {
  if (tipo === 'INIZIALE') return 'info'
  if (tipo === 'MODIFICA') return 'warn'
  if (tipo === 'ELIMINAZIONE') return 'danger'
  return 'secondary'
}
