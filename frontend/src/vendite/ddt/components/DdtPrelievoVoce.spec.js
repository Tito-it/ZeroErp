// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa `DdtPrelievoVoce` (Lotto 3 R-2b, piano-be-fe-magazzino-lotto-3
//        B1): i campi del prelievo compaiono SOLO se servono (dai flag che il
//        backend porta), una voce automatica non chiede niente, il prelievo
//        porta la voce giusta (il componente del kit) e la quantita' proposta
//        e' il residuo.
// Note: difetti che non danno errore — un campo lotto che manca lascia
//       l'operatore davanti al motivo «prelievi incompleti» senza un modo di
//       correggerlo; un campo in piu' chiede una scelta che il DB rifiuta.
// Indice test:
//   1) articolo a lotti, magazzino senza scaffali: quantita' e lotto, nient'altro
//   2) seriale: niente quantita' (un pezzo), il seriale dal magazzino della bolla
//   3) voce automatica: nessun form, il tag lo dice
//   4) «Aggiungi» manda la voce del kit, il residuo e il lotto scelto
//   5) non modificabile (fuori bozza o sola lettura): nessun form, nessun cestino
//   6) prelevato OLTRE la riga: non «da completare», niente form di aggiunta
//   7) scaffale di arrivo non modificabile: si legge accanto alla posizione, niente tendina vuota
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises } from '@vue/test-utils'

const chiamate = { lotti: [], assets: [], ubicazioni: [], crea: [] }
const vuoto = () => Promise.resolve({ data: { data: { results: [] } } })
vi.mock('../../../magazzino/api/magazzino', () => ({
  lookupLotti: (...a) => { chiamate.lotti.push(a); return vuoto() },
  lookupAssets: (...a) => { chiamate.assets.push(a); return vuoto() },
  lookupUbicazioni: (...a) => { chiamate.ubicazioni.push(a); return vuoto() },
}))
vi.mock('../api/ddtApi', () => ({
  createPrelievo: (...a) => { chiamate.crea.push(a); return Promise.resolve({ data: { data: { prelievo_id: 1 } } }) },
  deletePrelievo: () => Promise.resolve({ data: { data: {} } }),
  updatePrelievo: () => Promise.resolve({ data: { data: {} } }),
}))

import DdtPrelievoVoce from './DdtPrelievoVoce.vue'
import { monta } from '../../../../test/montaggio'

const TESTATA = {
  magazzino_id: 5, magazzino_usa_ubicazioni: false,
  magazzino_arrivo_id: null, magazzino_arrivo_usa_ubicazioni: null,
}
const voce = (extra = {}) => ({
  ddt_riga_id: 70, ddt_riga_componente_id: null, riga_nr: 1,
  articolo_id: 'a-1', articolo_codice: 'ART', articolo_descrizione: 'Articolo',
  requires_lotto: false, requires_serial: false, uom_codice: 'PZ',
  qta: '4', prelevata: '1', automatico: false, prelievi: [],
  ...extra,
})
const placeholders = (w) => w.findAllComponents({ name: 'Select' }).map((s) => s.props('placeholder'))

