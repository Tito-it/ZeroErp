// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Constants centralizzate del modulo documenti (sorgente codes,
//        ecc.). Estratte applicando la regola del 2 (memoria
//        `feedback_regola_del_2_estrai_bb`): 3+ occorrenze di stringhe
//        magic `'OFFERTA_COMMERCIALE'`/`'PREVENTIVO'`/`'CONTRATTO'` come
//        sorgente-code nei drawer e store. Qui solo i codici che il
//        frontend CONFRONTA; l'elenco dei builder registrati si legge dal
//        backend (`GET /documenti/context-builders/`).
// ------------------------------------------------------------

// I codici di `config.sorgenti` che il frontend CONFRONTA o MANDA: le sorgenti
// del motore documentale registrate lato BE
// (`apps.documenti.services.context_builders.registry`) e, dal 2026-10-19
// (grammatica unica, lotto 2a: un vocabolario solo per i tipi di documento),
// il tipo di documento della risoluzione IVA (`documento_tipo`), il `contesto`
// della situazione merce e il `documento` del lettore dei legami. Dal lotto 2b
// (stesso giorno) anche l'`origine` dei legami (tranne ONERE, che non e' una
// sorgente) e la destinazione dello smistamento del preventivo.
// ⚠️ Non e' l'elenco dei builder registrati (COMMESSA non ne ha uno): quello si
//    legge da `GET /documenti/context-builders/`.
// ⭐ La chiave E' il codice (`config.sorgenti.codice_interno`), come il nome
//    `SORGENTE_<codice>` lato BE: una chiave corta (`DDT`) e' un vocabolario
//    in piu' (brief-db-grammatica-unica-documenti). Lo presidia constants.spec.js.
export const SORGENTE_CODES = Object.freeze({
  PREVENTIVO: 'PREVENTIVO',
  CONTRATTO: 'CONTRATTO',
  OFFERTA_COMMERCIALE: 'OFFERTA_COMMERCIALE',
  ORDINE_VENDITA: 'ORDINE_VENDITA',
  // DDT di vendita (DDT accompagnatorio): quinto dominio del motore
  // documentale, context builder DDT_VENDITA registrato lato BE.
  DDT_VENDITA: 'DDT_VENDITA',
  // Reso di vendita: l'origine di un legame della commessa (il reso torna da
  // accreditare), nella finestra dei legami.
  RESO_VENDITA: 'RESO_VENDITA',
  // Fattura: sesto dominio del motore documentale, context builder FATTURA
  // registrato lato BE. Stampa/ristampa (nessuna emissione da UI).
  FATTURA: 'FATTURA',
  // Commessa: il documento che si annulla nella finestra dei legami
  // (`vendite.fn_documento_legami`), dove ha una frase sua.
  COMMESSA: 'COMMESSA',
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
