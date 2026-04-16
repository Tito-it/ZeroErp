// Client API per la gestione admin delle promo articoli (STADIO 0 resolver v5).
// Endpoint: /vendite/promo-articoli/ (AdminAPIView).

import api from '../../core/api'

const BASE = '/vendite/promo-articoli'

export function listPromoArticoli(params = {}) {
  return api.get(`${BASE}/`, { params })
}

export function getPromoArticolo(id) {
  return api.get(`${BASE}/${id}/`)
}

export function createPromoArticolo(payload) {
  return api.post(`${BASE}/`, payload)
}

export function updatePromoArticolo(id, payload) {
  return api.patch(`${BASE}/${id}/`, payload)
}
