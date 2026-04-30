// Client API per il modulo Amm. Software.
// Usa l'istanza axios condivisa con interceptor JWT.

import api from '../../core/api'

const BASE = '/amm-software'

// --- Operatori ---

export function listOperatori(params = {}) {
  return api.get(`${BASE}/operatori/`, { params })
}

export function getOperatore(authUserId) {
  return api.get(`${BASE}/operatori/${authUserId}/`)
}

export function createOperatore(payload) {
  return api.post(`${BASE}/operatori/`, payload)
}

export function updateOperatore(authUserId, payload) {
  return api.patch(`${BASE}/operatori/${authUserId}/`, payload)
}

export function disabilitaOperatore(authUserId) {
  return api.post(`${BASE}/operatori/${authUserId}/disabilita/`)
}

export function riattivaOperatore(authUserId) {
  return api.post(`${BASE}/operatori/${authUserId}/riattiva/`)
}

// --- Invito operatore ---

export function invitaOperatore(authUserId) {
  return api.post(`${BASE}/operatori/${authUserId}/invita/`)
}

export function reinviaInvito(authUserId) {
  return api.post(`${BASE}/operatori/${authUserId}/reinvia-invito/`)
}

// --- Override permessi operatore ---

export function getOverrideAree(authUserId) {
  return api.get(`${BASE}/operatori/${authUserId}/override-aree/`)
}

export function putOverrideAree(authUserId, items) {
  return api.put(`${BASE}/operatori/${authUserId}/override-aree/`, { items })
}

export function getOverrideAzioni(authUserId) {
  return api.get(`${BASE}/operatori/${authUserId}/override-azioni/`)
}

export function putOverrideAzioni(authUserId, items) {
  return api.put(`${BASE}/operatori/${authUserId}/override-azioni/`, { items })
}

export function getOverrideOggetti(authUserId) {
  return api.get(`${BASE}/operatori/${authUserId}/override-oggetti/`)
}

export function putOverrideOggetti(authUserId, items) {
  return api.put(`${BASE}/operatori/${authUserId}/override-oggetti/`, { items })
}

export function getModelOverridesLookup() {
  return api.get(`${BASE}/lookup/model-overrides/`)
}

// Fase 2 multi-face: shape `{scope_mode, emittenti_ids, allowed_scope_modes,
// can_change_scope, change_scope_reason, emittente_descrizione}`. La GET
// e' coerente con la PUT: stesso shape in input e output.
export function getEmittentiScope(authUserId) {
  return api.get(`${BASE}/operatori/${authUserId}/emittenti-scope/`)
}

// payload: { scope_mode: 'GLOBAL'|'SINGLE', emittenti_ids?: number[] }
export function putEmittentiScope(authUserId, payload) {
  return api.put(`${BASE}/operatori/${authUserId}/emittenti-scope/`, payload)
}

// --- Riepilogo permessi ---

export function getPermessiRiepilogo(params = {}) {
  return api.get(`${BASE}/permessi-riepilogo/`, { params })
}

export function getAuditLog(params = {}) {
  return api.get(`${BASE}/audit-log/`, { params })
}

// --- Reparti e profili ---

export function listReparti() {
  return api.get(`${BASE}/reparti/`)
}

export function getProfiloReparto(uoId) {
  return api.get(`${BASE}/reparti/${uoId}/profilo/`)
}

export function putProfiloReparto(uoId, aree, azioni) {
  return api.put(`${BASE}/reparti/${uoId}/profilo/`, { aree, azioni })
}

// --- Email Accounts ---

export function listEmailAccounts(params = {}) {
  return api.get(`${BASE}/email-accounts/`, { params })
}

export function getEmailAccount(id) {
  return api.get(`${BASE}/email-accounts/${id}/`)
}

export function createEmailAccount(payload) {
  return api.post(`${BASE}/email-accounts/`, payload)
}

export function updateEmailAccount(id, payload) {
  return api.patch(`${BASE}/email-accounts/${id}/`, payload)
}

export function testEmailAccount(id) {
  return api.post(`${BASE}/email-accounts/${id}/test/`)
}

// --- Email Templates ---

export function listEmailTemplates(params = {}) {
  return api.get(`${BASE}/email-templates/`, { params })
}

export function getEmailTemplate(id) {
  return api.get(`${BASE}/email-templates/${id}/`)
}

export function updateEmailTemplate(id, payload) {
  return api.patch(`${BASE}/email-templates/${id}/`, payload)
}

export function previewEmailTemplate(id, variabili) {
  return api.post(`${BASE}/email-templates/${id}/preview/`, { variabili })
}

// --- Email Log ---

export function listEmailLogs(params = {}) {
  return api.get(`${BASE}/email-log/`, { params })
}

export function getEmailLog(id) {
  return api.get(`${BASE}/email-log/${id}/`)
}

// --- Lookup ---

export function listUnitaOrganizzative() {
  return api.get(`${BASE}/lookup/unita-organizzative/`)
}

export function listAreeFunzionali() {
  return api.get(`${BASE}/lookup/aree-funzionali/`)
}

export function listAzioniProcesso() {
  return api.get(`${BASE}/lookup/azioni-processo/`)
}

export function listEmittentiFiscali() {
  return api.get(`${BASE}/lookup/emittenti-fiscali/`)
}

// --- Setup status (refactor operatore-emittenti) ---

// Stato setup refactor: contatori EF/operatori per banner UI.
// Restituisce { emittenti_attivi, operatori_totali, operatori_assegnati,
// operatori_admin_globali, operatori_non_assegnati }.
export function getSetupStatus() {
  return api.get(`${BASE}/setup-status/`)
}

// --- Form-defaults emittente fiscale (Fase 3) ---

// Defaults pre-compilazione form anagrafica emittente fiscale.
// Cast tipi gia' applicato lato BE: bollo_auto bool, bollo_soglia
// Decimal|null, rounding_policy str|null. Il FE non duplica il cast
// generico di /core/parameters/defaults/.
// Restituisce { defaults: { bollo_auto, bollo_soglia, rounding_policy },
//               non_editable_fields: [...] }.
export function getEmittenteFormDefaults() {
  return api.get(`${BASE}/emittenti-fiscali/form-defaults/`)
}

// Lookup statico modi di arrotondamento ammessi per emittente fiscale
// (4 codici fissi: UP/DOWN/HALF_UP/HALF_DOWN, niente HALF_EVEN).
// Single source of truth lato BE in
// amm_software_service._ROUNDING_MODE_VALIDI_EMITTENTE.
// Restituisce lista nuda di { codice, descrizione, ordering }.
export function lookupEmittenteRoundingModes() {
  return api.get(`${BASE}/lookup/rounding-modes/`)
}

// --- Audit hardening + email log lookup (Fase 5) ---

// Lookup sorgenti audit ammesse (8 righe). Single source of truth lato DB:
// script.vw_audit_sources. Sostituisce buildAuditTabellaOptions hardcoded.
// Restituisce lista nuda di { code, label_key, area_funzionale }.
export function lookupAuditSources() {
  return api.get(`${BASE}/lookup/audit-sources/`)
}

// Lookup statico stati email log (4 codici fissi: SENT/PENDING/RETRY/FAILED).
// Single source of truth lato BE in amm_software_service._EMAIL_LOG_STATI_VALIDI.
// Restituisce lista nuda di { codice, descrizione, ordering }.
export function lookupEmailLogStati() {
  return api.get(`${BASE}/lookup/email-log-stati/`)
}
