/**
 * Estrae il messaggio di errore dalla risposta API.
 * Pattern unificato per tutti i flussi auth e dominio.
 *
 * Gerarchia: error.message (envelope) → data.message (fallback legacy) → fallback.
 *
 * @param {Error} err - errore Axios
 * @param {string} [fallback=''] - messaggio fallback se non estraibile
 * @returns {string}
 */
export function extractApiError(err, fallback = '') {
  const resp = err?.response?.data
  return resp?.error?.message || resp?.data?.message || resp?.message || fallback
}

/**
 * Estrae il codice errore dalla risposta API.
 * @param {Error} err
 * @returns {string|null}
 */
export function extractApiErrorCode(err) {
  return err?.response?.data?.error?.code || null
}
