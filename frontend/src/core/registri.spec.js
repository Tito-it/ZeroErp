// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il contratto del registro di iscrizione e dei punti di
//        estensione: chiave doppia = errore, chiave assente = null, ordine.
//
// Indice test:
//  1. registro: iscrive e restituisce, assente = null
//  2. registro: chiave doppia o vuota = errore
//  3. punti: contributi in ordine, punto vuoto = elenco vuoto
//  4. punti: chiave doppia nello stesso punto = errore, in punti diversi no
// ------------------------------------------------------------

import { describe, expect, it } from 'vitest'
import { creaPuntiEstensione, creaRegistro } from './registri'

describe('creaRegistro', () => {
  it('iscrive e restituisce; una chiave assente risponde null', () => {
    const r = creaRegistro('prova')
    r.iscrivi('A', { n: 1 })
    expect(r.voce('A')).toEqual({ n: 1 })
    expect(r.voce('B')).toBeNull()
    expect(r.voce(null)).toBeNull()
    expect(r.chiavi()).toEqual(['A'])
  })

  it('una chiave doppia o vuota e\' un errore', () => {
    const r = creaRegistro('prova')
    r.iscrivi('A', {})
    expect(() => r.iscrivi('A', {})).toThrow(/due volte/)
    expect(() => r.iscrivi('', {})).toThrow(/vuota/)
  })
})

describe('creaPuntiEstensione', () => {
  it('restituisce i contributi in ordine; un punto senza contributi e\' vuoto', () => {
    const e = creaPuntiEstensione('prova')
    e.contribuisci('p', { chiave: 'b', ordine: 20 })
    e.contribuisci('p', { chiave: 'a', ordine: 10 })
    e.contribuisci('p', { chiave: 'c' })
    expect(e.contributi('p').map(c => c.chiave)).toEqual(['a', 'b', 'c'])
    expect(e.contributi('altro')).toEqual([])
  })

  it('la stessa chiave nello stesso punto e\' un errore, in punti diversi no', () => {
    const e = creaPuntiEstensione('prova')
    e.contribuisci('p', { chiave: 'a' })
    expect(() => e.contribuisci('p', { chiave: 'a' })).toThrow(/due volte/)
    expect(() => e.contribuisci('q', { chiave: 'a' })).not.toThrow()
    expect(() => e.contribuisci('p', {})).toThrow(/senza chiave/)
  })
})
