// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: il contratto di `VenditeNoteDrawer` da quando si monta DIRETTAMENTE
//        dai documenti (2026-10-31, regola del 2: ritirati i sei wrapper di
//        dominio). Quello che i wrapper dicevano ora sta qui: titolo, campi
//        della label riga, emittente, e il totale di `saved` per i badge.
//
// ⚠️ Si finge il solo `NoteDrawer` (il vero chiede la lista al catalogo):
//    qui si guarda cosa gli arriva.
//
// Indice test:
//   1) ⭐ ogni dominio ha il suo titolo, nelle DUE lingue
//   2) il basePath, l'emittente e il titolo arrivano al BB
//   3) le opzioni RIGA coi campi del dominio; le righe senza id restano fuori
//   4) `saved` riporta il totale (badge del padre)
//   5) senza id il drawer non si monta
//   6) ⭐ aperto senza emittente: in DEV lo dice in console; con l'emittente no
// ------------------------------------------------------------

import { describe, it, expect, vi, afterEach } from 'vitest'
import { defineComponent, h } from 'vue'
import { monta } from '../../../../test/montaggio'
import it_ from '../../../locales/it.json'
import en from '../../../locales/en.json'
import { DOMINI_NOTE_VENDITE } from './dominiNote'
import VenditeNoteDrawer from './VenditeNoteDrawer.vue'

const NoteDrawerFinto = defineComponent({
  name: 'NoteDrawer',
  props: ['visible', 'apiClient', 'codice', 'emittenteFiscaleId', 'title', 'supportsRiga', 'righeOptions'],
  emits: ['update:visible', 'saved'],
  setup: () => () => h('div', { class: 'note-drawer-finto' }),
})

const MESSAGGI = { vendite: { offerte: { note_titolo: 'Note offerta' } } }

function montaDrawer(props) {
  return monta(VenditeNoteDrawer, props, {
    messages: MESSAGGI,
    global: { stubs: { NoteDrawer: NoteDrawerFinto } },
  })
}

const leggi = (json, chiave) => chiave.split('.').reduce((o, k) => o?.[k], json)

describe('VenditeNoteDrawer', () => {
  afterEach(() => { vi.restoreAllMocks() })

  it('1) ogni dominio ha il suo titolo, nelle DUE lingue', () => {
    for (const [dominio, { titolo }] of Object.entries(DOMINI_NOTE_VENDITE)) {
      expect(typeof leggi(it_, titolo), `${dominio} it`).toBe('string')
      expect(typeof leggi(en, titolo), `${dominio} en`).toBe('string')
    }
  })

  it('2) il basePath, l\'emittente e il titolo arrivano al BB', () => {
    const w = montaDrawer({ dominio: 'offerte', id: 12, emittenteFiscaleId: 3, visible: true })
    const nd = w.findComponent(NoteDrawerFinto)
    expect(nd.props('apiClient').basePath).toBe('/vendite/offerte/12')
    expect(nd.props('codice')).toBe('vendite.note')
    expect(nd.props('emittenteFiscaleId')).toBe(3)
    expect(nd.props('title')).toBe('Note offerta')
  })

  it('3) le opzioni RIGA coi campi del dominio; le righe senza id restano fuori', () => {
    const w = montaDrawer({
      dominio: 'offerte',
      id: 12,
      emittenteFiscaleId: 3,
      righe: [
        { id: 1, articolo_codice: 'A1', articolo_descrizione: 'Primo' },
        { id: null, articolo_codice: 'KIT' },
        { id: 2 },
      ],
    })
    expect(w.findComponent(NoteDrawerFinto).props('righeOptions')).toEqual([
      { value: 1, label: 'A1 — Primo' },
      { value: 2, label: '#2' },
    ])
  })

  it('4) `saved` riporta il totale (badge del padre)', async () => {
    const w = montaDrawer({ dominio: 'ddt', id: 5, emittenteFiscaleId: 3 })
    await w.findComponent(NoteDrawerFinto).vm.$emit('saved', 7)
    expect(w.emitted('saved')).toEqual([[7]])
  })

  it('5) senza id il drawer non si monta', () => {
    const w = montaDrawer({ dominio: 'ddt', id: null, emittenteFiscaleId: 3 })
    expect(w.findComponent(NoteDrawerFinto).exists()).toBe(false)
  })

  it('6) aperto senza emittente: in DEV lo dice in console; con l\'emittente no', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const w = montaDrawer({ dominio: 'fatture', id: 9, emittenteFiscaleId: 4, visible: true })
    expect(warn).not.toHaveBeenCalled()
    await w.setProps({ emittenteFiscaleId: null })
    expect(warn).toHaveBeenCalledTimes(1)
    expect(warn.mock.calls[0][0]).toContain('emittenteFiscaleId')
  })
})
