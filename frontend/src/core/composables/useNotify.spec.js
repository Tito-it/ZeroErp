// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: La RETE sotto i tre toast d'errore (2026-09-09). Nasce insieme alla
//        de-duplicazione di `_toastErrore`: un refactor su un file senza
//        copertura si fa alla cieca, e questo file toglie il «alla cieca».
//        ⚠️ Quello che fissa non e' l'estetica del toast: e' che ognuno dei tre
//        rami chieda la DURATA giusta e metta la soluzione nel `detail` — le due
//        cose che a video si vedono, e che un refactor puo' scambiare senza che
//        niente fallisca.
// Note: ⛔ `TOAST_DURATION` NON e' mockata: le durate sono la posta in gioco, e
//        confrontarle con una copia finta proverebbe che il test e' coerente
//        con se stesso. Si mockano i due collaboratori esterni — il toast di
//        PrimeVue (che vuole un'app viva) e `useI18n` (che vuole un'istanza).
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'

import { TOAST_DURATION } from '../constants'

const add = vi.fn()

vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add }) }))
// Il ripiego dei messaggi passa da `t`: qui torna la chiave, cosi' si vede
// QUALE chiave sarebbe stata chiesta invece di una stringa qualunque.
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: (chiave) => chiave }) }))

const { useNotify } = await import('./useNotify')

beforeEach(() => add.mockClear())

describe('useNotify — i tre toast d’errore', () => {
  it('senza soluzione: nessun `detail`, e la durata normale', () => {
    useNotify().error('rotto')
    expect(add).toHaveBeenCalledWith(
      expect.objectContaining({
        severity: 'error',
        summary: 'rotto',
        detail: undefined,
        life: TOAST_DURATION.ERROR,
      }),
    )
  })

  it('⭐ con la soluzione: va nel `detail` e la durata si allunga', () => {
    // ⚠️ La durata cambia col TESTO, non con la gravita': e' la decisione del
    //    2026-09-09, e senza questo test un refactor la riporterebbe a `ERROR`
    //    senza che niente si accorga di niente.
    useNotify().error('rotto', 'Resettare il lotto.')
    expect(add).toHaveBeenCalledWith(
      expect.objectContaining({
        detail: 'Resettare il lotto.',
        life: TOAST_DURATION.ERROR_CON_SOLUZIONE,
      }),
    )
  })

  it('il toast di sistema resta persistente, con o senza soluzione', () => {
    useNotify().systemError('guasto', 'Segnalare al supporto.')
    expect(add).toHaveBeenCalledWith(
      expect.objectContaining({
        detail: 'Segnalare al supporto.',
        life: TOAST_DURATION.SYSTEM_ERROR,
      }),
    )
  })

  it('con un gesto: gruppo dedicato, persistente, azioni e soluzione insieme', () => {
    const azioni = [{ label: 'Apri Fattura 820', esegui: () => {} }]
    useNotify().errorConAzioni('rotto', azioni, 'Numerare prima.')
    expect(add).toHaveBeenCalledWith(
      expect.objectContaining({
        group: 'azioni',
        life: TOAST_DURATION.AZIONI,
        azioni,
        detail: 'Numerare prima.',
      }),
    )
  })

  it('⛔ senza azioni ricade sul toast normale — e NON perde la soluzione', () => {
    // E' il ripiego che il chiamante non deve ramificare. ⚠️ Perdere qui la
    // soluzione sarebbe muto: il toast comparirebbe lo stesso, senza la frase.
    useNotify().errorConAzioni('rotto', [], 'Numerare prima.')
    expect(add).toHaveBeenCalledOnce()
    expect(add).toHaveBeenCalledWith(
      expect.objectContaining({
        detail: 'Numerare prima.',
        life: TOAST_DURATION.ERROR_CON_SOLUZIONE,
      }),
    )
    expect(add.mock.calls[0][0].group).toBeUndefined()
  })

  it('⚠️ senza messaggio si chiede la chiave di ripiego, non una frase vuota', () => {
    useNotify().error(null)
    expect(add).toHaveBeenCalledWith(
      expect.objectContaining({ summary: 'notifications.generic_error' }),
    )
  })
})
