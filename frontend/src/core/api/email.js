// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Client API delle email dell'operatore — endpoint sotto /core/email/.
// Note: ⭐ La lista del log e il suo lookup degli stati sono aperti a ogni
//       operatore (skip d'area, 2026-09-26): chi vede quale mail lo decide la
//       RLS per ambito. ⛔ La lista e' OFFSET-based ({count, results}), non
//       page-based.
// ------------------------------------------------------------
import api from '../api'

// GET log delle email nel perimetro di chi chiede. params: search, stato,
// pratica_id, data_da, data_a (YYYY-MM-DD), order_by, order_dir, limit, offset.
export function listEmailLog(params) {
  return api.get('/core/email/log/', { params })
}

// GET gli stati possibili di una mail nel log: {results: [{codice,
// descrizione, ordering}]}, nell'ordine dichiarato dal backend.
export function lookupEmailLogStati() {
  return api.get('/core/email/log/stati/')
}
