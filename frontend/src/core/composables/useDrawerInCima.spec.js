// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Presidio della pila dei drawer di `useDrawerInCima`: esce solo il
//        drawer in cima, qualunque sia l'ordine di chiusura, e uno smontato o
//        disattivato non resta nella pila.
// ------------------------------------------------------------
import { effectScope, nextTick, ref } from 'vue'
import { afterEach, describe, expect, it } from 'vitest'
import { drawerAperti, useDrawerInCima } from './useDrawerInCima'

const scopi = []
function drawer(aperto = false) {
  const visibile = ref(aperto)
  const scope = effectScope()
  const api = scope.run(() => useDrawerInCima(() => visibile.value))
  scopi.push(scope)
  return { visibile, scope, ...api }
}

afterEach(() => {
  while (scopi.length) scopi.pop().stop()
})

describe('useDrawerInCima', () => {
  it('un drawer solo e\' in cima; chiuso, non e\' in pila', async () => {
    const a = drawer(true)
    expect(a.inCima.value).toBe(true)
    a.visibile.value = false
    await nextTick()
    expect(a.inCima.value).toBe(false)
    expect(drawerAperti()).toBe(0)
  })

  it('col figlio aperto il padre non e\' in cima; chiuso il figlio, torna', async () => {
    const padre = drawer(true)
    const figlio = drawer(false)
    figlio.visibile.value = true
    await nextTick()
    expect(figlio.inCima.value).toBe(true)
    expect(padre.inCima.value).toBe(false)
    figlio.visibile.value = false
    await nextTick()
    expect(padre.inCima.value).toBe(true)
  })

  it('durante l\'evento che chiude il figlio il padre resta sotto (pila aggiornata al ridisegno)', () => {
    const padre = drawer(true)
    const figlio = drawer(true)
    figlio.visibile.value = false
    // Nessun nextTick: e' l'istante dell'ESC, in cui il padre decide.
    expect(padre.inCima.value).toBe(false)
  })

  it('un drawer smontato aperto esce dalla pila', () => {
    const padre = drawer(true)
    const figlio = drawer(true)
    figlio.scope.stop()
    expect(padre.inCima.value).toBe(true)
    expect(drawerAperti()).toBe(1)
  })

  it('disattivato e riattivato (KeepAlive) torna in cima senza duplicarsi', () => {
    const a = drawer(true)
    const b = drawer(true)
    a.esce()
    expect(b.inCima.value).toBe(true)
    a.entra()
    expect(a.inCima.value).toBe(true)
    a.entra()
    expect(drawerAperti()).toBe(2)
  })
})
