// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Test dello store `auth` sugli eventi delle altre schede (brief
//        sicurezza §2): un logout fatto altrove porta questa scheda al login
//        col SUO motivo, non con «sessione scaduta» (rilievo di Tid,
//        2026-09-29).
// Note: `core/api` è finto (niente axios, niente router); `core/sessione` è
//       quello vero tranne l'iscrizione agli eventi, catturata per poterla
//       chiamare come farebbe il BroadcastChannel.
// ------------------------------------------------------------

/*
Indice test eseguiti:
1) LOGOUT da un'altra scheda → login col motivo USCITA_ALTRA_SCHEDA
*/

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const redirectToLogin = vi.fn()
vi.mock('../core/api', () => ({
  default: { post: vi.fn(), get: vi.fn() },
  redirectToLogin: (...args) => redirectToLogin(...args),
  rinnovaAccess: vi.fn()
}))

let suEvento = null
vi.mock('../core/sessione', async importOriginal => ({
  ...(await importOriginal()),
  suEventoAltraScheda: fn => {
    suEvento = fn
    return () => {}
  }
}))

const { useAuthStore } = await import('./auth')
const { EVENTO_SESSIONE, MOTIVO_USCITA } = await import('../core/sessione')

beforeEach(() => {
  setActivePinia(createPinia())
  redirectToLogin.mockClear()
  suEvento = null
})

describe('eventi delle altre schede', () => {
  it("1) LOGOUT da un'altra scheda → login col motivo USCITA_ALTRA_SCHEDA", () => {
    useAuthStore()
    expect(suEvento).toBeTypeOf('function')
    suEvento({ tipo: EVENTO_SESSIONE.LOGOUT })
    expect(redirectToLogin).toHaveBeenCalledWith(MOTIVO_USCITA.USCITA_ALTRA_SCHEDA)
  })
})
