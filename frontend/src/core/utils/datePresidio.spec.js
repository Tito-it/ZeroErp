// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Le date si convertono e si mostrano in un punto solo
//        (`core/utils/date.js`, `DATE_FORMAT`/`MONTH_FORMAT` di
//        `core/constants.js`). Né il lint né la build vedono le due forme
//        che qui si fermano, e tutte e due sbagliano IN SILENZIO:
//        - `toISOString()` su una data del DatePicker (mezzanotte LOCALE)
//          la porta in UTC, cioè al giorno prima: la scadenza della qualifica
//          di un fornitore si salvava così un giorno prima di quella scelta
//          (corretto il 2026-10-04). La strada è `toDateString` (solo data) o
//          `toTimestampString` (un istante), che vivono in `date.js`;
//        - un formato del DatePicker scritto sul posto: due selettori del mese
//          avevano due formati diversi, e uno mostrava un giorno su un campo
//          che non ne ha (regola del 2, `MONTH_FORMAT`, 2026-10-04).
//
// Indice test:
//  1. nessun `toISOString()` fuori da core/utils/date.js
//  2. nessun formato di DatePicker scritto a mano fuori dalle due sedi
// ------------------------------------------------------------
import { describe, it, expect } from 'vitest'

const sorgenti = import.meta.glob(
  ['../../**/*.vue', '../../**/*.js', '!../../**/*.spec.js', '!../../**/*.test.js'],
  { query: '?raw', import: 'default', eager: true },
)

// Le sole sedi ammesse, per regola, come percorso sotto `src/`.
// ⚠️ Si confronta il percorso RISOLTO, non la chiave del glob: Vite la scrive
//    relativa a questo file (`./date.js`, `../constants.js`), e un confronto
//    sulla chiave sbagliava l'esclusione senza errore.
const SEDE_DATE = ['src/core/utils/date.js']
const SEDI_FORMATO = ['src/core/constants.js', 'src/core/primevue-locale.js']

// Scopo: il percorso di un sorgente sotto `src/`, dalla chiave del glob.
function percorso(chiave) {
  const p = new URL(chiave, import.meta.url).pathname
  return p.slice(p.lastIndexOf('/src/') + 1)
}

// Toglie i commenti: la regola vale per il codice, e un commento che spiega
// perché `toISOString` è vietato lo deve poter nominare.
function senzaCommenti(testo) {
  return testo
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/(^|[^:'"`])\/\/[^\n]*/g, '$1')
}

function violazioni(regex, escluse) {
  const trovate = []
  for (const [chiave, testo] of Object.entries(sorgenti)) {
    const file = percorso(chiave)
    if (escluse.includes(file)) continue
    senzaCommenti(testo).split('\n').forEach((riga, i) => {
      if (regex.test(riga)) trovate.push(`${file}:${i + 1}: ${riga.trim()}`)
    })
  }
  return trovate
}

describe('date in un punto solo', () => {
  it('nessun `toISOString()` fuori da core/utils/date.js', () => {
    expect(Object.keys(sorgenti).length).toBeGreaterThan(100)
    expect(violazioni(/\.toISOString\(/, SEDE_DATE)).toEqual([])
  })

  it('nessun formato di DatePicker scritto a mano fuori dalle due sedi', () => {
    // L'attributo letterale (`date-format="…"`, `dateFormat="…"`, senza i
    // due punti del binding) o la chiave in un oggetto (`dateFormat: '…'`).
    // La forma ammessa è il binding a una costante: `:date-format="DATE_FORMAT"`.
    const letterale = /(?:^|[\s<])(?:date-format|dateFormat)="|dateFormat\s*:\s*['"`]/
    expect(violazioni(letterale, SEDI_FORMATO)).toEqual([])
  })
})
