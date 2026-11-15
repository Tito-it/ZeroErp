// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: `senzaCampiFermi` toglie dal PATCH i soli campi fermi.
//
// Indice test:
//  1) toglie i campi fermi, tiene gli altri (anche null e false)
//  2) non tocca il payload di partenza
//  3) nessun campo fermo: tutto il payload
// ------------------------------------------------------------
import { describe, expect, it } from 'vitest'
import { senzaCampiFermi } from './senzaCampiFermi'

const PAYLOAD = { fattore: 10, valido_dal: '2026-01-01', valido_al: null, attivo: false }
const fermo = (campo) => ['fattore', 'valido_dal'].includes(campo)

describe('senzaCampiFermi', () => {
  it('1) toglie i campi fermi, tiene gli altri (anche null e false)', () => {
    expect(senzaCampiFermi(PAYLOAD, fermo)).toEqual({ valido_al: null, attivo: false })
  })

  it('2) non tocca il payload di partenza', () => {
    const copia = { ...PAYLOAD }
    senzaCampiFermi(copia, fermo)
    expect(copia).toEqual(PAYLOAD)
  })

  it('3) nessun campo fermo: tutto il payload', () => {
    expect(senzaCampiFermi(PAYLOAD, () => false)).toEqual(PAYLOAD)
  })
})
