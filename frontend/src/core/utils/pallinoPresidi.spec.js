// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Un caso per RAMO di `statoPallino` (pallino dei presidi, 2026-09-18):
//        tutto a zero, solo allarmi, solo non letti, entrambi (con l'ordine),
//        piu' il limite «testata non ancora arrivata». Sono i rami che,
//        sbagliati, non falliscono — mostrano il colore sbagliato.
// Note: ⛔ Si asseriscono CHIAVE, VALORE e SEVERITY dei segmenti, e l'ordine:
//        e' cio' che un `if` sbagliato scambia senza che niente fallisca. Il
//        composable intero (timer, 403, adozione dal pannello) vive sopra BB e
//        store gia' provati; la resa e' la parte sua, ed e' pura — e sta
//        in un modulo senza import proprio perche' la si possa provare cosi'.
// ------------------------------------------------------------
import { describe, it, expect } from 'vitest'
import { SEGMENTO_ALLARMI, SEGMENTO_NON_LETTI, statoPallino } from './pallinoPresidi'

describe('statoPallino', () => {
  it('testata non arrivata: null, niente falsi verdi al primo paint', () => {
    expect(statoPallino(null)).toBeNull()
    expect(statoPallino(undefined)).toBeNull()
  })

  it('tutto a zero: UN segmento verde con lo zero — il «visto e vuoto»', () => {
    const r = statoPallino({ totale: 21, con_righe: 0, non_letti: 0 })
    expect(r.ok).toBe(true)
    expect(r.segmenti).toEqual([
      { chiave: SEGMENTO_ALLARMI, valore: 0, severity: 'success' },
    ])
  })

  it('solo allarmi: un segmento danger col numero', () => {
    const r = statoPallino({ totale: 21, con_righe: 3, non_letti: 0 })
    expect(r.ok).toBe(false)
    expect(r.segmenti).toEqual([
      { chiave: SEGMENTO_ALLARMI, valore: 3, severity: 'danger' },
    ])
    expect(r.allarmi).toBe(3)
    expect(r.nonLetti).toBe(0)
  })

  it('solo non letti: un segmento warn — cecita\', non guasto', () => {
    const r = statoPallino({ totale: 21, con_righe: 0, non_letti: 2 })
    expect(r.ok).toBe(false)
    expect(r.segmenti).toEqual([
      { chiave: SEGMENTO_NON_LETTI, valore: 2, severity: 'warn' },
    ])
  })

  it('entrambi: due segmenti, PRIMA gli allarmi', () => {
    const r = statoPallino({ totale: 21, con_righe: 1, non_letti: 4 })
    expect(r.ok).toBe(false)
    expect(r.segmenti.map((s) => s.chiave)).toEqual([SEGMENTO_ALLARMI, SEGMENTO_NON_LETTI])
    expect(r.segmenti.map((s) => s.severity)).toEqual(['danger', 'warn'])
  })

  it('campi assenti valgono zero: una testata parziale non accende niente', () => {
    const r = statoPallino({ totale: 0 })
    expect(r.ok).toBe(true)
    expect(r.segmenti[0].valore).toBe(0)
  })
})
