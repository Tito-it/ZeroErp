// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Client API dei legami di un documento che si annulla con conferma
//        (bolla, ordine, preventivo, contratto). Schema REST identico sui
//        quattro domini (factory BE `build_legami_view`): qui il gemello FE
//        bindato al basePath del dominio, come lineageApi.
// ------------------------------------------------------------
//
// GET {base}/{id}/legami/ -> { documento, id, legami, righe[] }
//   - legami: il numero da dichiarare nella conferma (`legami_confermati`);
//   - righe: una per legame — riga_nr (null per testata e commessa), origine
//     (ORDINE, RESO, PREVENTIVO, OFFERTA, COMMESSA), natura (CONSUMO o
//     PROVENIENZA), origine_id, origine_tipo_codice_interno, origine_codice
//     (dal lineage, null se non lo vede), qta.

import api from '../../../core/api'

// Scopo: GET dei legami del documento. basePath = path lista del dominio
//        (es. '/vendite/ordini'), id = pk di dominio.
export function getLegami(basePath, id) {
  const base = String(basePath).replace(/\/+$/, '')
  return api.get(`${base}/${id}/legami/`)
}
