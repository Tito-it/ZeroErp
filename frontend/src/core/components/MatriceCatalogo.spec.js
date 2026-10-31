// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: il contratto della base `MatriceCatalogo` (2026-10-31) nelle parti che
//        lo strato `MatriceOverride` non esercita — lo strato ha il suo spec,
//        che copre voci, ricerca e sola lettura passando di qui.
//
// Indice test:
//   1) le colonne del chiamante stanno dopo la voce
//   2) ⭐ senza lo slot `azioni` la colonna azioni non c'e' (matrice piena)
//   3) con lo slot `azioni` c'e', e la sola lettura (anche ereditata) la toglie
//   4) lo slot `empty` sostituisce il testo vuoto di default
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'
import { h, ref } from 'vue'
import Column from 'primevue/column'

import MatriceCatalogo from './MatriceCatalogo.vue'
import { READONLY_KEY } from '../composables/useReadonlyMode'
import { monta } from '../../../test/montaggio'

const VOCI = [{ id: 1, nome: 'Vendite' }, { id: 2, nome: 'Acquisti' }]

function matrice(props = {}, slots = {}, opts = {}) {
  return monta(MatriceCatalogo, {
    voci: VOCI,
    chiave: (v) => v.id,
    labelVoce: 'Area',
    ...props,
  }, {
    slots: {
      voce: ({ voce }) => voce.nome,
      colonne: () => h(Column, { header: 'Livello', field: 'id' }),
      ...slots,
    },
    ...opts,
  })
}

const intestazioni = (w) => w.findAll('thead th').map(th => th.text())

describe('MatriceCatalogo', () => {
  it('1) le colonne del chiamante stanno dopo la voce', () => {
    const w = matrice()
    expect(intestazioni(w)).toEqual(['Area', 'Livello'])
    expect(w.findAll('tbody tr')[1].text()).toContain('Acquisti')
  })

  it('2) senza lo slot `azioni` la colonna azioni non c\'e\'', () => {
    const w = matrice()
    expect(w.findAll('tbody tr')[0].findAll('td')).toHaveLength(2)
  })

  it('3) con lo slot `azioni` c\'e\', e la sola lettura (anche ereditata) la toglie', () => {
    const azioni = { azioni: ({ voce }) => h('button', `azione-${voce.id}`) }
    expect(matrice({}, azioni).findAll('tbody button')).toHaveLength(2)
    expect(matrice({ readonly: true }, azioni).findAll('tbody button')).toHaveLength(0)
    const ereditata = matrice({}, azioni, { provide: { [READONLY_KEY]: ref(true) } })
    expect(ereditata.findAll('tbody button')).toHaveLength(0)
  })

  it('4) lo slot `empty` sostituisce il testo vuoto di default', () => {
    const w = matrice({ voci: [] }, { empty: () => h('p', { class: 'vuoto-mio' }, 'Configura il catalogo') })
    expect(w.find('.vuoto-mio').text()).toBe('Configura il catalogo')
  })
})
