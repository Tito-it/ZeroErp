// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Test di `useEsitoInvito`: `inviato: false` e' un AVVISO, non un
//        successo (F-3 dell'analisi difetti doc API core, 2026-09-28).
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'

const notifiche = { success: vi.fn(), warn: vi.fn() }

vi.mock('./useNotify', () => ({ useNotify: () => notifiche }))
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: (k) => k }) }))

const { useEsitoInvito } = await import('./useEsitoInvito')

describe('useEsitoInvito', () => {
  beforeEach(() => {
    notifiche.success.mockClear()
    notifiche.warn.mockClear()
  })

  it('email partita: successo col messaggio del chiamante', () => {
    const { notificaEsitoInvito } = useEsitoInvito()
    expect(notificaEsitoInvito({ inviato: true }, 'Invito inviato')).toBe(true)
    expect(notifiche.success).toHaveBeenCalledWith('Invito inviato')
    expect(notifiche.warn).not.toHaveBeenCalled()
  })

  it('email non partita: avviso, nessun successo', () => {
    const { notificaEsitoInvito } = useEsitoInvito()
    expect(notificaEsitoInvito({ inviato: false }, 'Invito inviato')).toBe(false)
    expect(notifiche.warn).toHaveBeenCalledWith('common.invito_non_spedito')
    expect(notifiche.success).not.toHaveBeenCalled()
  })

  it('campo assente: resta un successo (solo `false` e\' un avviso)', () => {
    const { notificaEsitoInvito } = useEsitoInvito()
    expect(notificaEsitoInvito({}, 'ok')).toBe(true)
    expect(notificaEsitoInvito(null, 'ok')).toBe(true)
    expect(notifiche.warn).not.toHaveBeenCalled()
  })
})
