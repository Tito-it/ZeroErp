// Client API per gestione emittenti fiscali (admin only).
// Gli endpoint risiedono sotto /anagrafiche/emittenti-fiscali/ ma sono richiesti
// dalla sezione Amm. Software perche' protetti da AdminAPIView.

import api from '../../core/api'

const BASE = '/anagrafiche/emittenti-fiscali'

// --- Emittenti fiscali (CRUD) ---

export function listEmittentiFiscali(params = {}) {
  return api.get(`${BASE}/`, { params })
}

export function getEmittenteFiscale(id) {
  return api.get(`${BASE}/${id}/`)
}

export function createEmittenteFiscale(payload) {
  return api.post(`${BASE}/`, payload)
}

export function updateEmittenteFiscale(id, payload) {
  return api.patch(`${BASE}/${id}/`, payload)
}

// --- Mapping Billing Account ---

export function listEmittenteBillingAccount(emittenteId, params = {}) {
  return api.get(`${BASE}/${emittenteId}/billing-account/`, { params })
}

// Scopo: Rende l'emittente l'azienda predefinita (in cui nascono i clienti
//        creati senza sessione). Corpo vuoto: un cliente nasce gia' collegato
//        alla sua azienda, e il collegamento non si crea ne' si toglie da qui
//        (dal 2026-11-27; il DELETE e' ritirato, il DB lo rifiuta sempre).
export function impostaEmittentePredefinito(emittenteId) {
  return api.post(`${BASE}/${emittenteId}/billing-account/`, {})
}

// Scopo: Riepilogo mapping BA (has_default + count_specifici) indipendente dalla
//        pagina corrente. Risolve il bug A8/C3 del WIP frontend amm-software:
//        senza summary, il check "esiste gia' un default" fallisce se il record
//        default non e' nella pagina paginata visibile.
export function getEmittenteBillingAccountSummary(emittenteId) {
  return api.get(`${BASE}/${emittenteId}/billing-account/summary/`)
}

// --- Utilities ---

export function listEmittenteUtilities(emittenteId) {
  return api.get(`${BASE}/${emittenteId}/utilities/`)
}

export function createEmittenteUtility(emittenteId, payload) {
  return api.post(`${BASE}/${emittenteId}/utilities/`, payload)
}

export function updateEmittenteUtility(emittenteId, recordId, payload) {
  return api.patch(`${BASE}/${emittenteId}/utilities/${recordId}/`, payload)
}

export function deleteEmittenteUtility(emittenteId, recordId) {
  return api.delete(`${BASE}/${emittenteId}/utilities/${recordId}/`)
}
