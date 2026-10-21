// Client API del tracciamento core — gestione code (coda lavori generica +
// coda stampa). Endpoint sotto /core/tracciamento/ (area core), brief
// brief-be-fe-gestione-code-lavori-stampa. Le liste sono offset-based
// ({count, results}); le azioni richiedono Idempotency-Key.
import api from '../api'

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
  )
}

// POST requeue/sblocco di un job IN_CORSO o ERRORE (→ PENDING, alza
// max_tentativi di extraTentativi, default BE 3).
export function requeueCodaLavoro(jobId, extraTentativi = null) {
  const body = extraTentativi != null ? { extra_tentativi: extraTentativi } : {}
  return api.post(
    `/core/tracciamento/coda-lavori/${jobId}/requeue/`,
    body,
  )
}

// GET lista paginata della coda stampa (outbox PDF). params: ambito, stato,
// solo_vivi, lotto_id, data_da, data_a, limit, offset. Scope emittente BE.
export function listCodaStampa(params) {
  return api.get('/core/tracciamento/coda-stampa/', { params })
}

// ── Archiviazione (brief-db-archiviazione-righe-code, 2026-09-04) ──────────
// Toglie una riga dall'ELENCO senza toccarne lo stato: i conteggi del pannello
// «Esiti fatturazione» e il badge in topbar restano fermi. Vale per TUTTI (non
// e' una preferenza dell'operatore) e per questo il gate BE e' `code_manage`,
// non l'ownership di annulla/requeue.
// ⚠️ Solo su righe NON VIVE: su una riga viva il database rifiuta con
// `E_CODA_ARCHIVIAZIONE_NON_AMMESSA` (409). Il FE non ripete il criterio: si
// limita a disabilitare l'azione con `rigaCodaViva(row.stato)`.

// ⭐ I quattro verbi prendono un ELENCO di id, anche quando l'operatore agisce
// su una riga sola dal menu (che manda `[row.id]`). Un verbo di massa e uno
// singolo sarebbero due contratti da tenere allineati per lo stesso rifiuto,
// che e' PER RIGA.
// ⛔ Rispondono **200 anche a esito PARZIALE**: chi legge deve guardare
// `data.esito` (COMPLETATO | PARZIALE | ERRORE) e `data.falliti`, non lo
// status — una riga rifiutata dal database non affonda le altre.
function postArchiviazione(url, ids) {
  return api.post(
    url,
    { ids },
  )
}

// POST archivia N job TERMINALI della coda lavori.
export function archiviaCodaLavoro(ids) {
  return postArchiviazione('/core/tracciamento/coda-lavori/archivia/', ids)
}

// POST rimette in elenco N job archiviati della coda lavori.
export function ripristinaCodaLavoro(ids) {
  return postArchiviazione('/core/tracciamento/coda-lavori/ripristina/', ids)
}

// POST archivia N righe TERMINALI della coda stampa.
export function archiviaCodaStampa(ids) {
  return postArchiviazione('/core/tracciamento/coda-stampa/archivia/', ids)
}

// POST rimette in elenco N righe archiviate della coda stampa.
export function ripristinaCodaStampa(ids) {
  return postArchiviazione('/core/tracciamento/coda-stampa/ripristina/', ids)
}
