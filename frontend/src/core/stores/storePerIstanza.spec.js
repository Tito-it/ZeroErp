// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa `storePerIstanza`: ogni componente ha il SUO store, e lo store
//        sparisce con lui (registro di Pinia e stato).
//
// Indice test:
//  1. due componenti montati insieme: due store, stato separato
//  2. allo smontaggio lo store esce da Pinia (registro e `state`)
//  3. fuori da un componente (spec, script): uno store utilizzabile
// ------------------------------------------------------------

import { beforeEach, describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount } from '@vue/test-utils'
import { createPinia, defineStore, setActivePinia } from 'pinia'
import { ref } from 'vue'
import { storePerIstanza } from './storePerIstanza'

const useContatore = storePerIstanza('spec-contatore', (id) => defineStore(id, () => {
  const n = ref(0)
  return { n }
}))

function monta() {
  let store = null
  const wrapper = mount(defineComponent({
    setup() {
      store = useContatore()
      return () => h('div')
    },
  }))
  return { store, wrapper }
}

describe('storePerIstanza', () => {
  let pinia
  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
  })

  it('due componenti montati insieme: due store, stato separato', () => {
    const a = monta().store
    const b = monta().store
    a.n = 5
    expect(b.n).toBe(0)
    expect(a.$id).not.toBe(b.$id)
  })

  it('allo smontaggio lo store esce da Pinia', () => {
    const { store, wrapper } = monta()
    const id = store.$id
    expect(pinia._s.has(id)).toBe(true)
    wrapper.unmount()
    expect(pinia._s.has(id)).toBe(false)
    expect(id in pinia.state.value).toBe(false)
  })

  it('fuori da un componente: uno store utilizzabile', () => {
    const store = useContatore()
    store.n = 2
    expect(store.n).toBe(2)
  })
})
