// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il GIRO DI SCRITTURA di `createCrudStore` — l'aggancio
//        post-write `afterWrite` (2026-09-18, regola del 2: `unitaMisura` e
//        `uomTipi` invalidano la cache del lookup a ogni write) e il suo
//        ordine rispetto a `emitDataChanged`: prima si pulisce, poi si avvisa.
//        E il passthrough delle opzioni del core, che fino a quel giorno
//        perdeva `limit` in silenzio.
// Note: la factory produce uno store Pinia, quindi serve una Pinia attiva; le
//       api sono spie che rispondono l'envelope standard. Il primo presidio
//       della factory.
//
// Indice test:
//  1. `afterWrite` riceve (id, azione) su create, update e azione extra
//  2. `afterWrite` viene PRIMA di `emitDataChanged`
//  3. senza `afterWrite` il giro e' quello di sempre (solo l'evento)
//  4. le opzioni del core passano tal quali (`misura`, `ricercaCorta`)
// ------------------------------------------------------------

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { createCrudStore } from './createCrudStore'
import { useTabEvents } from '../composables/useTabEvents'
import { USO_MISURA, misuraDefault } from '../misurePagina'

// Scopo: una api finta che risponde `{ data: { data } }` come axios.
const risponde = (data) => vi.fn(async () => ({ data: { data } }))

let contatore = 0
// Scopo: un id di store diverso per test — Pinia tiene le definizioni per id.
function storeDiProva(opzioni) {
  contatore += 1
  return createCrudStore(`prova-crud-${contatore}`, {
    api: {
      list: risponde({ results: [], count: 0 }),
      create: risponde({ id: 7 }),
      update: risponde({ id: 7 }),
    },
    tabEntity: 'prova',
    ...opzioni,
  })()
}

describe('createCrudStore — il giro di scrittura', () => {
  beforeEach(() => { setActivePinia(createPinia()) })

  it('afterWrite riceve (id, azione) su create, update e azione extra', async () => {
    const afterWrite = vi.fn()
    const store = storeDiProva({
      afterWrite,
      extraActions: { disattiva: risponde({ id: 7 }) },
    })
    await store.create({})
    await store.update(7, {})
    await store.disattiva(7)
    expect(afterWrite.mock.calls).toEqual([[7, 'create'], [7, 'update'], [7, 'disattiva']])
  })

  // ⚠️ L'ordine e' il contratto: chi ascolta l'evento ricarica, e deve trovare
  //    la cache gia' invalidata — al contrario ricaricherebbe dalla cache vecchia.
  it('afterWrite viene PRIMA di emitDataChanged', async () => {
    const sequenza = []
    const { onDataChanged } = useTabEvents()
    const stacca = onDataChanged((ev) => sequenza.push(`evento:${ev.entityType}:${ev.entityId}`))
    const store = storeDiProva({ afterWrite: (id, azione) => sequenza.push(`afterWrite:${azione}:${id}`) })
    await store.update(7, {})
    stacca()
    expect(sequenza).toEqual(['afterWrite:update:7', 'evento:prova:7'])
  })

  it('senza afterWrite il giro e quello di sempre: solo l evento', async () => {
    const ricevuti = []
    const { onDataChanged } = useTabEvents()
    const stacca = onDataChanged((ev) => ricevuti.push(ev.entityId))
    const store = storeDiProva()
    await store.create({})
    stacca()
    expect(ricevuti).toEqual([7])
  })

  // 🔴 Fino al 2026-09-18 la factory ricopiava sei nomi a mano e `limit` — nato
  //    nel core la mattina stessa — non arrivava: lo store lo scriveva, il BB lo
  //    ignorava, nessun errore.
  it('le opzioni del core passano tal quali', () => {
    const store = storeDiProva({ misura: USO_MISURA.COMPATTA, orderBy: 'codice' })
    expect(store.filters.limit).toBe(misuraDefault(USO_MISURA.COMPATTA))
    expect(store.filters.limit).not.toBe(misuraDefault(USO_MISURA.PAGINA))
    expect(store.filters.order_by).toBe('codice')
    // E il core si riespone INTERO: `paramsFiltro` e `fetchSospesa` compresi.
    expect(typeof store.paramsFiltro).toBe('function')
    expect(store.fetchSospesa).toBe(false)
  })
})
