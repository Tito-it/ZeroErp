// Scopo: Helper date condivisi per drawer/form che integrano PrimeVue DatePicker
//        con payload JSON backend (stringhe ISO YYYY-MM-DD).
//        PrimeVue DatePicker v-model espone Date JS: evitiamo `new Date(iso)`
//        che introduce timezone shift e `date.toISOString().split('T')[0]`
//        che puo' saltare un giorno in fusi a ovest di UTC.

// Scopo: Converte una stringa ISO YYYY-MM-DD (date-only) in oggetto Date
//        nel fuso locale del browser. Ritorna null se input vuoto/non valido.
export function isoToLocalDate(iso) {
  if (!iso) return null
  const parts = String(iso).split('-').map(Number)
  if (parts.length < 3 || parts.some(Number.isNaN)) return null
  const [y, m, d] = parts
  return new Date(y, m - 1, d)
}

// Scopo: Converte un oggetto Date (da DatePicker) in stringa ISO YYYY-MM-DD
//        leggendo i componenti locali (anno/mese/giorno visibili all'utente).
//        Evita il timezone shift del toISOString().
export function localDateToIso(date) {
  if (!date) return null
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}
