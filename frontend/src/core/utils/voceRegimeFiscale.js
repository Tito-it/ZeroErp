// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: la voce del regime fiscale che il record HA GIA', per la combo
//        `LookupSelect rel="config.regimi_fiscali"` (prop `voceCorrente`).
//        La combo propone i soli regimi ATTIVI: uno spento dopo la scelta
//        resta del record, e senza questa voce il campo apparirebbe vuoto
//        con un valore dentro (il BB la aggiunge in coda, «non attiva»).
// ⭐ Regola del 2 (ok Tid 2026-11-22): era ricopiata identica in
//    `EmittenteFiscaleDrawer` e `FornitoreDrawer`. Legge le tre chiavi che i
//    due dettagli portano con lo stesso nome: `regime_fiscale_rf` (il
//    `codice_interno`, il valore della combo), `regime_fiscale_codice` e
//    `regime_fiscale_descrizione` (dal catalogo).
// ⛔ Fino al 2026-11-22 le due copie mettevano in `codice` il
//    `codice_interno`: il catalogo tiene le due colonne distinte, e a video va
//    il codice. Dalla stessa data i due dettagli portano `regime_fiscale_codice`.
// ------------------------------------------------------------

export function voceRegimeFiscale(dettaglio) {
  if (!dettaglio?.regime_fiscale_rf) return null
  return {
    codice_interno: dettaglio.regime_fiscale_rf,
    codice: dettaglio.regime_fiscale_codice,
    descrizione: dettaglio.regime_fiscale_descrizione,
  }
}
