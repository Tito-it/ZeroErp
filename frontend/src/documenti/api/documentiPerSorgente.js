// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Client API per i documenti generati a partire da una sorgente
//        (Tranche M motore documentale). Endpoint nidificati sotto
//        il dominio sorgente (Decisione 75: permessi del dominio).
//        Factory `buildSorgenteClient(basePathFn)` per consentire ad
//        altri domini sorgente (CONTRATTO/ORDINE in futuro) di
//        riutilizzare la stessa interfaccia client senza duplicazione.
// ------------------------------------------------------------

import api from '../../core/api'

// Scopo: Costruisce un client API per documenti generati di una specifica
//        sorgente. `basePathFn(sorgenteId)` ritorna il path radice della
//        sub-resource (es. `/vendite/preventivi/<id>/documenti`).
function buildSorgenteClient(basePathFn) {
  return {
    // Scopo: Lista paginata documenti generati per la sorgente.
    list(sorgenteId, params = {}) {
      return api.get(`${basePathFn(sorgenteId)}/`, { params })
    },

    // Scopo: Genera e persiste un nuovo documento PDF dalla sorgente.
    //        body opzionale: `template_documento_id`/`tipo_documento_output_id`.
    genera(sorgenteId, payload = {}) {
      return api.post(`${basePathFn(sorgenteId)}/genera/`, payload)
    },

    // Scopo: Anteprima PDF temporanea (Decisione 30: no persist, no
    //        evento timeline). Risposta binaria `application/pdf`.
    //        `responseType: 'blob'` per ricevere bytes invece di JSON.
    anteprima(sorgenteId, payload = {}) {
      return api.post(`${basePathFn(sorgenteId)}/anteprima/`, payload, {
        responseType: 'blob',
      })
    },

    // Scopo: Download PDF persistito (con emit `SCARICATO` lato BE).
    //        Risposta binaria `attachment` -> il caller crea blob URL
    //        per offrire "Salva con nome" senza rompere la SPA.
    download(sorgenteId, documentoId) {
      return api.get(
        `${basePathFn(sorgenteId)}/${documentoId}/file/`,
        { responseType: 'blob' },
      )
    },
  }
}

// Client per documenti di un PREVENTIVO. Path coerente con
// `apps/vendite/api/preventivi_urls.py` Tranche K.
export const preventivoDocumenti = buildSorgenteClient(
  (preventivoId) => `/vendite/preventivi/${preventivoId}/documenti`,
)

// Client per documenti di un CONTRATTO. Path coerente con
// `apps/vendite/api/urls_contratti.py`.
export const contrattoDocumenti = buildSorgenteClient(
  (contrattoId) => `/vendite/contratti/${contrattoId}/documenti`,
)
