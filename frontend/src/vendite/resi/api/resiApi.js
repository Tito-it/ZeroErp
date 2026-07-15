// Client API per il sottodominio vendite/resi (motore resi su DDT).
// URL REST standard: POST = crea/azione, PATCH = aggiorna, GET = consultazione.
// Ref: backend/apps/vendite/api/urls_resi.py (mount in urls_v1.py: /vendite/resi/).
//
// Clone strutturale ridotto di ddtApi (brief-be-fe-resi-vendita §10): niente
// componenti BoM / PDF / push / note / export (fuori perimetro slice). Le
// azioni di dominio hanno endpoint DEDICATI (conferma/annulla/ri-consegna):
// le fn madri DB applicano gli effetti (residuo, proiezione stato ordine,
// flip DDT) — nessun cambia-stato generico.

import api from '../../../core/api'

const BASE = '/vendite/resi'

// --- Testata CRUD ---

export function listResi(params = {}) {
  return api.get(`${BASE}/`, { params })
}

export function getReso(id) {
  return api.get(`${BASE}/${id}/`)
}

// Export CSV/XLSX della lista resi (DEF-1): stessi filtri/sort della lista.
// responseType blob (download gestito dal caller via useFileDownload).
export function exportResi(params = {}) {
  return api.get(`${BASE}/export/`, { params, responseType: 'blob' })
}

// Crea reso da DDT (DRAFT). Payload: { ddt_id, data?, righe? } — le righe
// opzionali ({ddt_riga_id, tipo_reso_id, qta_operativa, motivo}) vengono
// create in transazione con la testata (pannello "crea reso" del drawer DDT).
// BA/destinatario/utility/valuta/emittente li eredita il trigger DB dal DDT
// sorgente (che deve essere CONSEGNATO).
export function createReso(payload) {
  return api.post(`${BASE}/`, payload)
}

// Aggiorna testata (solo DRAFT, guard BE). Campi ammessi: data, meta.
export function updateReso(id, payload) {
  return api.patch(`${BASE}/${id}/`, payload)
}

// Hard-delete reso BOZZA orfano (solo DRAFT + 0 righe).
export function deleteReso(id) {
  return api.delete(`${BASE}/${id}/`)
}

// --- Azioni di dominio (fn madri DB, atomiche) ---

// DRAFT -> CONFERMATO: numero dal trigger, riapertura residuo ordine,
// proiezione stato ordine, flip DDT->RESO se reso totale.
export function confermaReso(id) {
  return api.post(`${BASE}/${id}/conferma/`, {})
}

// Annullo (da DRAFT o CONFERMATO): post-conferma storna gli effetti; bloccato
// se il reso e' gia' stato ri-spedito (E_RESO_ANNULLO_CON_RICONSEGNE).
export function annullaReso(id) {
  return api.post(`${BASE}/${id}/annulla/`, {})
}

// Genera il DDT di ri-consegna (parziale/multiplo). `righe` =
// [{resi_riga_id, qta}] in unita' BASE; omesse/null = tutta la copertura
// residua. Righe degeneri (lista vuota/malformata) -> 400 dal BE, mai
// degrado silenzioso a "ri-spedisci tutto".
export function generaDdtRiconsegna(id, { righe = null, data = null } = {}) {
  const payload = {}
  if (righe != null) payload.righe = righe
  if (data != null) payload.data = data
  return api.post(`${BASE}/${id}/genera-ddt-riconsegna/`, payload)
}

// --- Righe (solo testata DRAFT) ---

export function listRighe(resoId) {
  return api.get(`${BASE}/${resoId}/righe/`)
}

// Payload riga: { ddt_riga_id, tipo_reso_id, qta_operativa, motivo?, meta? }.
// Articolo/UoM/factor sono SNAPSHOT dalla riga DDT (il BE li copia).
export function createRiga(resoId, payload) {
  return api.post(`${BASE}/${resoId}/righe/`, payload)
}

export function updateRiga(resoId, rigaId, payload) {
  return api.patch(`${BASE}/${resoId}/righe/${rigaId}/`, payload)
}

export function deleteRiga(resoId, rigaId) {
  return api.delete(`${BASE}/${resoId}/righe/${rigaId}/`)
}

// --- Code di lavoro (viste dedicate, righe reso CONFERMATE) ---

export function listDaAccreditare(params = {}) {
  return api.get(`${BASE}/da-accreditare/`, { params })
}

export function listDaRiconsegnare(params = {}) {
  return api.get(`${BASE}/da-riconsegnare/`, { params })
}

// Export CSV/XLSX delle due code (DEF-1): stessi filtri/sort della lista.
// responseType blob (download gestito dal caller via useFileDownload).
export function exportDaAccreditare(params = {}) {
  return api.get(`${BASE}/da-accreditare/export/`, { params, responseType: 'blob' })
}

export function exportDaRiconsegnare(params = {}) {
  return api.get(`${BASE}/da-riconsegnare/export/`, { params, responseType: 'blob' })
}

// --- Dominio DDT (sorgente): righe con residuo rendibile ---

// Alimenta il pannello "crea reso" del drawer DDT: righe del DDT +
// qta_gia_resa / qta_resa_residua (+ _operativa). Il guard over-return resta
// a DB (E_RESO_QTA_SUPERA_CONSEGNATO).
export function getRigheDdtPerReso(ddtId) {
  return api.get(`/vendite/ddt/${ddtId}/righe-per-reso/`)
}
