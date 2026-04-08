// Client API per la gestione della matrice config.utilities_tipi_ruolo
// (admin only). Gli endpoint risiedono sotto /config/utilities-tipi-ruolo/
// ma sono richiesti dalla sezione Amm. Software perche' protetti da AdminAPIView.

import api from '../../core/api'

const BASE = '/config/utilities-tipi-ruolo'

// --- Matrice utilities x tipi_ruolo (CRUD admin) ---

export function listUtilitiesTipiRuolo(params = {}) {
  return api.get(`${BASE}/`, { params })
}

export function getUtilityTipoRuolo(id) {
  return api.get(`${BASE}/${id}/`)
}

export function createUtilityTipoRuolo(payload) {
  return api.post(`${BASE}/`, payload)
}

export function updateUtilityTipoRuolo(id, payload) {
  return api.patch(`${BASE}/${id}/`, payload)
}

// --- Usage emittenti fiscali per la riga matrice ---

export function listUtilityTipoRuoloUsage(id, params = {}) {
  return api.get(`${BASE}/${id}/usage/`, { params })
}
