// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: le DATE DI CONSEGNA della riga d'ordine e l'ONERE
//        (brief-db-addebito-trasporto-ordine K-3 e §9.9): un onere non si
//        spedisce, e il form non le mostra. In modifica lo dice la riga
//        (`e_onere` della vista di riga), in creazione l'articolo scelto nel
//        picker (`e_onere` di `vw_articoli_dettaglio`, 20261103-53).
// Note: si monta il form vero; sono finti lo store, le API delle componenti,
//       la risoluzione IVA, le UoM e i sotto-componenti (lookup articolo,
//       select IVA, pannelli componenti).
//
// Indice test:
//   1) in modifica, una riga-onere non mostra le date; una riga di merce si'
//   2) in creazione, scelto un articolo-onere le date spariscono
//   3) in creazione, passando da una merce con le date scritte a un onere, le
//      date si svuotano (nascoste ma piene partirebbero al salvataggio)
// ------------------------------------------------------------

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { flushPromises } from '@vue/test-utils'

const aggiornaRiga = vi.fn()
const addRiga = vi.fn()

vi.mock('../stores/ordini', () => ({
  useOrdiniStore: () => ({ aggiornaRiga, addRiga }),
}))
vi.mock('../api/ordiniApi', () => ({
  previewRigaComponenti: vi.fn().mockResolvedValue({ data: { data: {} } }),
}))
vi.mock('../../_shared/righe/useIvaRisolta', () => ({
  useIvaRisolta: () => ({
    ivaOrigine: ref(null), origineLabel: ref(''), risolviPer: async () => {}, reset: () => {},
  }),
}))
vi.mock('../../../catalogo/composables/useArticoloUomOptions', () => ({
  useArticoloUomOptions: () => ({
    uomOptions: ref([]), uomLoading: ref(false),
    loadUomPerArticolo: async () => [], pickBaseUomId: () => null, resetUomOptions: () => {},
  }),
}))

const { monta } = await import('../../../../test/montaggio')
const { default: OrdiniRigaForm } = await import('./OrdiniRigaForm.vue')

const RIGA = {
  id: 7, articolo_id: 'a1b2c3', articolo_codice: 'CALD', articolo_descrizione: 'Caldaia',
  descrizione: 'Caldaia', qta_operativa: '1',
  prezzo_unitario: '100', sconto_percentuale: '0', uom_operativa_id: 2,
  data_consegna_richiesta_cliente: null, data_consegna_confermata: null, meta: null,
}
const MERCE = { id: 'm1', codice: 'CALD', descrizione: 'Caldaia', is_composito: false, e_onere: false }
const ONERE = {
  id: 'o1', codice: 'ONERE_TRASPORTO', descrizione: 'Trasporto', is_composito: false,
  e_onere: true, causale_onere_id: 6,
}

const STUBS = {
  ArticoloLookup: true,
  IvaSelect: true,
  OrdiniRigaComponentiPanel: true,
  ComponentiCreateActionsPanel: true,
  ComponentiDialog: true,
}

async function apri(riga = null) {
  const w = monta(OrdiniRigaForm, { ordineId: 3, riga }, { global: { stubs: STUBS } })
  await flushPromises()
  return w
}

async function scegli(w, articolo) {
  w.findComponent({ name: 'ArticoloLookup' }).vm.$emit('select', articolo)
  await flushPromises()
}

const date = (w) => w.findAllComponents({ name: 'DatePicker' })

describe('OrdiniRigaForm — l\'onere non porta date di consegna', () => {
  beforeEach(() => {
    aggiornaRiga.mockReset()
    addRiga.mockReset()
  })

  it('1) in modifica lo dice la riga', async () => {
    expect(date(await apri({ ...RIGA, e_onere: true }))).toHaveLength(0)
    expect(date(await apri({ ...RIGA, e_onere: false }))).toHaveLength(2)
  })

  it('2) in creazione lo dice l\'articolo scelto', async () => {
    const w = await apri()
    await scegli(w, MERCE)
    expect(date(w)).toHaveLength(2)
    await scegli(w, ONERE)
    expect(date(w)).toHaveLength(0)
  })

  it('3) passando a un onere le date gia\' scritte si svuotano', async () => {
    const w = await apri()
    await scegli(w, MERCE)
    const giorno = new Date(2026, 10, 20)
    for (const d of date(w)) d.vm.$emit('update:modelValue', giorno)
    await flushPromises()
    expect(date(w)[0].props('modelValue')).toEqual(giorno)
    await scegli(w, ONERE)
    // Ritornando a una merce i campi ricompaiono: devono essere vuoti.
    await scegli(w, MERCE)
    expect(date(w).map((d) => d.props('modelValue'))).toEqual([null, null])
  })
})
