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

export function lookupArticoli(params = {}) {
  return api.get(`${BASE}/articoli/lookup/`, { params })
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
