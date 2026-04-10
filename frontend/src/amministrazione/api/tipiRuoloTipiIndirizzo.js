// Client API per la gestione della matrice config.tipi_ruolo_tipi_indirizzo
import api from '../../core/api'

const BASE = '/config/tipi-ruolo-tipi-indirizzo'

export function listTipiRuoloTipiIndirizzo(params = {}) {
  return api.get(`${BASE}/`, { params })
}

export function getTipoRuoloTipoIndirizzo(id) {
  return api.get(`${BASE}/${id}/`)
}

export function createTipoRuoloTipoIndirizzo(payload) {
  return api.post(`${BASE}/`, payload)
}

export function updateTipoRuoloTipoIndirizzo(id, payload) {
  return api.patch(`${BASE}/${id}/`, payload)
}
