// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: «Mostra permessi» della lista operatori (brief riepilogo-permessi,
//        2026-10-06): sotto ogni riga le aree come chip, dalla sede unica a DB.
//        Ha preso il posto della pagina «Riepilogo permessi». E gli utenti di
//        prova (brief-be-utenti-di-sviluppo T-6, 2026-10-18): nascosti di
//        default, un interruttore li chiede, un badge li segna.
// Note: si monta la vista vera; sono finti i contorni — le API, lo scaffolding della pagina e `ListaConfigurabile`, ridotta a cio' che la
//       vista le chiede (righe, `expandedRows`, slot `row-expansion`).
//
// Indice test:
//   1) acceso l'interruttore, tutte le righe si aprono e il riepilogo si chiede
//      in UNA chiamata
//   2) le chip: area, livello, numero degli override, triangolo del tetto
//   3) spento l'interruttore, le righe si chiudono
//   4) un nuovo caricamento della lista scarta le chip vecchie e le richiede
//   5) una lettura fallita lo dice sulla riga (non «caricamento» per sempre),
//      e richiudendo e riaprendo la riga si riprova
//   6) «Mostra gli utenti di prova»: spento di default, acceso scrive
//      `includi_di_prova` nello store e rilancia la lista; spento lo toglie
//   7) il badge «di prova» sta solo sulle righe con `di_prova`
// ------------------------------------------------------------

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

const getPermessiRiepilogo = vi.fn()
const applyFilters = vi.fn()

vi.mock('../api/amministrazione', () => ({
  listOperatori: vi.fn(),
  listUnitaOrganizzative: vi.fn().mockResolvedValue({ data: { data: { results: [] } } }),
  getPermessiRiepilogo: (...a) => getPermessiRiepilogo(...a),
  getSetupStatus: vi.fn().mockResolvedValue({ data: { data: {} } }),
}))
vi.mock('../../core/composables/useListaConfigurabilePage', async () => {
  const { ref } = await import('vue')
  return {
    useListaConfigurabilePage: () => ({
      searchText: ref(''), onPage: vi.fn(), onSort: vi.fn(), applyFilters,
      paginatorProps: {}, tablePage: 1, listaRef: ref(null), dirty: ref(false),
      onConfigLoaded: vi.fn(), pageActions: [], perimetroBloccato: ref(false),
    }),
  }
})
vi.mock('../../core/composables/useTabFreshness', () => ({ useTabFreshness: () => {} }))
vi.mock('../../core/composables/useReadonlyMode', async (originale) => ({
  ...(await originale()),
  useReadonlyMode: () => ({ isReadonly: false, isBlocked: false }),
}))

const { monta } = await import('../../../test/montaggio')
const { useOperatoriStore } = await import('../stores/operatori')
const { default: OperatoriListView } = await import('./OperatoriListView.vue')

const comeAxios = (data) => ({ data: { data } })

// La lista finta: rende lo slot `row-expansion` delle righe aperte, come la
// vera, e la cella del ruolo di ogni riga (dove stanno i badge).
const ListaFinta = defineComponent({
  name: 'ListaFinta',
  props: { rows: { type: Array, default: () => [] }, expandedRows: { type: Object, default: null } },
  setup(props, { slots }) {
    return () => h('div', [
      ...props.rows.map(r => h('div', { class: 'cella-ruolo', 'data-id': r.auth_user_id }, slots['cell-ruolo']?.({ data: r }))),
      ...props.rows
        .filter(r => props.expandedRows?.[r.auth_user_id])
        .map(r => h('div', { class: 'riga-aperta', 'data-id': r.auth_user_id }, slots['row-expansion']?.({ data: r }))),
    ])
  },
})
const Vuoto = defineComponent({ render: () => null })

const RIGHE = [
  { auth_user_id: 6, soggetto_cognome: 'Pochi', di_prova: false },
  { auth_user_id: 9, soggetto_cognome: 'Rossi', di_prova: true },
]
const RIEPILOGO = [
  { auth_user_id: 6, area_id: 2, area_descrizione: 'Anagrafiche', livello: 'TUTTO', override_count: 3, voci_limitate: 0 },
  { auth_user_id: 6, area_id: 5, area_descrizione: 'Vendite', livello: 'BLOCCATO', override_count: 1, voci_limitate: 1 },
  { auth_user_id: 9, area_id: 2, area_descrizione: 'Anagrafiche', livello: 'LETTURA', override_count: 0, voci_limitate: 0 },
]

let montata = null

async function montaLista({ accesa = true } = {}) {
  const w = montata = monta(OperatoriListView, {}, {
    global: {
      stubs: {
        ListaConfigurabile: ListaFinta,
        OperatoreDrawer: Vuoto,
        OperatoriNonAssegnatiBanner: Vuoto,
        PageActionsBar: Vuoto,
      },
    },
  })
  const store = useOperatoriStore()
  store.fetchList = vi.fn()
  store.items = [...RIGHE]
  await flushPromises()
  if (accesa) await interruttore(w, true)
  return { w, store }
}

