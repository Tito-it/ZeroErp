// Client API per il dominio catalogo (articoli, UoM, componenti, note).
import api from '../../core/api'

const BASE = '/catalogo'

// --- Articoli ---

export function listArticoli(params = {}) {
  return api.get(`${BASE}/articoli/`, { params })
}

export function getArticolo(id) {
  return api.get(`${BASE}/articoli/${id}/`)
}

export function createArticolo(payload) {
  return api.post(`${BASE}/articoli/`, payload)
}

export function updateArticolo(id, payload) {
  return api.patch(`${BASE}/articoli/${id}/`, payload)
}

export function disattivaArticolo(id) {
  return api.post(`${BASE}/articoli/${id}/disattiva/`, {})
}

export function riattivaArticolo(id) {
  return api.post(`${BASE}/articoli/${id}/riattiva/`, {})
}

export function lookupArticoli(params = {}) {
  return api.get(`${BASE}/articoli/lookup/`, { params })
}

// Fase 8 (A5): defaults pre-compilazione form articolo (oggi default_iva_id).
// Tipi gia' castati lato BE: il FE non duplica il cast da stringa generico
// di /core/parameters/defaults/.
export function getArticoloFormDefaults() {
  return api.get(`${BASE}/articoli/form-defaults/`)
}

// --- UoM operative articolo ---

export function listArticoloUom(articoloId) {
  return api.get(`${BASE}/articoli/${articoloId}/uom/`)
}

export function createArticoloUom(articoloId, payload) {
  return api.post(`${BASE}/articoli/${articoloId}/uom/`, payload)
}

export function updateArticoloUom(articoloId, uomOpId, payload) {
  return api.patch(`${BASE}/articoli/${articoloId}/uom/${uomOpId}/`, payload)
}

export function deleteArticoloUom(articoloId, uomOpId) {
  return api.delete(`${BASE}/articoli/${articoloId}/uom/${uomOpId}/`)
}

// --- Componenti BoM ---

export function listArticoloComponenti(articoloId) {
  return api.get(`${BASE}/articoli/${articoloId}/componenti/`)
}

export function createArticoloComponente(articoloId, payload) {
  return api.post(`${BASE}/articoli/${articoloId}/componenti/`, payload)
}

export function updateArticoloComponente(articoloId, compId, payload) {
  return api.patch(`${BASE}/articoli/${articoloId}/componenti/${compId}/`, payload)
}

export function deleteArticoloComponente(articoloId, compId) {
  return api.delete(`${BASE}/articoli/${articoloId}/componenti/${compId}/`)
}

// Scopo: Endpoint atomico Fase 3 — duplica versione corrente del componente.
//        Il BE chiude la sorgente con valido_al=chiudi_al (default oggi) e
//        crea una nuova riga con valido_dal=chiudi_al+1, copia verbatim
//        della struttura. Tutto in singola TX DB con advisory lock.
//        Idempotency-Key (UUID v4) e' obbligatoria: il BE rifiuta senza header.
//        payload: { chiudi_al?: 'YYYY-MM-DD' }
export function duplicaComponenteVersione(articoloId, compId, payload = {}) {
  return api.post(
    `${BASE}/articoli/${articoloId}/componenti/${compId}/duplica-versione/`,
    payload,
    { headers: { 'Idempotency-Key': crypto.randomUUID() } },
  )
}

// --- Note articolo ---

export function listArticoloNote(articoloId) {
  return api.get(`${BASE}/articoli/${articoloId}/note/`)
}

export function createArticoloNota(articoloId, payload) {
  return api.post(`${BASE}/articoli/${articoloId}/note/`, payload)
}

export function updateNota(notaId, payload) {
  return api.patch(`${BASE}/note/${notaId}/`, payload)
}

export function deleteNota(notaId) {
  return api.delete(`${BASE}/note/${notaId}/`)
}

// --- Unita' di misura (CRUD) ---

export function listUnitaMisura(params = {}) {
  return api.get(`${BASE}/unita-misura/`, { params })
}

export function getUnitaMisura(id) {
  return api.get(`${BASE}/unita-misura/${id}/`)
}

export function createUnitaMisura(payload) {
  return api.post(`${BASE}/unita-misura/`, payload)
}

export function updateUnitaMisura(id, payload) {
  return api.patch(`${BASE}/unita-misura/${id}/`, payload)
}

export function disattivaUnitaMisura(id) {
  return api.post(`${BASE}/unita-misura/${id}/disattiva/`, {})
}

// Nota: il lookup UoM usa l'endpoint generico lookupCodici('catalogo.unita_misura') da core/apiCore.js

// --- Note componenti ---

export function listComponenteNote(articoloId, compId) {
  return api.get(`${BASE}/articoli/${articoloId}/componenti/${compId}/note/`)
}

export function createComponenteNota(articoloId, compId, payload) {
  return api.post(`${BASE}/articoli/${articoloId}/componenti/${compId}/note/`, payload)
}

// --- Lookup statici ---

// Scopo: Lookup statico modi di arrotondamento UoM operativa.
//        Ritorna lista di {codice, descrizione, ordering}. Single source of truth
//        nel BE (catalogo_service._ROUNDING_MODE_VALIDI). Nessuna paginazione.
export function lookupUomRoundingModes() {
  return api.get(`${BASE}/lookup/rounding-modes/`)
}

// --- Conversioni UoM ---

export function listConversioniUom(params = {}) {
  return api.get(`${BASE}/conversioni-uom/`, { params })
}

export function getConversioneUom(id) {
  return api.get(`${BASE}/conversioni-uom/${id}/`)
}

export function createConversioneUom(payload) {
  return api.post(`${BASE}/conversioni-uom/`, payload)
}

export function updateConversioneUom(id, payload) {
  return api.patch(`${BASE}/conversioni-uom/${id}/`, payload)
}
