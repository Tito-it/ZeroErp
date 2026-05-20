// Scopo: Normalizza un valore `meta`/`snapshot` (jsonb DB) ad oggetto JS.
//        Difensivo contro la regressione "psycopg ritorna stringa JSON
//        invece di dict": senza coerce, accessi tipo `meta.field` o
//        `meta?.field` ritornano undefined silenziosamente, mascherando
//        bug reali (tooltip vuoto, riga_id non trovato, capability errate).
//
// Comportamento:
//   - dict (caso normale, jsonb deserializzato) → pass-through
//   - stringa JSON valida che produce object → parse
//   - stringa JSON malformata o null/undefined/non-object → {}
//   - lista, numero, booleano: trattati come "non oggetto" → {}
//
// Equivalente FE del helper BE `_coerce_meta_to_dict` in
// `apps/vendite/services/preventivi_service.py`. Tieni le due implementazioni
// allineate quando aggiungi/cambi semantica.
//
// Uso:
//   import { coerceJsonbToObject } from '@/core/utils/meta'
//   const m = coerceJsonbToObject(record?.meta)
//   const v = m.qualche_campo
export function coerceJsonbToObject(value) {
  if (value == null || value === '') return {}
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value)
      return parsed && typeof parsed === 'object' && !Array.isArray(parsed)
        ? parsed
        : {}
    } catch {
      return {}
    }
  }
  if (typeof value === 'object' && !Array.isArray(value)) return value
  return {}
}

// Scopo: Variante array di coerceJsonbToObject. Normalizza un valore
//        `jsonb_agg(...)` ad Array JS. Difensivo contro la regressione
//        psycopg che ritorna stringa JSON invece di list, sintomo visibile
//        nei JSONB aggregati ritornati da funzioni DB (es. `componenti`
//        in `vendite.fn_contratto_righe_preview` / `fn_preview_riga_componenti`).
//
// Comportamento:
//   - array (caso normale) → pass-through
//   - stringa JSON valida che produce array → parse
//   - null/undefined/stringa malformata/non-array → []
//
// Uso: passa l'output al :value di DataTable o alla prop `initialData`
//      di `ComponentiPanel` (vendite/_shared/componenti) in modalita'
//      data-driven, senza preoccuparsi della shape effettiva.
export function coerceJsonbToArray(value) {
  if (value == null || value === '') return []
  if (Array.isArray(value)) return value
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value)
      return Array.isArray(parsed) ? parsed : []
    } catch {
      return []
    }
  }
  return []
}
