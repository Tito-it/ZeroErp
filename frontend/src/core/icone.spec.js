// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Le icone si scrivono per SIGNIFICATO, in un punto solo
//        (censimento icone per significato, approvato da Tid 2026-09-27).
//        Un `'pi pi-...'` scritto a mano in un componente e' un segno senza
//        nome: il prossimo lo copia dal vicino sbagliato e due gesti diversi
//        finiscono per portare lo stesso disegno. Ne' il lint ne' la build se
//        ne accorgono; qui se ne accorge la CI.
//        Fissa anche che ogni glifo delle costanti esista in PrimeIcons: una
//        classe inesistente non da' errore, l'icona semplicemente non c'e'
//        (misurato: `pi-arrow-turn-down-right` nei listini, 2026-09-27).
//
// Indice test:
//  1. nessuna icona PrimeIcons scritta a mano fuori da constants/navigation
//  2. ogni glifo delle costanti di icona esiste in PrimeIcons
// ------------------------------------------------------------
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { MANAGE_ICONS, STATUS_ICONS, RECAPITO_ICONS } from './constants'
import { NAV_ICONS, TIPO_RUOLO_ICONS } from './navigation'

// Le sole due case dei nomi di icona.
const CASE = ['./constants.js', './navigation.js']

// Eccezioni dichiarate, ciascuna col suo motivo. ⛔ Non e' un parcheggio: una
// riga qui e' un debito con un brief aperto.
const ECCEZIONI = {
  // Copia a mano delle icone che il DB manda nelle azioni del lotto
  // (`config.stati_doc_fiscale_transizioni.meta.icon`): finche' il DB manda
  // glifi e non significati, cambiarle qui separerebbe il kebab della lista
  // dalla barra del drawer. Si chiude col brief DB sulle icone delle azioni.
  '../vendite/composables/useLottoAzioni.js': 3,
}

// Un letterale di icona: `pi pi-x` in stringa o attributo, o `'pi-x'` nudo.
const LETTERALE = /(?:['"`]\s*|class="|icon=")pi pi-[a-z]|'pi-[a-z][a-z-]*'/g

const sorgenti = import.meta.glob(
  ['../**/*.vue', '../**/*.js', '!../**/*.spec.js', '!../**/*.test.js'],
  { query: '?raw', import: 'default', eager: true },
)

// Toglie i commenti di riga e di blocco: la regola vale per il codice, e i
// commenti che spiegano un glifo lo devono poter nominare.
function senzaCommenti(testo) {
  return testo
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/(^|[^:'"`])\/\/[^\n]*/g, '$1')
}

// Letto dal disco: importato come modulo, in test il CSS arriva vuoto.
const primeiconsCss = readFileSync(
  new URL('../../node_modules/primeicons/primeicons.css', import.meta.url),
  'utf8',
)

describe('icone per significato', () => {
  it('nessuna icona PrimeIcons scritta a mano fuori da constants/navigation', () => {
    expect(Object.keys(sorgenti).length).toBeGreaterThan(100)
    const violazioni = []
    for (const [file, testo] of Object.entries(sorgenti)) {
      if (CASE.includes(file)) continue
      const trovati = senzaCommenti(testo).match(LETTERALE) ?? []
      const ammessi = ECCEZIONI[file] ?? 0
      if (trovati.length > ammessi) violazioni.push(`${file}: ${trovati.length} (ammessi ${ammessi})`)
    }
    expect(violazioni, 'usare MANAGE_ICONS / STATUS_ICONS / RECAPITO_ICONS / NAV_ICONS').toEqual([])
  })

  it('ogni glifo delle costanti di icona esiste in PrimeIcons', () => {
    const gruppi = { MANAGE_ICONS, STATUS_ICONS, RECAPITO_ICONS, NAV_ICONS, TIPO_RUOLO_ICONS }
    const mancanti = []
    for (const [gruppo, mappa] of Object.entries(gruppi)) {
      for (const [chiave, valore] of Object.entries(mappa)) {
        for (const glifo of String(valore).match(/pi-[a-z][a-z-]*/g) ?? []) {
          if (glifo === 'pi-spin') continue
          if (!primeiconsCss.includes(`.${glifo}:before`)) mancanti.push(`${gruppo}.${chiave}: ${glifo}`)
        }
      }
    }
    expect(mancanti).toEqual([])
  })
})
