// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Presidio di `useServerAutocomplete` (brief-be-fe-BB-audit §7.1 F-1):
//        una risposta superata non scrive i suggerimenti, e una ricerca in
//        attesa muore quando la scheda passa in background (KeepAlive).
//        Montato perche' `onDeactivated` esiste solo dentro un componente.
// ------------------------------------------------------------
import { defineComponent, h, KeepAlive, nextTick, ref } from 'vue'
import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AUTOCOMPLETE_DEBOUNCE_MS, useServerAutocomplete } from './useServerAutocomplete'

// Una risposta axios nella forma che il default di `transform` legge.
const risposta = (results) => ({ data: { data: { results } } })

// Una promessa che il test risolve quando vuole: l'ordine di arrivo lo decide lui.
function differita() {
  let resolve
  const promise = new Promise(r => { resolve = r })
  return { promise, resolve }
}

function ospite(searchFn, options) {
  let api
  const Ospite = defineComponent({
    name: 'OspiteAutocomplete',
    setup() {
      api = useServerAutocomplete(searchFn, options)
      return () => h('div')
    },
  })
  const Altra = defineComponent({ name: 'AltraScheda', render: () => h('span') })
  const scheda = ref('ospite')
  const wrapper = mount(defineComponent({
    render: () => h(KeepAlive, null, [scheda.value === 'ospite' ? h(Ospite) : h(Altra)]),
  }))
  return { api: () => api, scheda, wrapper }
}

beforeEach(() => { vi.useFakeTimers() })
afterEach(() => { vi.useRealTimers() })

describe('useServerAutocomplete', () => {
  it('cerca dopo il ritardo, una volta sola per una raffica di tasti', async () => {
    const searchFn = vi.fn().mockResolvedValue(risposta([{ id: 1 }]))
    const { api } = ospite(searchFn)
    api().onSearch({ query: 'ro' })
    api().onSearch({ query: 'ros' })
    expect(api().loading.value).toBe(true)
    vi.advanceTimersByTime(AUTOCOMPLETE_DEBOUNCE_MS)
    await vi.runAllTimersAsync()
    expect(searchFn).toHaveBeenCalledTimes(1)
    expect(searchFn).toHaveBeenCalledWith('ros')
    expect(api().suggestions.value).toEqual([{ id: 1 }])
    expect(api().loading.value).toBe(false)
  })

  it('una risposta superata non scrive sopra quella piu\' recente', async () => {
    const lenta = differita()
    const veloce = differita()
    const searchFn = vi.fn()
      .mockReturnValueOnce(lenta.promise)
      .mockReturnValueOnce(veloce.promise)
    const { api } = ospite(searchFn)

    api().onSearch({ query: 'ros' })
    vi.advanceTimersByTime(AUTOCOMPLETE_DEBOUNCE_MS)
    api().onSearch({ query: 'rossi' })
    vi.advanceTimersByTime(AUTOCOMPLETE_DEBOUNCE_MS)
    expect(searchFn).toHaveBeenCalledTimes(2)

    veloce.resolve(risposta([{ id: 'rossi' }]))
    await vi.runAllTimersAsync()
    lenta.resolve(risposta([{ id: 'ros' }]))
    await vi.runAllTimersAsync()

    expect(api().suggestions.value).toEqual([{ id: 'rossi' }])
    expect(api().loading.value).toBe(false)
  })

  it('una ricerca in attesa muore quando la scheda passa in background', async () => {
    const searchFn = vi.fn().mockResolvedValue(risposta([{ id: 1 }]))
    const { api, scheda } = ospite(searchFn)
    api().onSearch({ query: 'ros' })
    scheda.value = 'altra'
    await nextTick()
    vi.advanceTimersByTime(AUTOCOMPLETE_DEBOUNCE_MS * 3)
    await vi.runAllTimersAsync()
    expect(searchFn).not.toHaveBeenCalled()
    expect(api().loading.value).toBe(false)
  })

  it('una query troppo corta svuota, non cerca, e scarta la risposta in volo', async () => {
    const inVolo = differita()
    const onResponse = vi.fn()
    const searchFn = vi.fn().mockReturnValueOnce(inVolo.promise)
    const { api } = ospite(searchFn, { onResponse })

    api().onSearch({ query: 'ros' })
    vi.advanceTimersByTime(AUTOCOMPLETE_DEBOUNCE_MS)
    api().onSearch({ query: 'r' })
    expect(onResponse).toHaveBeenLastCalledWith(null)
    inVolo.resolve(risposta([{ id: 'ros' }]))
    await vi.runAllTimersAsync()

    expect(api().suggestions.value).toEqual([])
    expect(api().loading.value).toBe(false)
    expect(onResponse).toHaveBeenCalledTimes(1)
  })

  it('un errore del server: nessun suggerimento e «nessun risultato»', async () => {
    const searchFn = vi.fn().mockRejectedValue(new Error('500'))
    const { api } = ospite(searchFn)
    api().onSearch({ query: 'ros' })
    vi.advanceTimersByTime(AUTOCOMPLETE_DEBOUNCE_MS)
    await vi.runAllTimersAsync()
    expect(api().suggestions.value).toEqual([])
    expect(api().noResults.value).toBe(true)
    expect(api().loading.value).toBe(false)
  })
})
