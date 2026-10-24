// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il dialog della data RESTA APERTO FINO ALL'ESITO (2026-10-21, ok Tid):
//        si chiude solo se `azione` risponde `true`, resta aperto (e
//        riprovabile) sul `false`, e un secondo clic mentre il primo e' in volo
//        non parte. E' il confine del GESTO di `useChiaveGesto`: un reinvio
//        dopo un timeout avviene qui dentro, con la stessa key.
// Note: si monta il dialog VERO in modo `creazione` (non legge la finestra di
//       numerazione); si finge la cornice `AppDialog`.
//
// Indice test:
//  1) `true` chiude il dialog
//  2) `false` lo lascia aperto, e si puo' riprovare
//  3) un secondo clic in volo non chiama di nuovo l'azione
// ------------------------------------------------------------
import { describe, it, expect, vi } from 'vitest'
import { defineComponent } from 'vue'
import { flushPromises } from '@vue/test-utils'

import NumerazioneDataDialog from './NumerazioneDataDialog.vue'
import { monta } from '../../../test/montaggio'
import { MODO_DATA_DOCUMENTO } from '../constants'

vi.mock('../api/lotti', () => ({ getFinestraNumerazione: vi.fn() }))

const CorniceFinta = defineComponent({
  name: 'AppDialog',
  props: { loading: { type: Boolean, default: false } },
  emits: ['save', 'update:visible'],
  template: '<div><slot /></div>',
})

function montaDialog(azione) {
  return monta(
    NumerazioneDataDialog,
    { visible: true, modo: MODO_DATA_DOCUMENTO.CREAZIONE, competenzaMese: '2026-10-01', azione },
    { global: { stubs: { AppDialog: CorniceFinta } } },
  )
}

describe('NumerazioneDataDialog — aperto fino all\'esito', () => {
  it('`true` chiude il dialog', async () => {
    const azione = vi.fn().mockResolvedValue(true)
    const wrapper = montaDialog(azione)
    wrapper.findComponent(CorniceFinta).vm.$emit('save')
    await flushPromises()
    expect(azione).toHaveBeenCalledWith(null)
    expect(wrapper.emitted('update:visible')).toEqual([[false]])
  })

  it('`false` lo lascia aperto, e si puo\' riprovare', async () => {
    const azione = vi.fn().mockResolvedValueOnce(false).mockResolvedValueOnce(true)
    const wrapper = montaDialog(azione)
    const cornice = wrapper.findComponent(CorniceFinta)
    cornice.vm.$emit('save')
    await flushPromises()
    expect(wrapper.emitted('update:visible')).toBeUndefined()
    cornice.vm.$emit('save')
    await flushPromises()
    expect(azione).toHaveBeenCalledTimes(2)
    expect(wrapper.emitted('update:visible')).toEqual([[false]])
  })

  it('un secondo clic in volo non chiama di nuovo l\'azione', async () => {
    let risolvi
    const azione = vi.fn(() => new Promise((r) => { risolvi = r }))
    const wrapper = montaDialog(azione)
    const cornice = wrapper.findComponent(CorniceFinta)
    cornice.vm.$emit('save')
    await flushPromises()
    expect(cornice.props('loading')).toBe(true)
    cornice.vm.$emit('save')
    await flushPromises()
    expect(azione).toHaveBeenCalledTimes(1)
    risolvi(true)
    await flushPromises()
    expect(cornice.props('loading')).toBe(false)
  })
})
