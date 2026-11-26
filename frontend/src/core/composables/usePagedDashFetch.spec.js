// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Presidio di `usePagedDashFetch` sulla finestra EFFETTIVA (D-1 di
//        brief-be-fe-BB-audit, 2026-11-24): l'envelope e' `{count, results}`,
//        e dove il backend riporta l'offset all'ultima pagina lo dichiara in
//        `offset_effettivo`. Il paginatore ne ricava la pagina; senza il
//        campo resta la pagina chiesta, col ripiego del rientro in pagina 1.
// ------------------------------------------------------------
import { describe, expect, it, vi } from 'vitest'
import { usePagedDashFetch } from './usePagedDashFetch'

// Una risposta axios nella forma dell'envelope di successo.
const risposta = (data) => ({ data: { data } })

describe('usePagedDashFetch', () => {
  // 1. Pagina stantia sui cruscotti: il BE serve l'ultima e lo dichiara.
  it('adotta la pagina che `offset_effettivo` dichiara', async () => {
    const fetchPage = vi.fn().mockResolvedValue(
      risposta({ count: 45, results: [{ id: 41 }], offset_effettivo: 40 }),
    )
    const s = usePagedDashFetch(fetchPage)
    s.pageSize.value = 20
    s.page.value = 7
    await s.fetch()
    expect(fetchPage).toHaveBeenCalledWith({ limit: 20, offset: 120 })
    expect(s.page.value).toBe(3)
    expect(s.count.value).toBe(45)
    expect(s.items.value).toEqual([{ id: 41 }])
  })

  // 2. Endpoint senza la finestra effettiva: la pagina resta quella chiesta.
  it('senza `offset_effettivo` tiene la pagina chiesta', async () => {
    const fetchPage = vi.fn().mockResolvedValue(risposta({ count: 45, results: [{ id: 21 }] }))
    const s = usePagedDashFetch(fetchPage)
    s.pageSize.value = 20
    s.page.value = 2
    await s.fetch()
    expect(s.page.value).toBe(2)
    expect(fetchPage).toHaveBeenCalledTimes(1)
  })

  // 3. Senza clamp e oltre la fine: rientro in pagina 1 e seconda lettura.
  it('senza clamp, una pagina vuota oltre la fine rientra in pagina 1', async () => {
    const fetchPage = vi.fn()
      .mockResolvedValueOnce(risposta({ count: 5, results: [] }))
      .mockResolvedValueOnce(risposta({ count: 5, results: [{ id: 1 }] }))
    const s = usePagedDashFetch(fetchPage)
    s.pageSize.value = 20
    s.page.value = 3
    await s.fetch()
    expect(fetchPage).toHaveBeenCalledTimes(2)
    expect(fetchPage).toHaveBeenLastCalledWith({ limit: 20, offset: 0 })
    expect(s.page.value).toBe(1)
  })

  // 4. Zero righe: la finestra effettiva e' la prima.
  it('`offset_effettivo` a zero riporta in pagina 1 senza seconda lettura', async () => {
    const fetchPage = vi.fn().mockResolvedValue(risposta({ count: 0, results: [], offset_effettivo: 0 }))
    const s = usePagedDashFetch(fetchPage)
    s.page.value = 4
    await s.fetch()
    expect(s.page.value).toBe(1)
    expect(fetchPage).toHaveBeenCalledTimes(1)
  })
})