describe('DdtPrelievoVoce', () => {
  beforeEach(() => { Object.values(chiamate).forEach((l) => { l.length = 0 }) })

  it('articolo a lotti, magazzino senza scaffali: quantita\' e lotto, nient\'altro', async () => {
    const w = monta(DdtPrelievoVoce, { ddtId: 9, voce: voce({ requires_lotto: true }), testata: TESTATA, modificabile: true })
    await flushPromises()
    expect(w.findComponent({ name: 'InputNumber' }).exists()).toBe(true)
    expect(placeholders(w)).toEqual(['vendite.ddt.prelievi.campo_lotto'])
    expect(chiamate.lotti).toEqual([['a-1']])
    expect(chiamate.assets).toEqual([])
    expect(chiamate.ubicazioni).toEqual([])
  })

  it('seriale: niente quantita\' (un pezzo), il seriale dal magazzino della bolla', async () => {
    const w = monta(DdtPrelievoVoce, {
      ddtId: 9, voce: voce({ requires_serial: true }),
      testata: { ...TESTATA, magazzino_usa_ubicazioni: true }, modificabile: true,
    })
    await flushPromises()
    expect(w.findComponent({ name: 'InputNumber' }).exists()).toBe(false)
    expect(placeholders(w)).toEqual(['vendite.ddt.prelievi.campo_seriale', 'vendite.ddt.prelievi.campo_ubicazione'])
    expect(chiamate.assets).toEqual([['a-1', 5]])
    expect(chiamate.ubicazioni).toEqual([[5]])
  })

  it('voce automatica: nessun form, il tag lo dice', async () => {
    const w = monta(DdtPrelievoVoce, { ddtId: 9, voce: voce({ automatico: true, prelevata: '0' }), testata: TESTATA, modificabile: true })
    await flushPromises()
    expect(w.findComponent({ name: 'InputNumber' }).exists()).toBe(false)
    expect(w.findComponent({ name: 'Tag' }).props('value')).toBe('vendite.ddt.prelievi.automatico')
  })

  it('«Aggiungi» manda la voce del kit, il residuo e il lotto scelto', async () => {
    const w = monta(DdtPrelievoVoce, {
      ddtId: 9, voce: voce({ requires_lotto: true, ddt_riga_componente_id: 33 }),
      testata: TESTATA, modificabile: true,
    })
    await flushPromises()
    await w.findComponent({ name: 'Select' }).vm.$emit('update:modelValue', 12)
    const aggiungi = w.findAllComponents({ name: 'Button' }).find((b) => b.props('label') === 'vendite.ddt.prelievi.aggiungi')
    await aggiungi.trigger('click')
    await flushPromises()
    expect(chiamate.crea).toEqual([[9, 70, {
      qta: 3, ddt_riga_componente_id: 33, lotto_id: 12, asset_id: null,
      ubicazione_id: null, ubicazione_arrivo_id: null,
    }]])
    expect(w.emitted('changed')).toHaveLength(1)
  })

  it('non modificabile (fuori bozza o sola lettura): nessun form, nessun cestino', async () => {
    const w = monta(DdtPrelievoVoce, {
      ddtId: 9, voce: voce({ requires_lotto: true, prelievi: [{ id: 1, qta: '1', lotto_codice: 'L1' }] }),
      testata: TESTATA, modificabile: false,
    })
    await flushPromises()
    expect(w.findComponent({ name: 'InputNumber' }).exists()).toBe(false)
    expect(w.findAllComponents({ name: 'Button' })).toHaveLength(0)
    expect(chiamate.lotti).toEqual([])
  })

  it('prelevato OLTRE la riga: non «da completare», niente form di aggiunta', async () => {
    const w = monta(DdtPrelievoVoce, { ddtId: 9, voce: voce({ prelevata: '5' }), testata: TESTATA, modificabile: true })
    await flushPromises()
    expect(w.findComponent({ name: 'Tag' }).props('value')).toBe('vendite.ddt.prelievi.oltre')
    expect(w.findComponent({ name: 'InputNumber' }).exists()).toBe(false)
  })

  it('scaffale di arrivo non modificabile: si legge accanto alla posizione, niente tendina vuota', async () => {
    const w = monta(DdtPrelievoVoce, {
      ddtId: 9,
      voce: voce({ prelevata: '4', prelievi: [{ id: 1, qta: '4', ubicazione_arrivo_id: 8, ubicazione_arrivo_codice: 'A-01' }] }),
      testata: { ...TESTATA, magazzino_arrivo_id: 6, magazzino_arrivo_usa_ubicazioni: true },
      modificabile: false, arrivoModificabile: false,
    })
    await flushPromises()
    expect(w.findAllComponents({ name: 'Select' })).toHaveLength(0)
    expect(w.text()).toContain('vendite.ddt.prelievi.campo_ubicazione_arrivo A-01')
  })
})
