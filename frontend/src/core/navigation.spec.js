// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il filtro UNICO dei cancelli di voce (`isMenuItemAllowed`) e la
//        ricerca della voce di una rotta (`findMenuItem`): li leggono
//        sidebar, preferiti, widget e router guard.
// Note: ⛔ Il difetto che si presidia non da' errori: se il router non trova la
//       voce, il cancello resta solo a video e la pagina si apre
//       dall'indirizzo (e il backend risponde 403).
//
// Indice test:
//  1. voce senza cancelli: permessa
//  2. requireArea: bloccata se l'area e' BLOCCATA
//  3. requireAnyAction: basta un'azione; il super admin passa sempre
//  4. voce assente: non permessa
//  5. adminOnly: solo il super admin
//  6. il figlio eredita i cancelli del gruppo (via flattenMenu)
//  7. findMenuItem trova la voce di una rotta Strumenti (e nulla senza menuKey)
//  8. findMenuItem: il figlio di Diagnostica porta il cancello del gruppo
//  9. resolveTabDisplayLabel: ricalcola, non si fida della label salvata
// 10. resolveTabDisplayLabel: il nome dato a mano vince, il ripiego e' la label
// 11. rottaListaTipoRuolo: cliente e fornitore la loro lista, il resto i soggetti
// ------------------------------------------------------------

import { describe, expect, it } from 'vitest'

import { TIPO_RUOLO } from './constants'
import { findMenuItem, flattenMenu, isMenuItemAllowed, resolveTabDisplayLabel, rottaListaTipoRuolo } from './navigation'

function authCon({ aree = [], azioni = [], superAdmin = false } = {}) {
  return {
    isSuperAdmin: superAdmin,
    isAreaBlocked: (area) => !superAdmin && !aree.includes(area),
    isActionAllowed: (azione) => superAdmin || azioni.includes(azione),
  }
}

describe('isMenuItemAllowed', () => {
  it('voce senza cancelli: permessa', () => {
    expect(isMenuItemAllowed({ key: 'email' }, authCon())).toBe(true)
  })

  it('requireArea: bloccata se l\'area e\' BLOCCATA', () => {
    const voce = { key: 'code-lavoro', requireArea: 'strumenti' }
    expect(isMenuItemAllowed(voce, authCon())).toBe(false)
    expect(isMenuItemAllowed(voce, authCon({ aree: ['strumenti'] }))).toBe(true)
  })

  it('requireAnyAction: basta un\'azione; il super admin passa sempre', () => {
    const voce = { key: 'x', requireAnyAction: ['a1', 'a2'] }
    expect(isMenuItemAllowed(voce, authCon())).toBe(false)
    expect(isMenuItemAllowed(voce, authCon({ azioni: ['a2'] }))).toBe(true)
    expect(isMenuItemAllowed(voce, authCon({ superAdmin: true }))).toBe(true)
  })

  it('voce assente: non permessa', () => {
    expect(isMenuItemAllowed(null, authCon({ superAdmin: true }))).toBe(false)
  })

  it('adminOnly: solo il super admin', () => {
    const voce = { key: 'x', adminOnly: true }
    expect(isMenuItemAllowed(voce, authCon({ aree: ['strumenti'] }))).toBe(false)
    expect(isMenuItemAllowed(voce, authCon({ superAdmin: true }))).toBe(true)
  })

  it('il figlio eredita i cancelli del gruppo (via flattenMenu)', () => {
    // ⛔ Il figlio non dichiara niente: il cancello sta solo sul gruppo, e
    //    deve valere lo stesso — e' la strada del router guard.
    const [, figlio] = flattenMenu([
      { key: 'g', requireArea: 'vendite', children: [{ key: 'f', to: '/x/f' }] },
    ])
    expect(figlio.gruppo.key).toBe('g')
    expect(isMenuItemAllowed(figlio, authCon())).toBe(false)
    expect(isMenuItemAllowed(figlio, authCon({ aree: ['vendite'] }))).toBe(true)
  })
})

describe('findMenuItem', () => {
  it('trova la voce di una rotta Strumenti (e nulla senza menuKey)', () => {
    expect(findMenuItem('strumenti', 'code-lavoro')?.requireArea).toBe('strumenti')
    expect(findMenuItem('strumenti', 'email')?.to).toBe('/strumenti/email')
    expect(findMenuItem('strumenti', undefined)).toBeNull()
    expect(findMenuItem('inesistente', 'email')).toBeNull()
  })

  it('il figlio di Diagnostica porta il cancello del gruppo', () => {
    const voce = findMenuItem('strumenti', 'error-log')
    expect(voce?.to).toBe('/strumenti/diagnostica/error-log')
    expect(isMenuItemAllowed(voce, authCon({ aree: ['strumenti', 'vendite'] }))).toBe(false)
    expect(isMenuItemAllowed(voce, authCon({ superAdmin: true }))).toBe(true)
  })
})

describe('resolveTabDisplayLabel', () => {
  const messaggi = { 'nav_menu.vendite.ordini': 'Ordini di vendita', 'nav.vendite': 'Vendite' }
  const t = (k) => messaggi[k] ?? k
  const te = (k) => k in messaggi

  it('ricalcola, non si fida della label salvata', () => {
    // La tab nata prima dei messaggi i18n porta la chiave grezza.
    const tab = { domain: 'vendite', menuKey: 'ordini', label: 'nav_menu.vendite.ordini' }
    expect(resolveTabDisplayLabel(tab, t, te)).toBe('Ordini di vendita')
  })

  it('il nome dato a mano vince, il ripiego e\' la label', () => {
    expect(resolveTabDisplayLabel(
      { domain: 'vendite', menuKey: 'ordini', label: 'Mio', customLabel: true }, t, te,
    )).toBe('Mio')
    expect(resolveTabDisplayLabel({ domain: 'ignoto', label: 'Salvata' }, t, te)).toBe('Salvata')
    expect(resolveTabDisplayLabel(null, t, te)).toBe('')
  })
})

describe('rottaListaTipoRuolo', () => {
  it('cliente e fornitore la loro lista, ogni altro tipo (o nessuno) i soggetti', () => {
    expect(rottaListaTipoRuolo(TIPO_RUOLO.CLIENTE)).toBe('anagrafiche-clienti')
    expect(rottaListaTipoRuolo(TIPO_RUOLO.FORNITORE)).toBe('anagrafiche-fornitori')
    expect(rottaListaTipoRuolo('XX')).toBe('anagrafiche-soggetti')
    expect(rottaListaTipoRuolo(null)).toBe('anagrafiche-soggetti')
  })
})
