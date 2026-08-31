// Client API per il modulo Anagrafiche — gestione geografica.
// URL REST standard: POST = crea, PATCH = aggiorna (nessun verbo nel path).
// Ref: docs/it/dev/api.md

import api from '../../core/api'

const BASE = '/anagrafiche'

// --- Indirizzi dettaglio ---

export function listIndirizzi(params = {}) {
  return api.get(`${BASE}/indirizzi/`, { params })
}

export function getIndirizzo(id) {
  return api.get(`${BASE}/indirizzi/${id}/`)
}

export function createIndirizzo(payload) {
  return api.post(`${BASE}/indirizzi/`, payload)
}

export function updateIndirizzo(id, payload) {
  return api.patch(`${BASE}/indirizzi/${id}/`, payload)
}

// --- Codici postali ---

export function listCodiciPostali(params = {}) {
  return api.get(`${BASE}/codici-postali/`, { params })
}

export function createCodicePostale(payload) {
  return api.post(`${BASE}/codici-postali/`, payload)
}

export function updateCodicePostale(id, payload) {
  return api.patch(`${BASE}/codici-postali/${id}/`, payload)
}

export function lookupCodiciPostaliByComune(comuneId) {
  return api.get(`${BASE}/codici-postali/`, { params: { comune_id: comuneId, limit: 200 } })
}

// --- Toponomastica ---

export function listToponomastica(params = {}) {
  return api.get(`${BASE}/toponomastica/`, { params })
}

export function createToponomastica(payload) {
  return api.post(`${BASE}/toponomastica/`, payload)
}

export function updateToponomastica(id, payload) {
  return api.patch(`${BASE}/toponomastica/${id}/`, payload)
}

// --- Comuni ---

export function listComuni(params = {}) {
  return api.get(`${BASE}/comuni/`, { params })
}

export function createComune(payload) {
  return api.post(`${BASE}/comuni/`, payload)
}

// --- Province ---

export function listProvince(params = {}) {
  return api.get(`${BASE}/province/`, { params })
}

export function lookupProvince() {
  return api.get(`${BASE}/province/lookup/`)
}

export function createProvincia(payload) {
  return api.post(`${BASE}/province/`, payload)
}

export function updateProvincia(id, payload) {
  return api.patch(`${BASE}/province/${id}/`, payload)
}

// --- Regioni ---

export function listRegioni(params = {}) {
  return api.get(`${BASE}/regioni/`, { params })
}

export function createRegione(payload) {
  return api.post(`${BASE}/regioni/`, payload)
}

export function updateRegione(id, payload) {
  return api.patch(`${BASE}/regioni/${id}/`, payload)
}

export function lookupRegioni(params = {}) {
  return api.get(`${BASE}/regioni/lookup/`, { params })
}

// --- Stati ---

export function listStati(params = {}) {
  return api.get(`${BASE}/stati/`, { params })
}

export function createStato(payload) {
  return api.post(`${BASE}/stati/`, payload)
}

export function updateStato(id, payload) {
  return api.patch(`${BASE}/stati/${id}/`, payload)
}

// --- Soggetti ---

export function listSoggetti(params = {}) {
  return api.get(`${BASE}/soggetti/`, { params })
}

// Scopo: Export CSV/Excel della lista soggetti (DEF-1).
//        `params` accetta gli stessi filtri del list endpoint
//        (search/tipo_soggetto_dettaglio_id/order_*) + obbligatorio
//        `formato` ('csv' | 'xlsx'). Risposta come Blob per download
//        diretto. Errori: 422 se >10.000 righe (caller deve gestire).
export function exportSoggetti(params = {}) {
  return api.get(`${BASE}/soggetti/export/`, {
    params,
    responseType: 'blob',
  })
}

export function getSoggetto(id) {
  return api.get(`${BASE}/soggetti/${id}/`)
}

export function createSoggetto(payload) {
  return api.post(`${BASE}/soggetti/`, payload)
}

