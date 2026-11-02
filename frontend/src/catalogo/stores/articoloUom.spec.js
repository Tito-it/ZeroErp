// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa lo store delle UoM operative di un articolo (2026-10-31):
//        `nonEditableFields` e' stato DELLO STORE, per istanza, e si azzera
//        col padre. Fino a quel giorno era un `ref` di modulo, condiviso fra
//        tutti i drawer e mai azzerato.
//
// Indice test:
//  1. la busta scrive `nonEditableFields`; `reset()` lo azzera
//  2. due istanze: i campi di una non compaiono nell'altra
// ------------------------------------------------------------

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('../api/catalogo', () => ({ listArticoloUom: vi.fn() }))

import { listArticoloUom } from '../api/catalogo'
import { useArticoloUomStore } from './articoloUom'

const busta = (campi) => ({ data: { data: { results: [{ id: 1 }], count: 1, non_editable_fields: campi } } })

describe('useArticoloUomStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    listArticoloUom.mockReset()
  })

  it('1. la busta scrive `nonEditableFields`; `reset()` lo azzera', async () => {
    listArticoloUom.mockResolvedValue(busta(['uom_id']))
    const store = useArticoloUomStore()
    store.padreId = 'art-1'
    await store.fetchList()
    expect(listArticoloUom).toHaveBeenCalledWith('art-1', expect.any(Object))
    expect(store.nonEditableFields).toEqual(['uom_id'])
    store.reset()
    expect(store.nonEditableFields).toEqual([])
  })

  it('2. due istanze: i campi di una non compaiono nell\'altra', async () => {
    listArticoloUom.mockResolvedValue(busta(['uom_id', 'is_base']))
    const a = useArticoloUomStore()
    const b = useArticoloUomStore()
    a.padreId = 'art-1'
    await a.fetchList()
    expect(a.nonEditableFields).toEqual(['uom_id', 'is_base'])
    expect(b.nonEditableFields).toEqual([])
    expect(a.$id).not.toBe(b.$id)
  })
})
