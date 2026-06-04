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
})
