// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: La richiesta di reset password con nome utente o email (L-4, D-9):
//        l'etichetta segue la chiave d'ingresso del canale di login, e il
//        messaggio di esito parla di cio' che la persona ha digitato.
// Note: si monta la vista vera; e' finta solo l'API.
//
// Indice test:
//   1) canale ADMIN → etichetta «nome utente o email»
//   2) canale PORTALE o SHOP → etichetta «email»
//   3) richiesta con una «@» → messaggio dell'email; senza → dell'utente
// ------------------------------------------------------------

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

const richiediResetPassword = vi.fn()
vi.mock('../api/password', () => ({
  richiediResetPassword: (...a) => richiediResetPassword(...a),
}))

const { monta } = await import('../../../test/montaggio')
const { useAuthStore } = await import('../../stores/auth')
const { default: PasswordResetRequestView } = await import('./PasswordResetRequestView.vue')

const montaVista = () =>
  monta(PasswordResetRequestView, {}, { global: { stubs: { RouterLink: true } } })

const etichetta = (w) => w.find('input#identificativo').attributes('placeholder')

describe("reset password: nome utente o email (L-4)", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    richiediResetPassword.mockReset().mockResolvedValue({ data: {} })
  })

  it('1) canale ADMIN → nome utente o email', () => {
    useAuthStore().setLoginChannel('ADMIN')
    expect(etichetta(montaVista())).toBe('auth.reset_identificativo_label')
  })

  it('2) canale PORTALE o SHOP → email', () => {
    for (const canale of ['PORTALE', 'SHOP']) {
      useAuthStore().setLoginChannel(canale)
      expect(etichetta(montaVista())).toBe('auth.reset_email_label')
    }
  })

  it("3) il messaggio di esito parla di cio' che e' stato digitato", async () => {
    for (const [valore, atteso] of [
      ['ada@example.it', 'auth.reset_email_sent'],
      ['ada', 'auth.reset_username_sent'],
    ]) {
      const w = montaVista()
      await w.find('input#identificativo').setValue(valore)
      await w.find('form').trigger('submit')
      await flushPromises()
      expect(richiediResetPassword).toHaveBeenLastCalledWith(valore)
      expect(w.find('.login-success').text()).toBe(atteso)
    }
  })
})
