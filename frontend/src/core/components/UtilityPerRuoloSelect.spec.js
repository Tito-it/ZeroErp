// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il guard di versione di `UtilityPerRuoloSelect` (2026-09-24):
//        al cambio di `tipoRuoloCodice` la risposta del ruolo VECCHIO, se
//        arriva per ultima, non sovrascrive le voci del ruolo nuovo.
// Note: e' un difetto che non da' errore — la combo mostra semplicemente le
//       utility sbagliate. Le risposte qui arrivano apposta in ordine inverso.
// ------------------------------------------------------------

import { describe, it, expect, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'

const inAttesa = {}
vi.mock('../apiCore', () => ({
  lookupUtilitiesPerEmittente: (ruolo) => new Promise(r => { inAttesa[ruolo] = r }),
}))

import UtilityPerRuoloSelect from './UtilityPerRuoloSelect.vue'
import { monta } from '../../../test/montaggio'

const risposta = (id, descrizione) => ({ data: { data: { results: [{ id, descrizione }] } } })

describe('UtilityPerRuoloSelect — risposta vecchia', () => {
  it('la risposta del ruolo precedente, arrivata dopo, viene scartata', async () => {
    const w = monta(UtilityPerRuoloSelect, { modelValue: 2, tipoRuoloCodice: 'CL' })
    await w.setProps({ tipoRuoloCodice: 'FO' })

    inAttesa.FO(risposta(2, 'Gas naturale'))
    await flushPromises()
    inAttesa.CL(risposta(1, 'Energia elettrica'))
    await flushPromises()

    expect(w.element.getAttribute('title')).toBe('Gas naturale')
    expect(w.findComponent({ name: 'Select' }).props('options')).toEqual([{ id: 2, descrizione: 'Gas naturale' }])
    expect(w.findComponent({ name: 'Select' }).props('loading')).toBe(false)
  })
})
