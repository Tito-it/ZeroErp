// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: La CORREZIONE DI STRUTTURA del drawer articolo (A-10;
//        brief-db-articoli-ammessi-per-documento R-BE-1 e R-DB-3, 2026-10-18):
//        i campi che riapre li dice il dettaglio (`struttura_correggibile`,
//        dalla sede del DB), e al salvataggio la struttura cambiata viaggia
//        nello STESSO PATCH (`correzione_struttura`): una chiamata sola, che il
//        backend scrive in una transazione.
// Note: si monta il drawer vero; sono finti solo i contorni — le API (che
//       rispondono come axios, `{ data: { data } }`), il guscio `AppDrawer`
//       (rende il corpo e un Salva che emette `save`), la barra delle azioni
//       (un bottone per azione visibile), la conferma (accetta subito) e i
//       componenti figli che parlano col backend per conto loro.
//
// Indice test:
//   1) un campo bloccato si riapre solo se e' fra le colonne del dettaglio
//   2) in correzione, il Salva fa UN PATCH con `correzione_struttura` delle
//      sole colonne cambiate
//   3) senza correzione, il PATCH non porta `correzione_struttura`
//   4) un articolo-ONERE (`e_onere` del dettaglio) spegne magazzino, composito,
//      lotto e seriale, anche nella correzione di struttura (il guard del DB
//      non ha porta amministratore); il solo componente resta libero
//   5) la merce non usata ha i quattro interruttori accesi: lo spegnimento
//      viene da `e_onere`, non da un lucchetto qualunque
//   6) composito e solo componente si escludono (CHECK
//      `chk_articoli_composito_non_solo_componente`, BE10 di
//      brief-db-revisione-catalogo): acceso l'uno, l'altro e' spento, col
//      perche'; nessun valore cambia da solo
//   7) la sezione della distinta la apre `puo_gestire_bom` del dettaglio, non
//      il composito acceso nel form e non ancora salvato (BE12)
// ------------------------------------------------------------

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises } from '@vue/test-utils'

const getArticolo = vi.fn()
const updateArticolo = vi.fn()

// `useDrawerFormPreserve` legge la route per il cambio pagina.
vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {}, fullPath: '/catalogo/articoli' }),
}))
vi.mock('../../core/composables/useConfirmAction', () => ({
  useConfirmAction: () => ({ confirmAction: (opzioni) => opzioni.onAccept() }),
}))

vi.mock('../api/catalogo', () => ({
  listArticoli: vi.fn(),
  getArticolo: (...a) => getArticolo(...a),
  createArticolo: vi.fn(),
  updateArticolo: (...a) => updateArticolo(...a),
  disattivaArticolo: vi.fn(),
  riattivaArticolo: vi.fn(),
  lookupArticoloUom: vi.fn().mockResolvedValue({ data: { data: { results: [] } } }),
  listArticoloComponenti: vi.fn().mockResolvedValue({ data: { data: { results: [] } } }),
  makeArticoloNotesApi: () => ({ list: vi.fn().mockResolvedValue({ data: { data: { results: [] } } }) }),
  getArticoloFormDefaults: vi.fn().mockResolvedValue({ data: { data: {} } }),
}))

const { monta } = await import('../../../test/montaggio')
const { useAuthStore } = await import('../../stores/auth')
const { default: ArticoloDrawer } = await import('./ArticoloDrawer.vue')
const { default: ToggleSwitch } = await import('primevue/toggleswitch')

const ID = '00000000-0000-0000-0000-000000000001'
const comeAxios = (data) => ({ data: { data } })

const AppDrawerFinto = defineComponent({
  name: 'AppDrawerFinto',
  emits: ['save', 'update:visible'],
  setup(_, { slots, emit }) {
    return () => h('div', [
      slots.default?.(),
      h('button', { class: 'salva-finto', onClick: () => emit('save') }, 'salva'),
    ])
  },
})
const AzioniFinte = defineComponent({
  name: 'AzioniFinte',
  props: { actions: { type: Array, default: () => [] } },
  setup(props) {
    return () => h('div', props.actions.filter(a => a.visible !== false).map(a =>
      h('button', { class: `azione-${a.key}`, onClick: () => a.command() }, a.key)))
  },
})
const Vuoto = defineComponent({ render: () => null })

