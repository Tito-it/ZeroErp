// Client API per il modulo Anagrafiche — gestione geografica.
// URL REST standard: POST = crea, PATCH = aggiorna (nessun verbo nel path).
// Ref: docs/it/dev/api.md

import api from '../../core/api'

const BASE = '/anagrafiche'

// --- Indirizzi dettaglio ---

export function listIndirizzi(params = {}) {
  return api.get(`${BASE}/indirizzi/`, { params })
}

export function getIndirizzo(id) {
  return api.get(`${BASE}/indirizzi/${id}/`)
}

export function createIndirizzo(payload) {
  return api.post(`${BASE}/indirizzi/`, payload)
}

export function updateIndirizzo(id, payload) {
  return api.patch(`${BASE}/indirizzi/${id}/`, payload)
}

// --- Codici postali ---

export function listCodiciPostali(params = {}) {
  return api.get(`${BASE}/codici-postali/`, { params })
}

export function createCodicePostale(payload) {
  return api.post(`${BASE}/codici-postali/`, payload)
}

export function updateCodicePostale(id, payload) {
  return api.patch(`${BASE}/codici-postali/${id}/`, payload)
}

export function lookupCodiciPostaliByComune(comuneId) {
  return api.get(`${BASE}/codici-postali/`, { params: { comune_id: comuneId, limit: 200 } })
}

// --- Toponomastica ---

export function listToponomastica(params = {}) {
  return api.get(`${BASE}/toponomastica/`, { params })
}

export function createToponomastica(payload) {
  return api.post(`${BASE}/toponomastica/`, payload)
}

export function updateToponomastica(id, payload) {
  return api.patch(`${BASE}/toponomastica/${id}/`, payload)
}

// --- Comuni ---

export function listComuni(params = {}) {
  return api.get(`${BASE}/comuni/`, { params })
}

export function createComune(payload) {
  return api.post(`${BASE}/comuni/`, payload)
}

// --- Province ---

export function listProvince(params = {}) {
  return api.get(`${BASE}/province/`, { params })
}

export function lookupProvince() {
  return api.get(`${BASE}/province/lookup/`)
}

export function createProvincia(payload) {
  return api.post(`${BASE}/province/`, payload)
}

export function updateProvincia(id, payload) {
  return api.patch(`${BASE}/province/${id}/`, payload)
}

// --- Regioni ---

export function listRegioni(params = {}) {
  return api.get(`${BASE}/regioni/`, { params })
}

export function createRegione(payload) {
  return api.post(`${BASE}/regioni/`, payload)
}

export function updateRegione(id, payload) {
  return api.patch(`${BASE}/regioni/${id}/`, payload)
}

export function lookupRegioni(params = {}) {
  return api.get(`${BASE}/regioni/lookup/`, { params })
}

// --- Stati ---

export function listStati(params = {}) {
  return api.get(`${BASE}/stati/`, { params })
}

export function createStato(payload) {
  return api.post(`${BASE}/stati/`, payload)
}

export function updateStato(id, payload) {
  return api.patch(`${BASE}/stati/${id}/`, payload)
}

// --- Soggetti ---

export function listSoggetti(params = {}) {
  return api.get(`${BASE}/soggetti/`, { params })
}

export function getSoggetto(id) {
  return api.get(`${BASE}/soggetti/${id}/`)
}

export function createSoggetto(payload) {
  return api.post(`${BASE}/soggetti/`, payload)
}

export function updateSoggetto(id, payload) {
  return api.patch(`${BASE}/soggetti/${id}/`, payload)
}

export function listSoggettoContatti(soggettoId) {
  return api.get(`${BASE}/soggetti/${soggettoId}/contatti/`)
}

export function createSoggettoContatto(soggettoId, payload) {
  return api.post(`${BASE}/soggetti/${soggettoId}/contatti/`, payload)
}

export function updateSoggettoContatto(soggettoId, contattoId, payload) {
  return api.patch(`${BASE}/soggetti/${soggettoId}/contatti/${contattoId}/`, payload)
}

export function listSoggettoIndirizzi(soggettoId) {
  return api.get(`${BASE}/soggetti/${soggettoId}/indirizzi/`)
}

export function createSoggettoIndirizzo(soggettoId, payload) {
  return api.post(`${BASE}/soggetti/${soggettoId}/indirizzi/`, payload)
}

export function listSoggettoRuoli(soggettoId) {
  return api.get(`${BASE}/soggetti/${soggettoId}/ruoli/`)
}

export function assignSoggettoRuolo(soggettoId, payload) {
  return api.post(`${BASE}/soggetti/${soggettoId}/ruoli/`, payload)
}

// --- Stati ---

export function lookupStati() {
  return api.get(`${BASE}/stati/lookup/`)
}
