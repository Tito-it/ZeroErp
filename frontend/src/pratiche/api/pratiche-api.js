// Client API per il modulo Pratiche — motore workflow.
// URL REST standard: POST = crea/azione, PATCH = aggiorna, GET = consultazione.
// Ref: docs/it/dev/api.md, backend/apps/pratiche/api/urls_v1.py

import api from '../../core/api'

const BASE = '/pratiche'

// --- Pratiche CRUD ---

export function listPratiche(params = {}) {
  return api.get(`${BASE}/`, { params })
}

export function getPratica(praticaId) {
  return api.get(`${BASE}/${praticaId}/`)
}

export function createPratica(payload) {
  return api.post(`${BASE}/`, payload)
}

export function updatePratica(praticaId, payload) {
  return api.patch(`${BASE}/${praticaId}/`, payload)
}

// --- Azioni pratica ---

export function cambiaStatoPratica(praticaId, payload) {
  return api.post(`${BASE}/${praticaId}/stato/`, payload)
}

export function assegnaPratica(praticaId, payload) {
  return api.post(`${BASE}/${praticaId}/assegnazione/`, payload)
}

export function sospendiPratica(praticaId, payload = {}) {
  return api.post(`${BASE}/${praticaId}/sospendi/`, payload)
}

export function riattivaPratica(praticaId, payload = {}) {
  return api.post(`${BASE}/${praticaId}/riattiva/`, payload)
}

// --- Consultazione pratica ---

export function fetchGiornale(praticaId, params = {}) {
  return api.get(`${BASE}/${praticaId}/giornale/`, { params })
}

export function fetchSospensioni(praticaId, params = {}) {
  return api.get(`${BASE}/${praticaId}/sospensioni/`, { params })
}

export function fetchCalcoliTempo(praticaId, params = {}) {
  return api.get(`${BASE}/${praticaId}/calcoli-tempo/`, { params })
}

// --- Percorso (roadmap: template_flussi del tipo + stato istanziazione) ---

export function fetchPercorso(praticaId) {
  return api.get(`${BASE}/${praticaId}/percorso/`)
}

// --- Flussi CRUD ---

export function listFlussi(praticaId, params = {}) {
  return api.get(`${BASE}/${praticaId}/flussi/`, { params })
}

export function getFlusso(praticaId, flussoId) {
  return api.get(`${BASE}/${praticaId}/flussi/${flussoId}/`)
}

// ⭐ Dove vive un flusso, dal solo id: l'unica rotta dei flussi non annidata
// sotto la pratica. Serve a chi il flusso lo nomina DA FUORI e non ha la
// pratica in mano — il primo caso reale e' il bersaglio di un errore, che
// porta `FLUSSO:<id>` e nient'altro (deep-link `?flusso_id=` della dashboard).
// ⚠️ Risponde `{ pratica_id }` e non il flusso: il dettaglio resta uno solo.
export function getPraticaDiFlusso(flussoId) {
  return api.get(`${BASE}/flussi/${flussoId}/pratica/`)
}

// ⚠️ `params` porta l'emittente della pratica in QUERY: la rotta e' quella
//    della lista `pratiche.flussi` (`lista_codice` + `lista_emittente_param`),
//    e il cancello di perimetro vale per OGNI metodo e legge solo la query.
//    Senza, chi vede piu' emittenti (il super admin su «Tutti») prende un 422
//    alla creazione. Stessa forma di `createRegistro`.
export function createFlusso(praticaId, payload, params = {}) {
  return api.post(`${BASE}/${praticaId}/flussi/`, payload, { params })
}

// --- Azioni flusso ---

export function cambiaStatoFlusso(praticaId, flussoId, payload) {
  return api.post(`${BASE}/${praticaId}/flussi/${flussoId}/stato/`, payload)
}

export function sospendiFlusso(praticaId, flussoId, payload = {}) {
  return api.post(`${BASE}/${praticaId}/flussi/${flussoId}/sospendi/`, payload)
}

export function riattivaFlusso(praticaId, flussoId, payload = {}) {
  return api.post(`${BASE}/${praticaId}/flussi/${flussoId}/riattiva/`, payload)
}

// Assegna il flusso a un operatore e/o a un reparto. Il payload inviato
// distingue chiave assente (non toccare) da null esplicito (de-assegna): il
// caller include solo le chiavi che intende applicare.
export function assegnaFlusso(praticaId, flussoId, payload) {
  return api.post(`${BASE}/${praticaId}/flussi/${flussoId}/assegnazione/`, payload)
}

// --- Consultazione flusso ---

export function fetchPrerequisiti(praticaId, flussoId) {
  return api.get(`${BASE}/${praticaId}/flussi/${flussoId}/prerequisiti/`)
}

export function fetchCanaliFlusso(praticaId, flussoId) {
  return api.get(`${BASE}/${praticaId}/flussi/${flussoId}/canali/`)
}

// --- Generazione cross-pratica ---

export function fetchRegoleGenerazione(praticaId, flussoId) {
  return api.get(`${BASE}/${praticaId}/flussi/${flussoId}/regole-generazione/`)
}

export function generaPratica(praticaId, flussoId, payload) {
  return api.post(`${BASE}/${praticaId}/flussi/${flussoId}/genera/`, payload)
}

export function fetchPraticheGenerate(praticaId, flussoId) {
  return api.get(`${BASE}/${praticaId}/flussi/${flussoId}/pratiche-generate/`)
}

// --- Note pratica ---

export function fetchNote(praticaId) {
  return api.get(`${BASE}/${praticaId}/note/`)
}

export function createNota(praticaId, payload) {
  return api.post(`${BASE}/${praticaId}/note/`, payload)
}

export function updateNota(praticaId, notaId, payload) {
  return api.patch(`${BASE}/${praticaId}/note/${notaId}/`, payload)
}

export function deleteNota(praticaId, notaId) {
  return api.delete(`${BASE}/${praticaId}/note/${notaId}/`)
}

// --- Allegati pratica ---

export function fetchAllegati(praticaId) {
  return api.get(`${BASE}/${praticaId}/allegati/`)
}

export function createAllegato(praticaId, payload) {
  return api.post(`${BASE}/${praticaId}/allegati/`, payload)
}

export function deleteAllegato(praticaId, allegatoId) {
  return api.delete(`${BASE}/${praticaId}/allegati/${allegatoId}/`)
}

// --- Coda lavoro operatore ---

export function fetchCodaLavoro(params = {}) {
  return api.get(`${BASE}/coda-lavoro/`, { params })
}

export function prendiInCaricoFlusso(flussoId) {
  return api.post(`${BASE}/flussi/${flussoId}/prendi-in-carico/`, {})
}

// Operatori (risorse umane attive) di un reparto, per il picker di
// assegnazione del flusso a un operatore specifico del reparto.
export function fetchOperatoriReparto(unitaOrganizzativaId) {
  return api.get(`${BASE}/operatori/`, {
    params: { unita_organizzativa_id: unitaOrganizzativaId },
  })
}

// --- Competenze flussi ---

export function fetchCompetenzeFlussi() {
  return api.get(`${BASE}/competenze-flussi/`)
}

export function createCompetenzaFlusso(payload) {
  return api.post(`${BASE}/competenze-flussi/`, payload)
}

export function deleteCompetenzaFlusso(competenzaId) {
  return api.delete(`${BASE}/competenze-flussi/${competenzaId}/`)
}

// --- Formule tempo (lookup globale, non legato a pratica) ---

export function fetchFormuleTempo(params = {}) {
  return api.get(`${BASE}/formule-tempo/`, { params })
}
