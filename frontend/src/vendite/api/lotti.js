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
