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
import { makeRigheListaApi } from '../../_shared/righe/righeListaApi'

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

// Chiude la ri-consegna: dichiara DEFINITIVA una quota di merce resa (non
// tornera' al cliente). Stesso contratto righe della ri-spedizione — le due
// uscite condividono la copertura. `note` = motivo facoltativo.
export function chiudiRiconsegna(id, { righe = null, note = null } = {}) {
  const payload = {}
  if (righe != null) payload.righe = righe
  if (note != null) payload.note = note
  return api.post(`${BASE}/${id}/chiudi-riconsegna/`, payload)
}

// Riapre una chiusura (rimedio a una rinuncia errata): la quota torna
// ri-spedibile, l'ordine torna PARZIALMENTE_EVASO, l'accredito torna
// FACOLTATIVA. `righe` omesse = tutte le rinunce del reso.
export function riapriRiconsegna(id, { righe = null } = {}) {
  const payload = {}
  if (righe != null) payload.righe = righe
  return api.post(`${BASE}/${id}/riapri-riconsegna/`, payload)
}

// --- Righe (solo testata DRAFT) ---

// La LISTA configurabile delle righe (pagina + export, `…/righe/lista/`):
// factory condivisa coi documenti gemelli. `listRighe` qui sotto resta la
// lettura COMPLETA (dialog, stampe).
export const { listRigheLista, exportRigheLista } = makeRigheListaApi(BASE)

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

// --- Rientri: dove rientra la merce (3-bis R-1b) ---
// La situazione del reso: { muove_merce, magazzino_id, magazzino_usa_ubicazioni,
// voci: [{ resi_riga_id, ddt_riga_componente_id, riga_nr, articolo_*, uom_codice,
// qta, esatta, rientrata, automatico, prelievi_origine: [...], rientri: [...] }] }.
export function getRientri(resoId) {
  return api.get(`${BASE}/${resoId}/rientri/`)
}

// Payload: ddt_riga_prelievo_id (il prelievo d'origine, obbligatorio), qta
// (obbligatoria), ubicazione_id. Le regole le applica il DB.
export function createRientro(resoId, rigaId, payload) {
  return api.post(`${BASE}/${resoId}/righe/${rigaId}/rientri/`, payload)
}

export function deleteRientro(resoId, rigaId, rientroId) {
  return api.delete(`${BASE}/${resoId}/righe/${rigaId}/rientri/${rientroId}/`)
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

// --- Verbo dell'accredito (nota di credito sui resi) ---

// Accredita N righe di reso in un giro solo: genera le RETTIFICHE da cui
// nascera' la nota di credito al prossimo giro di fatturazione.
// ⭐ Un endpoint solo, e la riga singola e' una lista di uno (D-NC-7): due
// superfici per lo stesso verbo divergerebbero su permessi e forma dell'esito.
// Risposta 200 SEMPRE, anche a righe tutte rifiutate: e' un REPORT
// { esito: COMPLETATO|PARZIALE|ERRORE, totale, ok, accrediti[], falliti[] }.
// Idempotency-Key: modifica lo stato di un documento fiscale.
export function accreditaRighe(resiRigaIds) {
  return api.post(
    `${BASE}/accrediti/`,
    { resi_riga_ids: resiRigaIds },
  )
}

// Annulla l'accredito di una riga (il caso «ho cliccato la riga sbagliata»):
// toglie le rettifiche e l'accredito torna dovuto in coda. Motivo obbligatorio.
// ⛔ NON annulla il documento: quella e' la pipeline di fatturazione — e il
// reset di lotto fa l'opposto, RIGENERA la nota al giro dopo.
export function annullaAccredito(resoId, rigaId, motivo) {
  return api.post(
    `${BASE}/${resoId}/righe/${rigaId}/annulla-accredito/`,
    { motivo },
  )
}

// --- Dominio DDT (sorgente): righe con residuo rendibile ---

// Alimenta il pannello "crea reso" del drawer DDT: righe del DDT +
// qta_gia_resa / qta_resa_residua (+ _operativa). Il guard over-return resta
// a DB (E_RESO_QTA_SUPERA_CONSEGNATO).
export function getRigheDdtPerReso(ddtId) {
  return api.get(`/vendite/ddt/${ddtId}/righe-per-reso/`)
}
