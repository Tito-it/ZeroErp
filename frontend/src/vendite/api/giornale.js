// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Client API del giornale TRASVERSALE degli eventi (pezzo G
//        dell'osservabilita'): la Storia di tutte le entita' insieme,
//        filtrata per gravita'. Lista + export, stessi filtri.
// ------------------------------------------------------------

import api from '../../core/api'

const BASE = '/vendite/giornale'

// Scopo: la lista paginata del giornale trasversale.
export function listGiornale(params = {}) {
  return api.get(`${BASE}/`, { params })
}

// Scopo: export CSV/Excel del giornale, stessi filtri della lista.
// ⚠️ `formato` e non `format` (parametro magico di DRF); risposta Blob,
//    senza `useApiHandler` (`feedback_blob_download_no_useapihandler`).
export function exportGiornale(params = {}) {
  return api.get(`${BASE}/export/`, { params, responseType: 'blob' })
}
