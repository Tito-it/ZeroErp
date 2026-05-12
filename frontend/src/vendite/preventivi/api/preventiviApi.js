// Client API per il sottodominio vendite/preventivi.
// URL REST standard: POST = crea/azione, PATCH = aggiorna, GET = consultazione.
// Ref: backend/apps/vendite/api/preventivi_urls.py

import api from '../../../core/api'
import { generateIdempotencyKey } from '../../../core/utils/idempotency'

const BASE = '/vendite/preventivi'

// --- Testata CRUD ---

export function listPreventivi(params = {}) {
  return api.get(`${BASE}/`, { params })
}

export function getPreventivo(id) {
  return api.get(`${BASE}/${id}/`)
}

export function createPreventivo(payload) {
  return api.post(`${BASE}/`, payload)
}

export function updatePreventivo(id, payload) {
  return api.patch(`${BASE}/${id}/`, payload)
}

// Hard-delete preventivo BOZZA orfano (zero righe, zero pratiche).
// Usato dal flusso "abbandono bozza" del drawer create. Per stati avanzati
// usare invece cambiaStatoPreventivo(id, {nuovo_stato: 'ANNULLATO'}).
export function deletePreventivo(id) {
  return api.delete(`${BASE}/${id}/`)
}

// --- Azioni testata ---

export function cambiaStatoPreventivo(id, payload) {
  return api.post(`${BASE}/${id}/stato/`, payload)
}

export function creaRevisione(id) {
  return api.post(`${BASE}/${id}/revisione/`, {})
}

// --- Righe ---

export function listRighe(preventivoId) {
  return api.get(`${BASE}/${preventivoId}/righe/`)
}

export function createRiga(preventivoId, payload) {
  return api.post(`${BASE}/${preventivoId}/righe/`, payload)
}

export function updateRiga(preventivoId, rigaId, payload) {
  return api.patch(`${BASE}/${preventivoId}/righe/${rigaId}/`, payload)
}

export function deleteRiga(preventivoId, rigaId) {
  return api.delete(`${BASE}/${preventivoId}/righe/${rigaId}/`)
}

// Suggerisce il prezzo riga via pricing resolver v5. Il BE deriva BA, utility
// e data riferimento dal preventivo; al FE basta passare articolo_id + uom_id.
// Risposta: { prezzo_finale, prezzo_base_snapshot, origine, listino_id,
//   contratto_id, promo_id, tipo_variazione_applicata, valore_variazione_applicata }.
// Lettura pura, senza side-effect.
export function suggerisciPrezzoRiga(preventivoId, payload) {
  return api.post(`${BASE}/${preventivoId}/righe/suggerisci-prezzo/`, payload)
}

// Riepilogo IVA aggregato del preventivo (una riga per aliquota IVA, regola
// fiscale DPR 633/72 art. 21). Calcolo gia' eseguito in DB e mantenuto da
// trigger AFTER su preventivi_righe: il FE legge solo lo stato corrente.
// Risposta: array di { iva_id, iva_codice, iva_descrizione, iva_aliquota,
//   imponibile, imposta, arrotondamento, totale_riga, ... }.
export function getRiepilogoIva(preventivoId) {
  return api.get(`${BASE}/${preventivoId}/riepilogo-iva/`)
}

// --- Componenti BoM CASO A (refactor componenti 2026-05-11) ---
// Ogni componente esposto in fattura della riga padre composita CASO A diventa
// una riga negoziabile a se stante. Init implicito post-create_riga via
// gestisci_riga BE — niente POST pubblico dedicato.
// Il prezzo della riga padre e' SUM(componenti × coeff_qta), ricalcolato dai
// trigger DB a ogni mutazione del componente.

// Form atomic 2026-05-12: preview pre-save dei componenti per il drawer riga.
// Read-only: per ogni componente esposto del padre ritorna prezzo_suggerito
// (NULL + resolver_error_reason se manca listino), origine_prezzo, qta.
// Il FE pre-popola una tabella editabile; l'operatore valorizza eventuali
// NULL prima del save (con autorizzazione `prezzo_override_manuale`).
// Il payload del save include `componenti_overrides` con i prezzi manuali.
export function previewRigaComponenti(preventivoId, payload) {
  return api.post(
    `${BASE}/${preventivoId}/righe/preview-componenti/`,
    payload,
  )
}

export function listRigaComponenti(preventivoId, rigaId) {
  return api.get(`${BASE}/${preventivoId}/righe/${rigaId}/componenti/`)
}

// Update fine del singolo componente (prezzo override, IVA, ordine, origine).
// PATCH coerente con updateRiga/updatePreventivo: nessuna Idempotency-Key
// (BE non la richiede, usa request.data diretto, no handle_post_json).
export function updateRigaComponente(preventivoId, rigaId, componenteId, payload) {
  return api.patch(
    `${BASE}/${preventivoId}/righe/${rigaId}/componenti/${componenteId}/`,
    payload,
  )
}

// Soft delete componente: il trigger DB ricalcola il prezzo della riga padre.
export function deleteRigaComponente(preventivoId, rigaId, componenteId) {
  return api.delete(
    `${BASE}/${preventivoId}/righe/${rigaId}/componenti/${componenteId}/`,
  )
}

// --- Indirizzi ---

export function listIndirizzi(preventivoId) {
  return api.get(`${BASE}/${preventivoId}/indirizzi/`)
}

export function upsertIndirizzo(preventivoId, payload) {
  return api.post(`${BASE}/${preventivoId}/indirizzi/`, payload)
}

// --- Integrazione ---

// Idempotency-Key obbligatoria lato BE (`require_idempotency_key=True` su
// preventivi_views.py): push-commessa e' write-once, evitare doppio push
// in caso di retry/click ripetuto.
export function pushCommessa(preventivoId) {
  return api.post(
    `${BASE}/${preventivoId}/push-commessa/`,
    {},
    { headers: { 'Idempotency-Key': generateIdempotencyKey() } },
  )
}

export function statoFatturazione(preventivoId) {
  return api.get(`${BASE}/${preventivoId}/stato-fatturazione/`)
}

// Idempotency-Key obbligatoria lato BE (`require_idempotency_key=True`):
// la generazione pratica e' write-once, evita doppia pratica su retry.
export function generaPratica(preventivoId, payload) {
  return api.post(
    `${BASE}/${preventivoId}/genera-pratica/`,
    payload,
    { headers: { 'Idempotency-Key': generateIdempotencyKey() } },
  )
}

export function listPratiche(preventivoId) {
  return api.get(`${BASE}/${preventivoId}/pratiche/`)
}
