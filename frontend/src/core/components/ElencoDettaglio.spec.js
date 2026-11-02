// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: il contratto di `ElencoDettaglio` (2026-10-31, regola del 2): elenco
//        a sinistra, voce mostrata a destra.
//
// Indice test:
//   1) senza scelta si mostra la prima voce, ed e' quella marcata attiva
//   2) il clic emette la chiave (`v-model`): la scelta resta del chiamante
//   3) ⭐ una scelta che non e' piu' a vista ricade sulla prima a vista
//   4) la voce modificata ha il suo segno; senza voci, il testo vuoto
//   5) senza lo slot `filtri` la riga dei filtri non c'e'
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'
import { h } from 'vue'

import ElencoDettaglio from './ElencoDettaglio.vue'
import { monta } from '../../../test/montaggio'

const VOCI = [{ id: 1, nome: 'Vendite' }, { id: 2, nome: 'Acquisti' }]

function elenco(props = {}, slots = {}) {
  return monta(ElencoDettaglio, {
    voci: VOCI,
    chiave: (v) => v.id,
    etichetta: (v) => v.nome,
    ...props,
  }, {
    slots: { dettaglio: ({ voce }) => h('p', { class: 'mostrata' }, voce.nome), ...slots },
  })
}

const voci = (w) => w.findAll('.app-elenco-dettaglio-voce')

describe('ElencoDettaglio', () => {
  it('1) senza scelta si mostra la prima voce, ed e\' quella marcata attiva', () => {
    const w = elenco()
    expect(w.find('.mostrata').text()).toBe('Vendite')
    expect(voci(w)[0].classes()).toContain('app-elenco-dettaglio-voce--attiva')
    expect(voci(w)[1].classes()).not.toContain('app-elenco-dettaglio-voce--attiva')
  })

  it('2) il clic emette la chiave (`v-model`): la scelta resta del chiamante', async () => {
    const w = elenco()
    await voci(w)[1].trigger('click')
    expect(w.emitted('update:modelValue')).toEqual([[2]])
    await w.setProps({ modelValue: 2 })
    expect(w.find('.mostrata').text()).toBe('Acquisti')
  })

  it('3) una scelta che non e\' piu\' a vista ricade sulla prima a vista', async () => {
    const w = elenco({ modelValue: 2 })
    await w.setProps({ voci: [VOCI[0]] })
    expect(w.find('.mostrata').text()).toBe('Vendite')
  })

  it('4) la voce modificata ha il suo segno; senza voci, il testo vuoto', async () => {
    const w = elenco({ modificata: (v) => v.id === 2, testoVuoto: 'Niente' })
    expect(voci(w)[1].classes()).toContain('app-elenco-dettaglio-voce--modificata')
    expect(voci(w)[0].classes()).not.toContain('app-elenco-dettaglio-voce--modificata')
    await w.setProps({ voci: [] })
    expect(w.text()).toContain('Niente')
    expect(w.find('.mostrata').exists()).toBe(false)
  })

  it('5) senza lo slot `filtri` la riga dei filtri non c\'e\'', () => {
    expect(elenco().find('.app-elenco-dettaglio-filtri').exists()).toBe(false)
    const conFiltri = elenco({}, { filtri: () => h('input') })
    expect(conFiltri.find('.app-elenco-dettaglio-filtri input').exists()).toBe(true)
  })
})
