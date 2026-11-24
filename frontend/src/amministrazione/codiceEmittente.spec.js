// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Test di `codiceEmittenteInForma`: la forma della sigla, minuscole
//        comprese (le alza il DB, brief-be-fe-BB-audit F-2).
//
// Indice test:
//  1. maiuscole, minuscole e spazi ai bordi sono in forma
//  2. trattini, lettere accentate e lunghezze fuori dai limiti no
// ------------------------------------------------------------
import { describe, it, expect } from 'vitest'
import { FIELD_LENGTH } from '../core/constants'
import { codiceEmittenteInForma } from './codiceEmittente'

const MIN = FIELD_LENGTH.EMITTENTE_CODICE_MIN
const MAX = FIELD_LENGTH.EMITTENTE_CODICE_MAX

describe('codiceEmittenteInForma', () => {
  it('maiuscole, minuscole e spazi ai bordi sono in forma', () => {
    expect(codiceEmittenteInForma('A'.repeat(MIN))).toBe(true)
    // Il campo mostra `ACME` (app-codice-input) e il DB lo salva cosi':
    // il Salva deve accendersi anche se il valore digitato e' minuscolo.
    expect(codiceEmittenteInForma('a1'.padEnd(MIN, 'b'))).toBe(true)
    expect(codiceEmittenteInForma(` ${'Z9'.padEnd(MAX, '0')} `)).toBe(true)
  })

  it('trattini, lettere accentate e lunghezze fuori dai limiti no', () => {
    expect(codiceEmittenteInForma('')).toBe(false)
    expect(codiceEmittenteInForma(null)).toBe(false)
    expect(codiceEmittenteInForma('A'.repeat(MIN - 1))).toBe(false)
    expect(codiceEmittenteInForma('A'.repeat(MAX + 1))).toBe(false)
    expect(codiceEmittenteInForma('A-'.padEnd(MIN, 'B'))).toBe(false)
    expect(codiceEmittenteInForma('È'.padEnd(MIN, 'B'))).toBe(false)
  })
})
