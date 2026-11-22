// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: il drawer di una colonna di lista dopo il giro 4 di
//        brief-db-revisione-ui: il codice e' immutabile (BE12), senza campo
//        sorgente la colonna non si esporta (U25), un'azione non ha campo
//        sorgente (U24) e una colonna della genealogia si mostra soltanto.
//        I vincoli li giudica il DB: il form non propone cio' che il DB
//        rifiuterebbe.
// Note: si monta il drawer vero; sono finti lo store e il guscio `AppDrawer`.
//
// Indice test:
//   1) modifica: il codice e' spento e resta fuori dal PATCH
//   2) creazione: senza campo sorgente non esportabile; col campo si accende
//   3) creazione: un'azione svuota il campo sorgente, e non si esporta
//   4) creazione: la genealogia spegne filtro, ordinamento e ricerca
// ------------------------------------------------------------

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises } from '@vue/test-utils'

const store = {
  create: vi.fn(),
  update: vi.fn(),
}

vi.mock('../stores/uiColonnaAdmin', () => ({
  useUiColonnaAdminStore: () => store,
}))

const { monta } = await import('../../../test/montaggio')
const { default: ListaColonnaDrawer } = await import('./ListaColonnaDrawer.vue')

const AppDrawerFinto = defineComponent({
  name: 'AppDrawerFinto',
  emits: ['save', 'update:visible'],
  setup(_, { slots }) {
    return () => h('div', slots.default?.())
  },
})

const RIGA = {
  id: 7, lista_id: 4, codice: 'ragione_sociale', etichetta: 'Ragione sociale',
  etichetta_estesa: null, etichetta_i18n_key: null, campo_sorgente: 'ragione_sociale',
  origine_campo: 'VISTA', tipo_colonna: 'informazione', tipo_dato: 'string',
  filtrabile: true, ordinabile: true, esportabile: true, ricercabile_full: false,
  sensibile: false, attivo: true, formato: null, larghezza_default: null,
  ordine_default: 10, allineamento: 'left', gruppo: null, gruppo_ordine: null,
  nata_dal_seed: false, campi_del_software: [],
  // ⭐ Il codice e' fermo perche' lo dice la RIGA (il lucchetto del DB, da
  //    `dbops.fn_non_editable_fields`), non un nome cablato nel drawer.
  non_editable_fields: ['codice'],
}

// Il watch del drawer parte all'APERTURA: si monta chiuso e si apre.
async function apri(props) {
  const w = monta(ListaColonnaDrawer, { visible: false, listaId: 4, ...props }, {
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

// Il form del drawer, dallo stato del componente (i Select di PrimeVue non
// si pilotano dal DOM in jsdom).
function form(w) {
  return w.vm.$.setupState.form
}

describe('ListaColonnaDrawer — i vincoli del giro 4', () => {
  beforeEach(() => {
    store.create.mockReset().mockResolvedValue({ id: 10 })
    store.update.mockReset().mockResolvedValue({ id: 7 })
  })

  it('modifica: il codice e\' spento e resta fuori dal PATCH', async () => {
    const w = await apri({ mode: 'edit', recordId: 7, recordData: RIGA })
    const codice = w.findAll('input[type="text"]')[0]
    expect(codice.element.disabled).toBe(true)
    form(w).etichetta = 'Denominazione'
    await salva(w)

    expect(store.update).toHaveBeenCalledTimes(1)
    const [, payload] = store.update.mock.calls[0]
    expect(payload).not.toHaveProperty('codice')
    expect(payload.etichetta).toBe('Denominazione')
    // La riga caricata e' coerente coi CHECK: i watch non l'hanno toccata.
    expect(payload.esportabile).toBe(true)
  })

  it('creazione: senza campo sorgente non esportabile; col campo si accende', async () => {
    const w = await apri({ mode: 'create' })
    Object.assign(form(w), { codice: 'nuova', etichetta: 'Nuova' })
    await flushPromises()
    expect(form(w).esportabile).toBe(false)
    expect(w.find('#ui-col-esportabile').element.disabled).toBe(true)

    form(w).campo_sorgente = 'nuova'
    await flushPromises()
    expect(form(w).esportabile).toBe(true)
    await salva(w)
    const [, payload] = store.create.mock.calls[0]
    expect(payload).toMatchObject({ campo_sorgente: 'nuova', esportabile: true, origine_campo: 'VISTA' })
  })

  it('creazione: un\'azione svuota il campo sorgente, e non si esporta', async () => {
    const w = await apri({ mode: 'create' })
    Object.assign(form(w), { codice: 'apri', etichetta: 'Apri', campo_sorgente: 'id' })
    await flushPromises()
    form(w).tipo_colonna = 'azione'
    await flushPromises()
    expect(form(w).campo_sorgente).toBe('')
    expect(form(w).esportabile).toBe(false)
    await salva(w)
    const [, payload] = store.create.mock.calls[0]
    expect(payload).toMatchObject({ tipo_colonna: 'azione', campo_sorgente: null, esportabile: false })
  })

  it('creazione: la genealogia spegne filtro, ordinamento e ricerca', async () => {
    const w = await apri({ mode: 'create' })
    Object.assign(form(w), { codice: 'frontiera', etichetta: 'Frontiera', campo_sorgente: 'frontiera_codice' })
    await flushPromises()
    form(w).ricercabile_full = true
    form(w).origine_campo = 'LINEAGE'
    await flushPromises()
    await salva(w)
    const [, payload] = store.create.mock.calls[0]
    expect(payload).toMatchObject({
      origine_campo: 'LINEAGE', filtrabile: false, ordinabile: false, ricercabile_full: false,
    })
  })
})
