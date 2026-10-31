// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: la sola lettura del drawer profilo reparto (2026-10-31). Fino a quel
//        giorno il drawer non aveva la prop `readonly` e non spegneva i suoi
//        controlli: la catena del dominio arrivava ad AppDrawer (niente Salva),
//        ma Select e interruttori restavano accesi — l'operatore cambiava
//        valori che non sarebbero mai stati salvati.
//
// ⚠️ Si fingono i CONTORNI: lo store dei reparti, i due lookup e il guscio
//    AppDrawer (il vero monta il contenuto a fine animazione, che jsdom non
//    esegue). Il finto dichiara `readonly` per provare che il drawer la passa.
//
// Indice test:
//   1) editabile: i controlli sono accesi
//   2) ⭐ prop `readonly`: tutti i controlli spenti, e il guscio la riceve
//   3) ⭐ sola lettura ereditata dalla vista (catena), senza la prop
// ------------------------------------------------------------

import { describe, it, expect, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'
import { flushPromises } from '@vue/test-utils'

vi.mock('../api/amministrazione', () => ({
  listAreeFunzionali: () => Promise.resolve({ data: { data: { results: [
    { id: 1, codice: 'VEN', descrizione: 'Vendite' },
  ] } } }),
  listAzioniProcesso: () => Promise.resolve({ data: { data: { results: [
    { id: 9, permission_codename: 'can_x', descrizione: 'Azione X', area_codice: 'VEN', pericolosa: false },
  ] } } }),
}))

const profilo = ref(null)
vi.mock('../stores/reparti', () => ({
  useRepartiStore: () => ({
    get currentProfilo() { return profilo.value },
    fetchProfilo: async () => {
      profilo.value = { aree: [], azioni: [], richiede_secondo_fattore: false }
    },
    saveProfilo: vi.fn(),
  }),
}))

const { monta } = await import('../../../test/montaggio')
const { default: RepartoProfiloEditor } = await import('./RepartoProfiloEditor.vue')
const { READONLY_KEY } = await import('../../core/composables/useReadonlyMode')

const AppDrawerFinto = defineComponent({
  name: 'AppDrawerFinto',
  props: { readonly: { type: Boolean, default: false } },
  setup(props, { slots }) {
    return () => h('div', { class: 'drawer-finto', 'data-readonly': String(props.readonly) }, slots.default?.())
  },
})

async function apri(props = {}, provide = {}) {
  profilo.value = null
  const w = monta(RepartoProfiloEditor, { visible: false, uoId: 3, uoNome: 'Ufficio', ...props }, {
    provide,
    global: { stubs: { AppDrawer: AppDrawerFinto } },
  })
  await flushPromises()
  await w.setProps({ visible: true })
  await flushPromises()
  return w
}

// I controlli del form: l'interruttore del secondo fattore, i Select dei
// livelli e gli interruttori delle azioni.
const interruttori = (w) => w.findAll('.p-toggleswitch')
const selettori = (w) => w.findAll('.p-select')

describe('RepartoProfiloEditor — sola lettura', () => {
  it('1) editabile: i controlli sono accesi', async () => {
    const w = await apri()
    expect(selettori(w)).toHaveLength(1)
    expect(interruttori(w)).toHaveLength(2)
    expect(w.findAll('.p-disabled')).toHaveLength(0)
    expect(w.find('.drawer-finto').attributes('data-readonly')).toBe('false')
  })

  it('2) prop `readonly`: tutti i controlli spenti, e il guscio la riceve', async () => {
    const w = await apri({ readonly: true })
    expect(selettori(w)[0].classes()).toContain('p-disabled')
    for (const s of interruttori(w)) expect(s.classes()).toContain('p-disabled')
    expect(w.find('.drawer-finto').attributes('data-readonly')).toBe('true')
  })

  it('3) sola lettura ereditata dalla vista (catena), senza la prop', async () => {
    const w = await apri({}, { [READONLY_KEY]: ref(true) })
    expect(selettori(w)[0].classes()).toContain('p-disabled')
    for (const s of interruttori(w)) expect(s.classes()).toContain('p-disabled')
  })
})
