// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: la sostituzione della scheda oltre il limite (Tid, 2026-09-30) —
//        quale scheda si propone, e che la richiesta risponda sempre.
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { TABS } from '../core/constants'
import { useTabsStore } from './tabs'

vi.mock('../core/navigation', () => ({ DOMAIN_MENUS: {}, resolveTabIcon: () => null }))
vi.mock('../core/storage', () => ({ session: { get: () => null, set: () => {}, remove: () => {} }, STORAGE_KEYS: {} }))

function riempi(tabs, n = TABS.MAX_OPEN) {
  for (let i = 1; i <= n; i++) tabs.openTab({ path: `/d/p${i}`, domain: 'd' })
}

describe('tabs: sostituzione oltre il limite', () => {
  let tabs
  beforeEach(() => {
    setActivePinia(createPinia())
    tabs = useTabsStore()
  })

  it('sotto il limite non propone niente', () => {
    riempi(tabs, TABS.MAX_OPEN - 1)
    expect(tabs.schedaDaSostituire('/d/nuova')).toBeNull()
  })

  it('al limite propone l\'ultima in fila, non l\'attiva', () => {
    riempi(tabs)
    tabs.activateTab(tabs.tabs[2].id)
    expect(tabs.schedaDaSostituire('/d/nuova')?.path).toBe(`/d/p${TABS.MAX_OPEN}`)
  })

  it('al limite una scheda gia\' aperta si riattiva, non si sostituisce niente', () => {
    riempi(tabs)
    expect(tabs.schedaDaSostituire('/d/p3')).toBeNull()
  })

  it('openTab oltre il limite non apre: la conferma non si salta', () => {
    riempi(tabs)
    expect(tabs.openTab({ path: '/d/nuova', domain: 'd' })).toBeNull()
    expect(tabs.tabs).toHaveLength(TABS.MAX_OPEN)
  })

  it('la richiesta risponde col valore della dialog e si svuota', async () => {
    riempi(tabs)
    const promessa = tabs.chiediSostituzione(tabs.tabs.at(-1))
    expect(tabs.richiestaSostituzione?.tab.path).toBe(`/d/p${TABS.MAX_OPEN}`)
    tabs.richiestaSostituzione.rispondi(true)
    await expect(promessa).resolves.toBe(true)
    expect(tabs.richiestaSostituzione).toBeNull()
  })

  it('una seconda richiesta chiude la prima con «no», o resterebbe appesa', async () => {
    riempi(tabs)
    const prima = tabs.chiediSostituzione(tabs.tabs.at(-1))
    const seconda = tabs.chiediSostituzione(tabs.tabs.at(-1))
    await expect(prima).resolves.toBe(false)
    expect(tabs.richiestaSostituzione).not.toBeNull()
    tabs.richiestaSostituzione.rispondi(false)
    await expect(seconda).resolves.toBe(false)
  })

  it('la sostituzione tiene la nuova al posto dell\'ultima', () => {
    riempi(tabs)
    const ultima = tabs.schedaDaSostituire('/d/nuova')
    tabs.removeTab(ultima.id)
    const nuova = tabs.openTab({ path: '/d/nuova', domain: 'd' })
    expect(tabs.tabs).toHaveLength(TABS.MAX_OPEN)
    expect(tabs.tabs.at(-1).path).toBe('/d/nuova')
    expect(tabs.activeTabId).toBe(nuova.id)
  })
})
