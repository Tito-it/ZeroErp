// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa che un valore di filtro si STACCA dal letterale che lo dichiara —
//        copia profonda e congelamento profondo — perche' un default condiviso
//        per riferimento sposta il metro insieme alla cosa misurata.
// Note: i casi sono quelli che, sbagliati, NON danno errore: il segno mostrerebbe
//       il numero grigio su una lista ristretta a mano, e nessuno se ne accorgerebbe.
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'

import { clonaValore, clonaFiltri, congelaProfondo } from './clonaFiltri'

describe('clonaValore', () => {
  it('lascia passare gli scalari, `null` compreso', () => {
    expect(clonaValore(null)).toBe(null)
    expect(clonaValore(undefined)).toBe(undefined)
    expect(clonaValore(false)).toBe(false)
    expect(clonaValore(0)).toBe(0)
    expect(clonaValore('APERTA')).toBe('APERTA')
  })

  it('duplica un ARRAY: mutarne uno non tocca l-altro', () => {
    const originale = ['A', 'B']
    const copia = clonaValore(originale)
    expect(copia).toEqual(['A', 'B'])
    expect(copia).not.toBe(originale)
    copia.push('C')
    expect(originale).toEqual(['A', 'B'])
  })

  it('scende negli ANNIDAMENTI: un array dentro un oggetto e- staccato anche lui', () => {
    const originale = { stati: ['A'], soglia: { min: 1 } }
    const copia = clonaValore(originale)
    copia.stati.push('B')
    copia.soglia.min = 9
    expect(originale.stati).toEqual(['A'])
    expect(originale.soglia.min).toBe(1)
  })

  it('duplica una `Date`: e- mutabile ed e- un default vero (BoM «oggi alla nascita»)', () => {
    const originale = new Date('2026-09-23T00:00:00')
    const copia = clonaValore(originale)
    expect(copia).not.toBe(originale)
    expect(copia.getTime()).toBe(originale.getTime())
    copia.setFullYear(2030)
    expect(originale.getFullYear()).toBe(2026)
  })
})

describe('clonaFiltri', () => {
  it('stacca l-intero letterale, non solo il primo livello', () => {
    const DEFAULTS = { stato: null, stati: ['A'], attivo: true }
    const copia = clonaFiltri(DEFAULTS)
    expect(copia).toEqual(DEFAULTS)
    expect(copia).not.toBe(DEFAULTS)
    copia.stati.push('B')
    expect(DEFAULTS.stati).toEqual(['A'])
  })

  it('senza argomento non esplode: una lista puo- non avere filtri', () => {
    expect(clonaFiltri()).toEqual({})
  })
})

describe('congelaProfondo', () => {
  it('impedisce anche la `push` dentro un array annidato', () => {
    const d = congelaProfondo({ stati: ['A'] })
    expect(Object.isFrozen(d)).toBe(true)
    expect(Object.isFrozen(d.stati)).toBe(true)
    expect(() => { d.stati.push('B') }).toThrow()
    expect(d.stati).toEqual(['A'])
  })

  it('non entra in un ciclo su un oggetto gia- congelato', () => {
    const dentro = Object.freeze({ a: 1 })
    expect(() => congelaProfondo({ x: dentro, y: dentro })).not.toThrow()
  })
})
