// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: le tendine «erogazione» e «fonte della quantita'» di una riga
//        commerciale (riga di contratto, eccezione di offerta) costruite sulle
//        combinazioni che il DB dichiara per l'articolo
//        (`GET …/righe/erogazioni/` → `vendite.fn_documento_riga_erogazioni`).
// Note: brief-db-offerta-emissione-ed-erogazione B-R4, 2026-10-07.
// ------------------------------------------------------------

// ⛔ QUI NON C'E' UNA REGOLA. Quali combinazioni sono ammesse e quale e' quella
//    di default lo dice il DB, dall'articolo (tipologia, altrimenti natura di
//    vendita; DERIVATA_COMPONENTI in piu' sul composito). Queste funzioni
//    METTONO IN FORMA cio' che arriva: prendono le combinazioni come sono,
//    nell'ordine in cui il DB le da'. Prende il posto di
//    `fontiQuantitaErogazione.js`, che la matrice la ricopiava — e non sapeva
//    niente di tipologia ne' di utility.
//
// Una combinazione: { tipo_erogazione, fonte_quantita_attesa, e_default,
//                     generazione_canone, origine }.

// Scopo: le opzioni di una tendina dai valori, senza doppioni e nell'ordine
//        dato. ⭐ Il valore gia' scritto sulla riga resta fra le opzioni anche
//        se l'articolo oggi non lo ammette (B-D6: le righe gia' scritte restano
//        come sono), o la tendina lo mostrerebbe vuoto.
function opzioni(valori, corrente, etichetta) {
  const unici = [...new Set(valori)]
  if (corrente && !unici.includes(corrente)) unici.push(corrente)
  return unici.map((value) => ({ value, label: etichetta(value) }))
}

// Scopo: le erogazioni che l'articolo ammette, per la tendina.
export function opzioniErogazione(combinazioni, corrente, etichetta) {
  return opzioni((combinazioni ?? []).map((c) => c.tipo_erogazione), corrente, etichetta)
}

// Scopo: le fonti che l'articolo ammette CON l'erogazione scelta, per la tendina.
export function opzioniFonte(combinazioni, tipo, corrente, etichetta) {
  return opzioni(
    (combinazioni ?? [])
      .filter((c) => c.tipo_erogazione === tipo)
      .map((c) => c.fonte_quantita_attesa),
    corrente,
    etichetta,
  )
}

// Scopo: la combinazione che la riga erediterebbe dal DB (quella `e_default`),
//        o null.
export function combinazioneDefault(combinazioni) {
  return (combinazioni ?? []).find((c) => c.e_default) ?? null
}

// Scopo: la fonte dopo che l'operatore ha cambiato erogazione: la stessa se
//        l'articolo la ammette ancora con la nuova; l'unica ammessa se e' una
//        sola; altrimenti null, e la sceglie l'operatore. ⛔ Fra piu' fonti il
//        form non sceglie: quale preferire e' una regola del DB (il trigger
//        d'eredita'), non una da ricopiare qui.
export function fonteDopoCambioErogazione(combinazioni, tipo, fonteCorrente) {
  const fonti = (combinazioni ?? [])
    .filter((c) => c.tipo_erogazione === tipo)
    .map((c) => c.fonte_quantita_attesa)
  if (fonti.includes(fonteCorrente)) return fonteCorrente
  return fonti.length === 1 ? fonti[0] : null
}
