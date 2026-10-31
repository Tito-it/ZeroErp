// Client API per il dominio catalogo (articoli, UoM, componenti, note).
import api from '../../core/api'
import { makeNotesApi } from '../../core/api/notes'

const BASE = '/catalogo'

// --- Note (building block partizionato 2026-05-21) ---
//
// Wrapper di dominio sopra `makeNotesApi`: produce un set CRUD note bindato
// al parent path (articolo o componente). Catalogo usa pattern URL "split":
// LIST/POST sotto parent (`/catalogo/articoli/<id>/note/`), DETAIL su endpoint
// generico (`/catalogo/note/<id>/`). Si esprime con `detailBase: '/catalogo'`.
// Resto identico al pattern vendite (`makeNotesApi('/vendite/preventivi/<id>')`).

// Scopo: Set CRUD note articolo per il building block NoteDrawer.
export function makeArticoloNotesApi(articoloId) {
  return makeNotesApi(`${BASE}/articoli/${articoloId}`, { detailBase: BASE })
}

// Scopo: Set CRUD note componente articolo per il building block NoteDrawer.
export function makeComponenteNotesApi(articoloId, compId) {
  return makeNotesApi(`${BASE}/articoli/${articoloId}/componenti/${compId}`, { detailBase: BASE })
}

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

// La pagina della lista `catalogo.articolo_uom` (dal 2026-10-31): `search`,
// `limit`/`offset`, `order_by`/`order_dir`; la busta porta anche
// `non_editable_fields`. Per tutte le UoM in un colpo: `lookupArticoloUom`.
export function listArticoloUom(articoloId, params = {}) {
  return api.get(`${BASE}/articoli/${articoloId}/uom/`, { params })
}

// Lookup cross-dominio (skip_area_check lato BE): per autocomplete UoM nei
// drawer di vendite (preventivi, contratti, listini, promo articoli) che non
// possono richiedere LETTURA su catalogo solo per popolare un combo.
// Usato da `useArticoloUomOptions` e dal riepilogo del drawer articolo: la
// collezione intera `{count, results, non_editable_fields}`.
export function lookupArticoloUom(articoloId) {
  return api.get(`${BASE}/articoli/${articoloId}/uom/lookup/`)
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

// La distinta come LISTA CONFIGURABILE `catalogo.articolo_componenti`
// (brief-db-liste-righe-documento, lotto C): pagina ed export. ⚠️ Su
// `…/componenti/lista/` e NON `…/componenti/`: quella resta la lettura completa
// (il riepilogo nel drawer dell'articolo) e la creazione di un componente.
export function listArticoloComponentiLista(articoloId, params = {}) {
  return api.get(`${BASE}/articoli/${articoloId}/componenti/lista/`, { params })
}

export function exportArticoloComponentiLista(articoloId, params = {}) {
  return api.get(`${BASE}/articoli/${articoloId}/componenti/lista/export/`, { params, responseType: 'blob' })
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

// --- Unita' di misura (CRUD) ---

export function listUomTipi(params = {}) {
  return api.get(`${BASE}/uom-tipi/`, { params })
}

export function getUomTipo(id) {
  return api.get(`${BASE}/uom-tipi/${id}/`)
}

export function createUomTipo(payload) {
  return api.post(`${BASE}/uom-tipi/`, payload)
}

export function updateUomTipo(id, payload) {
  return api.patch(`${BASE}/uom-tipi/${id}/`, payload)
}

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
