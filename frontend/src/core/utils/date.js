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

// ⛔ SU UNA INVALID DATE QUESTA FUNZIONE PRODUCE "NaN-NaN-NaN", E DEVE
//    CONTINUARE A FARLO. Sembra un difetto ed e' il comportamento giusto QUI:
//    i suoi ~90 chiamanti sono in maggioranza PAYLOAD DI FORM (`valido_al`,
//    `data_valuta`, `data_scadenza`, `data_riattivazione_prevista`), e li'
//    «data scritta male» e «nessuna data» sono l'OPPOSTO l'una dell'altra.
//    Una stringa storta la respinge il backend con un 400 che l'operatore vede;
//    un `null` su un campo OPZIONALE verrebbe accettato e salverebbe il record
//    col campo SVUOTATO — su un `valido_al` vuol dire trasformare in silenzio
//    una validita' chiusa in una aperta.
// ⚠️ Provato e ritirato il 2026-09-08: il guard su `Number.isNaN` era stato
//    messo QUI per il filtro data delle code, e collassava i due significati
//    per tutti i chiamanti. Chi vuole «data oppure niente» usa
//    `toDateStringOrNull` qui sotto: sono due domande diverse e restano due
//    funzioni.
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
 * Come `toDateString`, ma una data NON VALIDA vale «nessuna data» (`null`).
 *
 * ⭐ E' la variante per i FILTRI di lista, dove «non ho ancora finito di
 * scrivere una data» deve valere «non filtrare» — non «filtra per una data
 * impossibile». Il chiamante tipico e' il `buildParams` di uno store.
 *
 * ⛔ NON usarla per i payload dei form: li' una data storta deve arrivare al
 * backend e farsi respingere, altrimenti il campo si salva vuoto in silenzio.
 * E' esattamente la ragione per cui esistono due funzioni invece di un guard
 * dentro `toDateString`.
 *
 * ⚠️ DA DOVE ARRIVA UNA INVALID DATE, perche' non e' un caso di laboratorio: i
 * `DatePicker` PrimeVue hanno `manualInput` a `true` di DEFAULT (verificato su
 * 4.5), quindi il campo si digita — e mentre si digita il componente emette
 * una `Date` non valida. Sulle due code produceva
 * `data_da=NaN-NaN-NaN` e un `E_VALIDATION_INPUT / data_da_invalid` a ogni
 * tasto (2026-09-07).
 *
 * @param {Date|string|null} d - Valore data
 * @returns {string|null} - 'YYYY-MM-DD', oppure null se assente o non valida
 */
export function toDateStringOrNull(d) {
  if (d instanceof Date && Number.isNaN(d.getTime())) return null
  return toDateString(d)
}

/**
 * Converte un valore data/ora in stringa ISO 8601 (UTC) per campi timestamptz.
 * A differenza di toDateString (solo data, no shift di fuso), qui serve l'istante
 * assoluto: per un timestamp completo toISOString() e' corretto e non ambiguo
 * (il backend lo casta a timestamptz).
 *
 * @param {Date|string|null} d - Valore data/ora
 * @returns {string|null} - Stringa ISO con offset (UTC) o null
 */
export function toTimestampString(d) {
  if (!d) return null
  const date = d instanceof Date ? d : new Date(d)
  if (isNaN(date.getTime())) return null
  return date.toISOString()
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

/**
 * Giorni di arretrato del floor temporale di default delle liste.
 * Sta qui, non nei singoli store: e' una scelta UX di progetto, e cambiarla
 * deve costare una riga sola.
 */
export const LISTE_FILTRO_DATA_GIORNI = 60

/**
 * Floor temporale di DEFAULT delle liste: `oggi - 60 giorni`, riportato al
 * PRIMO GIORNO del mese risultante. Es. oggi 15-08-2026 -> 01-06-2026.
 *
 * L'allineamento al giorno 1 non e' un arrotondamento estetico: rende il
 * default stabile dentro il mese (non scorre di un giorno ogni giorno, quindi
 * l'operatore non vede la lista cambiare da sola) e fa sempre vedere il mese
 * corrente per intero, che e' come si legge un archivio operativo.
 *
 * Regola precedente (fino al 2026-08-01): 1° gennaio dell'anno-1. Era troppo
 * larga — su liste popolate significava scorrere fino a due anni di documenti
 * per arrivare a quelli di ieri.
 *
 * @returns {Date} - Date locale a mezzanotte, primo del mese.
 */
export function defaultFiltroDataDa() {
  const d = addDaysToToday(-LISTE_FILTRO_DATA_GIORNI)
  d.setDate(1)
  return d
}

/**
 * Come `defaultFiltroDataDa()`, ma in stringa `YYYY-MM-DD`: e' la forma che
 * gli store mettono in `filters.data_da` e che il backend riceve.
 *
 * @returns {string} - Data ISO (solo giorno).
 */
export function defaultFiltroDataDaString() {
  return toDateString(defaultFiltroDataDa())
}
