// Client API per il sottodominio vendite/listini.
import api from '../../core/api'

const BASE = '/vendite/listini'

// --- Listini ---

export function listListini(params = {}) {
  return api.get(`${BASE}/`, { params })
}

export function getListino(id) {
  return api.get(`${BASE}/${id}/`)
}

export function createListino(payload) {
  return api.post(`${BASE}/`, payload)
}

export function updateListino(id, payload) {
  return api.patch(`${BASE}/${id}/`, payload)
}

// --- Versioni ---

export function listVersioni(listinoId) {
  return api.get(`${BASE}/${listinoId}/versioni/`)
}

export function getVersione(listinoId, verId) {
  return api.get(`${BASE}/${listinoId}/versioni/${verId}/`)
}

export function createVersione(listinoId, payload) {
  return api.post(`${BASE}/${listinoId}/versioni/`, payload)
}

export function updateVersione(listinoId, verId, payload) {
  return api.patch(`${BASE}/${listinoId}/versioni/${verId}/`, payload)
}

export function changeVersioneStato(listinoId, verId, payload) {
  return api.post(`${BASE}/${listinoId}/versioni/${verId}/stato/`, payload)
}

// --- Righe prezzo ---

export function listRighe(listinoId, verId) {
  return api.get(`${BASE}/${listinoId}/versioni/${verId}/righe/`)
}

export function createRiga(listinoId, verId, payload) {
  return api.post(`${BASE}/${listinoId}/versioni/${verId}/righe/`, payload)
}

export function updateRiga(listinoId, verId, rigaId, payload) {
  return api.patch(`${BASE}/${listinoId}/versioni/${verId}/righe/${rigaId}/`, payload)
}

export function deleteRiga(listinoId, verId, rigaId) {
  return api.delete(`${BASE}/${listinoId}/versioni/${verId}/righe/${rigaId}/`)
}

// --- Associazioni ---

export function listAssociazioni(listinoId) {
  return api.get(`${BASE}/${listinoId}/associazioni/`)
}

export function createAssociazione(listinoId, payload) {
  return api.post(`${BASE}/${listinoId}/associazioni/`, payload)
}

export function updateAssociazione(listinoId, assocId, payload) {
  return api.patch(`${BASE}/${listinoId}/associazioni/${assocId}/`, payload)
}

export function deleteAssociazione(listinoId, assocId) {
  return api.delete(`${BASE}/${listinoId}/associazioni/${assocId}/`)
}

// --- Test resolver ---

export function testResolverPrezzo(payload) {
  return api.post(`${BASE}/test-prezzo/`, payload)
}
