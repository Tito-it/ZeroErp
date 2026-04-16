// Client API per la gestione admin delle categorie cliente.
// Endpoint: /anagrafiche/categorie-clienti/ (AdminAPIView).
// Esposta sotto Amm. Software (precede la matrice categorie-listini).

import api from '../../core/api'

const BASE = '/anagrafiche/categorie-clienti'

export function listCategorieClienti(params = {}) {
  return api.get(`${BASE}/`, { params })
}

export function getCategoriaCliente(id) {
  return api.get(`${BASE}/${id}/`)
}

export function createCategoriaCliente(payload) {
  return api.post(`${BASE}/`, payload)
}

export function updateCategoriaCliente(id, payload) {
  return api.patch(`${BASE}/${id}/`, payload)
}
