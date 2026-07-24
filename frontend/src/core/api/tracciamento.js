// Client API del tracciamento core — gestione code (coda lavori generica +
// coda stampa). Endpoint sotto /core/tracciamento/ (area core), brief
// brief-be-fe-gestione-code-lavori-stampa. Le liste sono offset-based
// ({count, results}); le azioni richiedono Idempotency-Key.
import api from '../api'
import { generateIdempotencyKey } from '../utils/idempotency'

// GET conteggi per il badge top bar: job vivi (PENDING/IN_CORSO) delle due
// code, scoped all'operatore, + liveness dei worker drainer. Pollato a 60s.
export function getCodeConteggi() {
  return api.get('/core/tracciamento/code/conteggi/')
}

// GET lista paginata della coda lavori generica. params: ambito ('miei'|
// 'tutti', tutti richiede code_manage), stato, tipo, solo_vivi, data_da,
// data_a, limit, offset. Ogni riga porta is_mio (calcolato dal BE, P-5).
export function listCodaLavori(params) {
  return api.get('/core/tracciamento/coda-lavori/', { params })
}

// GET dettaglio completo di un job (payload, timeline, tentativi/errore,
// esito, proprietario, is_mio). Fuori scope/inesistente → 404.
export function getCodaLavoroDettaglio(jobId) {
  return api.get(`/core/tracciamento/coda-lavori/${jobId}/`)
}

// POST annulla un job PENDING (→ ANNULLATO). Solo job propri (o code_manage).
export function annullaCodaLavoro(jobId) {
  return api.post(
    `/core/tracciamento/coda-lavori/${jobId}/annulla/`,
    {},
    { headers: { 'Idempotency-Key': generateIdempotencyKey() } },
  )
}

// POST requeue/sblocco di un job IN_CORSO o ERRORE (→ PENDING, alza
// max_tentativi di extraTentativi, default BE 3).
export function requeueCodaLavoro(jobId, extraTentativi = null) {
  const body = extraTentativi != null ? { extra_tentativi: extraTentativi } : {}
  return api.post(
    `/core/tracciamento/coda-lavori/${jobId}/requeue/`,
    body,
    { headers: { 'Idempotency-Key': generateIdempotencyKey() } },
  )
}

// GET lista paginata della coda stampa (outbox PDF). params: ambito, stato,
// solo_vivi, lotto_id, data_da, data_a, limit, offset. Scope emittente BE.
export function listCodaStampa(params) {
  return api.get('/core/tracciamento/coda-stampa/', { params })
}
