// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il contratto dello store delle versioni di un template
//        (`documenti.template_versioni`, lista 88): il template nel path,
//        l'emittente del template in query sulla lista E sulla creazione —
//        il cancello di perimetro vale per ogni metodo della view.
//
// Indice test:
//  1. la lista manda il template nel path, l'emittente in query e i parametri di lista
//  2. la creazione manda l'emittente in query, non nel corpo
//  3. senza emittente la lista non legge, ed e' in attesa (padre composto)
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('../../core/composables/useTabEvents', () => ({
  useTabEvents: () => ({ emitDataChanged: vi.fn() }),
}))

vi.mock('../../core/api', () => ({
  default: {
    get: vi.fn(() => Promise.resolve({ data: { data: { results: [], count: 0 } } })),
    post: vi.fn(() => Promise.resolve({ data: { data: { id: 99 } } })),
  },
}))

import api from '../../core/api'
import { useTemplateVersioniStore } from './templateVersioni'

describe('templateVersioni store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    api.get.mockClear()
    api.post.mockClear()
  })

  it('1. template nel path, emittente in query, parametri di lista', async () => {
    const store = useTemplateVersioniStore()
    store.templateId = 12
    store.emittenteId = 5
    await store.fetchList()
    const [url, { params }] = api.get.mock.calls[0]
    expect(url).toBe('/documenti/templates/12/versioni/')
    expect(params).toMatchObject({
      emittente_fiscale_id: 5, order_by: 'versione', order_dir: 'desc', limit: 25, offset: 0,
    })
  })

  it('2. la creazione manda l\'emittente in query', async () => {
    const store = useTemplateVersioniStore()
    store.emittenteId = 5
    await store.create(12, { titolo: 'v' })
    const [url, corpo, config] = api.post.mock.calls[0]
    expect(url).toBe('/documenti/templates/12/versioni/')
    expect(corpo).toEqual({ titolo: 'v' })
    expect(config.params).toEqual({ emittente_fiscale_id: 5 })
  })

  it('3. senza emittente la lista non legge, ed e\' in attesa', async () => {
    const store = useTemplateVersioniStore()
    store.templateId = 12
    expect(await store.fetchList()).toBe(false)
    expect(api.get).not.toHaveBeenCalled()
    expect(store.attesaPadre).toBe(true)
  })
})
