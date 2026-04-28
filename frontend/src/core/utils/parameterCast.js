// Scopo: Cast helpers per i valori di config.parameters letti via
// useParameterDefaults / fetchParameterDefaults.
// Il backend (`ParameterService.get_defaults`) ritorna `dict[str, str]`:
// tutti i valori arrivano al FE come stringhe, anche `true`/`false` e numeri.
// Questi helper centralizzano la conversione con fallback resiliente
// (parametro assente, stringa vuota, valore non parsabile -> fallback).

// Scopo: Cast da stringa parametro a boolean. Accetta "true"/"false"
// case-insensitive. Qualsiasi altro valore (null, undefined, "", "abc",
// "1", "0", numeri) ritorna il fallback.
export function paramBool(value, fallback) {
  if (value === undefined || value === null || value === '') return fallback
  return String(value).toLowerCase() === 'true'
}

// Scopo: Cast da stringa parametro a number (decimale o intero).
// Stringhe non numeriche ritornano il fallback. Non normalizza separatori
// locale (il BE seeda sempre con `.` decimale).
export function paramNumber(value, fallback) {
  if (value === undefined || value === null || value === '') return fallback
  const n = Number(value)
  return Number.isFinite(n) ? n : fallback
}

// Scopo: Cast da stringa parametro a integer puro. Decimali troncati e
// stringhe non numeriche ritornano il fallback. Utile per id/contatori.
export function paramInt(value, fallback) {
  const n = paramNumber(value, NaN)
  if (!Number.isFinite(n)) return fallback
  return Math.trunc(n)
}

// Scopo: Cast da stringa parametro a stringa non vuota. Stringa vuota,
// null, undefined ritornano il fallback. Utile per codici/enum.
export function paramString(value, fallback) {
  if (value === undefined || value === null) return fallback
  const s = String(value).trim()
  return s === '' ? fallback : s
}
