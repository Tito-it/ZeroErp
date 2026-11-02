// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il kebab forzato di `RowActionsMenu` arriva dalla cella azioni della
//        lista (`CellaAzioniRiga` + `useAzioniRigaCompatte`), senza che il
//        caller giri lo scope `compact`.
//
// ⭐ Il difetto che pinna (2026-09-29): quattordici liste non giravano
//    `compact` a `:force-compact`; il packing contava il kebab, la cella
//    rendeva i pulsanti inline, e l'eccedenza usciva come scrollbar
//    orizzontale — nessun errore (righe della distinta contabile).
// ⚠️ Si asseriscono le CLASSI modificatrici, non la resa: jsdom non calcola
//    il CSS, e lo switch desktop/touch resta materia di collaudo a video.
//
// Indice test:
//   1) ⭐ dentro una cella azioni compatta: kebab forzato senza prop
//   2) cella azioni NON compatta: nessuna forzatura
//   3) fuori da una lista: nessuna forzatura (resta lo switch CSS)
//   4) `force-compact` esplicito vince anche su una cella non compatta
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'
import { h } from 'vue'

import CellaAzioniRiga from './CellaAzioniRiga.vue'
import RowActionsMenu from './RowActionsMenu.vue'
import { monta } from '../../../test/montaggio'

const AZIONI = [{ key: 'apri', label: 'Apri', icon: 'pi pi-eye', command: () => {} }]
const RIGA = { id: 1, attivo: true }

function forzato(wrapper) {
  return {
    kebab: wrapper.find('.app-row-actions-compact--on').exists(),
    inlineSpento: wrapper.find('.app-row-actions-inline--off').exists(),
  }
}

function inCella(compact, propsMenu = {}) {
  return monta(CellaAzioniRiga, { compact }, {
    slots: { default: () => h(RowActionsMenu, { row: RIGA, actions: AZIONI, ...propsMenu }) },
  })
}

describe('RowActionsMenu — kebab dalla cella azioni', () => {
  it('1) ⭐ dentro una cella azioni compatta: kebab forzato senza prop', () => {
    expect(forzato(inCella(true))).toEqual({ kebab: true, inlineSpento: true })
  })

  it('2) cella azioni NON compatta: nessuna forzatura', () => {
    expect(forzato(inCella(false))).toEqual({ kebab: false, inlineSpento: false })
  })

  it('3) fuori da una lista: nessuna forzatura (resta lo switch CSS)', () => {
    const w = monta(RowActionsMenu, { row: RIGA, actions: AZIONI })
    expect(forzato(w)).toEqual({ kebab: false, inlineSpento: false })
  })

  it('4) `force-compact` esplicito vince anche su una cella non compatta', () => {
    expect(forzato(inCella(false, { forceCompact: true }))).toEqual({ kebab: true, inlineSpento: true })
  })
})