export function updateSoggetto(id, payload) {
  return api.patch(`${BASE}/soggetti/${id}/`, payload)
}

export function listSoggettoContatti(soggettoId) {
  return api.get(`${BASE}/soggetti/${soggettoId}/contatti/`)
}

export function createSoggettoContatto(soggettoId, payload) {
  return api.post(`${BASE}/soggetti/${soggettoId}/contatti/`, payload)
}

export function updateSoggettoContatto(soggettoId, contattoId, payload) {
  return api.patch(`${BASE}/soggetti/${soggettoId}/contatti/${contattoId}/`, payload)
}

export function deleteSoggettoContatto(soggettoId, contattoId) {
  return api.delete(`${BASE}/soggetti/${soggettoId}/contatti/${contattoId}/`)
}

export function listSoggettoIndirizzi(soggettoId) {
  return api.get(`${BASE}/soggetti/${soggettoId}/indirizzi/`)
}

export function createSoggettoIndirizzo(soggettoId, payload) {
  return api.post(`${BASE}/soggetti/${soggettoId}/indirizzi/`, payload)
}

export function replaceSoggettoIndirizzo(soggettoId, indirizzoSoggettoId, payload) {
  return api.put(`${BASE}/soggetti/${soggettoId}/indirizzi/${indirizzoSoggettoId}/`, payload)
}

export function deleteSoggettoIndirizzo(soggettoId, indirizzoSoggettoId) {
  return api.delete(`${BASE}/soggetti/${soggettoId}/indirizzi/${indirizzoSoggettoId}/`)
}

export function listSoggettoRuoli(soggettoId) {
  return api.get(`${BASE}/soggetti/${soggettoId}/ruoli/`)
}

export function assignSoggettoRuolo(soggettoId, payload) {
  return api.post(`${BASE}/soggetti/${soggettoId}/ruoli/`, payload)
}

export function generaCF(payload) {
  return api.post(`${BASE}/soggetti/genera-cf/`, payload)
}

export function validaCFPIVA(payload) {
  return api.post(`${BASE}/soggetti/valida-cf-piva/`, payload)
}

export function checkIndirizzoDuplicato(payload) {
  return api.post(`${BASE}/indirizzi/check-duplicato/`, payload)
}

// --- Stati ---

export function lookupStati() {
  return api.get(`${BASE}/stati/lookup/`)
}

// --- Conti bancari soggetto ---

// ============================================================
//  Titoli IVA del soggetto (I7 / D10)
//  Il documento registrato che SOSTITUISCE l'aliquota ordinaria di una riga.
//  Proprietario il soggetto, destinatario l'emittente (D10-bis).
// ============================================================

export function listSoggettoTitoliIva(soggettoId) {
  return api.get(`${BASE}/soggetti/${soggettoId}/titoli-iva/`)
}

export function getSoggettoTitoloIva(soggettoId, titoloId) {
  return api.get(`${BASE}/soggetti/${soggettoId}/titoli-iva/${titoloId}/`)
}

export function createSoggettoTitoloIva(soggettoId, payload) {
  return api.post(`${BASE}/soggetti/${soggettoId}/titoli-iva/`, payload)
}

export function updateSoggettoTitoloIva(soggettoId, titoloId, payload) {
  return api.patch(`${BASE}/soggetti/${soggettoId}/titoli-iva/${titoloId}/`, payload)
}

export function deleteSoggettoTitoloIva(soggettoId, titoloId) {
  return api.delete(`${BASE}/soggetti/${soggettoId}/titoli-iva/${titoloId}/`)
}

// Ambiti: l'oggetto su cui il titolo si applica (D12). ⚠️ Non e' un'etichetta:
// e' la condizione di applicabilita', valutata riga per riga dal risolutore.
export function listTitoloIvaAmbiti(soggettoId, titoloId) {
  return api.get(`${BASE}/soggetti/${soggettoId}/titoli-iva/${titoloId}/ambiti/`)
}

