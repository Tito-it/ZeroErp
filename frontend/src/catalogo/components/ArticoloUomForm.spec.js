// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: I CAMPI FERMI di una mappatura in modifica (BE21 di
//        brief-db-revisione-catalogo, 2026-11-11): unita', fattore e inizio si
//        spengono quando il backend li dichiara in `nonEditableFields`; la
//        fine resta aperta, perche' chiudere e' la strada.
// Note: ⚠️ Si monta il form VERO; si fingono API e parametri. In creazione
//       niente e' fermo: i campi fermi lo sono solo per una riga scritta.
//
// Indice test:
//  1) in modifica: unita', fattore e inizio spenti, la fine no
//  2) in creazione: nessun campo spento da `nonEditableFields`
//  3) in modifica: il PATCH non porta i campi fermi (BB `senzaCampiFermi`)
// ------------------------------------------------------------
import { describe, it, expect, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import InputNumber from 'primevue/inputnumber'
import DatePicker from 'primevue/datepicker'
import FormFooter from '../../core/components/FormFooter.vue'

import ArticoloUomForm from './ArticoloUomForm.vue'
import { monta } from '../../../test/montaggio'

const updateArticoloUom = vi.fn()
vi.mock('../api/catalogo', () => ({
  createArticoloUom: vi.fn(),
  updateArticoloUom: (...a) => updateArticoloUom(...a),
}))
vi.mock('../../core/composables/useParameterDefaults', async () => {
  const { ref } = await import('vue')
  return { useParameterDefaults: () => ({ defaults: ref({}), load: async () => {} }) }
})

const FERMI = ['factor_to_base', 'uom_id', 'valido_dal']
const RIGA = {
  id: 7, uom_id: 3, factor_to_base: '10', is_base: false, valido_dal: '2026-10-01',
  valido_al: null, attivo: true,
}

async function montaForm(riga) {
  const wrapper = monta(
    ArticoloUomForm,
    { riga, articoloId: 'art-1', nonEditableFields: FERMI },
    { global: { stubs: { LookupSelect: { name: 'LookupSelect', props: ['disabled'], template: '<div />' } } } },
  )
  await flushPromises()
  return wrapper
}

function date(wrapper) {
  const [dal, al] = wrapper.findAllComponents(DatePicker)
  return { dal: dal.props('disabled'), al: al.props('disabled') }
}

describe('ArticoloUomForm', () => {
  it("1) in modifica: unita', fattore e inizio spenti, la fine no", async () => {
    const wrapper = await montaForm(RIGA)
    expect(wrapper.findComponent({ name: 'LookupSelect' }).props('disabled')).toBe(true)
    expect(wrapper.findComponent(InputNumber).props('disabled')).toBe(true)
    expect(date(wrapper)).toEqual({ dal: true, al: false })
  })

  it('2) in creazione: nessun campo spento da `nonEditableFields`', async () => {
    const wrapper = await montaForm(null)
    expect(wrapper.findComponent({ name: 'LookupSelect' }).props('disabled')).toBe(false)
    expect(wrapper.findComponent(InputNumber).props('disabled')).toBe(false)
    expect(date(wrapper)).toEqual({ dal: false, al: false })
  })

  it('3) in modifica: il PATCH non porta i campi fermi', async () => {
    updateArticoloUom.mockResolvedValue({ data: { data: { ...RIGA } } })
    const wrapper = await montaForm(RIGA)
    wrapper.findComponent(FormFooter).vm.$emit('save')
    await flushPromises()
    expect(updateArticoloUom).toHaveBeenCalledTimes(1)
    const [articolo, id, payload] = updateArticoloUom.mock.calls[0]
    expect([articolo, id]).toEqual(['art-1', 7])
    expect(Object.keys(payload)).not.toContain('factor_to_base')
    expect(Object.keys(payload)).not.toContain('valido_dal')
    expect(payload).toHaveProperty('valido_al', null)
  })
})
