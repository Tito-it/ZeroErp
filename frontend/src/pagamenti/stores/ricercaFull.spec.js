// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa la RICERCA LIBERA dei quattro store di pagamenti scritti a mano
//        (distinte, coda righe, rate fuori capienza, eccedenze — brief-be-
//        ricerca-full-liste-residue §5.3): la `search` viaggia con la regola di
//        `useListaStoreCore.paramsFiltro` (termine `trim`, da 3 caratteri), e
//        lo store dichiara `ricercaFull` (`null` alla nascita), la chiave che
//        `FiltriLista` legge per rendere o no la casella.
// Note: ⚠️ Fino al 2026-09-24 la chiave `search` c'era ma non viaggiava: la
//       casella a video avrebbe cercato senza che la lista cambiasse, e nessun
//       test l'avrebbe visto. Le api sono spie che rispondono l'envelope vuoto.
//
// Indice test (per ciascuno dei quattro store):
//  1. `ricercaFull` nasce `null`
//  2. 1-2 caratteri: la fetch parte, senza `search`
//  3. da 3 caratteri: `search` viaggia, trimmata
//  4. `ricercaMinCaratteri` nasce `null`; messa a 1 (dalla configurazione
//     della lista) un carattere viaggia — il `buildParams` scritto a mano
//     riceve la soglia dal BB di stato
// ------------------------------------------------------------

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('../api/pagamenti', () => {
  const vuota = () => vi.fn(async () => ({ data: { data: { results: [], count: 0 } } }))
  return {
    listDistinte: vuota(),
    listCodaRighe: vuota(),
    listRateFuoriCapienza: vuota(),
    listEccedenze: vuota(),
  }
})

import * as api from '../api/pagamenti'
import { useDistinteStore } from './distinte'
import { useCodaRigheStore } from './codaRighe'
import { useRateFuoriCapienzaStore } from './rateFuoriCapienza'
import { useEccedenzeStore } from './eccedenze'

const CASI = [
  ['distinte', useDistinteStore, 'listDistinte'],
  ['codaRighe', useCodaRigheStore, 'listCodaRighe'],
  ['rateFuoriCapienza', useRateFuoriCapienzaStore, 'listRateFuoriCapienza'],
  ['eccedenze', useEccedenzeStore, 'listEccedenze'],
]

describe.each(CASI)('pagamenti/%s — la ricerca libera', (_nome, useStore, fn) => {
  beforeEach(() => {
    setActivePinia(createPinia())
    api[fn].mockClear()
  })

  it('ricercaFull nasce null', () => {
    expect(useStore().ricercaFull).toBeNull()
  })

  it('1-2 caratteri: la fetch parte, senza search', async () => {
    const store = useStore()
    store.filters.search = ' ab '
    await store.fetchList()
    expect(api[fn]).toHaveBeenCalledTimes(1)
    expect(api[fn].mock.calls[0][0]).not.toHaveProperty('search')
  })

  it('da 3 caratteri: search viaggia, trimmata', async () => {
    const store = useStore()
    store.filters.search = '  abc  '
    await store.fetchList()
    expect(api[fn].mock.calls[0][0].search).toBe('abc')
  })

  it('la soglia e della lista: a 1 un carattere viaggia', async () => {
    const store = useStore()
    expect(store.ricercaMinCaratteri).toBeNull()
    store.ricercaMinCaratteri = 1
    store.filters.search = ' K '
    await store.fetchList()
    expect(api[fn].mock.calls[0][0].search).toBe('K')
  })
})
