// Client API building block per la genealogia/lineage dei documenti vendite
// (pannello "Passaggi"). Schema REST identico sui 7 domini (preventivi/
// offerte/ordini/contratti/ddt/resi/commesse — factory BE
// build_passaggi_view): qui il gemello FE bindato al basePath del dominio,
// come documentoIndirizziApi.
//
// GET {base}/{id}/passaggi/ -> { nodo, pratica|null, frontiera|null,
//                                avanti[], indietro[] }
//   - avanti/indietro: archi del grafo (fn_documento_lineage) con livello/
//     ordine per il rendering timeline; is_ramo_inverso=true per l'arco R
//     DDT->Reso (merce che torna, esclusa dalla frontiera forward).

import api from '../../../core/api'

// Scopo: GET dei passaggi del documento. basePath = path lista del dominio
//        (es. '/vendite/ordini'), id = pk di dominio (il BE traduce nella
//        chiave nodo polimorfa: il FE resta ignaro di key_selector, P-1).
export function getPassaggi(basePath, id) {
  const base = String(basePath).replace(/\/+$/, '')
  return api.get(`${base}/${id}/passaggi/`)
}
