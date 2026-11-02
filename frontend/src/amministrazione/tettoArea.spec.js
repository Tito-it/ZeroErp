// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Presidio della copia FE delle regole del tetto d'area (anteprima del
//        pannello permessi). Gli esiti sono QUELLI del pgTAP
//        `db/pgtap/script/test-permessi-tetto-area-v1.sql`, casi 3 e 4: se il
//        DB cambia la regola cambia quel test, e questo va riallineato.
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'
import { areaConsenteAzione, livelloConTettoArea } from './tettoArea'

describe('areaConsenteAzione — copia di script.fn_area_consente_azione', () => {
  it('3) pgTAP: LETTURA non basta a TUTTO, basta a LETTURA; NULL vale no', () => {
    const esiti = [
      areaConsenteAzione('LETTURA', 'TUTTO'),
      areaConsenteAzione('LETTURA', 'LETTURA'),
      areaConsenteAzione('TUTTO', 'LETTURA'),
      areaConsenteAzione('BLOCCATO', 'LETTURA'),
      areaConsenteAzione(null, 'TUTTO'),
      areaConsenteAzione('TUTTO', null),
    ]
    expect(esiti).toEqual([false, true, true, false, false, false])
  })

  it('un valore fuori enum vale no (fail-closed), non un confronto fra undefined', () => {
    expect(areaConsenteAzione('XYZ', 'TUTTO')).toBe(false)
    expect(areaConsenteAzione(undefined, 'LETTURA')).toBe(false)
  })
})

describe('livelloConTettoArea — copia di script.fn_livello_con_tetto_area', () => {
  it('4) pgTAP: il piu\' restrittivo; senza specifico vale l\'area; area NULL = BLOCCATO', () => {
    const esiti = [
      livelloConTettoArea('TUTTO', 'BLOCCATO'),
      livelloConTettoArea('TUTTO', 'LETTURA'),
      livelloConTettoArea('BLOCCATO', 'TUTTO'),
      livelloConTettoArea('LETTURA', 'TUTTO'),
      livelloConTettoArea(null, 'LETTURA'),
      livelloConTettoArea('TUTTO', null),
    ]
    expect(esiti).toEqual(['BLOCCATO', 'LETTURA', 'BLOCCATO', 'LETTURA', 'LETTURA', 'BLOCCATO'])
  })
})
