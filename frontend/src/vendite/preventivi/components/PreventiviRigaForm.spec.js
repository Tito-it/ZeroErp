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
//   3) «Usa prezzo listino»: il prezzo viaggia con la sua provenienza (K-6)
//   4) un prezzo cambiato dall'operatore non dichiara il listino
//   4b) cambiato e riscritto a mano col numero del listino: non lo dichiara
//   4c) in modifica, un prezzo che coincide col listino senza che il listino
//       l'abbia scritto non dichiara niente
//   5) il 409 della provenienza superata ricarica il prezzo dal listino
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
const suggerisciPrezzoRiga = vi.fn()
vi.mock('../api/preventiviApi', () => ({
  suggerisciPrezzoRiga: (...a) => suggerisciPrezzoRiga(...a),
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
const { useAuthStore } = await import('../../../stores/auth')
const { MANAGE_ICONS } = await import('../../../core/constants')
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
    suggerisciPrezzoRiga.mockReset().mockResolvedValue({ data: { data: {} } })
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

// Il listino da' alla riga 100, dalla riga 80 della versione 8.
const DAL_LISTINO = {
  prezzo_finale: '100.0000000000', origine: 'CATEGORIA', listino_versione_id: 8, listino_riga_id: 80,
}

async function montaColListino(riga = RIGA) {
  suggerisciPrezzoRiga.mockReset().mockResolvedValue({ data: { data: DAL_LISTINO } })
  const w = monta(PreventiviRigaForm, { preventivoId: 3, riga }, { global: { stubs: STUBS } })
  await flushPromises()
  return w
}

// Il campo del prezzo: l'InputNumber in valuta (la quantita' e' un altro).
function campoPrezzo(w) {
  return w.findAllComponents({ name: 'InputNumber' }).find((c) => c.props('mode') === 'currency')
}

async function salva(w) {
  const bottone = w.findAllComponents({ name: 'Button' }).find((b) => b.props('label') === 'common.save')
  await bottone.trigger('click')
  await flushPromises()
}

describe('PreventiviRigaForm — la provenienza del prezzo (K-6, D-5)', () => {
  beforeEach(() => {
    aggiornaRiga.mockReset().mockResolvedValue({ ...RIGA })
  })

  it('«Usa prezzo listino»: il prezzo viaggia con la sua provenienza', async () => {
    // La riga ha 90 a mano, il listino oggi da' 100; il bottone c'e' solo a
    // chi puo' fare override.
    const w = await montaColListino({ ...RIGA, prezzo_unitario: '90' })
    useAuthStore().user = { azioni_abilitate: { prezzo_override_manuale: true } }
    await flushPromises()
    const usa = w.findAllComponents({ name: 'Button' }).find((b) => b.props('icon') === MANAGE_ICONS.RIPRISTINA_LISTINO)
    await usa.trigger('click')
    await flushPromises()
    await salva(w)
    expect(aggiornaRiga.mock.calls[0][2].prezzo_unitario).toBe(100)
    const payload = aggiornaRiga.mock.calls[0][2]
    expect(payload.provenienza_prezzo).toEqual({
      origine_prezzo: 'CATEGORIA', listino_versione_id: 8, listino_riga_id: 80,
    })
  })

  it("un prezzo cambiato dall'operatore non dichiara il listino", async () => {
    const w = await montaColListino()
    await campoPrezzo(w).vm.$emit('update:modelValue', 90)
    await salva(w)
    const payload = aggiornaRiga.mock.calls[0][2]
    expect(payload.prezzo_unitario).toBe(90)
    expect(payload).not.toHaveProperty('provenienza_prezzo')
  })

  it('cambiato e riscritto a mano col numero del listino: non lo dichiara', async () => {
    const w = await montaColListino({ ...RIGA, prezzo_unitario: '90' })
    useAuthStore().user = { azioni_abilitate: { prezzo_override_manuale: true } }
    await flushPromises()
    const usa = w.findAllComponents({ name: 'Button' }).find((b) => b.props('icon') === MANAGE_ICONS.RIPRISTINA_LISTINO)
    await usa.trigger('click')
    await flushPromises()
    await campoPrezzo(w).vm.$emit('update:modelValue', 95)
    await flushPromises()
    await campoPrezzo(w).vm.$emit('update:modelValue', 100)
    await flushPromises()
    await salva(w)
    const payload = aggiornaRiga.mock.calls[0][2]
    expect(payload.prezzo_unitario).toBe(100)
    expect(payload).not.toHaveProperty('provenienza_prezzo')
  })

  it('in modifica un prezzo che coincide col listino, non scritto dal listino, non dichiara niente', async () => {
    const w = await montaColListino()
    await salva(w)
    expect(aggiornaRiga.mock.calls[0][2]).not.toHaveProperty('provenienza_prezzo')
  })

  it('il 409 della provenienza superata ricarica il prezzo dal listino', async () => {
    const w = await montaColListino()
    expect(suggerisciPrezzoRiga).toHaveBeenCalledTimes(1)
    aggiornaRiga.mockReset().mockRejectedValue({
      response: { data: { error: { code: 'E_PRICING_PROVENIENZA_SUPERATA', message: 'listino cambiato' } } },
    })
    await salva(w)
    expect(suggerisciPrezzoRiga).toHaveBeenCalledTimes(2)
  })
})
