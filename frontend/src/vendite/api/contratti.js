// Client API contratti v5 (testata + righe + utility 1:1 + cambio stato).
// Endpoint: /vendite/contratti/ (vedi docs/it/backend/vendite/manual/api_contratti.md).

import api from '../../core/api'

const BASE = '/vendite/contratti'

// Testata
export function listContratti(params = {}) {
  return api.get(`${BASE}/`, { params })
}

export function getContratto(id) {
  return api.get(`${BASE}/${id}/`)
}

export function createContratto(payload) {
  return api.post(`${BASE}/`, payload)
}

export function updateContratto(id, payload) {
  return api.patch(`${BASE}/${id}/`, payload)
}

export function cambiaStatoContratto(id, codiceInterno) {
  return api.post(`${BASE}/${id}/cambia-stato/`, { codice_interno: codiceInterno })
}

// Righe
export function addRigaContratto(contrattoId, payload) {
  return api.post(`${BASE}/${contrattoId}/righe/`, payload)
}

export function updateRigaContratto(contrattoId, rigaId, payload) {
  return api.patch(`${BASE}/${contrattoId}/righe/${rigaId}/`, payload)
}

export function deleteRigaContratto(contrattoId, rigaId) {
  return api.delete(`${BASE}/${contrattoId}/righe/${rigaId}/`)
}

// Utility 1:1
export function addUtilityContratto(contrattoId, payload) {
  return api.post(`${BASE}/${contrattoId}/utility/`, payload)
}

export function updateUtilityContratto(contrattoId, utilityId, payload) {
  return api.patch(`${BASE}/${contrattoId}/utility/${utilityId}/`, payload)
}
