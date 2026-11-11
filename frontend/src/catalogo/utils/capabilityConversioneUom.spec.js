// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: `capabilityConversioneUom` legge la capability della riga, senza
//        dedurre niente dalle date.
//
// Indice test:
//  1) in creazione (riga null) tutto libero
//  2) in vigore: interruttore fermo col motivo dell'eliminazione, fine libera dalla prima data
//  3) chiusa: fine ferma col suo motivo
//  4) fail-closed: una riga senza capability non si spegne e non si chiude
//  5) chiaveMotivoUom: la chiave i18n del motivo, null senza motivo
//  6) fraseMotivoUom: la frase tradotta, il codice se la chiave manca, '' senza motivo
//  7) fermoDallaCapability: spegne solo attivo e valido_al, secondo la capability
// ------------------------------------------------------------
import { describe, expect, it } from 'vitest'
import {
  capabilityConversioneUom, chiaveMotivoUom, fermoDallaCapability, fraseMotivoUom,
} from './capabilityConversioneUom'

describe('capabilityConversioneUom', () => {
  it('1) in creazione (riga null) tutto libero', () => {
    expect(capabilityConversioneUom(null)).toEqual({
      attivoFermo: false, motivoAttivo: null, fineFerma: false, motivoFine: null, primaFine: null,
    })
  })

  it('2) in vigore: interruttore fermo col motivo dell\'eliminazione, fine libera dalla prima data', () => {
    const c = capabilityConversioneUom({
      puo_cambiare_attivo: false, motivo_non_eliminabile: 'UOM_STORIA_IN_VIGORE',
      puo_chiudersi: true, motivo_non_chiudibile: null, data_min_chiusura: '2026-11-10',
    })
    expect(c.attivoFermo).toBe(true)
    expect(c.motivoAttivo).toBe('UOM_STORIA_IN_VIGORE')
    expect(c.fineFerma).toBe(false)
    expect(c.motivoFine).toBeNull()
    expect(c.primaFine).toBeInstanceOf(Date)
    expect(c.primaFine.getDate()).toBe(10)
  })

  it('3) chiusa: fine ferma col suo motivo', () => {
    const c = capabilityConversioneUom({
      puo_cambiare_attivo: false, motivo_non_eliminabile: 'UOM_STORIA_IN_VIGORE',
      puo_chiudersi: false, motivo_non_chiudibile: 'UOM_STORIA_CHIUSA', data_min_chiusura: null,
    })
    expect(c.fineFerma).toBe(true)
    expect(c.motivoFine).toBe('UOM_STORIA_CHIUSA')
    expect(c.primaFine).toBeNull()
  })

  it('4) fail-closed: una riga senza capability non si spegne e non si chiude', () => {
    const c = capabilityConversioneUom({ id: 1 })
    expect(c.attivoFermo).toBe(true)
    expect(c.fineFerma).toBe(true)
  })

  it('5) chiaveMotivoUom: la chiave i18n del motivo, null senza motivo', () => {
    expect(chiaveMotivoUom('UOM_STORIA_IN_VIGORE')).toBe('catalogo.motivo_uom_storia_in_vigore')
    expect(chiaveMotivoUom(null)).toBeNull()
  })

  it('6) fraseMotivoUom: la frase tradotta, il codice se la chiave manca, \'\' senza motivo', () => {
    const chiavi = { 'catalogo.motivo_uom_storia_chiusa': 'È già finita' }
    const t = (k) => chiavi[k]
    const te = (k) => k in chiavi
    expect(fraseMotivoUom(t, te, 'UOM_STORIA_CHIUSA')).toBe('È già finita')
    expect(fraseMotivoUom(t, te, 'UOM_MOTIVO_NUOVO')).toBe('UOM_MOTIVO_NUOVO')
    expect(fraseMotivoUom(t, te, null)).toBe('')
  })

  it('7) fermoDallaCapability: spegne solo attivo e valido_al, secondo la capability', () => {
    const cap = { attivoFermo: true, fineFerma: false }
    expect(fermoDallaCapability(cap, 'attivo')).toBe(true)
    expect(fermoDallaCapability(cap, 'valido_al')).toBe(false)
    expect(fermoDallaCapability(cap, 'fattore')).toBe(false)
  })
})
