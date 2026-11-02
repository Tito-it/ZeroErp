// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: le SEDI UNICHE della resa di una riga di giornale
//        (`vendite.giornale`, lista 79): quali colonne hanno una cella propria
//        e da quale catalogo si leggono le etichette di registro ed entita'.
// Note: ⭐ Nasce il 2026-09-27 (regola del 2, brief-db-liste-datatable-grezze
//       §3.1): la stessa lista si monta in DUE posti — il giornale trasversale
//       (`GiornaleListView`) e la Storia di fattura e lotto
//       (`GiornaleEntitaTab`) — e gli slot di cella scritti due volte sono la
//       forma in cui la stessa riga si legge in due modi a seconda della
//       schermata. Consumato da `GiornaleCella`, e dalla view per le tendine.
// ------------------------------------------------------------

import { lookupTipiEntita } from '../../../core/apiCore'

// Le colonne del catalogo che la cella sa rendere, per `codice` di colonna (i
// nomi degli slot sono `cell-${codice}`). ⚠️ Il CODICE, non il campo_sorgente:
// uno slot col nome sbagliato non da' errore — la cella ripiega sul testo
// grezzo e il Tag sparisce.
// ⭐ Chi non c'e' si rende da se': `quando` col formato del seed
//    (`datetime_short`), `entita_display` e `user_insert` come testo.
export const GIORNALE_CELLE = Object.freeze([
  'gravita', 'registro', 'entity_type', 'cosa', 'tx_id', 'correlation_id',
])

// ⭐ Le due SORGENTI delle etichette, una volta sola: tendine e celle devono
//    puntare alla STESSA entry di cache (`useLookupEtichettato` — «stessa
//    chiave = stesso insieme, o il primo montato vince in silenzio»).
//    · i tipi di entita' da `config.tipi_entita` (lookup dedicato: la tabella
//      non ha `id`/`descrizione`);
//    · i registri da `config.registri_giornale` (lookup generico), i soli VIVI:
//      un registro ritirato non ha piu' ramo nella vista, e in tendina sarebbe
//      una scelta vuota. La chiave stabile e' `codice_interno`, quella che il
//      backend valida.
export const SORGENTE_TIPI_ENTITA = Object.freeze({
  chiave: 'config.tipi_entita', fetcher: lookupTipiEntita,
})
export const SORGENTE_REGISTRI = Object.freeze({
  rel: 'config.registri_giornale', includiObsoleti: false,
})
export const CAMPO_CODICE_REGISTRO = 'codice_interno'
