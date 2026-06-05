// Client API per il sottodominio vendite/ordini (ordini di vendita).
// URL REST standard: POST = crea/azione, PATCH = aggiorna, GET = consultazione.
// Ref: backend/apps/vendite/api/urls_ordini.py (mount in urls_v1.py: /vendite/ordini/).
//
// Scheletro (analisi-ordini-vendita.md §6): testata + righe + componenti BoM
// + conferma (DRAFT->CONFERMATO) + push singolo a commessa. Niente revisioni
// ne' listino in testata (a differenza di preventivi/offerte). Componenti BoM
// via building block condiviso `makeComponentiBomApi` (schema URL identico ai
// domini gemelli) — regola del 2, nessuna implementazione nuova.

import api from '../../../core/api'
import { makeComponentiBomApi } from '../../../core/api/componentiBom'

const BASE = '/vendite/ordini'

// --- Testata CRUD ---

export function listOrdini(params = {}) {
  return api.get(`${BASE}/`, { params })
}

// Export CSV/XLSX lista configurabile (DEF-1). responseType blob: NON passare
// da useApiHandler (unwrap envelope perde header/data del file). Vedi memoria
// feedback_blob_download_no_useapihandler.
export function exportOrdini(params = {}) {
  return api.get(`${BASE}/export/`, { params, responseType: 'blob' })
}

export function getOrdine(id) {
  return api.get(`${BASE}/${id}/`)
}

// Crea ordine BOZZA (DRAFT). Il numero e' generato dal trigger DB
// (trgfn_ordini_gen_codice) — non va nel payload. Payload: billing_account_id
// (o soggetto_ruolo_id), utility_id, emittente_fiscale_id, valuta_id,
// modalita_pagamento_id, termine_pagamento_id, fatturazione_trigger,
// agente_soggetto_ruolo_id, data, meta.
export function createOrdine(payload) {
  return api.post(`${BASE}/`, payload)
}

// Aggiorna testata (solo in DRAFT, guard lato BE). PATCH: il BE usa request.data.
export function updateOrdine(id, payload) {
  return api.patch(`${BASE}/${id}/`, payload)
}

// Hard-delete ordine BOZZA (abbandono drawer create, solo DRAFT).
export function deleteOrdine(id) {
  return api.delete(`${BASE}/${id}/`)
}

// --- Transizioni / integrazione ---

// DRAFT -> CONFERMATO. Guard BE: origine DRAFT + almeno una riga.
export function confermaOrdine(id) {
  return api.post(`${BASE}/${id}/conferma/`, {})
}

// Push singolo dell'ordine CONFERMATO a commessa (chiusura giro). Ritorna un
// report orchestrator { stato, push_log_id, durata_ms, handlers, righe_pushable,
// fatturazione_trigger }. Pattern push singolo gemello preventivi/offerte.
export function pushOrdineACommessa(id) {
  return api.post(`${BASE}/${id}/push/`, {})
}

// --- Righe ---

export function listRighe(ordineId) {
  return api.get(`${BASE}/${ordineId}/righe/`)
}

export function createRiga(ordineId, payload) {
  return api.post(`${BASE}/${ordineId}/righe/`, payload)
}

export function updateRiga(ordineId, rigaId, payload) {
  return api.patch(`${BASE}/${ordineId}/righe/${rigaId}/`, payload)
}

export function deleteRiga(ordineId, rigaId) {
  return api.delete(`${BASE}/${ordineId}/righe/${rigaId}/`)
}

// --- Riepilogo IVA ---

// Riepilogo IVA aggregato dell'ordine (una riga per aliquota, regola fiscale
// DPR 633/72 art. 21). Calcolo gia' eseguito in DB dalla vista derivata
// vw_ordini_riepilogo_iva_dettaglio (stessa formula dei preventivi): il FE
// legge solo lo stato corrente, sempre coerente con le righe attive.
// Risposta: array di { iva_id, iva_codice, iva_descrizione, iva_aliquota,
//   imponibile, imposta, arrotondamento, totale_riga }.
export function getRiepilogoIva(ordineId) {
  return api.get(`${BASE}/${ordineId}/riepilogo-iva/`)
}

// --- Componenti BoM CASO A ---
// Schema REST identico a preventivi/contratti: i 4 metodi vengono dal building
// block `makeComponentiBomApi` (core/api/componentiBom.js), qui solo bindati al
// path base ordini e ri-esportati con gli stessi nomi. Init componenti avviene
// lato BE in gestisci_riga quando l'articolo e' composito.
const _componentiApi = makeComponentiBomApi(BASE)
export const previewRigaComponenti = _componentiApi.previewRigaComponenti
export const listRigaComponenti = _componentiApi.listRigaComponenti
export const updateRigaComponente = _componentiApi.updateRigaComponente
export const deleteRigaComponente = _componentiApi.deleteRigaComponente
