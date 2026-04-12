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

// Elimina un listino mai usato. Backend rifiuta con 400 se versioni_count > 0
// o associazioni_count > 0 (suggerisce PATCH attivo=false per disattivare).
export function deleteListino(id) {
  return api.delete(`${BASE}/${id}/`)
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

// Elimina una versione in stato BOZZA con tutte le sue righe (cascata).
// Il backend rifiuta con 400 se la versione non e' BOZZA.
export function deleteVersione(listinoId, verId) {
  return api.delete(`${BASE}/${listinoId}/versioni/${verId}/`)
}

export function changeVersioneStato(listinoId, verId, payload) {
  return api.post(`${BASE}/${listinoId}/versioni/${verId}/stato/`, payload)
}

// Clona una versione esistente in una nuova versione BOZZA dello stesso listino,
// copiando le righe attive. Vincolo D2: target.valido_dal >= src.valido_dal.
export function cloneVersione(listinoId, srcVerId, payload) {
  return api.post(`${BASE}/${listinoId}/versioni/${srcVerId}/clona/`, payload)
}

// Applica variazione percentuale massa ai prezzi delle righe attive
// di una versione BOZZA. Supporta dry_run per preview.
export function applicaVariazionePercentuale(listinoId, verId, payload) {
  return api.post(`${BASE}/${listinoId}/versioni/${verId}/applica-variazione/`, payload)
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
