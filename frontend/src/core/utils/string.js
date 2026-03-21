// Scopo: Utility centralizzate per formattazione stringhe.
// Primo carattere maiuscolo per nomi, cognomi, ragioni sociali.

/**
 * Primo carattere maiuscolo, resto minuscolo per ogni parola.
 * "mario rossi" → "Mario Rossi", "DE LUCA" → "De Luca"
 *
 * @param {string|null} s - Stringa da formattare
 * @returns {string} - Stringa formattata o stringa vuota
 */
export function capitalizeWords(s) {
  if (!s) return ''
  return s.trim().toLowerCase().replace(/\b\w/g, c => c.toUpperCase())
}

/**
 * Solo primo carattere maiuscolo della stringa.
 * "mario rossi" → "Mario rossi"
 *
 * @param {string|null} s - Stringa da formattare
 * @returns {string} - Stringa formattata o stringa vuota
 */
export function capitalizeFirst(s) {
  if (!s) return ''
  const t = s.trim()
  return t.charAt(0).toUpperCase() + t.slice(1)
}

/**
 * Blocca keypress per caratteri non alfanumerici.
 * Usare come handler @keypress su InputText/AutoComplete.
 *
 * @param {KeyboardEvent} event
 */
export function blockNonAlphanumeric(event) {
  if (!/[a-zA-Z0-9]/.test(event.key)) {
    event.preventDefault()
  }
}

/**
 * Normalizza un campo reactive a uppercase senza spazi.
 * Usare come handler @input su campi come IBAN, CF, P.IVA.
 *
 * @param {object} form - Oggetto reactive
 * @param {string} field - Nome del campo da normalizzare
 */
export function normalizeUpperNoSpaces(form, field) {
  if (typeof form[field] === 'string') {
    form[field] = form[field].toUpperCase().replace(/\s/g, '')
  }
}

/**
 * Normalizza un campo reactive a uppercase (mantiene spazi).
 * Usare come handler @input su campi che ammettono spazi.
 *
 * @param {object} form - Oggetto reactive
 * @param {string} field - Nome del campo da normalizzare
 */
export function normalizeUpper(form, field) {
  if (typeof form[field] === 'string') {
    form[field] = form[field].toUpperCase()
  }
}
