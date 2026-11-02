// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il contratto di `useSelezioneConValore` — la meta' «valore per
//        riga» delle macchine di selezione (Q-1 del piano D19, 2026-09-17):
//        la proposta semina, l'override resta, chi esce dalla selezione esce
//        dalla mappa, lo zero e il negativo NON si scartano (solo `null`), e
//        la mappa si sostituisce (i computed vedono ogni cambio).
// Note: e' un composable PURO (nessuna API, nessun i18n): si prova nudo.
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'

import { useSelezioneConValore } from './useSelezioneConValore'

const riga = (id, spazio) => ({ scadenza_id: id, spazio })

function fabbrica() {
  return useSelezioneConValore({ rowKey: 'scadenza_id', proponi: (r) => r.spazio })
}

describe('useSelezioneConValore — la mappa chiave → valore', () => {
  it('semina le righe scelte con la proposta', () => {
    const v = fabbrica()
    v.sincronizza([riga(1, 400), riga(2, -20)])
    expect(v.valoreDi(1)).toBe(400)
    expect(v.valoreDi(2)).toBe(-20)
  })

  it('l\'override dell\'operatore SOPRAVVIVE a una nuova sincronizzazione', () => {
    const v = fabbrica()
    v.sincronizza([riga(1, 400)])
    v.imposta(1, 150)
    v.sincronizza([riga(1, 400), riga(3, 10)])
    expect(v.valoreDi(1)).toBe(150)
    expect(v.valoreDi(3)).toBe(10)
  })

  it('chi esce dalla selezione esce dalla mappa, e se rientra riparte dalla proposta', () => {
    const v = fabbrica()
    v.sincronizza([riga(1, 400)])
    v.imposta(1, 150)
    v.sincronizza([])
    expect(v.valoreDi(1)).toBeNull()
    v.sincronizza([riga(1, 400)])
    expect(v.valoreDi(1)).toBe(400)
  })

  it('una sincronizzazione senza cambi non sostituisce la mappa', () => {
    const v = fabbrica()
    v.sincronizza([riga(1, 400)])
    const prima = v.valori.value
    v.sincronizza([riga(1, 400)])
    expect(v.valori.value).toBe(prima)
  })

  it('`incompleti` elenca le righe senza valore, ed e\' cio\' che tiene spento il Salva', () => {
    const v = fabbrica()
    v.sincronizza([riga(1, 400), riga(2, null)])
    expect(v.incompleti.value).toEqual(['2'])
    v.imposta(2, 5)
    expect(v.incompleti.value).toEqual([])
    v.imposta(1, null)
    expect(v.incompleti.value).toEqual(['1'])
  })

  it('`buildPayload` scarta solo `null`: lo zero e il negativo sono valori scritti', () => {
    const v = fabbrica()
    const righe = [riga(1, 400), riga(2, -20), riga(3, null), riga(4, 0)]
    v.sincronizza(righe)
    const payload = v.buildPayload(righe, (r, val) => ({ scadenza_id: r.scadenza_id, importo: val }))
    expect(payload).toEqual([
      { scadenza_id: 1, importo: 400 },
      { scadenza_id: 2, importo: -20 },
      { scadenza_id: 4, importo: 0 },
    ])
  })

  it('`includi` e\' del chiamante: chi vuole scartare lo zero lo dice', () => {
    const v = fabbrica()
    const righe = [riga(1, 400), riga(4, 0)]
    v.sincronizza(righe)
    const payload = v.buildPayload(righe, (r, val) => val, { includi: (val) => val != null && val !== 0 })
    expect(payload).toEqual([400])
  })

  it('`riproponi` torna alla proposta della riga', () => {
    const v = fabbrica()
    v.sincronizza([riga(1, 400)])
    v.imposta(1, 7)
    v.riproponi(riga(1, 400))
    expect(v.valoreDi(1)).toBe(400)
  })
})
