// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: API delle TABELLE DI CONFIGURAZIONE generiche (`/core/config/tables/`):
//        metadata delle colonne e CRUD di una tabella codice/descrizione
//        identificata dal suo `rel` (`schema.tabella`).
// ------------------------------------------------------------
import api from '../api'

const BASE = '/core/config/tables'

// Scopo: le tabelle del pannello (`{ schema, table, rel }`), dalla lista a DB
//        `config.tabelle_gestibili` con `pannello`.
export function listConfigTables() {
  return api.get(`${BASE}/`)
}

// Scopo: le colonne della tabella, con widget e default del DB.
export function getConfigTableMetadata(rel) {
  return api.get(`${BASE}/${rel}/metadata/`)
}

// Scopo: una pagina di record della tabella.
export function listConfigRecords(rel, params = {}) {
  return api.get(`${BASE}/${rel}/`, { params })
}

// Scopo: un record per id.
export function getConfigRecord(rel, id) {
  return api.get(`${BASE}/${rel}/${id}/`)
}

// Scopo: crea un record.
export function createConfigRecord(rel, payload) {
  return api.post(`${BASE}/${rel}/`, payload)
}

// Scopo: aggiorna un record; il payload porta solo i campi cambiati.
export function updateConfigRecord(rel, id, payload) {
  return api.patch(`${BASE}/${rel}/${id}/`, payload)
}
