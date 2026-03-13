// Client API per il modulo Amm. Software.
// Usa l'istanza axios condivisa con interceptor JWT.

import api from '../../core/api'

const BASE = '/amm-software'

// --- Utenti ---

export function listUtenti(params = {}) {
  return api.get(`${BASE}/utenti/`, { params })
}

export function getUtente(authUserId) {
  return api.get(`${BASE}/utenti/${authUserId}/`)
}

export function createUtente(payload) {
  return api.post(`${BASE}/utenti/`, payload)
}

export function updateUtente(authUserId, payload) {
  return api.patch(`${BASE}/utenti/${authUserId}/`, payload)
}

export function disabilitaUtente(authUserId) {
  return api.post(`${BASE}/utenti/${authUserId}/disabilita/`)
}

// --- Override permessi utente ---

export function getOverrideAree(authUserId) {
  return api.get(`${BASE}/utenti/${authUserId}/override-aree/`)
}

export function putOverrideAree(authUserId, items) {
  return api.put(`${BASE}/utenti/${authUserId}/override-aree/`, { items })
}

export function getOverrideAzioni(authUserId) {
  return api.get(`${BASE}/utenti/${authUserId}/override-azioni/`)
}

export function putOverrideAzioni(authUserId, items) {
  return api.put(`${BASE}/utenti/${authUserId}/override-azioni/`, { items })
}

export function getEmittentiScope(authUserId) {
  return api.get(`${BASE}/utenti/${authUserId}/emittenti-scope/`)
}

export function putEmittentiScope(authUserId, emittenteIds) {
  return api.put(`${BASE}/utenti/${authUserId}/emittenti-scope/`, { emittente_ids: emittenteIds })
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
