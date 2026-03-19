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
