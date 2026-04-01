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

export function getEmittentiScope(authUserId) {
  return api.get(`${BASE}/operatori/${authUserId}/emittenti-scope/`)
}

export function putEmittentiScope(authUserId, emittenteIds) {
  return api.put(`${BASE}/operatori/${authUserId}/emittenti-scope/`, { emittente_ids: emittenteIds })
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
