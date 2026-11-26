// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Presidio del colore del livello d'accesso in una sede sola (D-5 di
//        brief-be-fe-BB-audit, Tid 2026-11-24): LETTURA e' arancio ovunque, e
//        nessun file fuori da `severity.js` ne scrive una mappa sua.
// ------------------------------------------------------------
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { LIVELLO_ACCESSO } from '../constants'
import { livelloAccessoSeverity } from './severity'

// I sorgenti sotto `src/`, senza gli spec.
function sorgenti(dir) {
  return readdirSync(dir).flatMap((nome) => {
    const p = join(dir, nome)
    if (statSync(p).isDirectory()) return sorgenti(p)
    return /\.(js|vue)$/.test(nome) && !nome.includes('.spec.') ? [p] : []
  })
}

describe('livelloAccessoSeverity', () => {
  it('un colore per livello, LETTURA arancio', () => {
    expect(livelloAccessoSeverity(LIVELLO_ACCESSO.TUTTO)).toBe('success')
    expect(livelloAccessoSeverity(LIVELLO_ACCESSO.LETTURA)).toBe('warn')
    expect(livelloAccessoSeverity(LIVELLO_ACCESSO.BLOCCATO)).toBe('danger')
    expect(livelloAccessoSeverity('ALTRO')).toBe('secondary')
  })

  // ⛔ La copia ritirata rispondeva `info` per LETTURA: una funzione che
  //    confronta un livello con 'LETTURA' e ritorna una severity e' una mappa
  //    nuova, e il colore torna a dipendere dalla pagina.
  it('nessuna mappa del livello fuori da severity.js', () => {
    const radice = new URL('../../', import.meta.url).pathname
    const file = sorgenti(radice)
    expect(file.length).toBeGreaterThan(100)
    const copie = file.filter((p) => {
      if (p.endsWith(join('core', 'utils', 'severity.js'))) return false
      const testo = readFileSync(p, 'utf8')
      return /(===\s*(LIVELLO_ACCESSO\.LETTURA|'LETTURA'))\)\s*return\s*'(warn|info|success|danger|secondary)'/.test(testo)
    })
    expect(copie).toEqual([])
  })
})
