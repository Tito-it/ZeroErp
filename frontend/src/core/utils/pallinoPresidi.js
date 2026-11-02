// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: LA RESA DEL PALLINO DEI PRESIDI, in una funzione PURA: dalla testata
//        `{totale, con_righe, non_letti}` ai segmenti da disegnare in topbar
//        (decisione #8 di Tid, 2026-09-18). Consumata da `usePresidiPolling`.
// Note: ⛔ Nessun import, di proposito: e' il modulo che ha la spec, e un
//        import dal composable trascinerebbe store, auth e i18n nel test.
//        Stesso pattern di `vendite/_shared/lotti/ramoBannerLotto.js`.
// ------------------------------------------------------------

export const SEGMENTO_ALLARMI = 'allarmi'
export const SEGMENTO_NON_LETTI = 'non_letti'

// Scopo: LA RESA DEL PALLINO, in una funzione PURA (come `scegliRamoBanner`):
//        dalla testata ai segmenti da disegnare. Tre rami che, sbagliati, non
//        falliscono — mostrano il colore sbagliato — e per questo hanno una spec
//        con un caso ciascuno.
//        · tutto a zero          → UN segmento verde con lo `0` (il «visto e
//                                   vuoto», che e' il motivo del pallino);
//        · allarmi               → segmento `danger` col numero;
//        · non letti             → segmento `warn` col numero («chiede un
//                                   occhio»: cecita', non guasto);
//        · entrambi              → due segmenti, PRIMA gli allarmi (l'ordine e'
//                                   fisso: e' quello con cui si legge).
//        `null` finche' la testata non e' arrivata: al primo paint niente falsi
//        verdi e niente falsi rossi.
export function statoPallino(testata) {
  if (!testata) return null
  const allarmi = testata.con_righe ?? 0
  const nonLetti = testata.non_letti ?? 0
  const segmenti = []
  if (allarmi > 0) segmenti.push({ chiave: SEGMENTO_ALLARMI, valore: allarmi, severity: 'danger' })
  if (nonLetti > 0) segmenti.push({ chiave: SEGMENTO_NON_LETTI, valore: nonLetti, severity: 'warn' })
  const ok = segmenti.length === 0
  if (ok) segmenti.push({ chiave: SEGMENTO_ALLARMI, valore: 0, severity: 'success' })
  return { ok, segmenti, allarmi, nonLetti }
}
