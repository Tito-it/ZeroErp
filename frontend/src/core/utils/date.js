// Scopo: Utility centralizzata per formattazione date.
// Tutte le conversioni Date → stringa per API backend passano da qui.
// Evita il bug toISOString() che converte in UTC (mezzanotte locale → giorno prima in UTC).

/**
 * Converte un valore data in stringa YYYY-MM-DD per invio al backend.
 * Accetta: Date, stringa ISO, null/undefined.
 * Usa ora locale (non UTC) per evitare shift di giorno.
 *
 * @param {Date|string|null} d - Valore data
 * @returns {string|null} - Stringa 'YYYY-MM-DD' o null
 */
/**
 * Formatta una data per visualizzazione: DD/MM/YYYY.
 * Accetta: stringa 'YYYY-MM-DD', Date, null/undefined.
 *
 * @param {string|Date|null} d - Valore data
 * @returns {string} - Stringa 'DD/MM/YYYY' o stringa vuota
 */
export function displayDate(d) {
  if (!d) return ''
  const s = typeof d === 'string' ? d : toDateString(d)
  if (!s || s.length < 10) return s || ''
  const [y, m, day] = s.substring(0, 10).split('-')
  return `${day}/${m}/${y}`
}

export function toDateString(d) {
  if (!d) return null
  if (d instanceof Date) {
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${y}-${m}-${day}`
  }
  // Se gia' stringa, ritorna cosi' com'e' (assume formato valido)
  return String(d)
}
