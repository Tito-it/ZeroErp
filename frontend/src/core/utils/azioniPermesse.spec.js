// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: `azioniPermesse` / `passaggioPermesso` — i passaggi della riga,
//        fail-closed sul campo assente.
//
// Indice test:
//  1) campo presente: le action_key della riga
//  2) campo assente, null o non array: nessun passaggio (fail-closed)
//  3) passaggioPermesso: vero solo per una chiave della riga
// ------------------------------------------------------------
import { describe, expect, it } from 'vitest'
import { azioniPermesse, passaggioPermesso } from './azioniPermesse'

describe('azioniPermesse', () => {
  it('campo presente: le action_key della riga', () => {
    expect(azioniPermesse({ azioni_permesse: ['attiva', 'annulla'] })).toEqual(['attiva', 'annulla'])
  })

  it('campo assente, null o non array: nessun passaggio', () => {
    expect(azioniPermesse({})).toEqual([])
    expect(azioniPermesse(null)).toEqual([])
    expect(azioniPermesse({ azioni_permesse: null })).toEqual([])
    expect(azioniPermesse({ azioni_permesse: 'attiva' })).toEqual([])
  })
})

describe('passaggioPermesso', () => {
  it('vero solo per una chiave della riga', () => {
    const riga = { azioni_permesse: ['attiva'] }
    expect(passaggioPermesso(riga, 'attiva')).toBe(true)
    expect(passaggioPermesso(riga, 'annulla')).toBe(false)
    expect(passaggioPermesso({}, 'attiva')).toBe(false)
    // ⚠️ Una stringa non e' un elenco: 'attiva_listino'.includes('attiva')
    //    sarebbe vero, e fail-closed vuol dire falso.
    expect(passaggioPermesso({ azioni_permesse: 'attiva_listino' }, 'attiva')).toBe(false)
  })
})
