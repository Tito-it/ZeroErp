// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: La pagina d'arrivo di un dominio (`getDefaultRoute`) e i preferiti
//        salvati su voci poi ritirate dal menu (Amm. Software, «Permessi»
//        ritirata il 2026-10-06: il dominio si apriva su «non trovato»).
//
// Indice test:
//   1) senza preferiti → la prima voce del menu (Amm. Software → Accessi)
//   2) un preferito su una voce ritirata si scarta al caricamento
//   3) un preferito valido resta, e vince sulla prima voce
// ------------------------------------------------------------

import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { domainFavoriteKey, userScopedKey } from '../core/storage'
import { useNavigationStore } from './navigation'

const UTENTE = 7
const salvaPreferiti = (dominio, paths) =>
  localStorage.setItem(userScopedKey(domainFavoriteKey(dominio), UTENTE), JSON.stringify(paths))

describe("pagina d'arrivo di un dominio", () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('1) senza preferiti → la prima voce del menu', () => {
    const nav = useNavigationStore()
    nav.syncUserFavorites(UTENTE)
    expect(nav.getDefaultRoute('amm-software')).toBe('/amm-software/accessi')
  })

  it('2) un preferito su una voce ritirata si scarta', () => {
    salvaPreferiti('amm-software', ['/amm-software/permessi'])
    const nav = useNavigationStore()
    nav.syncUserFavorites(UTENTE)
    expect(nav.getDomainFavorites('amm-software')).toEqual([])
    expect(nav.getDefaultRoute('amm-software')).toBe('/amm-software/accessi')
  })

  it('3) un preferito valido resta e vince sulla prima voce', () => {
    salvaPreferiti('amm-software', ['/amm-software/permessi', '/amm-software/emittenti-fiscali'])
    const nav = useNavigationStore()
    nav.syncUserFavorites(UTENTE)
    expect(nav.getDomainFavorites('amm-software')).toEqual(['/amm-software/emittenti-fiscali'])
    expect(nav.getDefaultRoute('amm-software')).toBe('/amm-software/emittenti-fiscali')
  })
})
