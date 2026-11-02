// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: la pagina che non c'e' piu' (2026-09-28) vista da un consumatore
//        DIRETTO di `useListaEmptyStateFetch`, senza `useListaStoreCore`: le
//        code e le liste page-based (lotti, fondi da decidere) tengono
//        `limit`/`offset` nei filtri e convertono in `buildParams`. Il rientro
//        deve arrivare anche a loro. I casi del rientro stanno in
//        `useListaStoreCore.spec.js` §la pagina che non c'e' piu'.
//
// Indice test:
//  1. endpoint a `page`/`page_size`: oltre l'ultima, rilegge l'ultima pagina reale
//  2. filtri senza `offset`: nessuna rilettura
// ------------------------------------------------------------

import { describe, it, expect, vi } from 'vitest'
import { ref } from 'vue'

import { useListaEmptyStateFetch } from './useListaEmptyStateFetch'

// Scopo: una `fetchPage` che risponde in sequenza le buste date.
function risposte(...buste) {
  const coda = [...buste]
  return vi.fn(async () => {
    const [results, count] = coda.shift() ?? [[], 0]
    return { data: { data: { results, count } } }
  })
}

describe('useListaEmptyStateFetch — la pagina che non c\'e\' piu\'', () => {
  it('endpoint a `page`/`page_size`: oltre l\'ultima, rilegge l\'ultima pagina reale', async () => {
    const filters = ref({ search: '', limit: 10, offset: 20 })
    const fetchPage = risposte([[], 15], [[{ id: 11 }], 15])
    const { fetchList, items } = useListaEmptyStateFetch({
      filters,
      alwaysFetch: true,
      fetchPage,
      buildParams: (f) => ({ page: f.offset / f.limit + 1, page_size: f.limit }),
    })
    await fetchList()
    expect(fetchPage.mock.calls.map((c) => c[0].page)).toEqual([3, 2])
    expect(filters.value.offset).toBe(10)
    expect(items.value).toEqual([{ id: 11 }])
  })

  it('filtri senza `offset`: nessuna rilettura', async () => {
    const filters = ref({ search: '' })
    const fetchPage = risposte([[], 0])
    const { fetchList } = useListaEmptyStateFetch({
      filters, alwaysFetch: true, fetchPage, buildParams: () => ({}),
    })
    await fetchList()
    expect(fetchPage).toHaveBeenCalledTimes(1)
  })
})
