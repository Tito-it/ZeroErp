// Scopo: costanti e helper del modulo Amm. Software.
// Enum: re-export da core/constants (fonte unica di verita').
// Builder opzioni per Select centralizzati (zero duplicazione).

// Re-export enum da core — usati anche da stores/auth.js
export { RUOLO_SISTEMA, LIVELLO_ACCESSO } from '../core/constants'
import { RUOLO_SISTEMA, LIVELLO_ACCESSO } from '../core/constants'

// --- Tipo ruolo per SoggettoResolver ---
export const TIPO_RUOLO_CODICE = {
  RIS_UMANA: 'RIS_UMANA'
}

// Scopo: Costruisce le opzioni ruolo per Select.
// includeAll: aggiunge "Tutti" (per filtri lista) e "Disabilitato" (sola lettura).
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
