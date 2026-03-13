// Scopo: API client per endpoint core cross-dominio (lookup, search).
// Usa l'istanza axios condivisa con interceptor JWT.

import api from './api'

const BASE = '/core'

// --- Lookup codici generico (qualifiche, stati, ecc.) ---

export function lookupCodici(rel, params = {}) {
  return api.get(`${BASE}/lookup/codici/`, { params: { rel, ...params } })
}

// --- Lookup anagrafiche cross-dominio (Sprint 3) ---

export function lookupTipiSoggettoDettaglio() {
  return api.get(`${BASE}/lookup/tipi-soggetto-dettaglio/`)
}

export function lookupMatriceIndirizzi(tipoSoggettoDettaglioId) {
  return api.get(
    `${BASE}/lookup/tipi-soggetto-dettaglio/${tipoSoggettoDettaglioId}/indirizzi/`
  )
}

export function searchComuni(search, limit = 20) {
  return api.get(`${BASE}/lookup/comuni/`, { params: { search, limit } })
}

export function searchStradario(comuneId, search, limit = 20) {
  return api.get(`${BASE}/search/stradario/`, {
    params: { comune_id: comuneId, search, limit }
  })
}