// Un articolo USATO: il DB ha bloccato le colonne strutturali.
function articolo(sovrascritture = {}) {
  return {
    id: ID, codice: 'ART-1', descrizione: 'Articolo', descrizione_breve: null, uom_id: 1,
    attivo: true, is_composito: false, is_solo_componente: false, requires_serial: false,
    requires_lotto: false, gestito_a_magazzino: true, natura_vendita_id: 1,
    modo_approvvigionamento_id: 1, lead_time_giorni: null,
    non_editable_fields: ['codice', 'uom_id', 'requires_lotto', 'requires_serial'],
    struttura_correggibile: ['requires_lotto'],
    uom_operative: [], componenti: [], note: [],
    ...sovrascritture,
  }
}

async function apri(dettaglio) {
  getArticolo.mockResolvedValue(comeAxios(dettaglio))
  const w = monta(ArticoloDrawer, { visible: false, mode: 'edit', articoloId: ID }, {
    global: {
      stubs: {
        AppDrawer: AppDrawerFinto,
        DrawerActionsBar: AzioniFinte,
        DrawerEntityHeader: Vuoto,
        LookupSelect: Vuoto,
        IvaSelect: Vuoto,
        ContoContabileSelect: Vuoto,
        ArticoloUomDrawer: Vuoto,
        ArticoloBomDrawer: Vuoto,
        ArticoloNoteDrawer: Vuoto,
        PuntoEstensione: Vuoto,
      },
    },
  })
  useAuthStore().user = { is_super_admin: true }
  await w.setProps({ visible: true })
  await flushPromises()
  return w
}

// Scopo: l'interruttore del campo, trovato dalla sua etichetta.
function toggle(w, etichetta) {
  const campo = w.findAll('.form-field').find(f => f.find('label').exists()
    && f.find('label').text() === etichetta)
  return campo.findComponent(ToggleSwitch)
}

async function correggi(w) {
  await w.find('.azione-correggi_struttura').trigger('click')
  await flushPromises()
}

describe('ArticoloDrawer — correzione di struttura', () => {
  beforeEach(() => {
    getArticolo.mockReset()
    updateArticolo.mockReset().mockImplementation((_id, payload) =>
      Promise.resolve(comeAxios(articolo(payload))))
  })

  it('1) riapre solo le colonne del dettaglio', async () => {
    const w = await apri(articolo())
    expect(toggle(w, 'catalogo.field_requires_lotto').props('disabled')).toBe(true)
    await correggi(w)
    expect(toggle(w, 'catalogo.field_requires_lotto').props('disabled')).toBe(false)
    // Bloccato anche lui, ma non fra le colonne della correzione: resta fermo.
    expect(toggle(w, 'catalogo.field_requires_serial').props('disabled')).toBe(true)
  })

  it('2) in correzione il Salva fa un PATCH solo, con la struttura cambiata', async () => {
    const w = await apri(articolo())
    await correggi(w)
    toggle(w, 'catalogo.field_requires_lotto').vm.$emit('update:modelValue', true)
    await w.find('.salva-finto').trigger('click')
    await flushPromises()
    expect(updateArticolo).toHaveBeenCalledTimes(1)
    const [id, payload] = updateArticolo.mock.calls[0]
    expect(id).toBe(ID)
    expect(payload.correzione_struttura).toEqual({ requires_lotto: true })
    expect(payload.requires_lotto).toBe(true)
  })

  it('3) senza correzione il PATCH non porta la correzione', async () => {
    const w = await apri(articolo())
    await w.find('.salva-finto').trigger('click')
    await flushPromises()
    expect(updateArticolo).toHaveBeenCalledTimes(1)
    expect(updateArticolo.mock.calls[0][1]).not.toHaveProperty('correzione_struttura')
  })
})

