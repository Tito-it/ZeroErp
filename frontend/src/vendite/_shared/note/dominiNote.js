// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: I documenti di vendita che hanno le note, e cio' che di loro serve
//        a `VenditeNoteDrawer`: lo slug del basePath API
//        (`/vendite/{dominio}/{id}`), la chiave del titolo e i campi della
//        label del select RIGA, che variano con la forma delle righe.
// Note: ⭐ Una riga per documento: e' quello che distingueva i sei wrapper di
//       dominio ritirati il 2026-10-31 (regola del 2).
//       ⚠️ Un modulo e non una costante dentro il componente: il `validator`
//       di `defineProps` viene sollevato fuori da `setup()`, e non puo'
//       leggere variabili locali dello `<script setup>`.
//       ⚠️ Le righe dell'offerta sono le sue eccezioni
//       (`vendite.offerte_commerciali_eccezioni`): `articolo_codice`/
//       `articolo_descrizione`.
// ------------------------------------------------------------

export const DOMINI_NOTE_VENDITE = Object.freeze({
  contratti: { titolo: 'vendite.contratti.note_titolo', codeField: 'codice_articolo', descField: 'descrizione' },
  preventivi: { titolo: 'vendite.preventivi.note_titolo', codeField: 'codice_articolo', descField: 'descrizione' },
  offerte: { titolo: 'vendite.offerte.note_titolo', codeField: 'articolo_codice', descField: 'articolo_descrizione' },
  ordini: { titolo: 'vendite.ordini.note_titolo', codeField: 'articolo_codice', descField: 'descrizione' },
  ddt: { titolo: 'vendite.ddt.note_titolo', codeField: 'articolo_codice', descField: 'descrizione' },
  fatture: { titolo: 'vendite.fatture.note_titolo', codeField: 'articolo_codice', descField: 'descrizione' },
})
