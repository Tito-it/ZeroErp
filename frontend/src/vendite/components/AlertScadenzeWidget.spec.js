// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: l'alert delle scadenze listino non scambia un ERRORE per «nessuna
//        scadenza» (2026-10-31). Fino a quel giorno un `catch {}` azzerava il
//        conteggio e il widget spariva: lo stesso aspetto del caso buono.
//
// ⚠️ Si finge solo il client HTTP (`alertScadenze`), il contorno: il widget
//    e' quello vero.
//
// Indice test:
//   1) lettura buona con scadenze: il badge col conteggio
//   2) lettura buona senza scadenze: niente widget
//   3) ⭐ errore del server: il widget dice «non verificabili», non sparisce
//   4) 403: l'utente non vede le scadenze, niente widget e niente avviso
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises } from '@vue/test-utils'

vi.mock('../api/listini', () => ({ alertScadenze: vi.fn() }))

import { alertScadenze } from '../api/listini'
import AlertScadenzeWidget from './AlertScadenzeWidget.vue'
import { monta } from '../../../test/montaggio'

const MESSAGGI = {
  vendite: { listini: { alert_scadenze_non_verificabili: 'Non verificabili' } },
}

const risposta = (results) => ({ data: { data: { results, count: results.length } } })
const errore = (status) => Object.assign(new Error('http'), { response: { status } })

describe('AlertScadenzeWidget', () => {
  beforeEach(() => { alertScadenze.mockReset() })

  it('1) lettura buona con scadenze: il badge col conteggio', async () => {
    alertScadenze.mockResolvedValue(risposta([{ versione_id: 1 }, { versione_id: 2 }]))
    const w = monta(AlertScadenzeWidget, {}, { messages: MESSAGGI })
    await flushPromises()
    expect(w.find('.alert-scadenze-badge').text()).toBe('2')
  })

  it('2) lettura buona senza scadenze: niente widget', async () => {
    alertScadenze.mockResolvedValue(risposta([]))
    const w = monta(AlertScadenzeWidget, {}, { messages: MESSAGGI })
    await flushPromises()
    expect(w.find('.alert-scadenze-widget').exists()).toBe(false)
  })

  it('3) errore del server: il widget dice «non verificabili», non sparisce', async () => {
    alertScadenze.mockRejectedValue(errore(500))
    const w = monta(AlertScadenzeWidget, {}, { messages: MESSAGGI })
    await flushPromises()
    const btn = w.find('.alert-scadenze-widget button')
    expect(btn.exists()).toBe(true)
    expect(btn.attributes('aria-label')).toBe('Non verificabili')
    // Il clic riprova: alla lettura buona compare il conteggio.
    alertScadenze.mockResolvedValue(risposta([{ versione_id: 7 }]))
    await btn.trigger('click')
    await flushPromises()
    expect(w.find('.alert-scadenze-badge').text()).toBe('1')
  })

  it('4) 403: l\'utente non vede le scadenze, niente widget e niente avviso', async () => {
    alertScadenze.mockRejectedValue(errore(403))
    const w = monta(AlertScadenzeWidget, {}, { messages: MESSAGGI })
    await flushPromises()
    expect(w.find('.alert-scadenze-widget').exists()).toBe(false)
  })
})
