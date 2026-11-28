// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il guard di versione di `UtilityPerRuoloSelect` (2026-09-24):
//        al cambio di `tipoRuoloCodice` la risposta del ruolo VECCHIO, se
//        arriva per ultima, non sovrascrive le voci del ruolo nuovo. E (dal
//        2026-11-27, brief-db-utility-gestite-dall-emittente R-2) l'azienda
//        del documento arriva al lookup, e il suo cambio rilegge le voci.
// Note: e' un difetto che non da' errore — la combo mostra semplicemente le
//       utility sbagliate. Le risposte qui arrivano apposta in ordine inverso.
// ------------------------------------------------------------

import { describe, it, expect, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'

const inAttesa = {}
const rifiuta = {}
vi.mock('../apiCore', () => ({
  lookupUtilitiesPerEmittente: (ruolo, azienda = null) => new Promise((r, j) => {
    const chiave = azienda == null ? ruolo : `${ruolo}|${azienda}`
    inAttesa[chiave] = r
    rifiuta[chiave] = j
  }),
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

describe('UtilityPerRuoloSelect — l\'azienda del documento', () => {
  it('passa l\'azienda al lookup e al suo cambio rilegge le voci', async () => {
    const w = monta(UtilityPerRuoloSelect, { modelValue: null, tipoRuoloCodice: 'CL', emittenteFiscaleId: 5 })
    inAttesa['CL|5'](risposta(1, 'Energia elettrica'))
    await flushPromises()
    expect(w.findComponent({ name: 'Select' }).props('options')).toEqual([{ id: 1, descrizione: 'Energia elettrica' }])

    await w.setProps({ emittenteFiscaleId: 6 })
    inAttesa['CL|6'](risposta(2, 'Gas naturale'))
    await flushPromises()
    expect(w.findComponent({ name: 'Select' }).props('options')).toEqual([{ id: 2, descrizione: 'Gas naturale' }])
  })
})

// D-BE-2 (2026-11-28): al cambio d'azienda fatto dall'utente il valore che la
// nuova azienda non gestisce si ritira; il valore di un documento che si apre
// (azienda e utility insieme) no.
describe('UtilityPerRuoloSelect — il valore che la nuova azienda non gestisce', () => {
  async function montaSuAzienda5(extra = {}) {
    const w = monta(UtilityPerRuoloSelect, {
      modelValue: 1, tipoRuoloCodice: 'CL', emittenteFiscaleId: 5, ...extra,
    })
    inAttesa['CL|5'](risposta(1, 'Energia elettrica'))
    await flushPromises()
    return w
  }

  it("il cambio d'azienda dell'utente lo ritira", async () => {
    const w = await montaSuAzienda5()
    await w.setProps({ emittenteFiscaleId: 6 })
    inAttesa['CL|6'](risposta(2, 'Gas naturale'))
    await flushPromises()
    expect(w.emitted('update:modelValue')).toEqual([[null]])
    expect(w.emitted('change')).toEqual([[null]])
  })

  it("lo tiene se la nuova azienda lo gestisce", async () => {
    const w = await montaSuAzienda5()
    await w.setProps({ emittenteFiscaleId: 6 })
    inAttesa['CL|6'](risposta(1, 'Energia elettrica'))
    await flushPromises()
    expect(w.emitted('update:modelValue')).toBeUndefined()
  })

  it("non tocca il valore di un documento che arriva insieme alla sua azienda", async () => {
    const w = await montaSuAzienda5()
    await w.setProps({ emittenteFiscaleId: 6, modelValue: 3 })
    inAttesa['CL|6'](risposta(2, 'Gas naturale'))
    await flushPromises()
    expect(w.emitted('update:modelValue')).toBeUndefined()
  })

  it('non tocca un campo disabilitato', async () => {
    const w = await montaSuAzienda5({ disabled: true })
    await w.setProps({ emittenteFiscaleId: 6 })
    inAttesa['CL|6'](risposta(2, 'Gas naturale'))
    await flushPromises()
    expect(w.emitted('update:modelValue')).toBeUndefined()
  })

  it('non tocca il valore dopo una lettura fallita', async () => {
    const w = await montaSuAzienda5()
    await w.setProps({ emittenteFiscaleId: 6 })
    rifiuta['CL|6'](new Error('rete'))
    await flushPromises()
    expect(w.emitted('update:modelValue')).toBeUndefined()
  })
})
