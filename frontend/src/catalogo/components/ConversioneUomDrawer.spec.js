// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: I CAMPI FERMI di una conversione in modifica (BE21 di
//        brief-db-revisione-catalogo, 2026-11-11): unita', fattore e inizio si
//        spengono quando il dettaglio li dichiara in `non_editable_fields`, e il
//        Salva NON li rimanda. Il fattore e' numeric(18,6): tenuto come Number
//        nel form, oltre ~15 cifre significative tornerebbe diverso, e il
//        guard della storia rifiuterebbe una semplice chiusura.
// Note: si monta il drawer vero; finti solo i contorni — lo store (dettaglio e
//       update), il lookup delle unita', il guscio `AppDrawer` (rende il corpo
//       e un Salva che emette `save`), `LookupSelect`.
//
// Indice test:
//   1) in modifica: fattore e inizio spenti, la fine no
//   2) in modifica: il PATCH porta solo i campi aperti, mai i fermi
// ------------------------------------------------------------

import { describe, expect, it, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'
import { flushPromises } from '@vue/test-utils'
import InputNumber from 'primevue/inputnumber'
import DatePicker from 'primevue/datepicker'

const fetchDetail = vi.fn()
const update = vi.fn()

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {}, fullPath: '/catalogo/conversioni' }),
}))
vi.mock('../stores/conversioniUom', () => ({
  useConversioniUomStore: () => ({ fetchDetail, update, create: vi.fn() }),
}))
vi.mock('../../core/composables/useLookupCodici', async (importOriginal) => ({
  ...(await importOriginal()),
  useLookupCodici: () => ({ items: ref([]) }),
}))

const { monta } = await import('../../../test/montaggio')
const { default: ConversioneUomDrawer } = await import('./ConversioneUomDrawer.vue')

const AppDrawerFinto = defineComponent({
  name: 'AppDrawerFinto',
  emits: ['save', 'update:visible', 'cancel'],
  setup(_, { slots, emit }) {
    return () => h('div', [
      slots.default?.(),
      h('button', { class: 'salva-finto', onClick: () => emit('save') }, 'salva'),
    ])
  },
})
const Vuoto = defineComponent({ render: () => null })

const FERMI = ['fattore', 'uom_from_id', 'uom_to_id', 'valido_dal']
const DETTAGLIO = {
  id: 7, uom_from_id: 3, uom_to_id: 4, fattore: '1234567890.123457',
  valido_dal: '2026-01-01', valido_al: null, attivo: true, non_editable_fields: FERMI,
}

async function apri() {
  fetchDetail.mockResolvedValue({ ...DETTAGLIO })
  update.mockResolvedValue({ data: { data: { ...DETTAGLIO } } })
  const w = monta(ConversioneUomDrawer, { visible: false, mode: 'edit', convId: 7 }, {
    global: { stubs: { AppDrawer: AppDrawerFinto, LookupSelect: Vuoto } },
  })
  await w.setProps({ visible: true })
  await flushPromises()
  return w
}

describe('ConversioneUomDrawer', () => {
  it('1) in modifica: fattore e inizio spenti, la fine no', async () => {
    const w = await apri()
    expect(w.findComponent(InputNumber).props('disabled')).toBe(true)
    const [dal, al] = w.findAllComponents(DatePicker)
    expect({ dal: dal.props('disabled'), al: al.props('disabled') }).toEqual({ dal: true, al: false })
  })

  it('2) in modifica: il PATCH porta solo i campi aperti, mai i fermi', async () => {
    const w = await apri()
    await w.find('.salva-finto').trigger('click')
    await flushPromises()
    expect(update).toHaveBeenCalledTimes(1)
    const [id, payload] = update.mock.calls[0]
    expect(id).toBe(7)
    expect(Object.keys(payload).sort()).toEqual(['attivo', 'valido_al'])
  })
})
