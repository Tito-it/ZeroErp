// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Test dell'uscita dalla sessione (`core/uscitaSessione`): il freno
//        della credenziale scattato su una password chiesta dentro la
//        sessione chiude la sessione e porta al login col motivo.
// Note: il router e lo store `auth` sono finti.
// ------------------------------------------------------------

/*
Indice test eseguiti:
1) seSessioneChiusaDalFreno: E_UTENTE_BLOCCATO → sessione azzerata e login col motivo
2) seSessioneChiusaDalFreno: E_LOGIN_ATTESA o altro → nessuna uscita
*/

import { beforeEach, describe, expect, it, vi } from 'vitest'

const clearTokens = vi.fn()
const push = vi.fn()
const rottaCorrente = { value: { name: 'change-password', fullPath: '/change-password' } }

vi.mock('./routerApp', () => ({
  routerApp: () => ({ currentRoute: rottaCorrente, push })
}))
vi.mock('../stores/auth', () => ({
  useAuthStore: () => ({ clearTokens })
}))

const { seSessioneChiusaDalFreno } = await import('./uscitaSessione')

function errore403(code) {
  return { response: { status: 403, data: { error: { code } } } }
}

describe('core/uscitaSessione — la sessione chiusa dal freno della password', () => {
  beforeEach(() => {
    clearTokens.mockReset()
    push.mockReset().mockResolvedValue(undefined)
    rottaCorrente.value = { name: 'change-password', fullPath: '/change-password' }
  })

  it('E_UTENTE_BLOCCATO: azzera la sessione e porta al login col motivo', async () => {
    expect(seSessioneChiusaDalFreno(errore403('E_UTENTE_BLOCCATO'))).toBe(true)
    // redirectToLogin importa lo store in modo dinamico: si aspetta il giro.
    await vi.waitFor(() => expect(push).toHaveBeenCalled())
    expect(clearTokens).toHaveBeenCalledTimes(1)
    expect(push.mock.calls[0][0]).toMatchObject({
      name: 'login',
      query: { reason: 'password_attempts', redirect: '/change-password' }
    })
  })

  it("E_LOGIN_ATTESA o un altro errore: nessuna uscita", async () => {
    expect(seSessioneChiusaDalFreno(errore403('E_LOGIN_ATTESA'))).toBe(false)
    expect(seSessioneChiusaDalFreno({ response: { status: 400, data: { error: { code: 'E_CHANGE_PASSWORD' } } } })).toBe(false)
    await Promise.resolve()
    expect(push).not.toHaveBeenCalled()
    expect(clearTokens).not.toHaveBeenCalled()
  })
})
