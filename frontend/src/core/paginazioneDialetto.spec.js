// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: ⛔ Un dialetto solo per la paginazione (decisione Tid 2026-10-21):
//        ogni lista del backend legge `limit`/`offset` e rifiuta
//        `page`/`page_size` con un 400 (`pagina_da_query`). Fino a quel giorno
//        una ventina di liste parlava `page`/`page_size`, e il frontend li
//        calcolava da `limit`/`offset` in sette punti diversi.
//        Il presidio legge il CODICE (commenti esclusi): una chiamata nuova
//        scritta col vecchio dialetto fa rosso qui, invece che un 400 a video.
//        E' il gemello di `test_nessuna_view_legge_page_page_size` del backend.
//
// Indice test:
//  1. nessun sorgente manda `page_size`
//  2. nessun sorgente manda `page` come parametro di query
// ------------------------------------------------------------
import { describe, expect, it } from 'vitest'

const sorgenti = import.meta.glob(
  ['../**/*.vue', '../**/*.js', '!../**/*.spec.js', '!../**/*.test.js'],
  { query: '?raw', import: 'default', eager: true },
)

// Toglie i commenti: la regola vale per il codice, e i commenti che
// raccontano il dialetto ritirato lo devono poter nominare.
function senzaCommenti(testo) {
  return testo
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/(^|[^:'"`])\/\/[^\n]*/g, '$1')
}

function trovate(regex) {
  return Object.entries(sorgenti)
    .filter(([, testo]) => regex.test(senzaCommenti(testo)))
    .map(([file]) => file)
}

describe('paginazione: un dialetto solo', () => {
  it('nessun sorgente manda `page_size`', () => {
    expect(trovate(/\bpage_size\b/)).toEqual([])
  })

  // ⚠️ Solo la CHIAVE di query (`page:` in un oggetto di params, `page=` in
  //    un URL): `:page="tablePage"` del paginatore e lo stato `page` dei BB
  //    sono la pagina a video, non cio' che viaggia.
  //    (Le prop `page: { type: Number }` dei componenti lista non contano.)
  it('nessun sorgente manda `page` come parametro di query', () => {
    expect(trovate(/[{,]\s*page\s*:\s*[^\s{]|[?&]page=/)).toEqual([])
  })
})
