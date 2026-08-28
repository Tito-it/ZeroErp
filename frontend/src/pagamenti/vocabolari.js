// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: I vocabolari CHIUSI del dominio incassi che il frontend deve
//        conoscere, in un punto solo.
// Note: ⛔ QUI STANNO SOLO I VOCABOLARI CHE **NON** HANNO UN CATALOGO. Sono
//       `CHECK` del database o whitelist del backend: non esiste una tabella da
//       interrogare, quindi il frontend una copia la tiene per forza — e allora
//       la tiene in UN posto, dove si vede.
//       ⛔ Gli STATI (distinta e riga) NON stanno qui: sono tabelle di catalogo
//       (`pagamenti.vendite_contabili_stati`, `..._righe_stati`), gia' in
//       whitelist per il lookup generico, e il dettaglio della distinta se li
//       porta dietro coi flag che governano l'interfaccia. Copiarli qui
//       vorrebbe dire nascondere in silenzio lo stato che nascera' domani.
//       ⚠️ Ogni etichetta si risolve **fail-visible** (`labelOrCode`): un valore
//       che il backend aggiunge e i locales non conoscono si vede come CODICE,
//       non come cella vuota.
//       ⚠️ Nessun import di pinia o di store: questo modulo lo carica anche il
//       ROUTER, che non deve tirarsi dietro uno store per leggere una costante.
// ------------------------------------------------------------

// Le tre code della lista righe (Q-4 -> c). Contratto: `GET /pagamenti/righe/`
// param `coda`. ⛔ Vocabolario chiuso lato backend: un valore inventato e' un
// **400**, non una lista vuota.
// ⚠️ `TUTTE` e' parte del contratto ma **non ha una porta**: le voci di menu
//    sono due, ed erano due nella decisione. Resta dichiarata perche' e' il
//    vocabolario dell'endpoint, non perche' qualcuno la usi oggi.
export const CODE = Object.freeze({
  DA_ABBINARE: 'DA_ABBINARE',
  SOSPESE: 'SOSPESE',
  TUTTE: 'TUTTE',
})

// ⭐ Le DUE porte, e la rotta di ciascuna. Serve al selettore in pagina, che
//    NAVIGA invece di cambiare uno stato interno: la rotta e' l'unica verita' —
//    altrimenti l'etichetta del tab direbbe «Sospese» mentre a video si guarda
//    «Da abbinare», e a quel punto il deep-link non descrive piu' la pagina.
export const ROTTA_PER_CODA = Object.freeze({
  [CODE.DA_ABBINARE]: 'pagamenti-coda-abbinare',
  [CODE.SOSPESE]: 'pagamenti-coda-sospese',
})

// Origine della distinta — `CHECK` su `pagamenti.vendite_contabili.origine`.
export const ORIGINI_DISTINTA = Object.freeze(['MANUALE', 'AUTOMATICA', 'GENERATA'])

// Perche' una rata e' fuori capienza — whitelist `MOTIVI_FUORI_CAPIENZA` del
// backend. ⚠️ Sono DUE mondi diversi, non due sfumature: sovra-incasso (e'
// entrato piu' del dovuto) e movimento contrario (un segno che non torna).
export const MOTIVI_FUORI_CAPIENZA = Object.freeze(['SOVRA_INCASSATA', 'MOVIMENTO_CONTRARIO'])

// Di chi sono i soldi in eccedenza. ⛔ Sbagliare il verso significa rimborsare
// cio' che si deve incassare: e' un filtro esposto e una colonna a colori, non
// un segno da leggere dentro un numero.
export const CHI_E_IN_CREDITO = Object.freeze(['CLIENTE', 'AZIENDA'])

// Il colore del verso. ⚠️ `CLIENTE` in credito = c'e' qualcosa da restituire,
// quindi arancio; `AZIENDA` in credito = da incassare, informativo.
export const SEVERITY_CHI_E_IN_CREDITO = Object.freeze({
  CLIENTE: 'warn',
  AZIENDA: 'info',
})
