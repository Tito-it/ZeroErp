// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: il drawer del template dopo il seed di primo impianto
//        (brief-db-seed-primo-impianto-non-si-riscrive §16.14, R3 e Q24): un
//        template si spegne con l'interruttore `attivo` (non si elimina), e su
//        un template nato dal seed i campi del programma mostrano il motivo.
// Note: si monta il drawer vero; sono finti lo store (che tiene il dettaglio
//       in `currentTemplate`, come quello vero) e il guscio `AppDrawer`.
//
// Indice test:
//   1) template di seed: segno «di sistema» e motivo sotto i campi del programma
//   2) template dell'installazione: nessun segno, nessun motivo
//   3) spegnere il template: il payload porta `attivo: false`, e solo i campi del form
//   4) un campo del form nell'elenco (oggi non c'e'): spento, col motivo, fuori dal PATCH
// ------------------------------------------------------------

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises } from '@vue/test-utils'

const store = {
  currentTemplate: null,
  fetchDetail: vi.fn(),
  update: vi.fn(),
}

vi.mock('../stores/emailTemplates', () => ({
  useEmailTemplatesStore: () => store,
}))
vi.mock('../api/amministrazione', () => ({
  previewEmailTemplate: vi.fn(),
}))

const { monta } = await import('../../../test/montaggio')
const { default: EmailTemplateDrawer } = await import('./EmailTemplateDrawer.vue')

const AppDrawerFinto = defineComponent({
  name: 'AppDrawerFinto',
  emits: ['save', 'update:visible'],
  setup(_, { slots }) {
    return () => h('div', slots.default?.())
  },
})

const BASE = {
  id: 3, codice: 'RESET_PASSWORD', lingua: 'it', oggetto: 'Reimposta la password',
  corpo_html: '<p>x</p>', corpo_testo: null, variabili_disponibili: ['nome', 'link'],
  attivo: true,
}
const DI_SEED = {
  ...BASE,
  nata_dal_seed: true,
  campi_del_software: ['codice', 'unita_organizzativa_id', 'tipo_prestazione_id', 'lingua', 'variabili_disponibili'],
}
const DELL_INSTALLAZIONE = { ...BASE, nata_dal_seed: false, campi_del_software: [] }

// Il watch del drawer parte all'APERTURA: si monta chiuso e si apre.
async function apri(dettaglio) {
  store.fetchDetail.mockImplementation(async () => { store.currentTemplate = dettaglio })
  const w = monta(EmailTemplateDrawer, { visible: false, mode: 'edit', templateId: dettaglio.id }, {
    global: { stubs: { AppDrawer: AppDrawerFinto } },
  })
  await w.setProps({ visible: true })
  await flushPromises()
  return w
}

describe('EmailTemplateDrawer — seed di primo impianto e solo disattivazione', () => {
  beforeEach(() => {
    store.currentTemplate = null
    store.fetchDetail.mockReset()
    store.update.mockReset().mockResolvedValue({ ...DI_SEED, attivo: false })
  })

  it('template di seed: segno «di sistema» e motivo sotto i campi del programma', async () => {
    const w = await apri(DI_SEED)
    expect(w.find('[data-testid="template-di-sistema"]').exists()).toBe(true)
    expect(w.find('[data-testid="motivo-codice"]').exists()).toBe(true)
    expect(w.find('[data-testid="motivo-lingua"]').exists()).toBe(true)
    expect(w.find('[data-testid="motivo-variabili_disponibili"]').exists()).toBe(true)
  })

  it("template dell'installazione: nessun segno, nessun motivo", async () => {
    const w = await apri(DELL_INSTALLAZIONE)
    expect(w.find('[data-testid="template-di-sistema"]').exists()).toBe(false)
    expect(w.find('[data-testid="motivo-codice"]').exists()).toBe(false)
    expect(w.find('[data-testid="motivo-lingua"]').exists()).toBe(false)
    expect(w.find('[data-testid="motivo-variabili_disponibili"]').exists()).toBe(false)
  })

  it('spegnere il template: il payload porta `attivo: false`, e solo i campi del form', async () => {
    const w = await apri(DI_SEED)
    w.findComponent('[data-testid="template-attivo"]').vm.$emit('update:modelValue', false)
    await w.findComponent(AppDrawerFinto).vm.$emit('save')
    await flushPromises()

    expect(store.update).toHaveBeenCalledTimes(1)
    const [id, payload] = store.update.mock.calls[0]
    expect(id).toBe(3)
    // ⛔ Nessun campo del programma nel PATCH: il guard del DB lo rifiuterebbe.
    expect(Object.keys(payload).sort()).toEqual(['attivo', 'corpo_html', 'corpo_testo', 'oggetto'])
    expect(payload.attivo).toBe(false)
    expect(w.emitted('saved')).toHaveLength(1)
  })

  it("un campo del form nell'elenco (oggi non c'e'): spento, col motivo, fuori dal PATCH", async () => {
    // Il caso si costruisce: l'elenco di oggi non nomina `oggetto`, ma il form
    // segue l'elenco, non i nomi che conosce.
    const w = await apri({ ...DI_SEED, campi_del_software: [...DI_SEED.campi_del_software, 'oggetto'] })
    expect(w.find('[data-testid="motivo-oggetto"]').exists()).toBe(true)
    expect(w.find('[data-testid="motivo-corpo_html"]').exists()).toBe(false)

    await w.findComponent(AppDrawerFinto).vm.$emit('save')
    await flushPromises()
    const payload = store.update.mock.calls[0][1]
    expect(Object.keys(payload).sort()).toEqual(['attivo', 'corpo_html', 'corpo_testo'])
  })
})
