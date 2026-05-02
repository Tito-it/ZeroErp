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

// Scopo: Lookup utility ammesse per un tipo ruolo (strict, da config.utilities_tipi_ruolo).
// Usato dal componente riusabile UtilityPerRuoloSelect.
export function lookupUtilitiesPerRuolo(tipoRuoloCodice) {
  return api.get(
    `${BASE}/lookup/tipi-ruolo/${tipoRuoloCodice}/utilities/`
  )
}

// Scopo: Lookup utility ammesse per un ruolo soggetto (es. CL), filtrate
// per l'emittente dell'utente corrente (intersezione ruolo + EF + configurazione).
// Usata dalle combo filtro nelle liste (clienti, fornitori, ecc.).
export function lookupUtilitiesPerEmittente(ruolo) {
  return api.get(`${BASE}/lookup/utilities-per-emittente/`, { params: { ruolo } })
}

// Scopo: Lookup dedicato conti contabili con filtro tipo (A=Acquisto, V=Vendita).
// Espone tipo_conto che il lookup generico config.conti_contabili non ritorna.
export function lookupContiContabili(tipo) {
  const params = tipo ? { tipo } : {}
  return api.get(`${BASE}/lookup/conti-contabili/`, { params })
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

// --- Parametri di sistema ---

export function fetchParameterDefaults(codes) {
  return api.get(`${BASE}/parameters/defaults/`, {
    params: { codes: codes.join(',') }
  })
}

export function fetchParameterSettings() {
  return api.get(`${BASE}/parameters/settings/`)
}

// Scope ammessi: 'user' (default, override personale) | 'emittente' (admin, override aziendale).
// Il default 'user' e' definito anche in PARAMETER_SCOPE.USER (composables/useParameterSettings.js):
// teniamo qui la stringa letterale solo come fallback difensivo, le chiamate dovrebbero
// sempre passare un valore esplicito tramite il composable.
export function upsertParameterOverride(parameterCode, value, scope = 'user') {
  return api.post(`${BASE}/parameters/settings/override/`, {
    parameter_code: parameterCode,
    value,
    scope
  })
}

export function deleteParameterOverride(overrideId, scope = 'user') {
  return api.delete(`${BASE}/parameters/settings/override/${overrideId}/`, {
    params: { scope }
  })
}

// --- Billing account lookup (ricerca ricca cross-dominio) ---

// Scopo: Cerca billing_account per autocomplete.
//        Backend: GET /api/v1/anagrafiche/billing-account/lookup/
//        Ricerca multi-campo (codice, ragione sociale, id fiscale, PDP).
//        Filtro utility e scope emittente automatici lato backend.
export function lookupBillingAccount(params = {}) {
  return api.get('/anagrafiche/billing-account/lookup/', { params })
}

// Scopo: Restituisce un singolo BA arricchito per restore dell'AutoComplete in edit.
//        Backend: GET /api/v1/anagrafiche/billing-account/{id}/lookup/
export function getBillingAccountLookupById(id) {
  return api.get(`/anagrafiche/billing-account/${id}/lookup/`)
}

// --- Istanze utility lookup (preventivi prospect senza BA, future utility-aware flows) ---

// Scopo: Cerca istanze_utilities per autocomplete.
//        Backend: GET /api/v1/anagrafiche/istanze-utility/lookup/
//        Ricerca multi-campo (codice istanza, ragione sociale, indirizzo).
//        Filtri utility (strict post Strategia C) e soggetto opzionali.
//        Scope emittente automatico lato backend (via BA collegato all'istanza).
export function lookupIstanzeUtility(params = {}) {
  return api.get('/anagrafiche/istanze-utility/lookup/', { params })
}

// Scopo: Restituisce una singola istanza arricchita per restore AutoComplete in edit.
//        Backend: GET /api/v1/anagrafiche/istanze-utility/{id}/lookup/
export function getIstanzaUtilityLookupById(id) {
  return api.get(`/anagrafiche/istanze-utility/${id}/lookup/`)
}