// Scopo: un interruttore della pagina, scelto dalla sua etichetta (sono due:
//        «Mostra permessi» e il filtro degli utenti di prova), come lo usa
//        l'operatore.
function toggleDi(w, etichetta) {
  return w.findAllComponents({ name: 'FiltroToggle' }).find(c => c.props('label') === etichetta)
}
async function interruttore(w, acceso, etichetta = 'amministrazione.mostra_permessi') {
  const toggle = toggleDi(w, etichetta)
  toggle.vm.$emit('update:modelValue', acceso)
  toggle.vm.$emit('change', acceso)
  await flushPromises()
}

const righeAperte = (w) => w.findAll('.riga-aperta').map(r => Number(r.attributes('data-id')))

describe('OperatoriListView — «Mostra permessi»', () => {
  // ⚠️ Store nuovo e vista smontata a ogni test: una vista rimasta montata
  //    reagirebbe anche lei a `store.items`, e le chiamate si sommerebbero.
  afterEach(() => { montata?.unmount(); montata = null })
  beforeEach(() => {
    setActivePinia(createPinia())
    applyFilters.mockReset()
    getPermessiRiepilogo.mockReset().mockImplementation((ids) =>
      Promise.resolve(comeAxios({ results: RIEPILOGO.filter(r => ids.includes(r.auth_user_id)) })))
  })

  it('1) acceso l\'interruttore, tutto si apre e il riepilogo si chiede una volta', async () => {
    const { w } = await montaLista({ accesa: false })
    expect(righeAperte(w)).toEqual([])
    expect(getPermessiRiepilogo).not.toHaveBeenCalled()
    await interruttore(w, true)
    expect(righeAperte(w)).toEqual([6, 9])
    expect(getPermessiRiepilogo).toHaveBeenCalledTimes(1)
    expect(getPermessiRiepilogo.mock.calls[0][0].sort()).toEqual([6, 9])
  })

  it('2) le chip dicono area, livello, override e tetto', async () => {
    const { w } = await montaLista()
    const [anagrafiche, vendite] = w.find('.riga-aperta[data-id="6"]').findAll('.operatore-permessi-area')
    expect(anagrafiche.text()).toContain('Anagrafiche')
    expect(anagrafiche.text()).toContain('3')
    expect(anagrafiche.find('.app-permessi-tetto-icona').exists()).toBe(false)
    expect(vendite.find('.app-permessi-tetto-icona').exists()).toBe(true)
    // Zero override: niente numero.
    const rossi = w.find('.riga-aperta[data-id="9"]').find('.operatore-permessi-area')
    expect(rossi.findComponent({ name: 'Badge' }).exists()).toBe(false)
  })

  it('3) spento l\'interruttore, le righe si chiudono', async () => {
    const { w } = await montaLista()
    await interruttore(w, false)
    expect(righeAperte(w)).toEqual([])
  })

  it('4) un nuovo caricamento scarta le chip vecchie e le richiede', async () => {
    const { w, store } = await montaLista()
    expect(getPermessiRiepilogo).toHaveBeenCalledTimes(1)
    store.items = [...RIGHE]
    await flushPromises()
    expect(getPermessiRiepilogo).toHaveBeenCalledTimes(2)
    expect(righeAperte(w)).toEqual([6, 9])
  })

  it('5) una lettura fallita si dice, e si riprova riaprendo la riga', async () => {
    getPermessiRiepilogo.mockRejectedValueOnce(new Error('rete'))
    const { w } = await montaLista()
    expect(w.find('.riga-aperta[data-id="6"]').text()).toContain('common.error_loading')

    const lista = w.findComponent(ListaFinta)
    lista.vm.$emit('update:expandedRows', {})
    await flushPromises()
    lista.vm.$emit('update:expandedRows', { 6: true })
    await flushPromises()
    expect(getPermessiRiepilogo).toHaveBeenCalledTimes(2)
    expect(w.find('.riga-aperta[data-id="6"]').findAll('.operatore-permessi-area')).toHaveLength(2)
  })

  it('6) «Mostra gli utenti di prova» allarga la lista solo se acceso', async () => {
    const { w, store } = await montaLista({ accesa: false })
    const etichetta = 'amministrazione.mostra_di_prova'
    expect(toggleDi(w, etichetta).props('modelValue')).toBe(false)
    expect(store.filters.includi_di_prova).toBeNull()

    await interruttore(w, true, etichetta)
    expect(store.filters.includi_di_prova).toBe(true)
    expect(applyFilters).toHaveBeenCalledTimes(1)

    await interruttore(w, false, etichetta)
    expect(store.filters.includi_di_prova).toBeNull()
    expect(applyFilters).toHaveBeenCalledTimes(2)
  })

  it('7) il badge «di prova» sta solo sulle righe di prova', async () => {
    const { w } = await montaLista({ accesa: false })
    const badge = (id) => w.find(`.cella-ruolo[data-id="${id}"]`).text()
    expect(badge(9)).toContain('amministrazione.di_prova_badge')
    expect(badge(6)).not.toContain('amministrazione.di_prova_badge')
  })
})
