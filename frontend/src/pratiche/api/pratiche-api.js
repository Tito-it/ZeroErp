// Client API per il modulo Pratiche — motore workflow.
// URL REST standard: POST = crea/azione, PATCH = aggiorna, GET = consultazione.
// Ref: docs/it/dev/api.md, backend/apps/pratiche/api/urls_v1.py

import api from '../../core/api'

const BASE = '/pratiche'

// --- Pratiche CRUD ---

export function listPratiche(params = {}) {
  return api.get(`${BASE}/`, { params })
}

export function getPratica(praticaId) {
  return api.get(`${BASE}/${praticaId}/`)
}

export function createPratica(payload) {
  return api.post(`${BASE}/`, payload)
}

export function updatePratica(praticaId, payload) {
  return api.patch(`${BASE}/${praticaId}/`, payload)
}

// --- Azioni pratica ---

export function cambiaStatoPratica(praticaId, payload) {
  return api.post(`${BASE}/${praticaId}/stato/`, payload)
}

export function assegnaPratica(praticaId, payload) {
  return api.post(`${BASE}/${praticaId}/assegnazione/`, payload)
}

export function sospendiPratica(praticaId, payload = {}) {
  return api.post(`${BASE}/${praticaId}/sospendi/`, payload)
}

export function riattivaPratica(praticaId, payload = {}) {
  return api.post(`${BASE}/${praticaId}/riattiva/`, payload)
}

// --- Consultazione pratica ---

export function fetchGiornale(praticaId, params = {}) {
  return api.get(`${BASE}/${praticaId}/giornale/`, { params })
}

export function fetchSospensioni(praticaId, params = {}) {
  return api.get(`${BASE}/${praticaId}/sospensioni/`, { params })
}

export function fetchCalcoliTempo(praticaId, params = {}) {
  return api.get(`${BASE}/${praticaId}/calcoli-tempo/`, { params })
}

// --- Flussi CRUD ---

export function listFlussi(praticaId, params = {}) {
  return api.get(`${BASE}/${praticaId}/flussi/`, { params })
}

export function getFlusso(praticaId, flussoId) {
  return api.get(`${BASE}/${praticaId}/flussi/${flussoId}/`)
}

export function createFlusso(praticaId, payload) {
  return api.post(`${BASE}/${praticaId}/flussi/`, payload)
}

// --- Azioni flusso ---

export function cambiaStatoFlusso(praticaId, flussoId, payload) {
  return api.post(`${BASE}/${praticaId}/flussi/${flussoId}/stato/`, payload)
}

export function sospendiFlusso(praticaId, flussoId, payload = {}) {
  return api.post(`${BASE}/${praticaId}/flussi/${flussoId}/sospendi/`, payload)
}

export function riattivaFlusso(praticaId, flussoId, payload = {}) {
  return api.post(`${BASE}/${praticaId}/flussi/${flussoId}/riattiva/`, payload)
}

// --- Consultazione flusso ---

export function fetchPrerequisiti(praticaId, flussoId) {
  return api.get(`${BASE}/${praticaId}/flussi/${flussoId}/prerequisiti/`)
}

export function fetchCanaliFlusso(praticaId, flussoId) {
  return api.get(`${BASE}/${praticaId}/flussi/${flussoId}/canali/`)
}

// --- Generazione cross-pratica ---

export function fetchRegoleGenerazione(praticaId, flussoId) {
  return api.get(`${BASE}/${praticaId}/flussi/${flussoId}/regole-generazione/`)
}

export function generaPratica(praticaId, flussoId, payload) {
  return api.post(`${BASE}/${praticaId}/flussi/${flussoId}/genera/`, payload)
}

export function fetchPraticheGenerate(praticaId, flussoId) {
  return api.get(`${BASE}/${praticaId}/flussi/${flussoId}/pratiche-generate/`)
}

// --- Formule tempo (lookup globale, non legato a pratica) ---

export function fetchFormuleTempo(params = {}) {
  return api.get(`${BASE}/formule-tempo/`, { params })
}