export function createTitoloIvaAmbito(soggettoId, titoloId, payload) {
  return api.post(`${BASE}/soggetti/${soggettoId}/titoli-iva/${titoloId}/ambiti/`, payload)
}

export function deleteTitoloIvaAmbito(soggettoId, titoloId, ambitoId) {
  return api.delete(`${BASE}/soggetti/${soggettoId}/titoli-iva/${titoloId}/ambiti/${ambitoId}/`)
}

// Registro movimenti del plafond (D5). ⛔ In POST si scrive SOLO una forzatura
// manuale: fatture e note di credito le produce la fatturazione (I4).
export function listTitoloIvaMovimenti(soggettoId, titoloId) {
  return api.get(`${BASE}/soggetti/${soggettoId}/titoli-iva/${titoloId}/movimenti/`)
}

export function createTitoloIvaForzatura(soggettoId, titoloId, payload) {
  return api.post(`${BASE}/soggetti/${soggettoId}/titoli-iva/${titoloId}/movimenti/`, payload)
}

// Annulla un movimento con il CONTRO-MOVIMENTO (Q7). ⛔ Non e' una DELETE:
// l'annullo aggiunge una riga di segno opposto che punta a quella annullata —
// il registro resta append-only e la traccia resta.
export function annullaTitoloIvaMovimento(soggettoId, titoloId, movimentoId, payload) {
  return api.post(
    `${BASE}/soggetti/${soggettoId}/titoli-iva/${titoloId}/movimenti/${movimentoId}/annulla/`,
    payload,
  )
}

// Presidio cross-soggetto: i titoli il cui consumo ha superato il tetto (Q4).
export function listTitoliIvaSfondati() {
  return api.get(`${BASE}/titoli-iva/sfondati/`)
}

export function listSoggettoContiBancari(soggettoId) {
  return api.get(`${BASE}/soggetti/${soggettoId}/conti-bancari/`)
}

export function createSoggettoContoBancario(soggettoId, payload) {
  return api.post(`${BASE}/soggetti/${soggettoId}/conti-bancari/`, payload)
}

export function updateSoggettoContoBancario(soggettoId, cbId, payload) {
  return api.patch(`${BASE}/soggetti/${soggettoId}/conti-bancari/${cbId}/`, payload)
}

export function deleteSoggettoContoBancario(soggettoId, cbId) {
  return api.delete(`${BASE}/soggetti/${soggettoId}/conti-bancari/${cbId}/`)
}

// --- Conti bancari lookup ---

export function lookupContiBancari(search) {
  return api.get(`${BASE}/conti-bancari/lookup/`, { params: { search } })
}

export function lookupBankBranches(search) {
  return api.get(`${BASE}/bank-branches/lookup/`, { params: { search } })
}

// --- Clienti ---

export function listClienti(params = {}) {
  return api.get(`${BASE}/clienti/`, { params })
}

// Scopo: Export CSV/Excel della lista clienti (DEF-1).
//        `params` accetta gli stessi filtri del list endpoint
//        (search/utility_id/stato_cliente_id/order_*) + obbligatorio
//        `format` ('csv' | 'xlsx'). Risposta come Blob per download
//        diretto. Errori: 422 se >10.000 righe (caller deve gestire).
export function exportClienti(params = {}) {
  return api.get(`${BASE}/clienti/export/`, {
    params,
    responseType: 'blob',
  })
}

export function getCliente(id) {
  return api.get(`${BASE}/clienti/${id}/`)
}

export function createCliente(payload) {
  return api.post(`${BASE}/clienti/`, payload)
}

export function updateCliente(clienteId, payload) {
  return api.patch(`${BASE}/clienti/${clienteId}/`, payload)
}

