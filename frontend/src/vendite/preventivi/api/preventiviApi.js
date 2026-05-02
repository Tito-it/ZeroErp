// Client API per il sottodominio vendite/preventivi.
// URL REST standard: POST = crea/azione, PATCH = aggiorna, GET = consultazione.
// Ref: backend/apps/vendite/api/preventivi_urls.py

import api from '../../../core/api'

const BASE = '/vendite/preventivi'

// --- Testata CRUD ---

export function listPreventivi(params = {}) {
  return api.get(`${BASE}/`, { params })
}

export function getPreventivo(id) {
  return api.get(`${BASE}/${id}/`)
}

export function createPreventivo(payload) {
  return api.post(`${BASE}/`, payload)
}

export function updatePreventivo(id, payload) {
  return api.patch(`${BASE}/${id}/`, payload)
}

// Hard-delete preventivo BOZZA orfano (zero righe, zero pratiche).
// Usato dal flusso "abbandono bozza" del drawer create. Per stati avanzati
// usare invece cambiaStatoPreventivo(id, {nuovo_stato: 'ANNULLATO'}).
export function deletePreventivo(id) {
  return api.delete(`${BASE}/${id}/`)
}

// --- Azioni testata ---

export function cambiaStatoPreventivo(id, payload) {
  return api.post(`${BASE}/${id}/stato/`, payload)
}

export function creaRevisione(id) {
  return api.post(`${BASE}/${id}/revisione/`, {})
}

// --- Righe ---

export function listRighe(preventivoId) {
  return api.get(`${BASE}/${preventivoId}/righe/`)
}

export function createRiga(preventivoId, payload) {
  return api.post(`${BASE}/${preventivoId}/righe/`, payload)
}

export function updateRiga(preventivoId, rigaId, payload) {
  return api.patch(`${BASE}/${preventivoId}/righe/${rigaId}/`, payload)
}

export function deleteRiga(preventivoId, rigaId) {
  return api.delete(`${BASE}/${preventivoId}/righe/${rigaId}/`)
}

// --- Indirizzi ---

export function listIndirizzi(preventivoId) {
  return api.get(`${BASE}/${preventivoId}/indirizzi/`)
}

export function upsertIndirizzo(preventivoId, payload) {
  return api.post(`${BASE}/${preventivoId}/indirizzi/`, payload)
}

// --- Integrazione ---

export function pushCommessa(preventivoId) {
  return api.post(`${BASE}/${preventivoId}/push-commessa/`, {})
}

export function statoFatturazione(preventivoId) {
  return api.get(`${BASE}/${preventivoId}/stato-fatturazione/`)
}

export function generaPratica(preventivoId, payload) {
  return api.post(`${BASE}/${preventivoId}/genera-pratica/`, payload)
}

export function listPratiche(preventivoId) {
  return api.get(`${BASE}/${preventivoId}/pratiche/`)
}
