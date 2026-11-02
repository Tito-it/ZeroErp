// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa `ListinoDocumentoSelect` (F-2 di brief-db-offerta-emissione-ed-
//        erogazione): la tendina chiede i listini per utility ed emittente del
//        form, si ricarica quando cambiano, scarta la risposta vecchia, tiene
//        fra le opzioni il listino gia' scritto sul documento e azzera una
//        scelta che non e' piu' fra le opzioni.
// Note: sono difetti che non danno errore — la combo mostra semplicemente i
//       listini sbagliati, o un valore vuoto. Le risposte qui arrivano a mano.
// Indice test:
//   1) senza utility o emittente non chiede niente
//   2) chiede per (utility, emittente) e propone cio' che il DB risponde
//   3) al cambio d'emittente richiede; la risposta vecchia, arrivata dopo, si scarta
//   4) il listino gia' scritto resta fra le opzioni, senza doppioni
//   5) cambiata la utility, la scelta che il DB non propone piu' si azzera
//   6) su una risposta in errore la scelta resta (la lista vuota non e' un «no»)
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises } from '@vue/test-utils'

const chiamate = []
vi.mock('../api/lookup', () => ({
  lookupListiniSelezionabili: (utilityId, emittenteFiscaleId) => new Promise((r, rifiuta) => {
    chiamate.push({ utilityId, emittenteFiscaleId, rispondi: r, rifiuta })
  }),
}))

import ListinoDocumentoSelect from './ListinoDocumentoSelect.vue'
import { monta } from '../../../test/montaggio'

const risposta = (...listini) => ({ data: { data: { results: listini } } })
const L1 = { id: 1, codice: 'L1', descrizione: 'Listino uno' }
const L2 = { id: 2, codice: 'L2', descrizione: 'Listino due' }
const select = (w) => w.findComponent({ name: 'Select' })

describe('ListinoDocumentoSelect', () => {
  beforeEach(() => { chiamate.length = 0 })

  it('senza utility o emittente non chiede niente', async () => {
    const w = monta(ListinoDocumentoSelect, { modelValue: null, utilityId: 3, emittenteFiscaleId: null })
    await flushPromises()
    expect(chiamate).toHaveLength(0)
    expect(select(w).props('options')).toEqual([])
    expect(select(w).props('placeholder')).toBe('vendite.listini.selezionabili_utility_emittente_first')
  })

  it('chiede per (utility, emittente) e propone cio\' che il DB risponde', async () => {
    const w = monta(ListinoDocumentoSelect, { modelValue: null, utilityId: 3, emittenteFiscaleId: 41 })
    expect(chiamate.map((c) => [c.utilityId, c.emittenteFiscaleId])).toEqual([[3, 41]])
    chiamate[0].rispondi(risposta(L1))
    await flushPromises()
    expect(select(w).props('options')).toEqual([L1])
    expect(select(w).props('loading')).toBe(false)
  })

  it('al cambio d\'emittente richiede; la risposta vecchia, arrivata dopo, si scarta', async () => {
    const w = monta(ListinoDocumentoSelect, { modelValue: null, utilityId: 3, emittenteFiscaleId: 41 })
    await w.setProps({ emittenteFiscaleId: 42 })
    expect(chiamate.map((c) => c.emittenteFiscaleId)).toEqual([41, 42])

    chiamate[1].rispondi(risposta(L2))
    await flushPromises()
    chiamate[0].rispondi(risposta(L1))
    await flushPromises()

    expect(select(w).props('options')).toEqual([L2])
    expect(select(w).props('loading')).toBe(false)
  })

  it('il listino gia\' scritto resta fra le opzioni, senza doppioni', async () => {
    const record = { listino_id: 9, listino_codice: 'OLD', listino_descrizione: 'Vecchio' }
    const w = monta(ListinoDocumentoSelect, { modelValue: 9, utilityId: 3, emittenteFiscaleId: 41, record })
    chiamate[0].rispondi(risposta(L1))
    await flushPromises()
    expect(select(w).props('options')).toEqual([L1, { id: 9, codice: 'OLD', descrizione: 'Vecchio' }])
    // Il listino del documento e' fra le opzioni: la scelta non si tocca.
    expect(w.emitted('update:modelValue')).toBeUndefined()

    await w.setProps({ record: { listino_id: 1, listino_codice: 'L1', listino_descrizione: 'Listino uno' } })
    expect(select(w).props('options').map((l) => l.id)).toEqual([1])
  })

  it('cambiata la utility, la scelta che il DB non propone piu\' si azzera', async () => {
    const w = monta(ListinoDocumentoSelect, { modelValue: 1, utilityId: 3, emittenteFiscaleId: 41 })
    chiamate[0].rispondi(risposta(L1))
    await flushPromises()
    expect(w.emitted('update:modelValue')).toBeUndefined()

    await w.setProps({ utilityId: 4 })
    chiamate[1].rispondi(risposta(L2))
    await flushPromises()
    expect(w.emitted('update:modelValue')).toEqual([[null]])
  })

  it('su una risposta in errore la scelta resta', async () => {
    const w = monta(ListinoDocumentoSelect, { modelValue: 1, utilityId: 3, emittenteFiscaleId: 41 })
    chiamate[0].rifiuta(new Error('rete'))
    await flushPromises()
    expect(select(w).props('options')).toEqual([])
    expect(w.emitted('update:modelValue')).toBeUndefined()
  })
})
