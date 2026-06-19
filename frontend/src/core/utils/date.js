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

/**
 * Formatta un timestamp per visualizzazione: DD/MM/YYYY, HH:mm:ss.
 * Accetta: stringa ISO, Date, null/undefined.
 *
 * @param {string|Date|null} ts - Valore timestamp
 * @returns {string} - Stringa 'DD/MM/YYYY, HH:mm:ss' o stringa vuota
 */
export function displayTimestamp(ts) {
  if (!ts) return ''
  const d = ts instanceof Date ? ts : new Date(ts)
  if (isNaN(d.getTime())) return ''
  const day = String(d.getDate()).padStart(2, '0')
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const y = d.getFullYear()
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  const ss = String(d.getSeconds()).padStart(2, '0')
  return `${day}/${m}/${y}, ${hh}:${mm}:${ss}`
}

/**
 * Formatta solo l'ora (HH:mm) di un timestamp, in fuso locale.
 * Accetta: stringa ISO, Date, null/undefined.
 *
 * @param {string|Date|null} ts - Valore timestamp
 * @returns {string} - Stringa 'HH:mm' o stringa vuota
 */
export function displayTime(ts) {
  if (!ts) return ''
  const d = ts instanceof Date ? ts : new Date(ts)
  if (isNaN(d.getTime())) return ''
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${hh}:${mm}`
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

/**
 * Converte una stringa ISO 'YYYY-MM-DD' in Date locale senza shift di fuso.
 * Usato per precaricare DatePicker da valori persistiti nel backend.
 *
 * @param {string|Date|null} s - Stringa ISO o Date
 * @returns {Date|null} - Date locale a mezzanotte o null
 */
export function parseIsoDate(s) {
  if (!s) return null
  if (s instanceof Date) return s
  const match = String(s).match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (!match) return null
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
}

/**
 * Ritorna una Date locale a mezzanotte = oggi + N giorni.
 * Helper standard per i parameters lead-gg dei `defaultForm()` (Fase 2
 * refactor frontend vendite). Centralizzare evita pattern ripetuto
 * `const d = new Date(); d.setHours(0,0,0,0); d.setDate(d.getDate() + N)`
 * in ogni drawer (era cablato in CloneVersioneDrawer, PromoArticoloDrawer).
 *
 * @param {number} n - Giorni da sommare a oggi (0 = oggi, 1 = domani, ...).
 * @returns {Date} - Date locale a mezzanotte.
 */
export function addDaysToToday(n) {
  const d = new Date()
  d.setHours(0, 0, 0, 0)
  if (n) d.setDate(d.getDate() + Number(n))
  return d
}
