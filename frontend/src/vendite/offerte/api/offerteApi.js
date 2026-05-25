// Client API per il sottodominio vendite/offerte commerciali.
// URL REST: POST = crea/azione, PATCH = aggiorna, GET = consultazione.
// Ref: backend/apps/vendite/api/urls_offerte.py (mount in urls_v1.py: /vendite/offerte/).

import api from '../../../core/api'

const BASE = '/vendite/offerte'

// --- Testata CRUD ---

export function listOfferte(params = {}) {
  return api.get(`${BASE}/`, { params })
}

export function getOfferta(id) {
  return api.get(`${BASE}/${id}/`)
}

// Crea offerta BOZZA. Il codice OFC-* e' generato dal trigger DB (Step 5
// brief): non va inviato nel payload (la whitelist BE lo rifiuta come unknown_key).
// Payload richiesto: emittente_fiscale_id, billing_account_id, istanza_utility_id,
// utility_id, listino_id, validita_dal. Opzionali: listino_versione_id,
// valore_variazione_globale, tipo_variazione_globale (solo PERCENTUALE),
// validita_al, meta.
export function createOfferta(payload) {
  return api.post(`${BASE}/`, payload)
}

// Aggiorna testata (solo in BOZZA, guard lato BE).
export function updateOfferta(id, payload) {
  return api.patch(`${BASE}/${id}/`, payload)
}

// Hard-delete offerta BOZZA orfana (drawer create abbandono).
// Per annullare un'offerta gia' BOZZA con motivazione di processo usare
// `annullaOfferta` (BOZZA -> ANNULLATA).
export function deleteOfferta(id) {
  return api.delete(`${BASE}/${id}/`)
}

// --- Transizioni di stato ---

// BOZZA -> EMESSA. Body vuoto, transizioni e validazioni nel trigger DB
// (listino_versione_id NOT NULL + versione ATTIVA).
export function emettiOfferta(id) {
  return api.post(`${BASE}/${id}/emetti/`, {})
}

// EMESSA -> ACCETTATA o RIFIUTATA. Motivazione obbligatoria su RIFIUTATA.
export function registraEsitoOfferta(id, { esito, motivazione }) {
  return api.post(`${BASE}/${id}/registra-esito/`, {
    esito,
    motivazione: motivazione || '',
  })
}

// BOZZA -> ANNULLATA (ritiro da noi). Motivazione obbligatoria.
// Non e' ammesso annullare da EMESSA (state machine asimmetrica: dopo
// l'emissione, o accetta il cliente o rifiuta, o si riemette come revisione).
export function annullaOfferta(id, { motivazione }) {
  return api.post(`${BASE}/${id}/annulla/`, { motivazione })
}

// --- Revisioni ---

// EMESSA -> crea rev.N+1 (BOZZA). La fn DB copia testata + eccezioni attive +
// utility 1:1 e marca la rev.N corrente come SUPERATA via trigger AFTER INSERT.
export function creaRevisioneOfferta(id) {
  return api.post(`${BASE}/${id}/crea-revisione/`, {})
}

// Catena revisioni che condividono il root. Lettura libera in ogni stato.
export function listRevisioniOfferta(id) {
  return api.get(`${BASE}/${id}/revisioni/`)
}

// --- Push a contratto ---

// ACCETTATA -> contratto DRAFT (Step 8 brief). Idempotente per costruzione:
// doppia invocazione fallisce con E_OFFERTA_CONTRATTO_GIA_GENERATO.
// `praticaId` opzionale: se valorizzato, il contratto viene collegato come
// sorgente di una pratica esistente.
// Risposta: { contratto_id, contratto_codice, sorgente_uid }.
export function pushOffertaAContratto(id, { praticaId = null } = {}) {
  const body = praticaId != null ? { pratica_id: praticaId } : {}
  return api.post(`${BASE}/${id}/push-contratto/`, body)
}

// --- Eccezioni (CRUD, solo BOZZA in write) ---

export function listEccezioni(offertaId) {
  return api.get(`${BASE}/${offertaId}/eccezioni/`)
}

export function createEccezione(offertaId, payload) {
  return api.post(`${BASE}/${offertaId}/eccezioni/`, payload)
}

export function updateEccezione(offertaId, eccezioneId, payload) {
  return api.patch(`${BASE}/${offertaId}/eccezioni/${eccezioneId}/`, payload)
}

export function deleteEccezione(offertaId, eccezioneId) {
  return api.delete(`${BASE}/${offertaId}/eccezioni/${eccezioneId}/`)
}

// --- Utility 1:1 (CRUD, solo BOZZA in write) ---

// La utility e' un record 1:1 con la testata offerta: gli endpoint usano il
// pattern collezione per coerenza con `contratti_utilities` (vedi piano
// BE+FE §3.4 C2). Read libero, write solo in BOZZA.
export function getOffertaUtility(offertaId) {
  return api.get(`${BASE}/${offertaId}/utility/`)
}

export function createOffertaUtility(offertaId, payload) {
  return api.post(`${BASE}/${offertaId}/utility/`, payload)
}

export function updateOffertaUtility(offertaId, utilityId, payload) {
  return api.patch(`${BASE}/${offertaId}/utility/${utilityId}/`, payload)
}
