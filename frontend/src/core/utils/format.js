// Scopo: Utility centralizzate per formattazione valori.
// Un solo punto di modifica per formati numerici/dimensioni in tutta l'applicazione.

/**
 * Formatta una dimensione in byte in formato leggibile (B, KB, MB, GB).
 *
 * @param {number|null} bytes - Dimensione in byte
 * @returns {string} - Stringa formattata o vuota se null/0
 */
export function formatSize(bytes) {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

/**
 * Formatta un valore come valuta locale (default EUR in it-IT).
 *
 * @param {number|string|null} value
 * @param {Object} [opts]
 * @param {string} [opts.currency='EUR']
 * @param {string} [opts.locale='it-IT']
 * @param {string} [opts.placeholder=''] - cosa restituire per null/undefined
 * @param {number} [opts.minimumFractionDigits] - override decimali min (default locale: 2 per EUR)
 * @param {number} [opts.maximumFractionDigits] - override decimali max (default locale: 2 per EUR)
 * @returns {string}
 */
export function formatCurrency(value, opts = {}) {
  const {
    currency = 'EUR',
    locale = 'it-IT',
    placeholder = '',
    minimumFractionDigits,
    maximumFractionDigits,
  } = opts
  if (value == null) return placeholder
  const formatOpts = { style: 'currency', currency }
  if (minimumFractionDigits != null) formatOpts.minimumFractionDigits = minimumFractionDigits
  if (maximumFractionDigits != null) formatOpts.maximumFractionDigits = maximumFractionDigits
  return Number(value).toLocaleString(locale, formatOpts)
}

/**
 * Formatta un valore come numero locale (default 2 decimali in it-IT).
 *
 * @param {number|string|null} value
 * @param {Object} [opts]
 * @param {string} [opts.locale='it-IT']
 * @param {number} [opts.minimumFractionDigits=2]
 * @param {number} [opts.maximumFractionDigits]
 * @param {string} [opts.placeholder='']
 * @returns {string}
 */
export function formatNumber(value, opts = {}) {
  const {
    locale = 'it-IT',
    minimumFractionDigits = 2,
    maximumFractionDigits,
    placeholder = '',
  } = opts
  if (value == null) return placeholder
  const formatOpts = { minimumFractionDigits }
  if (maximumFractionDigits != null) formatOpts.maximumFractionDigits = maximumFractionDigits
  return Number(value).toLocaleString(locale, formatOpts)
}
