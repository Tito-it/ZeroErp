// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: il tab «Versioni» del drawer listino (2026-10-31, brief-db-liste-
//        datatable-grezze-secondo-giro riga 5): legge la pagina delle versioni
//        SOLO a tab aperto, col listino nel path, e chiede alla vista i drawer
//        delle versioni con i suoi eventi.
//
// ⚠️ Si fingono i CONTORNI: il client HTTP (`listVersioni`), il registro delle
//    azioni di riga (`useAzioneRiga`), il guscio `DrawerTabLista` (il vero
//    chiede la config del catalogo) e il kebab (`RowActionsMenu`, che qui
//    rende un pulsante per voce visibile). Il tab, il suo store e
//    `useDrawerTabLista` sono quelli veri.
//
// Indice test:
//   1) ⭐ tab chiuso: nessuna lettura
//   2) tab aperto: legge le versioni DEL listino, e le righe arrivano alla lista
//   3) il kebab chiede alla vista clone e righe, col listino; il clic di riga apre le righe
//   4) «Attiva» c'e' solo se il passaggio e' permesso (`azioni_permesse`)
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises } from '@vue/test-utils'

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}))
vi.mock('../api/listini', () => ({ listVersioni: vi.fn(), deleteVersione: vi.fn() }))
vi.mock('../../core/composables/useAzioneRiga', () => ({
  useAzioneRiga: () => ({ bloccata: () => false, motivo: () => null }),
}))

const { listVersioni } = await import('../api/listini')
const { monta } = await import('../../../test/montaggio')
const { default: ListinoVersioniTab } = await import('./ListinoVersioniTab.vue')

// Il guscio: rende ogni riga col suo slot `actions`, e una riga cliccabile.
const DrawerTabListaFinto = defineComponent({
  name: 'DrawerTabListaFinto',
  props: { rows: { type: Array, default: () => [] } },
  emits: ['row-click'],
  setup(props, { slots, emit }) {
    return () => h('div', { class: 'lista-finta' }, props.rows.map((r) =>
      h('div', { class: 'riga', 'data-id': r.id }, [
        h('span', { class: 'apri', onClick: () => emit('row-click', r) }, r.codice_versione),
        slots.actions?.({ data: r }),
      ])))
  },
})
const RowActionsMenuFinto = defineComponent({
  name: 'RowActionsMenuFinto',
  props: { actions: { type: Array, default: () => [] } },
  setup(props) {
    return () => h('span', props.actions.filter((a) => a.visible !== false).map((a) =>
      h('button', { class: `azione-${a.key}`, onClick: a.command }, a.key)))
  },
})

const LISTINO = { id: 10, codice: 'L1', descrizione: 'Listino', utility_id: 1 }
const V1 = { id: 101, codice_versione: 'V1', stato: 'BOZZA', azioni_permesse: ['attiva'] }
const V2 = { id: 102, codice_versione: 'V2', stato: 'ATTIVA', azioni_permesse: [] }

function apri(props = {}) {
  return monta(ListinoVersioniTab, { listino: LISTINO, attivo: true, ...props }, {
    global: {
      stubs: {
        DrawerTabLista: DrawerTabListaFinto,
        RowActionsMenu: RowActionsMenuFinto,
        AttivaVersioneDialog: true,
        ChiudiVersioneDialog: true,
      },
    },
  })
}

describe('ListinoVersioniTab', () => {
  beforeEach(() => {
    listVersioni.mockReset()
    listVersioni.mockResolvedValue({ data: { data: { results: [V1, V2], count: 2 } } })
  })

  it('1) tab chiuso: nessuna lettura', async () => {
    apri({ attivo: false })
    await flushPromises()
    expect(listVersioni).not.toHaveBeenCalled()
  })

  it('2) tab aperto: legge le versioni DEL listino, e le righe arrivano alla lista', async () => {
    const w = apri()
    await flushPromises()
    expect(listVersioni).toHaveBeenCalled()
    expect(listVersioni.mock.calls[0][0]).toBe(10)
    expect(w.findAll('.riga').map((r) => r.attributes('data-id'))).toEqual(['101', '102'])
  })

  it('3) il kebab chiede alla vista clone e righe, col listino; il clic di riga apre le righe', async () => {
    const w = apri()
    await flushPromises()
    await w.find('.riga[data-id="102"] .azione-clona').trigger('click')
    expect(w.emitted('open-clona-versione')[0]).toEqual([V2, LISTINO])
    await w.find('.riga[data-id="101"] .azione-gestisci-righe').trigger('click')
    expect(w.emitted('open-righe')[0]).toEqual([V1, LISTINO])
    await w.find('.riga[data-id="102"] .apri').trigger('click')
    expect(w.emitted('open-righe')[1]).toEqual([V2, LISTINO])
  })

  it('4) «Attiva» c\'e\' solo se il passaggio e\' permesso (`azioni_permesse`)', async () => {
    const w = apri()
    await flushPromises()
    expect(w.find('.riga[data-id="101"] .azione-attiva').exists()).toBe(true)
    expect(w.find('.riga[data-id="102"] .azione-attiva').exists()).toBe(false)
  })
})
