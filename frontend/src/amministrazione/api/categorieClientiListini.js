// Client API per la matrice admin anagrafiche.categorie_clienti_listini.
// Gli endpoint sono sotto /anagrafiche/categorie-clienti-listini/ (AdminAPIView).
// Sezione Amm. Software lato FE perche' matrice dimensionale pricing v5.

import api from '../../core/api'

const BASE = '/anagrafiche/categorie-clienti-listini'

// Lista paginata con filtri dimensionali (search, attivo, categoria, utility,
// emittente, listino, valid_at).
export function listCategorieClientiListini(params = {}) {
  return api.get(`${BASE}/`, { params })
}

export function getCategoriaClienteListino(id) {
  return api.get(`${BASE}/${id}/`)
}

export function createCategoriaClienteListino(payload) {
  return api.post(`${BASE}/`, payload)
}

export function updateCategoriaClienteListino(id, payload) {
  return api.patch(`${BASE}/${id}/`, payload)
}
