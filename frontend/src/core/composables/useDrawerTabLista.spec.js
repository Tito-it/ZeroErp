// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il legame col PADRE COMPOSTO di `useDrawerTabLista`
//        (2026-09-27, regola del 2): un oggetto di getter, una parte per
//        chiave, seguito da un watch multi-sorgente. Lo store e'
//        `useListaStoreCore` vero, con una `fetchPage` spia: si guarda cosa
//        arriva sul filo.
// Note: ⛔ I casi che contano sono due. Il padre A META' (documento aperto,
//       emittente non ancora arrivato): nessuna lettura, e lo store in
//       `attesaPadre`. E il RIDISEGNO con gli stessi valori: nessuna seconda
//       fetch — la ragione per cui prima si componeva una chiave-stringa.
//
// Indice test:
//  1. padre completo: le parti vanno nello store e la lista legge una volta
//  2. padre a meta': nessuna lettura, attesa dichiarata; l'ultima parte legge
//  3. un getter rivalutato con gli stessi valori non rilegge
//  4. padre vuoto: `reset()`, niente attesa
//  5. la forma semplice (`parentId` + `parentField`) resta com'era
//  6. nuovo padre completo: righe del precedente via SUBITO, filtri e ordine
//     di partenza, il passo della pagina resta
//  7. lista sospesa dal cancello: quando la config lo abbassa, la lista legge
// ------------------------------------------------------------

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick, reactive } from 'vue'
import { mount } from '@vue/test-utils'
import { createPinia, defineStore, setActivePinia } from 'pinia'

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}))
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: (k) => k }) }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: vi.fn() }) }))
// jsdom non ha `matchMedia`, che `useSearchTable` legge per le righe compatte.
window.matchMedia ??= () => ({
  matches: false, addEventListener: () => {}, removeEventListener: () => {},
})

import { useDrawerTabLista } from './useDrawerTabLista'
import { useListaStoreCore } from './useListaStoreCore'

const spia = () => vi.fn(async () => ({ data: { data: { results: [{ id: 1 }], count: 1 } } }))

// Scopo: uno store Pinia sul core col padre documento + emittente.
function creaStore(fetchPage, opzioni = {}) {
  return defineStore(`tab-lista-spec-${Math.random()}`, () => useListaStoreCore({
    fetchPage, startsEmpty: false, parentField: 'documentoId',
    emittenteParam: 'emittente_fiscale_id', ...opzioni,
  }))()
}

// Scopo: monta il BB dentro un componente, con le «props» in un reactive che
//        il test cambia come farebbe il drawer.
function monta(store, props, opzioni) {
  let esposto = null
  mount(defineComponent({
    setup() {
      esposto = useDrawerTabLista(store, opzioni(props))
      return () => h('div')
    },
  }))
  return esposto
}

const padreDocumento = (p) => ({
  parentId: {
    documentoId: () => p.documentoId,
    emittenteId: () => p.emittenteFiscaleId,
  },
})

