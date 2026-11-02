// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
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
import { SORGENTE_CODES } from '../constants'

// Scopo: Costruisce un client API per documenti generati di una specifica
//        sorgente. `basePathFn(sorgenteId)` ritorna il path radice della
//        sub-resource (es. `/vendite/preventivi/<id>/documenti`).
function buildSorgenteClient(basePathFn) {
  return {
    // Scopo: Lista paginata documenti generati per la sorgente (lista
    //        `documenti.documenti_sorgente`): contratto di lista standard —
    //        `limit`/`offset`, `order_by`/`order_dir`, `search`, envelope
    //        `paginated_envelope` (`results`/`count`).
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

    // Scopo: Lista di tutti i file (principale + allegati) del documento.
    listFiles(sorgenteId, documentoId) {
      return api.get(`${basePathFn(sorgenteId)}/${documentoId}/allegati/`)
    },

    // Scopo: Aggiunge allegati (file secondari) a un documento gia' generato
    //        (modalita' append). `formData` contiene i file sotto `allegati`.
    aggiungiAllegati(sorgenteId, documentoId, formData) {
      return api.post(
        `${basePathFn(sorgenteId)}/${documentoId}/allegati/`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } },
      )
    },

    // Scopo: Download di uno specifico file del documento per id (principale
    //        o allegato). Risposta binaria.
    downloadFile(sorgenteId, documentoId, fileId) {
      return api.get(
        `${basePathFn(sorgenteId)}/${documentoId}/file/${fileId}/`,
        { responseType: 'blob' },
      )
    },

    // Scopo: RISTAMPA FEDELE (percorso 3) — ri-renderizza il documento
    //        com'era, dalla versione di template con cui nacque e dal
    //        contesto congelato. Funziona anche sui documenti privi di file
    //        salvato (persistenza iniziata il 2026-07-21), che sono gli unici
    //        per cui `download` non e' disponibile.
    //        ⚠️ Da NON confondere con `genera`, che EMETTE un documento nuovo
    //        col modello di oggi e i dati di oggi.
    //        La fedelta' di byte arriva nell'header `X-Ristampa-Pdf-Hash-Match`
    //        (`1`/`0`): il corpo e' il PDF, quindi il verdetto viaggia li'.
    ristampaFedele(sorgenteId, documentoId) {
      return api.get(
        `${basePathFn(sorgenteId)}/${documentoId}/ristampa/`,
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

// Client per documenti di un'OFFERTA_COMMERCIALE. Path coerente con
// `apps/vendite/api/urls_offerte.py`. Nota: la GENERAZIONE avviene
// tramite l'endpoint `emetti/` (multipart) del dominio offerta, non via
// `genera`; qui restano anteprima/lista/download/allegati.
export const offertaDocumenti = buildSorgenteClient(
  (offertaId) => `/vendite/offerte/${offertaId}/documenti`,
)

// Client per documenti di un ORDINE_VENDITA. Path coerente con
// `apps/vendite/api/urls_ordini.py`. La stampa conferma d'ordine usa
// `anteprima` on-demand (Decisione §12.4(a): stampa disaccoppiata dallo
// stato, ristampabile); `genera`/lista/download restano per l'archivio.
export const ordineDocumenti = buildSorgenteClient(
  (ordineId) => `/vendite/ordini/${ordineId}/documenti`,
)

// Client per documenti di un DDT_VENDITA (DDT accompagnatorio). Path coerente
// con `apps/vendite/api/urls_ddt.py`. La GENERAZIONE definitiva avviene
// all'emissione (`emetti/` multipart, DRAFT->EMESSO + PDF atomico, mirror
// ordine); qui restano anteprima (bozza)/genera (ristampa)/lista/download.
export const ddtDocumenti = buildSorgenteClient(
  (ddtId) => `/vendite/ddt/${ddtId}/documenti`,
)

// Client per documenti di una FATTURA (stampa/ristampa). Path coerente con
// `apps/vendite/api/urls_fatture.py`. La fattura NON si emette da UI (nasce
// dalla pipeline): niente `emetti/`. La stampa singola sincrona passa da
// `anteprima` (render on-the-fly) / `genera` (archivio); il massivo dalla coda.
export const fattureDocumenti = buildSorgenteClient(
  (fatturaId) => `/vendite/fatture/${fatturaId}/documenti`,
)

// Scopo: codice sorgente -> client API. Sede UNICA della mappa: la leggono lo
//        store delle azioni (`documentiPerSorgente`) e gli store-lista
//        (`documentiSorgenteLista`, uno per sorgente). Quando un nuovo dominio
//        sorgente entra nel motore documentale, basta aggiungere l'entry qui.
// ⚠️ Stava nello store delle azioni finche' ne aveva uno solo; il 2026-09-27
//    la lista e' uscita in uno store suo e i consumatori sono diventati due —
//    una seconda copia della mappa divergerebbe alla prima sorgente nuova.
export const SORGENTE_CLIENT_MAP = Object.freeze({
  [SORGENTE_CODES.PREVENTIVO]: preventivoDocumenti,
  [SORGENTE_CODES.CONTRATTO]: contrattoDocumenti,
  [SORGENTE_CODES.OFFERTA_COMMERCIALE]: offertaDocumenti,
  [SORGENTE_CODES.ORDINE_VENDITA]: ordineDocumenti,
  [SORGENTE_CODES.DDT_VENDITA]: ddtDocumenti,
  [SORGENTE_CODES.FATTURA]: fattureDocumenti,
})
