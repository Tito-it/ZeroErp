// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: il drawer della testata di un preset dopo il giro 1a di
//        brief-db-revisione-ui e il §16.15 di
//        brief-db-seed-primo-impianto-non-si-riscrive: `is_default` non esiste
//        piu' (Q26), la bozza nasce spenta, e su un preset nato dal seed i
//        campi del programma sono spenti col motivo e restano fuori dal PATCH
//        (R-UI-sup).
// Note: si monta il drawer vero; sono finti lo store e il guscio `AppDrawer`.
//       ⚠️ L'elenco dei campi del programma lo porta la riga (come la manda
//       il backend): qui si costruisce, non si ricopia quello del DB.
//
// Indice test:
//   1) creazione: niente `is_default` nel payload, la bozza nasce spenta
//   2) preset di seed: codice spento col motivo, fuori dal PATCH
//   3) preset dell'installazione: nessun motivo, il codice viaggia
// ------------------------------------------------------------

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises } from '@vue/test-utils'

const store = {
  create: vi.fn(),
  update: vi.fn(),
}

vi.mock('../stores/uiPresetAdmin', () => ({
  useUiPresetAdminStore: () => store,
}))

const { monta } = await import('../../../test/montaggio')
const { default: ListaPresetDrawer } = await import('./ListaPresetDrawer.vue')

const AppDrawerFinto = defineComponent({
  name: 'AppDrawerFinto',
  emits: ['save', 'update:visible'],
  setup(_, { slots }) {
    return () => h('div', slots.default?.())
  },
})

const BASE = {
  id: 9, lista_id: 4, codice: 'sistema', descrizione: 'Preset di sistema',
  ambito: 'sistema', profilo_accesso_id: null, emittente_fiscale_id: null,
  pagina_dimensione: null, attivo: true,
}
const DI_SEED = {
  ...BASE,
  nata_dal_seed: true,
  campi_del_software: ['lista_id', 'codice', 'ambito', 'profilo_accesso_id', 'emittente_fiscale_id'],
}
const DELL_INSTALLAZIONE = { ...BASE, nata_dal_seed: false, campi_del_software: [] }

// Il watch del drawer parte all'APERTURA: si monta chiuso e si apre.
async function apri(props) {
  const w = monta(ListaPresetDrawer, { visible: false, listaId: 4, ...props }, {
    global: { stubs: { AppDrawer: AppDrawerFinto } },
  })
  await w.setProps({ visible: true })
  await flushPromises()
  return w
}

async function salva(w) {
  await w.findComponent(AppDrawerFinto).vm.$emit('save')
  await flushPromises()
}

describe('ListaPresetDrawer — preset senza is_default e seed di primo impianto', () => {
  beforeEach(() => {
    store.create.mockReset().mockResolvedValue({ id: 10 })
    store.update.mockReset().mockResolvedValue({ id: 9 })
  })

  it('creazione: niente `is_default` nel payload, la bozza nasce spenta', async () => {
    const w = await apri({ mode: 'create' })
    const inputs = w.findAll('input[type="text"]')
    await inputs[0].setValue('nuovo')
    await inputs[1].setValue('Nuovo preset')
    await salva(w)

    expect(store.create).toHaveBeenCalledTimes(1)
    const [listaId, payload] = store.create.mock.calls[0]
    expect(listaId).toBe(4)
    expect(payload).not.toHaveProperty('is_default')
    expect(payload.attivo).toBe(false)
  })

  it('preset di seed: codice spento col motivo, fuori dal PATCH', async () => {
    const w = await apri({ mode: 'edit', recordId: 9, recordData: DI_SEED })
    expect(w.find('[data-testid="motivo-codice"]').exists()).toBe(true)
    expect(w.find('[data-testid="motivo-descrizione"]').exists()).toBe(false)
    await salva(w)

    const [id, payload] = store.update.mock.calls[0]
    expect(id).toBe(9)
    // ⛔ Un campo del programma nel PATCH lo rifiuterebbe il guard del DB.
    expect(payload).not.toHaveProperty('codice')
    expect(payload.descrizione).toBe('Preset di sistema')
  })

  it("preset dell'installazione: nessun motivo, il codice viaggia", async () => {
    const w = await apri({ mode: 'edit', recordId: 9, recordData: DELL_INSTALLAZIONE })
    expect(w.find('[data-testid="motivo-codice"]').exists()).toBe(false)
    await salva(w)
    expect(store.update.mock.calls[0][1].codice).toBe('sistema')
  })
})
