// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il contratto della factory degli store «Revisioni»: il padre
//        COMPOSTO del core (documento + emittente — documento nel path,
//        emittente in query come `emittente_fiscale_id`, il
//        `lista_emittente_param` delle due view) e la rilettura dopo
//        un'azione di stato, che parte solo sul documento agganciato.
// Note: ⛔ Il caso che conta e' l'emittente mancante: nessuna fetch, perche'
//       verrebbe rifiutata (422) a chi ne vede piu' d'uno.
//
// Indice test:
//  1. senza emittente la lista non legge, ed e' in attesa
//  2. la fetch manda il documento nel path e l'emittente in query
//  3. due store dalla stessa factory non condividono stato
//  4. rileggiSeAgganciato: rilegge solo il documento agganciato
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { createRevisioniStore } from './createRevisioniStore'

const vuota = () => Promise.resolve({ data: { data: { results: [], count: 0 } } })
const fetchA = vi.fn(vuota)
const fetchB = vi.fn(vuota)
const useA = createRevisioniStore('test-revisioni-a', { fetchRevisioni: fetchA, orderBy: 'rev' })
const useB = createRevisioniStore('test-revisioni-b', {
  fetchRevisioni: fetchB, orderBy: 'revisione_numero',
})

describe('createRevisioniStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    fetchA.mockClear()
    fetchB.mockClear()
  })

  it('1. senza emittente la lista non legge, ed e\' in attesa', async () => {
    const store = useA()
    store.documentoId = 12
    expect(await store.fetchList()).toBe(false)
    expect(fetchA).not.toHaveBeenCalled()
    expect(store.attesaPadre).toBe(true)
  })

  it('2. la fetch manda il documento nel path e l\'emittente in query', async () => {
    const store = useA()
    store.documentoId = 12
    store.emittenteId = 3
    await store.fetchList()
    expect(fetchA).toHaveBeenCalledTimes(1)
    const [documentoId, params] = fetchA.mock.calls[0]
    expect(documentoId).toBe(12)
    expect(params).toMatchObject({
      emittente_fiscale_id: 3, order_by: 'rev', order_dir: 'asc', offset: 0,
    })
  })

  it('3. due store dalla stessa factory non condividono stato', async () => {
    const a = useA()
    const b = useB()
    a.documentoId = 12
    expect(b.documentoId).toBeNull()
    b.documentoId = 40
    b.emittenteId = 3
    await b.fetchList()
    expect(fetchA).not.toHaveBeenCalled()
    expect(fetchB.mock.calls[0][1]).toMatchObject({ order_by: 'revisione_numero' })
  })

  it('4. rileggiSeAgganciato: rilegge solo il documento agganciato', async () => {
    const store = useA()
    expect(store.rileggiSeAgganciato(12)).toBe(false)
    store.documentoId = 12
    store.emittenteId = 3
    expect(store.rileggiSeAgganciato(99)).toBe(false)
    expect(fetchA).not.toHaveBeenCalled()
    await store.rileggiSeAgganciato(12)
    expect(fetchA).toHaveBeenCalledTimes(1)
  })
})
