// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: `idNellaForma` — l'id nella forma dichiarata, o `null`.
//
// Indice test:
//  1) INTERO: testo o numero > 0 → numero
//  2) INTERO: zero, negativi, decimali, testo, array, vuoto → null
//  3) UUID: un uuid resta stringa; un numero o un testo qualunque → null
//  4) forma sconosciuta → null
// ------------------------------------------------------------
import { describe, expect, it } from 'vitest'
import { FORME_ID, idNellaForma } from './idNellaForma'

const UUID = '019bbee2-5f6a-704f-bbd0-34ed84db252d'

describe('idNellaForma', () => {
  it('1) INTERO: testo o numero > 0 → numero', () => {
    expect(idNellaForma('42', FORME_ID.INTERO)).toBe(42)
    expect(idNellaForma(7, FORME_ID.INTERO)).toBe(7)
  })

  it('2) INTERO: zero, negativi, decimali, testo, array, vuoto → null', () => {
    for (const v of ['0', '-3', '1.5', 'abc', ['1', '2'], '', null, undefined, UUID,
      // Forme che `Number()` accetterebbe, e aprirebbero un'altra riga.
      '1e3', '0x10', ' 7 ', '+5', '7.0', '007',
      // Oltre 2^53: si arrotonderebbe all'id accanto.
      '9007199254740993', 2 ** 53]) {
      expect(idNellaForma(v, FORME_ID.INTERO)).toBeNull()
    }
  })

  it('3) UUID: un uuid resta stringa; un numero o un testo qualunque → null', () => {
    expect(idNellaForma(UUID, FORME_ID.UUID)).toBe(UUID)
    expect(idNellaForma(UUID.toUpperCase(), FORME_ID.UUID)).toBe(UUID.toUpperCase())
    for (const v of ['42', 42, 'abc', '', null]) {
      expect(idNellaForma(v, FORME_ID.UUID)).toBeNull()
    }
  })

  it('4) forma sconosciuta → null', () => {
    expect(idNellaForma('42', 'boh')).toBeNull()
  })
})
