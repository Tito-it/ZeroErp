// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Presidio di `vesteFermaOggi`: lo stato e l'utilizzabilita' restano
//        due domande, e «ferma» vuol dire solo «accesa ma non apre la porta».
// ------------------------------------------------------------
import { describe, expect, it } from 'vitest'
import { STATO_VESTE } from '../constants'
import { vesteFermaOggi } from './veste'

describe('vesteFermaOggi', () => {
  it('la veste accesa che oggi non apre la porta e\' ferma', () => {
    expect(vesteFermaOggi({ stato: STATO_VESTE.ATTIVO, utilizzabile: false })).toBe(true)
  })

  it('la veste accesa che apre la porta non e\' ferma', () => {
    expect(vesteFermaOggi({ stato: STATO_VESTE.ATTIVO, utilizzabile: true })).toBe(false)
  })

  it('una veste spenta non e\' «ferma»: lo dice gia\' il suo stato', () => {
    for (const stato of [STATO_VESTE.REVOCATA, STATO_VESTE.PENDING, STATO_VESTE.NON_SPEDITO, STATO_VESTE.DISATTIVO]) {
      expect(vesteFermaOggi({ stato, utilizzabile: false })).toBe(false)
    }
  })

  it('senza la chiave del DB non si inventa un rifiuto', () => {
    expect(vesteFermaOggi({ stato: STATO_VESTE.ATTIVO })).toBe(false)
    expect(vesteFermaOggi(null)).toBe(false)
  })
})
