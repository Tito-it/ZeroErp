// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il pannello dei presidi (`PresidiProcessiPanel`) parla a CHI DEVE
//        AGIRE: un presidio acceso mostra prima l'azione, poi il significato,
//        poi a chi tocca, e la descrizione della vista chiusa sotto «Dettaglio
//        tecnico» (brief-db-presidi-cosa-significa-cosa-fare §6, 2026-10-06).
// Note: le righe hanno la forma di `stato_presidi` del backend; l'i18n dei test
//       rende la CHIAVE, quindi i badge si riconoscono dalla chiave.
//
// Indice test:
//   1) acceso col testo: azione, poi significato, poi badge; descrizione chiusa
//   2) un badge per ciascuno dei tre valori di chi agisce
//   3) senza testo: la descrizione resta aperta, nessun dettaglio tecnico
//   4) non letto: niente azione né badge, l'errore resta
// ------------------------------------------------------------

import { describe, expect, it } from 'vitest'

const { monta } = await import('../../../test/montaggio')
const { default: PresidiProcessiPanel } = await import('./PresidiProcessiPanel.vue')

function presidio(sovrascritture = {}) {
  return {
    vista: 'dbops.vw_lotti_fermi_da_guardare',
    descrizione: 'commento tecnico della vista',
    significato: 'Ci sono giri di fatturazione fermi.',
    azione: 'Apri ogni lotto e rilancialo o annullalo.',
    chi_agisce: 'AMMINISTRATORE',
    conteggio: 2,
    righe: [],
    troncato: false,
    elencabili: true,
    errore: null,
    da_guardare: true,
    ...sovrascritture,
  }
}

const monta1 = (p) => monta(PresidiProcessiPanel, { presidi: [p] })

describe('PresidiProcessiPanel — il testo per chi agisce', () => {
  it('1) acceso col testo: azione, poi significato, poi badge; descrizione chiusa', () => {
    const w = monta1(presidio())
    const testo = w.find('.app-presidio').text()
    const azione = testo.indexOf('Apri ogni lotto')
    const significato = testo.indexOf('Ci sono giri')
    const badge = testo.indexOf('amministrazione.processi.chi_agisce.amministratore')
    expect(azione).toBeGreaterThanOrEqual(0)
    expect(azione).toBeLessThan(significato)
    expect(significato).toBeLessThan(badge)

    // ⭐ La descrizione c'è, ma dentro il dettaglio tecnico CHIUSO.
    const dettaglio = w.find('details.app-presidio-dettaglio')
    expect(dettaglio.exists()).toBe(true)
    expect(dettaglio.attributes('open')).toBeUndefined()
    expect(dettaglio.find('summary').text())
      .toBe('amministrazione.processi.presidi_dettaglio_tecnico')
    expect(dettaglio.text()).toContain('commento tecnico della vista')
  })

  it.each([
    ['AMMINISTRATORE', 'amministrazione.processi.chi_agisce.amministratore'],
    ['SISTEMISTA', 'amministrazione.processi.chi_agisce.sistemista'],
    ['SVILUPPO', 'amministrazione.processi.chi_agisce.sviluppo'],
  ])('2) chi agisce %s ha il suo badge', (chi, chiave) => {
    const w = monta1(presidio({ chi_agisce: chi }))
    expect(w.find('.app-presidio-chi').text()).toBe(chiave)
  })

  it('3) senza testo: la descrizione resta aperta, nessun dettaglio tecnico', () => {
    const w = monta1(presidio({ significato: null, azione: null, chi_agisce: null }))
    expect(w.find('details').exists()).toBe(false)
    expect(w.find('.app-presidio-chi').exists()).toBe(false)
    // ⛔ Mai sul vuoto: la descrizione è l'unica spiegazione, e si vede.
    expect(w.find('p.app-presidio-desc').text()).toBe('commento tecnico della vista')
  })

  it('4) non letto: niente azione né badge, l\'errore resta', () => {
    // È la forma che il backend consegna per un presidio che non si è letto:
    // il significato sì, l'azione e chi agisce no.
    const w = monta1(presidio({
      conteggio: null, errore: 'connessione persa', azione: null, chi_agisce: null,
    }))
    expect(w.find('.app-presidio-errore').text()).toBe('connessione persa')
    expect(w.find('.app-presidio-azione').exists()).toBe(false)
    expect(w.find('.app-presidio-chi').exists()).toBe(false)
    expect(w.find('.app-presidio-significato').text()).toContain('Ci sono giri')
  })
})
