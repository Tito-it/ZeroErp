// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
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
//
//        ⭐ Dal 2026-10-09 (brief un-solo-fuso-aziendale F-5) anche il FUSO:
//        «oggi», l'ora di un istante e l'ora digitata sono quelli
//        dell'AZIENDA, e passano da `date.js`. Fuori di li' si fermano le
//        forme che usano il fuso del PC, tutte mute:
//        - `new Date()` per «oggi» o «adesso» (`oggiAziendale`, `adesso`);
//        - `new Date(stringa)`: su `'YYYY-MM-DD'` e' la mezzanotte UTC, il
//          giorno prima nei fusi negativi (`parseIsoDate`, `parseIstante`);
//        - `setHours(0, 0, 0, 0)` per togliere l'ora (`giornoDi`);
//        - `toLocaleDateString`/`toLocaleTimeString`, che senza `timeZone`
//          scrivono nel fuso del PC (`displayOggiEsteso`, `displayTimestamp`).
//        Ammessi: la copia `new Date(x.getTime())` e la costruzione numerica
//        `new Date(anno, mese, giorno)`, che non leggono un fuso.
//
// Indice test:
//  1. nessun `toISOString()` fuori da core/utils/date.js
//  2. nessun formato di DatePicker scritto a mano fuori dalle due sedi
//  3. nessun `new Date()` vuoto fuori da date.js
//  4. nessun `new Date(x)` con un solo argomento che non sia `y.getTime()`
//  5. nessun `setHours(` fuori da date.js
//  6. nessun `toLocaleDateString(`/`toLocaleTimeString(` fuori da date.js
//  7. controprova: la scansione degli argomenti di `new Date(` vede le forme
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

// Scopo: gli argomenti di ogni `new Date(…)` di una riga (fra la parentesi
//         aperta e la sua chiusa, contando le annidate).
function argomentiNewDate(riga) {
  const esiti = []
  const rx = /new Date\(/g
  let m
  while ((m = rx.exec(riga)) !== null) {
    let livello = 1
    let i = m.index + m[0].length
    const inizio = i
    for (; i < riga.length && livello > 0; i++) {
      if (riga[i] === '(') livello++
      else if (riga[i] === ')') livello--
    }
    esiti.push(riga.slice(inizio, i - 1).trim())
  }
  return esiti
}

// Scopo: un argomento di `new Date(…)` che non legge un fuso: una copia
//         (`x.getTime()`) o piu' argomenti numerici (`anno, mese, giorno`).
function newDateAmmesso(arg) {
  if (arg.endsWith('.getTime()')) return true
  let livello = 0
  for (const c of arg) {
    if (c === '(' || c === '[' || c === '{') livello++
    else if (c === ')' || c === ']' || c === '}') livello--
    else if (c === ',' && livello === 0) return true
  }
  return false
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

  it('nessun `new Date()` vuoto fuori da date.js', () => {
    expect(violazioni(/new Date\(\s*\)/, SEDE_DATE)).toEqual([])
  })

  it('nessun `new Date(x)` con un solo argomento che non sia `y.getTime()`', () => {
    const trovate = []
    for (const [chiave, testo] of Object.entries(sorgenti)) {
      const file = percorso(chiave)
      if (SEDE_DATE.includes(file)) continue
      senzaCommenti(testo).split('\n').forEach((riga, i) => {
        for (const arg of argomentiNewDate(riga)) {
          if (arg && !newDateAmmesso(arg)) trovate.push(`${file}:${i + 1}: ${riga.trim()}`)
        }
      })
    }
    expect(trovate).toEqual([])
  })

  it('nessun `setHours(` fuori da date.js', () => {
    expect(violazioni(/\.setHours\(/, SEDE_DATE)).toEqual([])
  })

  it('nessun `toLocaleDateString(`/`toLocaleTimeString(` fuori da date.js', () => {
    expect(violazioni(/\.toLocale(?:Date|Time)String\(/, SEDE_DATE)).toEqual([])
  })

  it('controprova: la scansione di `new Date(` vede le forme', () => {
    expect(argomentiNewDate("const d = new Date(s + 'T00:00:00')")).toEqual(["s + 'T00:00:00'"])
    expect(argomentiNewDate('x = new Date(a.b(c))')).toEqual(['a.b(c)'])
    expect(newDateAmmesso("s + 'T00:00:00'")).toBe(false)
    expect(newDateAmmesso('val')).toBe(false)
    expect(newDateAmmesso('v.getTime()')).toBe(true)
    expect(newDateAmmesso('Number(anno), Number(mese) - 1, 1')).toBe(true)
  })
})