describe('useDrawerTabLista — il padre composto', () => {
  beforeEach(() => { setActivePinia(createPinia()) })

  it('padre completo: le parti vanno nello store e la lista legge una volta', async () => {
    const fetchPage = spia()
    const store = creaStore(fetchPage)
    monta(store, reactive({ documentoId: 12, emittenteFiscaleId: 3 }), padreDocumento)
    await nextTick()
    expect(store.documentoId).toBe(12)
    expect(store.emittenteId).toBe(3)
    expect(fetchPage).toHaveBeenCalledTimes(1)
    expect(fetchPage.mock.calls[0][0]).toBe(12)
    expect(fetchPage.mock.calls[0][1]).toMatchObject({ emittente_fiscale_id: 3 })
  })

  it('padre a meta\': nessuna lettura, attesa dichiarata; l\'ultima parte legge', async () => {
    const fetchPage = spia()
    const store = creaStore(fetchPage)
    const props = reactive({ documentoId: 12, emittenteFiscaleId: null })
    monta(store, props, padreDocumento)
    await nextTick()
    expect(fetchPage).not.toHaveBeenCalled()
    expect(store.attesaPadre).toBe(true)
    // Arriva il dettaglio: l'emittente c'e', e la lettura parte da sola.
    props.emittenteFiscaleId = 3
    await nextTick()
    expect(store.attesaPadre).toBe(false)
    expect(fetchPage).toHaveBeenCalledTimes(1)
    expect(fetchPage.mock.calls[0][1]).toMatchObject({ emittente_fiscale_id: 3 })
  })

  it('un getter rivalutato con gli stessi valori non rilegge', async () => {
    const fetchPage = spia()
    const store = creaStore(fetchPage)
    // `giro` e' letto dal getter: cambiarlo lo fa rivalutare, coi valori uguali.
    const props = reactive({ documentoId: 12, emittenteFiscaleId: 3, giro: 0 })
    monta(store, props, (p) => ({
      parentId: {
        documentoId: () => (p.giro >= 0 ? p.documentoId : null),
        emittenteId: () => p.emittenteFiscaleId,
      },
    }))
    await nextTick()
    props.giro += 1
    await nextTick()
    props.giro += 1
    await nextTick()
    expect(fetchPage).toHaveBeenCalledTimes(1)
  })

  it('padre vuoto: `reset()`, niente attesa', async () => {
    const fetchPage = spia()
    const store = creaStore(fetchPage)
    const props = reactive({ documentoId: 12, emittenteFiscaleId: 3 })
    monta(store, props, padreDocumento)
    await nextTick()
    await Promise.resolve()
    expect(store.items).toHaveLength(1)
    // Drawer chiuso: il documento torna `null`, l'emittente del dettaglio
    // precedente puo' restare — non e' un'attesa, e' nessun padre.
    props.documentoId = null
    await nextTick()
    expect(store.items).toEqual([])
    expect(store.documentoId).toBeNull()
    expect(store.attesaPadre).toBe(false)
    expect(fetchPage).toHaveBeenCalledTimes(1)
  })

  it('la forma semplice (`parentId` + `parentField`) resta com\'era', async () => {
    const fetchPage = spia()
    const store = creaStore(fetchPage, { emittenteParam: null, parentField: 'fatturaId' })
    const props = reactive({ fatturaId: 40 })
    monta(store, props, (p) => ({ parentId: () => p.fatturaId, parentField: 'fatturaId' }))
    await nextTick()
    expect(store.fatturaId).toBe(40)
    expect(fetchPage.mock.calls[0][0]).toBe(40)
    props.fatturaId = 41
    await nextTick()
    expect(fetchPage).toHaveBeenCalledTimes(2)
    expect(fetchPage.mock.calls[1][0]).toBe(41)
  })

  it('nuovo padre completo: righe del precedente via subito, filtri e ordine di partenza', async () => {
    let risolvi = null
    const fetchPage = vi.fn()
      .mockResolvedValueOnce({ data: { data: { results: [{ id: 1 }], count: 1 } } })
      .mockImplementationOnce(() => new Promise((r) => { risolvi = r }))
    const store = creaStore(fetchPage, { orderBy: 'rev', filterDefaults: { attivo: null } })
    const props = reactive({ documentoId: 12, emittenteFiscaleId: 3 })
    monta(store, props, padreDocumento)
    await nextTick()
    await Promise.resolve()
    expect(store.items).toHaveLength(1)
    store.filters.attivo = true
    store.filters.order_by = 'data'
    store.filters.limit = 10
    // Altro documento, stesso emittente: il padre resta completo.
    props.documentoId = 13
    await nextTick()
    // La risposta di 13 non e' ancora arrivata: le righe di 12 non ci sono piu'.
    expect(store.items).toEqual([])
    expect(store.filters.attivo).toBeNull()
    expect(store.filters.order_by).toBe('rev')
    expect(store.filters.limit).toBe(10)
    expect(fetchPage.mock.calls[1][0]).toBe(13)
    risolvi({ data: { data: { results: [{ id: 2 }], count: 1 } } })
  })

  it('lista sospesa dal cancello: quando la config lo abbassa, la lista legge', async () => {
    const fetchPage = spia()
    const store = creaStore(fetchPage)
    // Il tab si e' montato prima del dettaglio: la prima config (senza
    // emittente) ha alzato il cancello, e la fetch del padre completo e'
    // uscita senza chiamare.
    store.fetchSospesa = true
    const tab = monta(store, reactive({ documentoId: 12, emittenteFiscaleId: 3 }), padreDocumento)
    await nextTick()
    expect(fetchPage).not.toHaveBeenCalled()
    // La config riletta con l'emittente abbassa il cancello.
    tab.onConfigLoaded({ richiede_scelta_emittente: false })
    await nextTick()
    expect(store.fetchSospesa).toBe(false)
    expect(fetchPage).toHaveBeenCalledTimes(1)
  })
})
