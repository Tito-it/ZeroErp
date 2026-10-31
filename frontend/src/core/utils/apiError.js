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

/**
 * L'endpoint ha NEGATO l'accesso (401/403): l'utente non vede quel dato.
 *
 * ⭐ Estratto il 2026-10-31 alla terza copia (regola del 2, ok Tid): i lettori
 *    «ambientali» (contatori code, pallino presidi, alert scadenze listino) ne
 *    fanno un ramo a parte — un rifiuto si NASCONDE, ogni altro errore si
 *    segnala o tiene l'ultimo valore. Due copie scritte a mano divergono sui
 *    codici (una con il solo 403 tratterebbe una sessione scaduta da guasto).
 * ⛔ Non e' «errore di autorizzazione da mostrare»: chi la usa decide di tacere.
 *
 * @param {Error} err - errore Axios
 * @returns {boolean}
 */
export function eAccessoNegato(err) {
  const status = err?.response?.status
  return status === 401 || status === 403
}
