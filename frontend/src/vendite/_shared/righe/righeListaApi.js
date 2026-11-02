// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: le due chiamate della LISTA delle righe di un documento di vendita
//        — la pagina e il suo export — per la lista configurabile
//        `vendite.<doc>_righe` (brief-db-liste-righe-documento, lotto B,
//        2026-09-28). Regola del 2: preventivo, ordine, DDT e reso.
// Note: ⚠️ `…/righe/lista/` e NON `…/righe/`: quella resta la lettura COMPLETA
//       (`listRighe` di ordine e reso, per i dialog di evasione e
//       ri-consegna) e la creazione di una riga. Il perche' e' nel backend
//       (`apps/vendite/api/righe_lista_views.py`).
//       ⭐ I parametri li prepara lo store-lista (`paramsFiltro`), compreso
//       `emittente_fiscale_id`, il lasciapassare del cancello di perimetro.
// ------------------------------------------------------------
import api from '../../../core/api'

// Scopo: le chiamate di pagina ed export per un dominio (`/vendite/ordini`).
export function makeRigheListaApi(base) {
  return {
    // (documentoId, params) → envelope paginato standard.
    listRigheLista: (documentoId, params = {}) =>
      api.get(`${base}/${documentoId}/righe/lista/`, { params }),
    // (documentoId, params) → il file (CSV/XLSX), come ogni export di lista.
    exportRigheLista: (documentoId, params = {}) =>
      api.get(`${base}/${documentoId}/righe/lista/export/`, { params, responseType: 'blob' }),
  }
}
