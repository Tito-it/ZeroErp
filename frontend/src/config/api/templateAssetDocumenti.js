// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Client API per la gestione admin degli asset documentali
//        (Tranche L "Modelli documenti" sotto Configurazione).
//        Endpoint backend Tranche G:
//         /api/v1/documenti/asset/        GET (list) | POST (multipart upload)
//         /api/v1/documenti/asset/<id>/   GET (detail) | PATCH (metadati)
//         /api/v1/documenti/asset/<id>/file/ GET download binario
//
//        DELETE NON esposta (trigger DB A3 block_delete: soft-disable
//        via PATCH `attivo=false` o `valido_al`).
// ------------------------------------------------------------

import api from '../../core/api'

const BASE = '/documenti/asset'

// Scopo: Lista paginata asset (envelope paginato BE).
export function listTemplateAssetDocumenti(params = {}) {
  return api.get(`${BASE}/`, { params })
}

// Scopo: Dettaglio asset per id.
export function getTemplateAssetDocumento(id) {
  return api.get(`${BASE}/${id}/`)
}

// Scopo: Download binario del file asset originale.
export function downloadTemplateAssetDocumento(id) {
  return api.get(`${BASE}/${id}/file/`, { responseType: 'blob' })
}

// Scopo: Miniatura di un asset immagine (PNG di lato al massimo 128 px; SVG
//        com'e'). Il backend risponde con ETag e `no-cache`: il browser la
//        tiene in cache e la rivalida (304), senza riscaricare il file.
export function miniaturaTemplateAssetDocumento(id) {
  return api.get(`${BASE}/${id}/miniatura/`, { responseType: 'blob' })
}

// Scopo: Upload asset (multipart). `file` -> binario; gli altri campi
//        sono i metadati anagrafici. Il BE valida MIME contro whitelist
//        per `tipi_asset_documento.codice_interno`.
export function uploadTemplateAssetDocumento(payload) {
  // payload e' un FormData costruito dal componente upload.
  return api.post(`${BASE}/`, payload, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// Scopo: PATCH metadati. I 5 campi file (storage_key/sha256/file_size/
//        mime/file_name) e i 4 anag (codice/codice_interno/asset_tipo_id/
//        emittente_fiscale_id) sono immutabili lato BE.
export function updateTemplateAssetDocumento(id, payload) {
  return api.patch(`${BASE}/${id}/`, payload)
}
