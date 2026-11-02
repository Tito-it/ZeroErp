// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: «Aggiorna date di consegna» — una data su piu' righe di un documento
//        di vendita (brief-db-date-consegna-righe-in-blocco §5, §8). Una
//        chiamata per ordine e preventivo: cambia solo il path del dominio,
//        che lo dichiara la sua API (`makeDateConsegnaApi(BASE)`).
// Note: ⚠️ La chiamata la fa lo STORE del dominio, che avvisa le liste dopo la
//       scrittura (frontend-standards §«Producer cross-tab»): mai il dialog.
// ------------------------------------------------------------
import api from '../../../core/api'

// Le due modalita' (D-2): tutte le righe, o solo quelle senza data.
export const MODALITA_DATE_CONSEGNA = Object.freeze({
  TUTTE: 'TUTTE',
  SOLO_VUOTE: 'SOLO_VUOTE',
})

// Scopo: la chiamata per un dominio (`/vendite/ordini`).
export function makeDateConsegnaApi(base) {
  return {
    // (documentoId, { colonna, data, modalita, anteprima }) →
    // `{ aggiornate, saltate_spedite, anteprima, ... }` nell'envelope standard.
    // `anteprima: true` esegue lo stesso UPDATE e lo annulla: i numeri della
    // scrittura, e un rifiuto del DB arriva gia' qui.
    aggiornaDateConsegna: (documentoId, payload) =>
      api.post(`${base}/${documentoId}/righe/date-consegna/`, payload),
  }
}
