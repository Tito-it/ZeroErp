// Client API per gestione emittenti fiscali (admin only).
// Gli endpoint risiedono sotto /anagrafiche/emittenti-fiscali/ ma sono richiesti
// dalla sezione Amm. Software perche' protetti da AdminAPIView.

import api from '../../core/api'

const BASE = '/anagrafiche/emittenti-fiscali'

// --- Emittenti fiscali (CRUD) ---

export function listEmittentiFiscali(params = {}) {
  return api.get(`${BASE}/`, { params })
}

export function getEmittenteFiscale(id) {
  return api.get(`${BASE}/${id}/`)
}

export function createEmittenteFiscale(payload) {
  return api.post(`${BASE}/`, payload)
}

export function updateEmittenteFiscale(id, payload) {
  return api.patch(`${BASE}/${id}/`, payload)
}

// --- Mapping Billing Account ---

export function listEmittenteBillingAccount(emittenteId) {
  return api.get(`${BASE}/${emittenteId}/billing-account/`)
}

export function createEmittenteBillingAccount(emittenteId, payload) {
  return api.post(`${BASE}/${emittenteId}/billing-account/`, payload)
}

export function deleteEmittenteBillingAccount(emittenteId, mappingId) {
  return api.delete(`${BASE}/${emittenteId}/billing-account/${mappingId}/`)
}

// --- Utilities ---

export function listEmittenteUtilities(emittenteId) {
  return api.get(`${BASE}/${emittenteId}/utilities/`)
}

export function createEmittenteUtility(emittenteId, payload) {
  return api.post(`${BASE}/${emittenteId}/utilities/`, payload)
}

export function updateEmittenteUtility(emittenteId, recordId, payload) {
  return api.patch(`${BASE}/${emittenteId}/utilities/${recordId}/`, payload)
}

export function deleteEmittenteUtility(emittenteId, recordId) {
  return api.delete(`${BASE}/${emittenteId}/utilities/${recordId}/`)
}
