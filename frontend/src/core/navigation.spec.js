// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
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
//  5. findMenuItem trova la voce di una rotta Strumenti (e nulla senza menuKey)
//  6. resolveTabDisplayLabel: ricalcola, non si fida della label salvata
//  7. resolveTabDisplayLabel: il nome dato a mano vince, il ripiego e' la label
// ------------------------------------------------------------

import { describe, expect, it } from 'vitest'

import { findMenuItem, isMenuItemAllowed, resolveTabDisplayLabel } from './navigation'

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
})

describe('findMenuItem', () => {
  it('trova la voce di una rotta Strumenti (e nulla senza menuKey)', () => {
    expect(findMenuItem('strumenti', 'code-lavoro')?.requireArea).toBe('strumenti')
    expect(findMenuItem('strumenti', 'email')?.to).toBe('/strumenti/email')
    expect(findMenuItem('strumenti', undefined)).toBeNull()
    expect(findMenuItem('inesistente', 'email')).toBeNull()
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
