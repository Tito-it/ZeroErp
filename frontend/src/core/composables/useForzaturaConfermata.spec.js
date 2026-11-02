// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il contratto del doppio tempo «rifiuto confermabile → conferma →
//        ripeti» (`useForzaturaConfermata`), dal 2026-09-27 con due domini che
//        lo usano: la capienza dei pagamenti e il consenso al riuso della
//        credenziale. Fissa cio' che i due chiamanti danno per scontato:
//        - il primo tentativo parte SENZA dichiarazione;
//        - sul `confirm_and_retry` non parte il toast e la domanda arriva col
//          messaggio del database;
//        - `conferma(dichiarazione)` ripete la STESSA chiamata con la
//          dichiarazione del dominio, qualunque sia (il BB non ne conosce le
//          parole);
//        - un nuovo rifiuto confermabile al secondo tempo ripropone la domanda
//          (la credenziale e' cambiata nel frattempo), non un banner.
// Note: ⛔ `useNotify`, lo store auth e i bersagli sono mockati come nella spec
//        di `useApiHandler`: qui si prova il BB, non l'handler.
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'

const notifiche = {
  success: vi.fn(),
  error: vi.fn(),
  systemError: vi.fn(),
  errorConAzioni: vi.fn(),
}

vi.mock('../../stores/auth', () => ({ useAuthStore: () => ({ isSuperAdmin: false }) }))
vi.mock('./useNotify', () => ({ useNotify: () => notifiche }))
vi.mock('../bersagli', () => ({ estraiBersagli: () => [] }))
vi.mock('../bersaglioGesto', () => ({ azioniDaBersagli: () => [] }))

const { useForzaturaConfermata, CONFERMA_E_RIPETI } = await import('./useForzaturaConfermata')

// Il rifiuto nella forma in cui axios lo consegna.
function rifiuto(uiAction, message = 'Domanda dal database') {
  return { response: { status: 409, data: { error: { code: 'E_PROVA', message, ui_action: uiAction } } } }
}

// La risposta di successo nella forma axios + envelope.
function ok(data) {
  return { data: { data } }
}

beforeEach(() => {
  Object.values(notifiche).forEach((f) => f.mockClear())
})

describe('useForzaturaConfermata', () => {
  it('il primo tentativo parte senza dichiarazione e, se passa, non chiede niente', async () => {
    const chiamata = vi.fn().mockResolvedValue(ok({ id: 1 }))
    const { esegui, richiestaConferma } = useForzaturaConfermata()

    expect(await esegui(chiamata)).toEqual({ id: 1 })
    expect(chiamata).toHaveBeenCalledWith({})
    expect(richiestaConferma.value).toBeNull()
  })

  it('sul rifiuto confermabile porta la domanda del database, senza toast', async () => {
    const chiamata = vi.fn().mockRejectedValue(rifiuto(CONFERMA_E_RIPETI, 'Email gia\' di mario'))
    const { esegui, richiestaConferma } = useForzaturaConfermata()

    expect(await esegui(chiamata)).toBeNull()
    expect(richiestaConferma.value).toEqual({ messaggio: 'Email gia\' di mario' })
    expect(notifiche.error).not.toHaveBeenCalled()
  })

  it('conferma ripete la stessa chiamata con la dichiarazione del dominio', async () => {
    const chiamata = vi.fn()
      .mockRejectedValueOnce(rifiuto(CONFERMA_E_RIPETI))
      .mockResolvedValueOnce(ok({ id: 7 }))
    const { esegui, conferma, richiestaConferma } = useForzaturaConfermata()

    await esegui(chiamata)
    expect(await conferma({ riusa_auth_user_id: 42 })).toEqual({ id: 7 })
    expect(chiamata).toHaveBeenLastCalledWith({ riusa_auth_user_id: 42 })
    expect(richiestaConferma.value).toBeNull()
  })

  it('un nuovo rifiuto confermabile al secondo tempo ripropone la domanda', async () => {
    const chiamata = vi.fn()
      .mockRejectedValueOnce(rifiuto(CONFERMA_E_RIPETI, 'prima'))
      .mockRejectedValueOnce(rifiuto(CONFERMA_E_RIPETI, 'di nuovo'))
    const { esegui, conferma, richiestaConferma } = useForzaturaConfermata()

    await esegui(chiamata)
    const prima = richiestaConferma.value
    expect(await conferma({ riusa_auth_user_id: 42 })).toBeNull()
    expect(richiestaConferma.value).toEqual({ messaggio: 'di nuovo' })
    // Contratto: una domanda nuova e' un oggetto nuovo (il chiamante lo
    // confronta per identita' per sapere se rileggere i dati).
    expect(richiestaConferma.value).not.toBe(prima)
    expect(notifiche.error).not.toHaveBeenCalled()
  })

  it('un rifiuto vero al secondo tempo e\' un errore normale, e la domanda resta', async () => {
    const chiamata = vi.fn()
      .mockRejectedValueOnce(rifiuto(CONFERMA_E_RIPETI))
      .mockRejectedValueOnce(rifiuto('show_error_banner', 'Rifiuto vero'))
    const { esegui, conferma, richiestaConferma } = useForzaturaConfermata()

    await esegui(chiamata)
    const prima = richiestaConferma.value
    expect(await conferma({ riusa_auth_user_id: 42 })).toBeNull()
    expect(notifiche.error).toHaveBeenCalledWith('Rifiuto vero', null)
    // La domanda resta QUELLA di prima: il chiamante non rilegge niente.
    expect(richiestaConferma.value).toBe(prima)
  })

  it('annulla chiude la domanda e conferma non ripete piu\' niente', async () => {
    const chiamata = vi.fn().mockRejectedValueOnce(rifiuto(CONFERMA_E_RIPETI))
    const { esegui, conferma, annulla, richiestaConferma } = useForzaturaConfermata()

    await esegui(chiamata)
    annulla()
    expect(richiestaConferma.value).toBeNull()
    expect(await conferma({ riusa_auth_user_id: 42 })).toBeNull()
    expect(chiamata).toHaveBeenCalledTimes(1)
  })
})
