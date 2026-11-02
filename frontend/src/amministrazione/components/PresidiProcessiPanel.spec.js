// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
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
//   5) per causa: ogni gruppo col suo rimedio e il suo badge sopra le sue righe
//   6) causa senza testo: si dice, e non prende il rimedio del presidio
//   7) senza cause: una tabella sola con tutte le righe, nessun titolo di causa
//   9) le date delle righe si leggono nell'ora dell'azienda, non in ISO grezzo
//   8) per causa il conteggio (R-2): una causa oltre il campione c'è, col suo
//      numero, e dice quante righe ne mostra; su una vista non elencabile no
// ------------------------------------------------------------

import { describe, expect, it } from 'vitest'

const { monta } = await import('../../../test/montaggio')
const { default: PresidiProcessiPanel } = await import('./PresidiProcessiPanel.vue')
const { displayTimestamp } = await import('../../core/utils/date')

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

  it('5) per causa: ogni gruppo col suo rimedio e il suo badge sopra le sue righe', () => {
    const w = monta1(presidio({
      chi_agisce: 'SISTEMISTA',
      azione: null,
      significato: 'Segui il rimedio accanto alla causa.',
      righe: [{ id: 'p1' }, { id: 'p2' }],
      cause: [
        { causa: 'TIMER_FERMO', chi_agisce: 'SISTEMISTA', significato: 's1',
          azione: 'Riaccendi il timer.', conteggio: 1, righe: [{ id: 'p1' }] },
        { causa: 'NON_PROGRAMMATO', chi_agisce: 'SVILUPPO', significato: 's2',
          azione: 'Completa il catalogo.', conteggio: 1, righe: [{ id: 'p2' }] },
      ],
    }))
    const gruppi = w.findAll('.app-presidio-causa')
    expect(gruppi).toHaveLength(2)
    const secondo = gruppi[1].text()
    expect(secondo).toContain('NON_PROGRAMMATO')
    expect(secondo).toContain('amministrazione.processi.chi_agisce.sviluppo')
    expect(secondo.indexOf('Completa il catalogo.')).toBeLessThan(secondo.indexOf('p2'))
    expect(secondo).not.toContain('p1')
    expect(gruppi[0].text()).not.toContain('Completa il catalogo.')
  })

  it('6) causa senza testo: si dice, e non prende il rimedio del presidio', () => {
    const w = monta1(presidio({
      azione: 'Rimedio del presidio.',
      righe: [{ id: 'p1' }],
      cause: [{ causa: null, chi_agisce: null, significato: null, azione: null,
        conteggio: 1, righe: [{ id: 'p1' }] }],
    }))
    const gruppo = w.find('.app-presidio-causa')
    expect(gruppo.text()).toContain('amministrazione.processi.presidi_causa_non_indicata')
    expect(gruppo.text()).toContain('amministrazione.processi.presidi_causa_senza_testo')
    expect(gruppo.text()).not.toContain('Rimedio del presidio.')
  })

  it('7) senza cause: una tabella sola con tutte le righe, nessun titolo di causa', () => {
    const w = monta1(presidio({ righe: [{ id: 'p1' }, { id: 'p2' }], cause: [] }))
    expect(w.findAll('.app-presidio-causa')).toHaveLength(0)
    expect(w.findAll('table.app-presidio-righe')).toHaveLength(1)
    expect(w.findAll('table.app-presidio-righe tbody tr')).toHaveLength(2)
  })

  it('8) per causa il conteggio: anche oltre il campione, e quante righe ne mostra', () => {
    const cause = [
      { causa: 'A', chi_agisce: 'SISTEMISTA', significato: 's', azione: 'a',
        conteggio: 3, righe: [{ id: 'p1' }] },
      { causa: 'B', chi_agisce: 'SVILUPPO', significato: 's', azione: 'b',
        conteggio: 7, righe: [] },
    ]
    const w = monta1(presidio({ conteggio: 10, righe: [{ id: 'p1' }], cause }))
    const gruppi = w.findAll('.app-presidio-causa')
    expect(gruppi.map((g) => g.find('.app-presidio-causa-conteggio').text())).toEqual(['3', '7'])
    expect(gruppi[1].text()).toContain('amministrazione.processi.presidi_causa_mostrate')
    expect(gruppi[1].find('table').exists()).toBe(false)

    // Non elencabile: i numeri sì, la nota del campione no (la dice la testa).
    const definer = monta1(presidio({ conteggio: 10, righe: [], elencabili: false, cause }))
    const g2 = definer.findAll('.app-presidio-causa')
    expect(g2.map((g) => g.find('.app-presidio-causa-conteggio').text())).toEqual(['3', '7'])
    expect(definer.text()).not.toContain('amministrazione.processi.presidi_causa_mostrate')
  })

  it('9) le date delle righe si leggono nell\'ora dell\'azienda, non in ISO grezzo', () => {
    const istante = '2026-10-09T13:47:54.044Z'
    const w = monta1(presidio({
      righe: [{ quando: istante, giorno: '2026-10-09', ingenuo: '2026-10-09 13:47', testo: 'x' }],
    }))
    const celle = w.findAll('table.app-presidio-righe tbody td').map((c) => c.text())
    expect(celle).toEqual([displayTimestamp(istante), '09/10/2026', '2026-10-09 13:47', 'x'])
  })
})
