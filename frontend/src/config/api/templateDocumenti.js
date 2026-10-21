// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Client API per la gestione admin dei template documentali e
//        delle loro versioni (Tranche L "Modelli documenti" sotto
//        Configurazione). Endpoint backend Tranche C/E/F:
//         /api/v1/documenti/templates/                    GET (list) | POST (create)
//         /api/v1/documenti/templates/<id>/               GET (detail) | PATCH (update)
//         /api/v1/documenti/templates/<id>/personalizza/  POST
//         /api/v1/documenti/templates/risoluzione/        GET
//         /api/v1/documenti/templates/<id>/versioni/      GET (list) | POST (create)
//         /api/v1/documenti/templates/<id>/versioni/<vid>/ GET | PATCH | DELETE
//         /api/v1/documenti/templates/<id>/versioni/<vid>/clona/    POST
//         /api/v1/documenti/templates/<id>/versioni/<vid>/pubblica/ POST
//         /api/v1/documenti/context-builders/              GET (registro builder)
// ------------------------------------------------------------

import api from '../../core/api'

const BASE = '/documenti/templates'

// Scopo: Lista paginata template (envelope `paginated_envelope` BE).
export function listTemplateDocumenti(params = {}) {
  return api.get(`${BASE}/`, { params })
}

// Scopo: Dettaglio template per id (404 unificato no leak fuori scope).
export function getTemplateDocumento(id) {
  return api.get(`${BASE}/${id}/`)
}

// Scopo: Crea testata template. Permission BE `documenti_template_manage`.
export function createTemplateDocumento(payload) {
  return api.post(`${BASE}/`, payload)
}

// Scopo: PATCH testata template. Immutabili (output/sorgente/emittente)
//        rifiutati lato BE PRIMA di altre validazioni.
export function updateTemplateDocumento(id, payload) {
  return api.patch(`${BASE}/${id}/`, payload)
}

// Scopo: «Personalizza»: la copia di un modello STANDARD per un'azienda, con
//        la prima versione in bozza che ne dichiara l'origine (la fa il DB).
//        Payload `{emittente_fiscale_id, is_default?, codice?, codice_interno?,
//        descrizione?}`: i facoltativi assenti li decide il DB (i nomi dello
//        standard; predefinita se l'azienda non ne ha gia' una sua).
export function personalizzaTemplateDocumento(id, payload) {
  return api.post(`${BASE}/${id}/personalizza/`, payload)
}

// Scopo: Con che cosa stampa ogni azienda del perimetro, documento per
//        documento (envelope `results`): l'esito della risoluzione del DB —
//        EMITTENTE, STANDARD, SENZA_PREDEFINITO, NON_RISOLTO.
export function listRisoluzioneTemplate(params = {}) {
  return api.get(`${BASE}/risoluzione/`, { params })
}

// Scopo: Lista paginata delle versioni di un template.
// ⭐ Contratto di lista standard (lista `documenti.template_versioni`,
//    2026-09-27): `limit`/`offset`, `order_by`/`order_dir`, `search`, envelope
//    `paginated_envelope` (`results`/`count`).
export function listTemplateVersioni(templateId, params = {}) {
  return api.get(`${BASE}/${templateId}/versioni/`, { params })
}

// Scopo: Dettaglio versione (incluso payload html/css/markdown).
export function getTemplateVersione(templateId, versioneId) {
  return api.get(`${BASE}/${templateId}/versioni/${versioneId}/`)
}

// Scopo: Crea nuova versione BOZZA. Numero versione calcolato server-side
//        (`MAX+1`); il client non lo passa.
// ⚠️ `params` in QUERY: la view della creazione e' la stessa della lista
//    (`documenti.template_versioni`), e il cancello di perimetro emittente
//    vale per ogni suo metodo — l'emittente del template viaggia qui.
export function createTemplateVersione(templateId, payload, params = {}) {
  return api.post(`${BASE}/${templateId}/versioni/`, payload, { params })
}

// Scopo: PATCH versione. Solo BOZZA modificabile (trigger DB A1
//        protect_pubblicata come guardrail finale).
export function updateTemplateVersione(templateId, versioneId, payload) {
  return api.patch(`${BASE}/${templateId}/versioni/${versioneId}/`, payload)
}

// Scopo: DELETE versione (solo BOZZA, trigger DB A2 block_delete).
export function deleteTemplateVersione(templateId, versioneId) {
  return api.delete(`${BASE}/${templateId}/versioni/${versioneId}/`)
}

// Scopo: Clona versione esistente -> nuova BOZZA (override `titolo` opzionale).
export function clonaTemplateVersione(templateId, versioneId, payload = {}) {
  return api.post(`${BASE}/${templateId}/versioni/${versioneId}/clona/`, payload)
}

// Scopo: Transizione BOZZA -> PUBBLICATA. Richiede `valido_dal` non NULL.
//        EXCLUDE GiST DB blocca eventuali overlap con altre PUBBLICATA attive.
export function pubblicaTemplateVersione(templateId, versioneId, payload) {
  return api.post(`${BASE}/${templateId}/versioni/${versioneId}/pubblica/`, payload)
}

// Scopo: I builder di contesto REGISTRATI nel backend, con la forma dei dati
//        che producono (`{codice, versione_contesto}`, envelope `results`).
//        E' la tendina del template: il registro si legge, non si ricopia.
export function listContextBuilders() {
  return api.get('/documenti/context-builders/')
}
