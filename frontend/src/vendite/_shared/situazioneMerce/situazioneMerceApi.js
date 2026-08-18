// Client API della "situazione merce" di un documento (pannello del cantiere 2,
// brief-design-situazione-merce-ordine). Schema REST identico sui due domini —
// ordine e DDT, factory BE `build_situazione_merce_view` — quindi qui il
// gemello FE bindato al basePath, come `lineageApi` e `documentoIndirizziApi`.
//
// GET {base}/{id}/situazione-merce/ -> { righe_ordine[], partite[],
//                                        accrediti[], riconsegne[] }
//   - righe_ordine: il riassunto PER RIGA D'ORDINE. Vuoto sul DDT di proposito:
//     li' la domanda e' «cosa e' successo a QUESTA spedizione».
//   - partite: la merce, a grana riga di DDT.
//   - accrediti / riconsegne: le due code di lavoro del documento, le STESSE
//     viste che alimentano i tab «Da accreditare» / «Da ri-consegnare» — cosi'
//     il pannello non puo' contraddirle.
//
// ⚠️ `differenza` puo' essere `null` e NON significa zero: significa che il
// conto non si applica. Nessun consumatore deve fare `?? 0`.

import api from '../../../core/api'

// Scopo: GET della situazione merce del documento. basePath = path lista del
//        dominio ('/vendite/ordini' | '/vendite/ddt'), id = pk di dominio.
export function getSituazioneMerce(basePath, id) {
  const base = String(basePath).replace(/\/+$/, '')
  return api.get(`${base}/${id}/situazione-merce/`)
}
