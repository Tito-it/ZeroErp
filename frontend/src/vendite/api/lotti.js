// Client API lotti di fatturazione — registro dei giri (cockpit Fase B).
// Doc BE: api_lotti (lista+dettaglio), api_lotto_fatture_list, pipeline.
// La lista/dettaglio sono read; le azioni (avanza step, rerun, reset) sono
// write con Idempotency-Key. Nessuna logica: la macchina step/gate vive nel
// motore DB/BE, il drawer diagnostico rende ed esercita.
import api from '../../core/api'
import { generateIdempotencyKey } from '../../core/utils/idempotency'

const BASE = '/vendite/lotti'

// GET lista lotti paginata (filtri competenza/stato/tipo_doc/emittente/utility).
export function listLotti(params = {}) {
  return api.get(`${BASE}/`, { params })
}

// GET dettaglio testata lotto (B-1). 404 su lotto fuori scope/inesistente.
export function getLotto(lottoId) {
  return api.get(`${BASE}/${lottoId}/`)
}

// GET fatture del lotto (stato esecuzione, esclusa, ordinamento, paginazione).
export function listLottoFatture(lottoId, params = {}) {
  return api.get(`${BASE}/${lottoId}/fatture/`, { params })
}

// GET task-run runtime del lotto (tentativi/esiti per step).
export function listLottoTaskRuns(lottoId, { limit = 100 } = {}) {
  return api.get(`${BASE}/${lottoId}/task-runs/`, { params: { limit } })
}

// GET riepilogo segnalazioni del lotto (critical/warning/attention + blocco step).
export function getLottoSegnalazioni(lottoId) {
  return api.get(`${BASE}/${lottoId}/segnalazioni/`)
}

// POST avanza pipeline lotto di UN step (com'è il motore). Riusata anche per il
// rerun su ERRORE: stesso endpoint, stesso lotto. `lock_batch_id` opzionale per
// correlare gli eventi del giro.
export function runLottoPipeline(lottoId, { lockBatchId = null } = {}) {
  const payload = { lotto_id: lottoId }
  if (lockBatchId) payload.lock_batch_id = lockBatchId
  return api.post(
    '/vendite/pipeline/run/',
    payload,
    { headers: { 'Idempotency-Key': generateIdempotencyKey() } },
  )
}

// POST «Rendi definitive» (C-4): numerazione di un singolo lotto EMESSA. Esegue
// lo step DEFINITIVA (numera + accoda stampa). Gate fiscale separato (I-7):
// endpoint e permesso dedicati (numera_fatture_lotti), distinto da «Avanza».
export function numeraLotto(lottoId) {
  return api.post(
    `/vendite/fatturazione/lotti/${lottoId}/numera/`,
    {},
    { headers: { 'Idempotency-Key': generateIdempotencyKey() } },
  )
}

// POST ristampa MASSIVA di un lotto DEFINITIVA (C-8): accoda in coda stampa una
// riga per fattura non esclusa; il worker draina_coda_stampa le renderizza
// (async). Ritorna { lotto_id, accodate }. Re-stampa, mai numerazione (gate BE
// DEFINITIVA). Accodamento sincrono (non un job con polling).
export function ristampaLotto(lottoId) {
  return api.post(
    `/vendite/fatturazione/lotti/${lottoId}/ristampa/`,
    {},
    { headers: { 'Idempotency-Key': generateIdempotencyKey() } },
  )
}

// GET esiti giri fatturazione per corsia (job_run_log) + stato coda stampa
// (conteggi per stato, scope emittente operatore). Sola lettura (C-5).
export function getFatturazioneEsiti() {
  return api.get('/vendite/fatturazione/esiti/')
}

// POST «Fattura competenza» (C-3/C-6): avvia un GIRO di fatturazione on-demand,
// NON bloccante (I-3). Accoda un job in dbops.coda_lavori e ritorna subito
// { job_id, stato: 'PENDING' }; l'avanzamento si segue via getFatturazioneRun.
// Corsia differita → si ferma a EMESSA (D-1): la numerazione è atto separato
// (I-7). Idempotenza a 2 layer: header HTTP + chiave business competenza+scope.
export function runFatturazione(competenzaMese) {
  return api.post(
    '/vendite/fatturazione/run/',
    { competenza_mese: competenzaMese },
    { headers: { 'Idempotency-Key': generateIdempotencyKey() } },
  )
}

// POST «Rendi definitive competenza» (C-4/C-7): numerazione di PERIMETRO, NON
// bloccante. Accoda un job che esegue lo step DEFINITIVA (numera + accoda
// stampa) sui lotti EMESSA del mese. Atto fiscale SEPARATO dalla fatturazione
// (I-7). Ritorna { job_id, stato: 'PENDING' }; avanzamento via getFatturazioneRun.
export function runNumerazione(competenzaMese) {
  return api.post(
    '/vendite/fatturazione/numera/',
    { competenza_mese: competenzaMese },
    { headers: { 'Idempotency-Key': generateIdempotencyKey() } },
  )
}

// GET stato di un job accodato (polling, C-3/C-4/C-6/C-7). Ownership per SCOPE:
// un job di altro scope/inesistente → 404. Sola lettura (nessuna Idempotency-Key).
export function getFatturazioneRun(jobId) {
  return api.get(`/vendite/fatturazione/run/${jobId}/`)
}

// POST reset del lotto a bozza (DEMOLIZIONE pre-fiscale): cancella le fatture
// non numerate; le attività tornano libere per un lotto nuovo. Azione forte.
export function resetLottoDraft(lottoId) {
  return api.post(
    `${BASE}/${lottoId}/reset-draft/`,
    {},
    { headers: { 'Idempotency-Key': generateIdempotencyKey() } },
  )
}

// POST reset di una singola fattura del lotto a DRAFT (fattura strettamente DRAFT).
export function resetLottoFatturaDraft(lottoId, fatturaId) {
  return api.post(
    `${BASE}/${lottoId}/fatture/${fatturaId}/reset-draft/`,
    {},
    { headers: { 'Idempotency-Key': generateIdempotencyKey() } },
  )
}
