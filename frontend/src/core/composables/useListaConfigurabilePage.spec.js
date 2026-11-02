// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa cio' che `onConfigLoaded` scrive nello store dalla
//        configurazione risolta della lista: la SOGLIA della ricerca libera
//        (`ricerca_min_caratteri`, brief-db-be-fe-ricerca-soglia-per-lista §5),
//        e la ricarica quando la soglia vera cambia cio' che si manda.
// Note: ⚠️ Il caso che conta e' il deep-link (`?search=KG` su unita' di
//       misura): la prima fetch parte INSIEME alla configurazione, con la
//       soglia di ripiego, e senza ricarica la lista resterebbe intera finche'
//       l'operatore non preme un altro tasto. Lo store e' `useListaStoreCore`
//       vero, con una `fetchPage` spia: si guarda cosa arriva sul filo.
//
// Indice test:
//  1. la soglia della config va nello store; un valore non valido e' `null`
//  2. deep-link corto sotto la soglia di progetto: la config a 1 ricarica,
//     e la seconda fetch manda il termine
//  3. nessun termine in casella: la soglia cambia, ma non si ricarica
//  4. config ripetuta con la stessa soglia: nessuna ricarica
//  5. soglia e pagina cambiano insieme: UNA fetch sola
//  — il watcher della casella (`useSearchTable`) —
//  6. lista a video col filtro data (i preventivi): «a» e «ab» non ricaricano
//     e non tornano a pagina 1; «abc» cerca, da pagina 1
// ------------------------------------------------------------

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { createPinia, defineStore, setActivePinia } from 'pinia'

const query = { value: {} }
vi.mock('vue-router', () => ({
  useRoute: () => ({ query: query.value }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}))
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: (k) => k }) }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: vi.fn() }) }))
// jsdom non ha `matchMedia`, che `useSearchTable` legge per le righe compatte.
window.matchMedia ??= () => ({
  matches: false, addEventListener: () => {}, removeEventListener: () => {},
})

import { useListaConfigurabilePage } from './useListaConfigurabilePage'
import { useListaStoreCore } from './useListaStoreCore'

// Scopo: uno store Pinia sul core, con una `fetchPage` spia (envelope vuoto).
function creaStore(fetchPage) {
  return defineStore(`lista-spec-${Math.random()}`, () => useListaStoreCore({
    fetchPage, startsEmpty: false,
  }))()
}

// Scopo: monta il composable dentro un componente (lifecycle veri) e ne
//        restituisce `onConfigLoaded`.
function monta(store) {
  let pagina
  mount(defineComponent({
    setup() {
      pagina = useListaConfigurabilePage(store, {})
      return () => h('div')
    },
  }))
  return pagina
}

const spia = () => vi.fn(async () => ({ data: { data: { results: [], count: 0 } } }))
const config = (extra = {}) => ({ ricerca_full: true, pagina_dimensione: null, ...extra })

describe('useListaConfigurabilePage — la soglia della ricerca dalla configurazione', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    query.value = {}
  })

  it('la soglia della config va nello store; un valore non valido e null', () => {
    const store = creaStore(spia())
    const { onConfigLoaded } = monta(store)
    onConfigLoaded(config({ ricerca_min_caratteri: 1 }))
    expect(store.ricercaMinCaratteri).toBe(1)
    for (const cattivo of [0, -1, '1', 1.5, null, undefined]) {
      onConfigLoaded(config({ ricerca_min_caratteri: cattivo }))
      expect(store.ricercaMinCaratteri).toBeNull()
    }
  })

  it('deep-link corto: la config a 1 ricarica, e la fetch manda il termine', async () => {
    query.value = { search: 'KG' }
    const fetchPage = spia()
    const store = creaStore(fetchPage)
    const { onConfigLoaded } = monta(store)
    // La prima fetch, partita prima della config: soglia di ripiego, niente search.
    await store.fetchList()
    expect(fetchPage.mock.calls[0][0]).not.toHaveProperty('search')
    onConfigLoaded(config({ ricerca_min_caratteri: 1 }))
    await vi.waitFor(() => expect(fetchPage).toHaveBeenCalledTimes(2))
    expect(fetchPage.mock.calls[1][0].search).toBe('KG')
  })

  it('nessun termine in casella: la soglia cambia, ma non si ricarica', async () => {
    const fetchPage = spia()
    const store = creaStore(fetchPage)
    const { onConfigLoaded } = monta(store)
    await store.fetchList()
    onConfigLoaded(config({ ricerca_min_caratteri: 1 }))
    expect(store.ricercaMinCaratteri).toBe(1)
    expect(fetchPage).toHaveBeenCalledTimes(1)
  })

  it('config ripetuta con la stessa soglia: nessuna ricarica', async () => {
    query.value = { search: 'KG' }
    const fetchPage = spia()
    const store = creaStore(fetchPage)
    const { onConfigLoaded } = monta(store)
    onConfigLoaded(config({ ricerca_min_caratteri: 1 }))
    await vi.waitFor(() => expect(fetchPage).toHaveBeenCalledTimes(1))
    onConfigLoaded(config({ ricerca_min_caratteri: 1 }))
    expect(fetchPage).toHaveBeenCalledTimes(1)
  })

  it('soglia e pagina cambiano insieme: una fetch sola', async () => {
    query.value = { search: 'KG' }
    const fetchPage = spia()
    const store = creaStore(fetchPage)
    const { onConfigLoaded } = monta(store)
    await store.fetchList()
    onConfigLoaded(config({ ricerca_min_caratteri: 1, pagina_dimensione: 50 }))
    await vi.waitFor(() => expect(fetchPage).toHaveBeenCalledTimes(2))
    expect(fetchPage.mock.calls[1][0]).toMatchObject({ search: 'KG', limit: 50 })
  })
})

describe('useListaConfigurabilePage — il tasto che non cambia la richiesta', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    query.value = {}
    vi.useFakeTimers()
  })
  afterEach(() => vi.useRealTimers())

  // Scopo: scrive nella casella e fa scadere il debounce.
  async function digita(pagina, testo) {
    pagina.searchText.value = testo
    await nextTick()
    await vi.runAllTimersAsync()
  }

  // ⭐ Il caso di Tid (2026-09-26): i preventivi partono col filtro data di
  //    default, e «a»/«ab» ricaricavano la stessa lista pesante senza `search`.
  it('lista col filtro data: 1-2 caratteri non ricaricano ne tornano a pagina 1', async () => {
    const fetchPage = spia()
    const store = defineStore('lista-spec-preventivi', () => useListaStoreCore({
      fetchPage, filterDefaults: { data_da: '2026-07-01' }, gateKeys: ['data_da'],
    }))()
    const pagina = monta(store)
    await store.fetchList()
    store.filters.offset = 50
    const prima = fetchPage.mock.calls.length

    await digita(pagina, 'a')
    await digita(pagina, 'ab')
    expect(fetchPage).toHaveBeenCalledTimes(prima)
    expect(store.filters.search).toBe('ab')
    expect(store.filters.offset).toBe(50)

    await digita(pagina, 'abc')
    expect(fetchPage).toHaveBeenCalledTimes(prima + 1)
    expect(fetchPage.mock.calls.at(-1)[0]).toMatchObject({ search: 'abc', offset: 0 })
  })
})
