// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: il verbo «Riporta da emettere» e la lettura dei suoi motivi ostativi.
// Note: l'oggetto e' l'ATTIVITA' FATTURABILE, non il cruscotto — oggi il gesto
//       parte dalla card «Emesse non fatturate», ma domani puo' partire da
//       un'altra schermata e il client non deve seguirla.
// ------------------------------------------------------------
import api from '../../core/api'

// POST /vendite/attivita-fatturabili/riporta-da-emettere/
// Rimette in coda di fatturazione le attivita' indicate: le libera e riporta a
// NON_EMESSA le righe di commessa passate a EMESSA per causa loro.
// ⚠️ Nessun lotto viene rigenerato e nessuna fattura viene ricreata: il lavoro
//    ricompare in «Da emettere» e segue il giro normale.
// ⚠️ SINCRONO: due scritture e una transazione, nessun job da seguire. Non si
//    accoda per simmetria con «Rendi definitive», che porta la dedup.
export function riportaDaEmettere(attivitaFatturabiliIds) {
  return api.post(
    '/vendite/attivita-fatturabili/riporta-da-emettere/',
    { attivita_fatturabili_ids: attivitaFatturabiliIds },
  )
}

// POST /vendite/attivita-fatturabili/riportabili/
// I motivi che impedirebbero il riporto, senza tentarlo.
// ⚠️ E' un POST pur essendo una LETTURA: una selezione di 200 righe non sta in
//    una query string. Nessun side-effect: la key che l'interceptor
//    aggiunge a ogni POST qui e' innocua (il BE la ignora).
// ⭐ Serve a spiegare invece di far fallire: incontrare
//    `E_ATTIVITA_GIA_DA_EMETTERE` significa che l'elenco a schermo era
//    invecchiato, quindi si ri-guarda prima di agire su una selezione vecchia.
export function checkRiportabili(attivitaFatturabiliIds) {
  return api.post('/vendite/attivita-fatturabili/riportabili/', {
    attivita_fatturabili_ids: attivitaFatturabiliIds,
  })
}
