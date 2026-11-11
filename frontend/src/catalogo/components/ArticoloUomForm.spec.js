// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: I CAMPI FERMI di una mappatura in modifica (BE21 di
//        brief-db-revisione-catalogo, 2026-11-11): unita', fattore e inizio si
//        spengono quando il backend li dichiara in `nonEditableFields`; la
//        fine resta aperta, perche' chiudere e' la strada.
// Note: ⚠️ Si monta il form VERO; si fingono API e parametri. Il dizionario
//       del montaggio di prova e' vuoto: il motivo esce col suo codice
//       (`labelOrCode`), e il test guarda quello. In creazione
//       niente e' fermo: i campi fermi lo sono solo per una riga scritta.
//
// Indice test:
//  1) in modifica: unita', fattore e inizio spenti, la fine no
//  2) in creazione: nessun campo spento da `nonEditableFields`
//  3) in modifica: il PATCH non porta i campi fermi (BB `senzaCampiFermi`)
//  4) in vigore (capability, BE21-b): interruttore spento col motivo, fuori dal
//     PATCH; la fine parte dalla prima data ammessa
//  5) gia' finita: la fine spenta col suo motivo, fuori dal PATCH
//  6) fail-closed: una riga senza capability non si spegne e non si chiude
// ------------------------------------------------------------
import { describe, it, expect, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import InputNumber from 'primevue/inputnumber'
import DatePicker from 'primevue/datepicker'
import ToggleSwitch from 'primevue/toggleswitch'
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
// Una mappatura in vigore, come la consegna la vista (capability del DB).
const RIGA = {
  id: 7, uom_id: 3, factor_to_base: '10', is_base: false, valido_dal: '2026-10-01',
  valido_al: null, attivo: true,
  puo_eliminarsi: false, motivo_non_eliminabile: 'UOM_STORIA_IN_VIGORE',
  puo_cambiare_attivo: false, puo_chiudersi: true,
  data_min_chiusura: '2026-11-10', data_default_chiusura: '2026-11-11', motivo_non_chiudibile: null,
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

// L'interruttore «attivo» e' l'ultimo del form (prima vendita, acquisto,
// logistica e frazioni).
function attivo(wrapper) {
  return wrapper.findAllComponents(ToggleSwitch).at(-1)
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

  it('4) in vigore: interruttore spento col motivo, fuori dal PATCH; fine dalla prima data', async () => {
    updateArticoloUom.mockReset()
    updateArticoloUom.mockResolvedValue({ data: { data: { ...RIGA } } })
    const wrapper = await montaForm(RIGA)
    expect(attivo(wrapper).props('disabled')).toBe(true)
    expect(wrapper.find('[data-testid="motivo-attivo"]').text()).toBe('UOM_STORIA_IN_VIGORE')
    const al = wrapper.findAllComponents(DatePicker)[1]
    expect(al.props('minDate').getDate()).toBe(10)
    wrapper.findComponent(FormFooter).vm.$emit('save')
    await flushPromises()
    const payload = updateArticoloUom.mock.calls[0][2]
    expect(Object.keys(payload)).not.toContain('attivo')
    expect(payload).toHaveProperty('valido_al', null)
  })

  it("5) gia' finita: la fine spenta col suo motivo, fuori dal PATCH", async () => {
    updateArticoloUom.mockReset()
    updateArticoloUom.mockResolvedValue({ data: { data: { ...RIGA } } })
    const chiusa = {
      ...RIGA, valido_al: '2026-10-31', puo_chiudersi: false,
      data_min_chiusura: null, data_default_chiusura: null, motivo_non_chiudibile: 'UOM_STORIA_CHIUSA',
    }
    const wrapper = await montaForm(chiusa)
    expect(date(wrapper).al).toBe(true)
    expect(wrapper.find('[data-testid="motivo-fine"]').text()).toBe('UOM_STORIA_CHIUSA')
    wrapper.findComponent(FormFooter).vm.$emit('save')
    await flushPromises()
    expect(Object.keys(updateArticoloUom.mock.calls[0][2])).not.toContain('valido_al')
  })

  it('6) fail-closed: una riga senza capability non si spegne e non si chiude', async () => {
    const { puo_cambiare_attivo: _a, puo_chiudersi: _c, ...senza } = RIGA
    const wrapper = await montaForm(senza)
    expect(attivo(wrapper).props('disabled')).toBe(true)
    expect(date(wrapper).al).toBe(true)
  })
})
