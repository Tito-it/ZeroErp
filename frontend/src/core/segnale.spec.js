// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa le tre protezioni del segnale (`core/segnale.js`), che prima
//        dell'estrazione stavano in una sola delle due copie: iterazione su
//        una copia, ascoltatori isolati, de-registrazione allo smontaggio.
//        Fissa anche il consumatore `adottaTestataPresidi`, che non aveva test.
//
// Indice test:
//  1. consegna gli argomenti a tutti gli ascoltatori
//  2. chiama solo gli ascoltatori vivi al momento dell'emissione
//  3. un ascoltatore che solleva non ferma gli altri
//  4. dentro uno scope si de-registra da solo allo smontaggio
//  5. adottaTestataPresidi: consegna la testata, ignora il null
// ------------------------------------------------------------

import { describe, expect, it, vi } from 'vitest'
import { effectScope } from 'vue'
import { creaSegnale } from './segnale'

// Il pallino leggerebbe la testata dal client HTTP (che in node non ha
// `localStorage`) e avvierebbe un timer: qui interessa solo l'adozione.
vi.mock('./api/presidi', () => ({ getPresidiConteggi: vi.fn() }))
vi.mock('./composables/useRefreshPeriodico', () => ({
  useRefreshPeriodico: () => ({ avvia: vi.fn(), ferma: vi.fn() }),
}))

describe('creaSegnale', () => {
  it('consegna gli argomenti a tutti gli ascoltatori', () => {
    const s = creaSegnale('prova')
    const ricevuti = []
    s.ascolta(x => ricevuti.push(['a', x]))
    s.ascolta(x => ricevuti.push(['b', x]))
    s.emetti(7)
    expect(ricevuti).toEqual([['a', 7], ['b', 7]])
  })

  it('chiama solo gli ascoltatori vivi al momento dell\'emissione', () => {
    const s = creaSegnale('prova')
    let chiamate = 0
    // Si ri-registra a ogni chiamata, come un componente che smonta e rimonta:
    // sul Set vivo il ciclo non finirebbe mai.
    const rimonta = () => {
      chiamate++
      if (chiamate > 10) throw new Error('ciclo aperto')
      via()
      via = s.ascolta(rimonta)
    }
    let via = s.ascolta(rimonta)
    const avviso = vi.spyOn(console, 'warn').mockImplementation(() => {})
    s.emetti()
    avviso.mockRestore()
    expect(chiamate).toBe(1)
  })

  it('un ascoltatore che solleva non ferma gli altri', () => {
    const s = creaSegnale('prova')
    const avviso = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const chiamati = []
    s.ascolta(() => { throw new Error('rotto') })
    s.ascolta(() => chiamati.push('b'))
    expect(() => s.emetti()).not.toThrow()
    expect(chiamati).toEqual(['b'])
    avviso.mockRestore()
  })

  it('dentro uno scope si de-registra da solo allo smontaggio', () => {
    const s = creaSegnale('prova')
    const chiamati = []
    const scope = effectScope()
    scope.run(() => s.ascolta(() => chiamati.push('x')))
    s.emetti()
    scope.stop()
    s.emetti()
    expect(chiamati).toEqual(['x'])
  })
})

describe('adottaTestataPresidi', () => {
  it('consegna la testata, ignora il null', async () => {
    const { adottaTestataPresidi, usePresidiPolling } = await import('./composables/usePresidiPolling')
    const scope = effectScope()
    const pallino = scope.run(() => usePresidiPolling())
    adottaTestataPresidi({ totale: 3 })
    expect(pallino.testata.value).toEqual({ totale: 3 })
    adottaTestataPresidi(null)
    expect(pallino.testata.value).toEqual({ totale: 3 })
    scope.stop()
    adottaTestataPresidi({ totale: 9 })
    expect(pallino.testata.value).toEqual({ totale: 3 })
  })
})