// Lista utility "guidate da emittente" per un BA esistente.
// Refactor operatore-emittenti, sez. 3 del WIP. Ritorna utility ammesse
// per il ruolo del soggetto del BA filtrate sull'emittente associato +
// parametri override (is_personalizzata_per_ef, soglie, arrotondamento).
// ruolo: 'CL' (cliente) | 'FO' (fornitore) | 'GE' (gestore).
export function listUtilitiesPerBillingAccount(billingAccountId, ruolo) {
  return api.get(`${BASE}/billing-account/${billingAccountId}/utilities/`, {
    params: { ruolo },
  })
}

// --- Fornitori ---

export function listFornitori(params = {}) {
  return api.get(`${BASE}/fornitori/`, { params })
}

// Scopo: Export CSV/Excel della lista fornitori (DEF-1).
//        `params` accetta gli stessi filtri del list endpoint
//        (search/stato_fornitore_id/order_*) + obbligatorio
//        `formato` ('csv' | 'xlsx'). Risposta come Blob per download
//        diretto. Errori: 422 se >10.000 righe (caller deve gestire).
export function exportFornitori(params = {}) {
  return api.get(`${BASE}/fornitori/export/`, {
    params,
    responseType: 'blob',
  })
}

export function getFornitore(id) {
  return api.get(`${BASE}/fornitori/${id}/`)
}

export function createFornitore(payload) {
  return api.post(`${BASE}/fornitori/`, payload)
}

export function updateFornitore(fornitoreId, payload) {
  return api.patch(`${BASE}/fornitori/${fornitoreId}/`, payload)
}

// --- Contatti ruolo ---

export function listRuoloContatti(ruoloId, params = {}) {
  return api.get(`${BASE}/ruoli/${ruoloId}/contatti/`, { params })
}

export function createRuoloContatto(ruoloId, payload) {
  return api.post(`${BASE}/ruoli/${ruoloId}/contatti/`, payload)
}

export function updateRuoloContatto(ruoloId, contattoId, payload) {
  return api.patch(`${BASE}/ruoli/${ruoloId}/contatti/${contattoId}/`, payload)
}

export function deleteRuoloContatto(ruoloId, contattoId) {
  return api.delete(`${BASE}/ruoli/${ruoloId}/contatti/${contattoId}/`)
}

// --- Conti bancari ruolo ---

export function listRuoloContiBancari(ruoloId, params = {}) {
  return api.get(`${BASE}/ruoli/${ruoloId}/conti-bancari/`, { params })
}

export function createRuoloContoBancario(ruoloId, payload) {
  return api.post(`${BASE}/ruoli/${ruoloId}/conti-bancari/`, payload)
}

export function updateRuoloContoBancario(ruoloId, cbId, payload) {
  return api.patch(`${BASE}/ruoli/${ruoloId}/conti-bancari/${cbId}/`, payload)
}

export function deleteRuoloContoBancario(ruoloId, cbId) {
  return api.delete(`${BASE}/ruoli/${ruoloId}/conti-bancari/${cbId}/`)
}

// --- Indirizzi ruolo ---

export function listRuoloIndirizzi(ruoloId, params = {}) {
  return api.get(`${BASE}/ruoli/${ruoloId}/indirizzi/`, { params })
}

export function createRuoloIndirizzo(ruoloId, payload) {
  return api.post(`${BASE}/ruoli/${ruoloId}/indirizzi/`, payload)
}

export function updateRuoloIndirizzo(ruoloId, indirizzoId, payload) {
  return api.patch(`${BASE}/ruoli/${ruoloId}/indirizzi/${indirizzoId}/`, payload)
}

export function deleteRuoloIndirizzo(ruoloId, indirizzoId) {
  return api.delete(`${BASE}/ruoli/${ruoloId}/indirizzi/${indirizzoId}/`)
}

// --- Ruoli config resolver ---

export function getConfigResolver(tipoRuoloCodice) {
  return api.get(`${BASE}/ruoli/${tipoRuoloCodice}/config-resolver/`)
}
