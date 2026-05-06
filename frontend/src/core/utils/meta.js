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
