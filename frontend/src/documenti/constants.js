// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Constants centralizzate del modulo documenti (sorgente codes,
//        ecc.). Estratte applicando la regola del 2 (memoria
//        `feedback_regola_del_2_estrai_bb`): 3+ occorrenze di stringhe
//        magic `'OFFERTA_COMMERCIALE'`/`'PREVENTIVO'`/`'CONTRATTO'` come
//        sorgente-code nei drawer e store. La whitelist piena (con
//        i18nKey + registered) vive in
//        `config/constants/documentiContextBuilders.js` per il template
//        editor; qui solo gli enum di codice riusabili da chiunque.
// ------------------------------------------------------------

// Codici sorgente documentale registrati lato BE
// (`apps.documenti.services.context_builders.registry`).
// Allineati alle voci `registered: true` di
// `config/constants/documentiContextBuilders.js`.
export const SORGENTE_CODES = Object.freeze({
  PREVENTIVO: 'PREVENTIVO',
  CONTRATTO: 'CONTRATTO',
  OFFERTA_COMMERCIALE: 'OFFERTA_COMMERCIALE',
  ORDINE_VENDITA: 'ORDINE_VENDITA',
  // DDT di vendita (DDT accompagnatorio): quinto dominio del motore
  // documentale, context builder DDT_VENDITA registrato lato BE.
  DDT: 'DDT_VENDITA',
})

// Modalita' PDF di uno stato documento, capability `pdf.mode` esposta da
// `script.fn_available_actions_*` (colonna `config.stati_doc_*.pdf_mode`,
// CHECK IN ('PREVIEW','ARCHIVE','NONE')). Single source dei literal lato FE:
// consumati da `EntityPdfButton` (drawer) e dalla lista Ordini
// (`OrdiniSearchTable`, `row.pdf_mode === PDF_MODE.ARCHIVE`).
//   - PREVIEW: anteprima on-the-fly bozza (non persistita);
//   - ARCHIVE: PDF gia' generato all'emissione (gestione documenti);
//   - NONE:    nessuna gestione PDF (es. ANNULLATO).
export const PDF_MODE = Object.freeze({
  PREVIEW: 'PREVIEW',
  ARCHIVE: 'ARCHIVE',
  NONE: 'NONE',
})
