// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa `ResoRientroVoce` (3-bis R-1b, piano-be-fe-magazzino-lotto-3
//        B2): il rientro si fa da un PRELIEVO d'origine (con uno solo la scelta
//        e' gia' fatta), lo scaffale si chiede solo se il magazzino di rientro
//        usa le ubicazioni, la quantita' proposta e' quella che manca, e fuori
//        bozza non si scrive niente.
// Indice test:
//   1) un solo prelievo d'origine: gia' scelto; magazzino senza scaffali: nessuno scaffale
//   2) magazzino con scaffali: lo scaffale si chiede e si legge dal magazzino del reso
//   3) «Aggiungi» manda prelievo, residuo e scaffale alla riga del reso
//   4) non modificabile: nessun form, nessun cestino
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises } from '@vue/test-utils'

const chiamate = { ubicazioni: [], crea: [] }
vi.mock('../../../magazzino/api/magazzino', () => ({
  lookupUbicazioni: (...a) => { chiamate.ubicazioni.push(a); return Promise.resolve({ data: { data: { results: [] } } }) },
}))
vi.mock('../api/resiApi', () => ({
  createRientro: (...a) => { chiamate.crea.push(a); return Promise.resolve({ data: { data: { rientro_id: 1 } } }) },
  deleteRientro: () => Promise.resolve({ data: { data: {} } }),
}))

import ResoRientroVoce from './ResoRientroVoce.vue'
import { monta } from '../../../../test/montaggio'

const ORIGINE = { id: 501, ddt_riga_componente_id: null, qta: '4', lotto_codice: 'LB', asset_seriale: null, ubicazione_codice: null }
const voce = (extra = {}) => ({
  resi_riga_id: 80, ddt_riga_componente_id: null, riga_nr: 1,
  articolo_codice: 'ART', articolo_descrizione: 'Articolo', uom_codice: 'PZ',
  qta: '2', rientrata: '0', automatico: false,
  prelievi_origine: [ORIGINE], rientri: [],
  ...extra,
})
const TESTATA = { magazzino_id: 5, magazzino_usa_ubicazioni: false }
const selects = (w) => w.findAllComponents({ name: 'Select' })

describe('ResoRientroVoce', () => {
  beforeEach(() => { chiamate.ubicazioni.length = 0; chiamate.crea.length = 0 })

  it('un solo prelievo d\'origine: gia\' scelto; magazzino senza scaffali: nessuno scaffale', async () => {
    const w = monta(ResoRientroVoce, { resoId: 9, voce: voce(), testata: TESTATA, modificabile: true })
    await flushPromises()
    expect(selects(w)).toHaveLength(1)
    expect(selects(w)[0].props('modelValue')).toBe(501)
    expect(chiamate.ubicazioni).toEqual([])
  })

  it('magazzino con scaffali: lo scaffale si chiede e si legge dal magazzino del reso', async () => {
    const w = monta(ResoRientroVoce, {
      resoId: 9, voce: voce(), testata: { ...TESTATA, magazzino_usa_ubicazioni: true }, modificabile: true,
    })
    await flushPromises()
    expect(selects(w).map((s) => s.props('placeholder'))).toEqual([
      'vendite.resi.rientri.campo_origine', 'vendite.resi.rientri.campo_ubicazione',
    ])
    expect(chiamate.ubicazioni).toEqual([[5]])
  })

  it('«Aggiungi» manda prelievo, residuo e scaffale alla riga del reso', async () => {
    const w = monta(ResoRientroVoce, { resoId: 9, voce: voce({ rientrata: '0.5' }), testata: TESTATA, modificabile: true })
    await flushPromises()
    const aggiungi = w.findAllComponents({ name: 'Button' }).find((b) => b.props('label') === 'vendite.resi.rientri.aggiungi')
    await aggiungi.trigger('click')
    await flushPromises()
    expect(chiamate.crea).toEqual([[9, 80, { ddt_riga_prelievo_id: 501, qta: 1.5, ubicazione_id: null }]])
    expect(w.emitted('changed')).toHaveLength(1)
  })

  it('non modificabile: nessun form, nessun cestino', async () => {
    const w = monta(ResoRientroVoce, {
      resoId: 9, voce: voce({ rientri: [{ id: 3, qta: '2', lotto_codice: 'LB' }], rientrata: '2' }),
      testata: TESTATA, modificabile: false,
    })
    await flushPromises()
    expect(selects(w)).toHaveLength(0)
    expect(w.findAllComponents({ name: 'Button' })).toHaveLength(0)
  })
})
