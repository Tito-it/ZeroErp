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

export function lookupTipiRuoliPerNatura(naturaSoggetto = null) {
  const params = {}
  if (naturaSoggetto) params.natura_soggetto = naturaSoggetto
  return api.get(`${BASE}/lookup/tipi-ruoli-natura/`, { params })
}

export function lookupFormeGiuridiche(tipoSoggettoDettaglioId = null) {
  const params = {}
  if (tipoSoggettoDettaglioId) params.tipo_soggetto_dettaglio_id = tipoSoggettoDettaglioId
  return api.get(`${BASE}/lookup/forme-giuridiche/`, { params })
}

export function lookupMatriceIndirizzi(tipoSoggettoDettaglioId) {
  return api.get(
    `${BASE}/lookup/tipi-soggetto-dettaglio/${tipoSoggettoDettaglioId}/indirizzi/`
  )
}

export function lookupMatriceIndirizziRuolo(tipoRuoloCodice) {
  return api.get(
    `${BASE}/lookup/tipi-ruolo/${tipoRuoloCodice}/indirizzi/`
  )
}

// --- Sistema codici ---

export function lookupSistemaCodici(schema, tabella, colonna = 'codice') {
  return api.get(`${BASE}/lookup/sistema-codici/`, { params: { schema, tabella, colonna } })
}

export function searchComuni(search, limit = 20) {
  return api.get(`${BASE}/lookup/comuni/`, { params: { search, limit } })
}

export function searchStradario(comuneId, search, limit = 20) {
  return api.get(`${BASE}/search/stradario/`, {
    params: { comune_id: comuneId, search, limit }
  })
}

export function searchStradarioGenerale(search, limit = 30) {
  return api.get(`${BASE}/search/stradario-generale/`, {
    params: { search, limit }
  })
}
