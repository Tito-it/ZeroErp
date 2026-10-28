// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: presidio di `ammettePersonalizzazione` (brief-db-parametri-senza-override
//        FE-1): la lista e il drawer dei parametri non offrono l'override dove
//        `fn_list_parameters_for_user` dice `ammette_override = false`.
//        Solo `false` esclude: un campo assente lascia la decisione al DB.
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'

import { ammettePersonalizzazione } from './parameterLevel'

describe('ammettePersonalizzazione', () => {
  it('false: il parametro vale per tutti', () => {
    expect(ammettePersonalizzazione({ ammette_override: false })).toBe(false)
  })

  it('true: si personalizza', () => {
    expect(ammettePersonalizzazione({ ammette_override: true })).toBe(true)
  })

  it('campo assente o parametro nullo: non esclude, il rifiuto resta del DB', () => {
    expect(ammettePersonalizzazione({})).toBe(true)
    expect(ammettePersonalizzazione(null)).toBe(true)
  })
})