describe('ArticoloDrawer — articolo-onere', () => {
  const ONERE_SENZA = [
    'catalogo.field_gestito_a_magazzino', 'catalogo.field_composito',
    'catalogo.field_requires_lotto', 'catalogo.field_requires_serial',
  ]
  // Un articolo NON usato: nessun lucchetto del DB, cosi' a spegnere puo'
  // essere solo l'onere.
  const libero = { non_editable_fields: [], struttura_correggibile: [], gestito_a_magazzino: false }

  beforeEach(() => {
    getArticolo.mockReset()
    updateArticolo.mockReset()
  })

  it('4) un onere spegne i quattro interruttori, anche in correzione', async () => {
    const w = await apri(articolo({
      e_onere: true, causale_onere_id: 6,
      non_editable_fields: ['requires_lotto'], struttura_correggibile: ['requires_lotto'],
    }))
    for (const etichetta of ONERE_SENZA) {
      expect(toggle(w, etichetta).props('disabled'), etichetta).toBe(true)
    }
    expect(toggle(w, 'catalogo.field_solo_componente').props('disabled')).toBe(false)
    expect(w.text()).toContain('catalogo.hint_onere_struttura')
    // Anche nella sezione magazzino il perche' prende il posto del suggerimento.
    expect(w.text()).not.toContain('catalogo.hint_gestito_a_magazzino')
    await correggi(w)
    expect(toggle(w, 'catalogo.field_requires_lotto').props('disabled')).toBe(true)
  })

  it('5) la merce non usata ha i quattro interruttori accesi', async () => {
    const w = await apri(articolo({ ...libero, e_onere: false, causale_onere_id: null }))
    for (const etichetta of ONERE_SENZA) {
      expect(toggle(w, etichetta).props('disabled'), etichetta).toBe(false)
    }
    expect(w.text()).not.toContain('catalogo.hint_onere_struttura')
    expect(w.text()).toContain('catalogo.hint_gestito_a_magazzino')
  })
})

describe('ArticoloDrawer — composito e solo componente', () => {
  const libero = { non_editable_fields: [], struttura_correggibile: [] }

  beforeEach(() => {
    getArticolo.mockReset()
    updateArticolo.mockReset()
  })

  it('6) acceso l\'uno, l\'altro e\' spento col perche\'', async () => {
    const w = await apri(articolo({ ...libero, is_composito: true }))
    expect(toggle(w, 'catalogo.field_solo_componente').props('disabled')).toBe(true)
    expect(toggle(w, 'catalogo.field_composito').props('disabled')).toBe(false)
    expect(w.text()).toContain('catalogo.hint_composito_solo_componente')

    await toggle(w, 'catalogo.field_composito').vm.$emit('update:modelValue', false)
    await flushPromises()
    expect(toggle(w, 'catalogo.field_solo_componente').props('disabled')).toBe(false)
    expect(toggle(w, 'catalogo.field_solo_componente').props('modelValue')).toBe(false)
    expect(w.text()).not.toContain('catalogo.hint_composito_solo_componente')

    await toggle(w, 'catalogo.field_solo_componente').vm.$emit('update:modelValue', true)
    await flushPromises()
    expect(toggle(w, 'catalogo.field_composito').props('disabled')).toBe(true)
    expect(toggle(w, 'catalogo.field_composito').props('modelValue')).toBe(false)
  })
})

describe('ArticoloDrawer — la sezione della distinta', () => {
  beforeEach(() => {
    getArticolo.mockReset()
    updateArticolo.mockReset()
  })

  it('7) la apre il dettaglio salvato, non il form', async () => {
    const libero = { non_editable_fields: [], struttura_correggibile: [] }
    const w = await apri(articolo({ ...libero, puo_gestire_bom: false }))
    expect(w.text()).not.toContain('catalogo.tab_bom')
    await toggle(w, 'catalogo.field_composito').vm.$emit('update:modelValue', true)
    await flushPromises()
    expect(w.text()).not.toContain('catalogo.tab_bom')

    const k = await apri(articolo({ ...libero, is_composito: true, puo_gestire_bom: true }))
    expect(k.text()).toContain('catalogo.tab_bom')
  })
})
