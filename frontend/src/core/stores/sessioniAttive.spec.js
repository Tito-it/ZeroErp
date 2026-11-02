// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa lo store delle sessioni attive (`core.sessioni_attive`): la
//        lista paginata del core e `totaleAttive`, il numero su cui il
//        pannello della home si mostra, conta il badge e conferma «revoca
//        tutte» — che NON e' il `count` delle righe trovate.
//
// Indice test:
//  1. parte dal piu' recente: `order_by=data_ultimo_evento`, `order_dir=desc`
//  2. `totaleAttive` lo scrive `totale_attive` del backend, non `count`
//  3. senza `totale_attive` nell'envelope NON ripiega su `count` (con una
//     ricerca attiva `count` dice le trovate: e' il numero sbagliato)
//  4. `reset()` riporta `totaleAttive` a zero (logout)
// ------------------------------------------------------------

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('../api/sessioni', () => ({
  listSessioni: vi.fn(),
}))

import { listSessioni } from '../api/sessioni'
import { useSessioniAttiveStore } from './sessioniAttive'

const risposta = (data) => ({ data: { data } })

describe('core/sessioniAttive — lista e totale delle attive', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    listSessioni.mockReset()
  })

  it('parte dal piu\' recente', async () => {
    listSessioni.mockResolvedValue(risposta({ results: [], count: 0, totale_attive: 0 }))
    await useSessioniAttiveStore().fetchList()
    const params = listSessioni.mock.calls[0][0]
    expect(params.order_by).toBe('data_ultimo_evento')
    expect(params.order_dir).toBe('desc')
    expect(params.limit).toBe(25)
    expect(params.offset).toBe(0)
  })

  it('totaleAttive e\' totale_attive, non count', async () => {
    listSessioni.mockResolvedValue(risposta({ results: [{ jti: 'a' }], count: 1, totale_attive: 3 }))
    const store = useSessioniAttiveStore()
    await store.fetchList()
    expect(store.totalRecords).toBe(1)
    expect(store.totaleAttive).toBe(3)
  })

  it('senza totale_attive non ripiega su count', async () => {
    listSessioni.mockResolvedValue(risposta({ results: [{ jti: 'a' }, { jti: 'b' }], count: 2 }))
    const store = useSessioniAttiveStore()
    await store.fetchList()
    expect(store.totaleAttive).toBe(0)
  })

  it('reset riporta totaleAttive a zero', async () => {
    listSessioni.mockResolvedValue(risposta({ results: [{ jti: 'a' }], count: 1, totale_attive: 1 }))
    const store = useSessioniAttiveStore()
    await store.fetchList()
    store.reset()
    expect(store.totaleAttive).toBe(0)
    expect(store.items).toEqual([])
  })
})
