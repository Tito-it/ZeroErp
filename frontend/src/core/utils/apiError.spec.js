// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: `eAccessoNegato` — il rifiuto (401/403) che i lettori ambientali
//        nascondono, distinto da ogni altro errore (estratto 2026-10-31).
//
// Indice test:
//   1) 401 e 403 sono un rifiuto
//   2) ogni altro errore non lo e' (5xx, 404, rete senza risposta, null)
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'
import { eAccessoNegato } from './apiError'

const errore = (status) => ({ response: { status } })

describe('eAccessoNegato', () => {
  it('1) 401 e 403 sono un rifiuto', () => {
    expect(eAccessoNegato(errore(401))).toBe(true)
    expect(eAccessoNegato(errore(403))).toBe(true)
  })

  it('2) ogni altro errore non lo e\'', () => {
    expect(eAccessoNegato(errore(500))).toBe(false)
    expect(eAccessoNegato(errore(404))).toBe(false)
    expect(eAccessoNegato(new Error('Network Error'))).toBe(false)
    expect(eAccessoNegato(null)).toBe(false)
  })
})
