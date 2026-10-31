// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: i due campi del canone della testata (BB `campiCanone`).
//
// Indice test:
//   1) vuoti: i due campi a null (decide il default del DB)
//   2) dal dettaglio: i valori salvati; senza, null
//   3) verso il backend: solo i valorizzati, mai `null` (NOT NULL col default)
//   4) le opzioni: i due codici del CHECK e i dodici mesi 1-12
// ------------------------------------------------------------
import { describe, it, expect } from 'vitest'
import { GENERAZIONE_CANONE } from '../../constants'
import {
  campiCanoneDaDettaglio, campiCanoneDaForm, campiCanoneVuoti,
  opzioniGenerazioneCanone, opzioniMesePartenza,
} from './campiCanone'

describe('campiCanone', () => {
  it('1) vuoti', () => {
    expect(campiCanoneVuoti()).toEqual({ generazione_canone: null, mese_partenza_canone: null })
  })

  it('2) dal dettaglio', () => {
    expect(campiCanoneDaDettaglio({ generazione_canone: 'FINE_PERIODO', mese_partenza_canone: 2 }))
      .toEqual({ generazione_canone: 'FINE_PERIODO', mese_partenza_canone: 2 })
    expect(campiCanoneDaDettaglio({})).toEqual(campiCanoneVuoti())
    expect(campiCanoneDaDettaglio(null)).toEqual(campiCanoneVuoti())
  })

  it('3) verso il backend: solo i valorizzati', () => {
    expect(campiCanoneDaForm(campiCanoneVuoti())).toEqual({})
    expect(campiCanoneDaForm({ generazione_canone: 'FINE_PERIODO', mese_partenza_canone: null }))
      .toEqual({ generazione_canone: 'FINE_PERIODO' })
    expect(campiCanoneDaForm({ generazione_canone: null, mese_partenza_canone: 7 }))
      .toEqual({ mese_partenza_canone: 7 })
  })

  it('4) le opzioni', () => {
    const t = (k) => k
    expect(opzioniGenerazioneCanone(t).map((o) => o.value))
      .toEqual([GENERAZIONE_CANONE.INIZIO_PERIODO, GENERAZIONE_CANONE.FINE_PERIODO])
    const mesi = opzioniMesePartenza('it')
    expect(mesi.map((o) => o.value)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
    expect(mesi[1].label.toLowerCase()).toContain('febbraio')
  })
})
