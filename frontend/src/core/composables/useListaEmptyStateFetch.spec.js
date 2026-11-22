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
//  3. BE25 (2): `meta.ordinamento` diventa `ordinamentoApplicato`, non un filtro
//  4. BE25 (2): `svuota()` spegne l'ordinamento applicato insieme alle righe
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

describe('useListaEmptyStateFetch — l\'ordinamento applicato dal backend (BE25 (2))', () => {
  it('3. `meta.ordinamento` della risposta diventa `ordinamentoApplicato`, non un filtro', async () => {
    const filters = ref({ search: '', limit: 10, offset: 0, order_by: null, order_dir: null })
    const ordinamento = { order_by: 'data_documento', order_dir: 'desc', col: 'data' }
    const fetchPage = vi.fn()
      .mockResolvedValueOnce({ data: { data: { results: [], count: 0 }, meta: { ordinamento } } })
      .mockResolvedValueOnce({ data: { data: { results: [], count: 0 } } })
    const lista = useListaEmptyStateFetch({
      filters, alwaysFetch: true, fetchPage, buildParams: () => ({}),
    })
    await lista.fetchList()
    expect(lista.ordinamentoApplicato.value).toEqual(ordinamento)
    // ⛔ Non e' un clic dell'operatore: i filtri non cambiano.
    expect(filters.value.order_by).toBeNull()
    // La risposta dopo, senza ordinamento applicato, lo spegne.
    await lista.fetchList()
    expect(lista.ordinamentoApplicato.value).toBeNull()
  })

  // ⚠️ E' un fatto della risposta: va via con le sue righe. Senza, `reset()`
  //    (il logout, `userScoped`) lascia acceso il preset dell'utente di prima.
  it('4. `svuota()` spegne l\'ordinamento applicato insieme alle righe', async () => {
    const filters = ref({ search: '', limit: 10, offset: 0, order_by: null, order_dir: null })
    const ordinamento = { order_by: 'data_documento', order_dir: 'desc', col: 'data' }
    const fetchPage = vi.fn().mockResolvedValue({
      data: { data: { results: [{ id: 1 }], count: 1 }, meta: { ordinamento } },
    })
    const lista = useListaEmptyStateFetch({
      filters, alwaysFetch: true, fetchPage, buildParams: () => ({}),
    })
    await lista.fetchList()
    expect(lista.ordinamentoApplicato.value).toEqual(ordinamento)
    lista.svuota()
    expect(lista.items.value).toEqual([])
    expect(lista.ordinamentoApplicato.value).toBeNull()
  })
})
