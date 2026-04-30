// Scopo: costanti e helper del modulo Amm. Software.
// Enum: re-export da core/constants (fonte unica di verita').
// Builder opzioni per Select centralizzati (zero duplicazione).

// Re-export enum da core — usati anche da stores/auth.js e test.
export { LIVELLO_ACCESSO } from '../core/constants'
import { LIVELLO_ACCESSO } from '../core/constants'

// --- Tipo ruolo per SoggettoResolver ---
export const TIPO_RUOLO_CODICE = {
  RIS_UMANA: 'RIS_UMANA'
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

// Fase 5 (LANDED): le opzioni filtro audit-log arrivano dal lookup BE
// /amm-software/lookup/audit-sources/ (vw_audit_sources, single source DB).
// Vedi AuditLogView.vue: usa useGlobalLookup('amm.audit_sources') con
// label tradotta via t(label_key). Il vecchio buildAuditTabellaOptions e' stato
// rimosso (era hardcoded e mancava override_oggetti + identita_digitali).

// --- Arrotondamento importi ---
// Fase 3 (LANDED): l'enum dei modi di arrotondamento e' gestito dal lookup
// statico /amm-software/lookup/rounding-modes/ via wrapper riusabile
// EmittenteRoundingModeSelect. Single source of truth lato BE in
// amm_software_service._ROUNDING_MODE_VALIDI_EMITTENTE.
// Range decimali tecnico, allineato al CHECK constraint DB
// (chk_emittenti_fiscali_utilities_arrotondamento_dec).
export const ROUNDING_DECIMALI_RANGE = { MIN: 0, MAX: 6 }

// --- Email log stati ---
// Fase 5 (LANDED): l'enum + le opzioni filtro arrivano dal lookup BE
// /amm-software/lookup/email-log-stati/. Vedi EmailLogStatoSelect.vue
// (wrapper riusabile cached con useGlobalLookup('amm.email_log_stati')).
// Single source of truth lato BE: amm_software_service._EMAIL_LOG_STATI_VALIDI.
//
// `getEmailLogStatoSeverity` resta lato FE (puro mapping CSS, presentation).
// Mantiene i 4 codici hardcoded per resilience: se il BE ne aggiungesse uno
// nuovo, la severity ricadrebbe sul default 'info'.

// Scopo: Restituisce la severity PrimeVue per uno stato email log (puro CSS).
export function getEmailLogStatoSeverity(stato) {
  if (stato === 'SENT') return 'success'
  if (stato === 'FAILED') return 'danger'
  if (stato === 'RETRY') return 'warn'
  return 'info' // PENDING o codice non riconosciuto
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

// Scopo: Restituisce la severity PrimeVue per un tipo operazione audit.
export function getAuditOpSeverity(tipo) {
  if (tipo === 'INIZIALE') return 'info'
  if (tipo === 'MODIFICA') return 'warn'
  if (tipo === 'ELIMINAZIONE') return 'danger'
  return 'secondary'
}
