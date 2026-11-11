// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Presidio di `useIngressoDaQuery`: i parametri d'ingresso di una vista
//        sotto KeepAlive, applicati una volta e tolti dalla query.
// ------------------------------------------------------------

/*
Indice test eseguiti:
1) al primo ingresso il gestore riceve il valore UNA volta, e la query si pulisce
2) restando sulla pagina, una query nuova si applica (era il buco dei lotti)
3) una vista in cache NON reagisce alla query di un'altra rotta (il buco dei contratti)
4) rientrando da un'altra rotta col parametro, si applica (onActivated)
5) piu' parametri: una sola `replace`, gestori nell'ordine dichiarato
6) lo stesso deep-link, ripetuto dopo la pulizia, si applica di nuovo
*/

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { defineComponent, h, KeepAlive, nextTick, reactive, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'

const route = reactive({ name: 'vista', query: {} })
const router = { replace: vi.fn(({ query }) => { route.query = query }) }

vi.mock('vue-router', () => ({
  useRoute: () => route,
  useRouter: () => router,
}))

const { useIngressoDaQuery } = await import('./useIngressoDaQuery')

const montati = []

function montaInCache(gestori) {
  const Vista = defineComponent({
    name: 'VistaIngresso',
    setup() {
      useIngressoDaQuery({ nomeRotta: 'vista', gestori })
      return () => h('div')
    },
  })
  const visibile = ref(true)
  montati.push(mount(defineComponent({
    setup: () => () => h(KeepAlive, null, [visibile.value ? h(Vista) : h('span')]),
  })))
  return {
    async esci() { visibile.value = false; await nextTick() },
    async entra() { visibile.value = true; await flushPromises() },
  }
}

describe('useIngressoDaQuery', () => {
  beforeEach(() => {
    route.name = 'vista'
    route.query = {}
    router.replace.mockClear()
  })

  afterEach(() => {
    montati.splice(0).forEach((w) => w.unmount())
  })

  it('1) al primo ingresso il gestore riceve il valore UNA volta, e la query si pulisce', async () => {
    route.query = { open: '7', altro: 'x' }
    const open = vi.fn()
    montaInCache({ open })
    await flushPromises()
    expect(open).toHaveBeenCalledTimes(1)
    expect(open).toHaveBeenCalledWith('7')
    expect(route.query).toEqual({ altro: 'x' })
  })

  it('2) restando sulla pagina, una query nuova si applica', async () => {
    const open = vi.fn()
    montaInCache({ open })
    await flushPromises()
    route.query = { open: '8' }
    await flushPromises()
    expect(open).toHaveBeenCalledWith('8')
  })

  it('3) una vista in cache NON reagisce alla query di un\'altra rotta', async () => {
    const open = vi.fn()
    const vista = montaInCache({ open })
    await flushPromises()
    await vista.esci()
    route.name = 'altra'
    route.query = { open: '9' }
    await flushPromises()
    expect(open).not.toHaveBeenCalled()
    expect(route.query).toEqual({ open: '9' })
  })

  it('4) rientrando da un\'altra rotta col parametro, si applica', async () => {
    const open = vi.fn()
    const vista = montaInCache({ open })
    await flushPromises()
    await vista.esci()
    route.name = 'altra'
    route.query = { open: '10' }
    await flushPromises()
    route.name = 'vista'
    await vista.entra()
    expect(open).toHaveBeenCalledTimes(1)
    expect(open).toHaveBeenCalledWith('10')
  })

  it('5) piu\' parametri: una sola `replace`, gestori nell\'ordine dichiarato', async () => {
    route.query = { open: '3', competenza: '2026-10-01' }
    const ordine = []
    montaInCache({
      competenza: (v) => ordine.push(['competenza', v]),
      open: (v) => ordine.push(['open', v]),
    })
    await flushPromises()
    expect(router.replace).toHaveBeenCalledTimes(1)
    expect(route.query).toEqual({})
    expect(ordine).toEqual([['competenza', '2026-10-01'], ['open', '3']])
  })

  it('6) lo stesso deep-link, ripetuto dopo la pulizia, si applica di nuovo', async () => {
    route.query = { open: '5' }
    const open = vi.fn()
    montaInCache({ open })
    await flushPromises()
    route.query = { open: '5' }
    await flushPromises()
    expect(open).toHaveBeenCalledTimes(2)
  })
})
