// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: IL TESTO INTERO DEL VALORE SELEZIONATO di una combo — quello che va
//        nel `title`, cosi' al passaggio del mouse si legge cio' che la combo
//        stretta taglia coi puntini.
// Note: ⭐ Nato da A4 di brief-fe-filtri-lista-su-schermo-compatto (2026-09-24,
//        ok Tid): da quando le larghezze dei filtri sono classi (`sm`/`md`/`lg`)
//        una combo `md` con una descrizione di catalogo mostra il valore
//        troncato, e per leggerlo bisognava aprire la tendina. E' la stessa
//        cosa che `.app-lista-cella` fa per le celle di lista (`testoCella`).
//
//       ⭐ REGOLA DEL 2: i consumatori sono le due combo `md` del criterio di A1
//        — `LookupSelect` e `UtilityPerRuoloSelect` — e la decisione «quale
//        testo, e quando nessuno» e' una sola. Scritta nei due componenti,
//        divergerebbe al primo `show-code`.
//
//       ⚠️ Nessuna selezione ⇒ `undefined`, MAI la stringa vuota: con `''` Vue
//        stampa `title=""`, un attributo che non dice niente. `undefined` lo
//        toglie. Stessa cosa per una voce trovata ma senza etichetta.
//
//       ⛔ Serve solo al desktop: sul touch non c'e' hover. Non e' un modo di
//        rendere leggibile la combo al telefono, e' un aiuto dove il mouse c'e'.
// ------------------------------------------------------------

// Scopo: il testo della voce selezionata fra `opzioni`, o `undefined`.
// `etichetta` e' il NOME del campo (`'descrizione'`) oppure una funzione
// `voce => testo` — la seconda per chi compone il testo (`show-code`), cosi'
// il `title` dice esattamente cio' che si legge a video.
// ⚠️ `valore === null` si cerca lo stesso: la voce «Tutti» di un filtro ha
// valore `null` ed e' una selezione vera. `undefined` invece non e' un valore.
export function etichettaSelezionata(opzioni, valore, { campoValore = 'id', etichetta = 'descrizione' } = {}) {
  if (valore === undefined || !Array.isArray(opzioni)) return undefined
  return etichettaVoce(opzioni.find(o => o?.[campoValore] === valore), etichetta)
}

// Scopo: il testo di una voce GIA' TROVATA, o `undefined` — per chi la voce
// selezionata la cerca gia' per conto suo (`selectedItem` di `LookupSelect`) e
// non deve cercarla una seconda volta. La regola «mai `''`» resta qui, una.
export function etichettaVoce(voce, etichetta = 'descrizione') {
  if (!voce) return undefined
  const testo = typeof etichetta === 'function' ? etichetta(voce) : voce[etichetta]
  if (testo == null) return undefined
  const s = String(testo).trim()
  return s === '' ? undefined : s
}
