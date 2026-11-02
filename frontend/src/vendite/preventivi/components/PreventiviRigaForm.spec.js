// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: in MODIFICA la riga di preventivo spedisce cio' che il form fa
//        modificare a video. Fino al 2026-10-20 la descrizione era editabile
//        ma l'edit non la mandava: la modifica si perdeva senza avviso (i
//        gemelli ordini e DDT la mandavano gia').
// Note: si monta il form vero; sono finti lo store (che raccoglie il payload),
//       le API del pricing, i limiti, la risoluzione IVA, le UoM e i
//       sotto-componenti (lookup articolo, select IVA, pannelli componenti).
//
// Indice test:
//   1) in modifica la descrizione cambiata arriva nel payload
//   2) in modifica una descrizione svuotata arriva come null (reset esplicito)
// ------------------------------------------------------------

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { flushPromises } from '@vue/test-utils'

const aggiornaRiga = vi.fn()
const addRiga = vi.fn()

vi.mock('../stores/preventivi', () => ({
  usePreventiviStore: () => ({ aggiornaRiga, addRiga }),
}))
vi.mock('../../composables/useLimitiPricing', () => ({
  useLimitiPricing: () => ({ limiti: ref({}), load: async () => {}, L2_ERROR_CODES: [] }),
}))
vi.mock('../api/preventiviApi', () => ({
  suggerisciPrezzoRiga: vi.fn().mockResolvedValue({ data: { data: {} } }),
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
const { default: PreventiviRigaForm } = await import('./PreventiviRigaForm.vue')

// Riga semplice (non composita): niente pannello componenti, prezzo inviato.
const RIGA = {
  id: 7, articolo_id: 'a1b2c3', articolo_codice: 'CALD', articolo_descrizione: 'Caldaia',
  descrizione: 'Caldaia', qta_operativa: '2',
  prezzo_unitario: '100', sconto_percentuale: '0', uom_operativa_id: 2,
  data_consegna_richiesta_cliente: null, meta: null,
}

const STUBS = {
  ArticoloLookup: true,
  IvaSelect: true,
  PreventiviRigaComponentiPanel: true,
  ComponentiCreateActionsPanel: true,
  ComponentiDialog: true,
  L2ErrorBanner: true,
}

async function salvaConDescrizione(descrizione) {
  const w = monta(PreventiviRigaForm, { preventivoId: 3, riga: RIGA }, { global: { stubs: STUBS } })
  await flushPromises()
  await w.findAllComponents({ name: 'InputText' })[0].setValue(descrizione)
  const salva = w.findAllComponents({ name: 'Button' }).find((b) => b.props('label') === 'common.save')
  await salva.trigger('click')
  await flushPromises()
  expect(aggiornaRiga).toHaveBeenCalledTimes(1)
  const [preventivoId, rigaId, payload] = aggiornaRiga.mock.calls[0]
  expect([preventivoId, rigaId]).toEqual([3, 7])
  return payload
}

describe('PreventiviRigaForm — il payload di modifica', () => {
  beforeEach(() => {
    aggiornaRiga.mockReset().mockResolvedValue({ ...RIGA })
    addRiga.mockReset()
  })

  it('in modifica la descrizione cambiata arriva nel payload', async () => {
    const payload = await salvaConDescrizione('Caldaia a condensazione')
    expect(payload.descrizione).toBe('Caldaia a condensazione')
  })

  it('in modifica una descrizione svuotata arriva come null (reset esplicito)', async () => {
    const payload = await salvaConDescrizione('')
    expect(payload).toHaveProperty('descrizione', null)
  })
})
