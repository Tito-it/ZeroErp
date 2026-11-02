// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il contratto dello store della lista `pratiche.flussi`: il
//        padre COMPOSTO del core (pratica + emittente) — la pratica nel path,
//        l'emittente in query come `emittente_fiscale_id`, cioe' il
//        `lista_emittente_param` della view.
// Note: ⛔ Il caso che conta e' l'emittente mancante: nessuna fetch, perche'
//       verrebbe rifiutata (422) a chi ne vede piu' d'uno — e la lista e' in
//       `attesaPadre`, non «vuota».
//
// Indice test:
//  1. senza emittente la lista non legge, ed e' in attesa
//  2. la fetch manda la pratica nel path e l'emittente in query, coi parametri di lista
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('../api/pratiche-api', () => ({
  listFlussi: vi.fn(() => Promise.resolve({ data: { data: { results: [], count: 0 } } })),
}))

import { listFlussi } from '../api/pratiche-api'
import { usePraticaFlussiStore } from './praticaFlussi'

describe('praticaFlussi store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    listFlussi.mockClear()
  })

  it('1. senza emittente la lista non legge, ed e\' in attesa', async () => {
    const store = usePraticaFlussiStore()
    store.praticaId = 12
    expect(await store.fetchList()).toBe(false)
    expect(listFlussi).not.toHaveBeenCalled()
    expect(store.attesaPadre).toBe(true)
  })

  it('2. la fetch manda la pratica nel path e l\'emittente in query', async () => {
    const store = usePraticaFlussiStore()
    store.praticaId = 12
    store.emittenteId = 3
    await store.fetchList()
    expect(listFlussi).toHaveBeenCalledTimes(1)
    const [praticaId, params] = listFlussi.mock.calls[0]
    expect(praticaId).toBe(12)
    expect(params).toMatchObject({
      emittente_fiscale_id: 3, order_by: 'sequenza', order_dir: 'asc', offset: 0,
    })
  })
})
