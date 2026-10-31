// Client API per il sottodominio vendite/listini.
import api from '../../core/api'

const BASE = '/vendite/listini'

// --- Listini ---

export function listListini(params = {}) {
  return api.get(`${BASE}/`, { params })
}

export function getListino(id) {
  return api.get(`${BASE}/${id}/`)
}

export function createListino(payload) {
  return api.post(`${BASE}/`, payload)
}

export function updateListino(id, payload) {
  return api.patch(`${BASE}/${id}/`, payload)
}

// Elimina un listino mai usato. Backend rifiuta con 400 se versioni_count > 0
// (suggerisce PATCH attivo=false per disattivare).
export function deleteListino(id) {
  return api.delete(`${BASE}/${id}/`)
}

// --- Versioni ---

// La pagina delle versioni (lista `vendite.listini_versioni`, il tab «Versioni»
// del drawer listino): `search`, `limit`/`offset`, `order_by`/`order_dir`.
export function listVersioni(listinoId, params = {}) {
  return api.get(`${BASE}/${listinoId}/versioni/`, { params })
}

export function getVersione(listinoId, verId) {
  return api.get(`${BASE}/${listinoId}/versioni/${verId}/`)
}

export function createVersione(listinoId, payload) {
  return api.post(`${BASE}/${listinoId}/versioni/`, payload)
}

export function updateVersione(listinoId, verId, payload) {
  return api.patch(`${BASE}/${listinoId}/versioni/${verId}/`, payload)
}

// Elimina una versione in stato BOZZA con tutte le sue righe: il verbo del DB
// (fn_elimina_versione_listino) rifiuta fuori dalla BOZZA o se un documento la usa.
export function deleteVersione(listinoId, verId) {
  return api.delete(`${BASE}/${listinoId}/versioni/${verId}/`)
}

export function changeVersioneStato(listinoId, verId, payload) {
  return api.post(`${BASE}/${listinoId}/versioni/${verId}/stato/`, payload)
}

// «Chiudi» di una versione ATTIVA: fissa la fine (`valido_al`) o la toglie
// (`valido_al: null`), dal verbo del DB. La fine nel passato la rifiuta il DB
// sul campo `valido_al`; il PATCH generico della fine di una ATTIVA non passa.
export function programmaChiusuraVersione(listinoId, verId, valido_al) {
  return api.post(`${BASE}/${listinoId}/versioni/${verId}/chiusura/`, { valido_al })
}

// Clona una versione esistente (da qualunque stato) in una nuova versione BOZZA
// dello stesso listino, copiando le righe attive. D2 (target.valido_dal >=
// src.valido_dal) la dice il verbo del DB, sul campo valido_dal.
export function cloneVersione(listinoId, srcVerId, payload) {
  return api.post(`${BASE}/${listinoId}/versioni/${srcVerId}/clona/`, payload)
}

// Applica variazione percentuale massa ai prezzi delle righe attive
// di una versione BOZZA. Supporta dry_run per preview.
export function applicaVariazionePercentuale(listinoId, verId, payload) {
  return api.post(`${BASE}/${listinoId}/versioni/${verId}/applica-variazione/`, payload)
}

// Tipologie listino ammesse per la utility indicata (matrice
// config.listini_tipologie_utilities). Restituisce solo righe attive.
// Risposta: {"data": {"results": [{id, codice, descrizione, ...}]}}.
export function listTipologiePerUtility(utilityId) {
  return api.get(`${BASE}/tipologie-per-utility/`, {
    params: { utility_id: utilityId }
  })
}

// --- Righe prezzo ---

export function listRighe(listinoId, verId, params = {}) {
  return api.get(`${BASE}/${listinoId}/versioni/${verId}/righe/`, { params })
}

export function createRiga(listinoId, verId, payload) {
  return api.post(`${BASE}/${listinoId}/versioni/${verId}/righe/`, payload)
}

export function updateRiga(listinoId, verId, rigaId, payload) {
  return api.patch(`${BASE}/${listinoId}/versioni/${verId}/righe/${rigaId}/`, payload)
}

export function deleteRiga(listinoId, verId, rigaId) {
  return api.delete(`${BASE}/${listinoId}/versioni/${verId}/righe/${rigaId}/`)
}

// --- Test resolver prezzi v5 ---
// Endpoint diagnostico del resolver pricing v5: risolve il prezzo attraverso
// i 3 stadi (PROMO/CONTRATTO/CATEGORIA). Richiede tutti i parametri positivi
// (no null). L'emittente e' derivato dal JWT se non specificato.
export function resolvePrezzoV5(payload) {
  return api.post('/vendite/pricing/resolve/', payload)
}

// --- Diagnostica configurazione asset pricing v5 ---
// Endpoint complementare al resolver: ispeziona la configurazione (BA,
// contratto, matrice categoria→listino, promo) e ritorna una checklist
// a stadi + azioni suggerite. Read-only, nessun side-effect. Stesso shape
// payload del resolver (articolo, uom, ba, utility, data, classe_utenza,
// emittente derivato dal JWT).
export function diagnoseConfigurazionePricing(payload) {
  return api.post('/vendite/pricing/diagnose/', payload)
}

// --- L2 limiti variazione prezzo per utente corrente ---
// Ritorna { max_sconto_pct, max_maggiorazione_pct } risolti con cascata
// estesa user -> categoria_cliente -> group -> emittente -> default
// (refactor 2026-05-15). `billingAccountId` opzionale: se fornito alimenta
// il livello categoria_cliente con la categoria del BA destinatario; senza,
// il livello viene saltato. Usato dal FE per mostrare hint sotto il campo
// prezzo nel drawer riga preventivo coerente con il cliente target.
export function getLimitiPricingUtente(billingAccountId = null) {
  const params = {}
  if (billingAccountId != null && billingAccountId !== '') {
    params.billing_account_id = billingAccountId
  }
  return api.get('/vendite/pricing/limiti-utente/', { params })
}

// --- Bundle componenti BoM (modello unificato 2026-05-13) ---
// Endpoint per gestire `vendite.listini_righe_componenti`: prezzi bundle
// dei figli BoM di un padre composito in contesto versione listino.
// Vedi `manual/modello-componenti-bom.md` §8.


// Preview BoM corrente del padre composito + prezzi bundle già definiti
// per quella versione listino. Pre-popola il Dialog di editing.
export function previewBundleComponenti(listinoId, verId, padreId) {
  return api.get(`${BASE}/${listinoId}/versioni/${verId}/bundle/${padreId}/`)
}

// Upsert batch dei prezzi bundle per il padre composito. Solo versione BOZZA.
// `rows`: [{ articolo_componente_id, articolo_figlio_id, prezzo, iva_id? }, ...]
// Righe con prezzo null vengono ignorate (non gestite a bundle).
export function saveBundleComponenti(listinoId, verId, padreId, rows) {
  return api.post(
    `${BASE}/${listinoId}/versioni/${verId}/bundle/${padreId}/`,
    { rows },
  )
}

// Elimina TUTTI i prezzi bundle del composito dalla versione. Tabula rasa
// idempotente: soft-delete cascade su `listini_righe_componenti`. Solo
// versione BOZZA. Idempotente: 0 disattivati senza errore se gia' vuoto.
export function deleteBundleComponenti(listinoId, verId, padreId) {
  return api.delete(
    `${BASE}/${listinoId}/versioni/${verId}/bundle/${padreId}/`,
  )
}
