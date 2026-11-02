// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa quale testo va nel `title` di una combo stretta, e quando
//        nessuno — A4 di brief-fe-filtri-lista-su-schermo-compatto.
// Note: i casi sono quelli che, sbagliati, NON danno errore: un `title=""`
//       vuoto, o un tooltip che dice una cosa diversa da quella a video.
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'

import { etichettaSelezionata, etichettaVoce } from './etichettaSelezionata'

const OPZIONI = [
  { id: 1, codice: 'EE', descrizione: 'Energia elettrica — mercato libero' },
  { id: 2, codice: 'GAS', descrizione: 'Gas naturale' },
  { id: 3, codice: 'X', descrizione: '   ' },
]

describe('etichettaSelezionata', () => {
  it('rende il testo intero della voce selezionata', () => {
    expect(etichettaSelezionata(OPZIONI, 1)).toBe('Energia elettrica — mercato libero')
  })

  it('legge il campo valore e il campo etichetta dichiarati', () => {
    expect(etichettaSelezionata(OPZIONI, 'GAS', { campoValore: 'codice', etichetta: 'codice' })).toBe('GAS')
  })

  it('con una funzione rende cio\' che si legge a video (show-code)', () => {
    const fmt = v => `${v.descrizione} (${v.codice})`
    expect(etichettaSelezionata(OPZIONI, 2, { etichetta: fmt })).toBe('Gas naturale (GAS)')
  })

  it('nessuna selezione ⇒ undefined, mai la stringa vuota', () => {
    expect(etichettaSelezionata(OPZIONI, null)).toBeUndefined()
    expect(etichettaSelezionata(OPZIONI, undefined)).toBeUndefined()
    expect(etichettaSelezionata(OPZIONI, 99)).toBeUndefined()
  })

  it('voce trovata ma senza testo ⇒ undefined', () => {
    expect(etichettaSelezionata(OPZIONI, 3)).toBeUndefined()
    expect(etichettaSelezionata([{ id: 4 }], 4)).toBeUndefined()
  })

  it('la voce «Tutti» (valore null) e\' una selezione vera', () => {
    const conTutti = [{ id: null, descrizione: 'Tutti' }, ...OPZIONI]
    expect(etichettaSelezionata(conTutti, null)).toBe('Tutti')
  })

  it('undefined non aggancia una voce senza il campo valore', () => {
    expect(etichettaSelezionata([{ descrizione: 'orfana' }], undefined)).toBeUndefined()
  })

  it('confronto stretto: l\'id 1 non e\' la stringa «1»', () => {
    expect(etichettaSelezionata(OPZIONI, '1')).toBeUndefined()
  })

  it('opzioni non ancora caricate ⇒ undefined, senza sollevare', () => {
    expect(etichettaSelezionata(null, 1)).toBeUndefined()
    expect(etichettaSelezionata([], 1)).toBeUndefined()
  })
})

describe('etichettaVoce', () => {
  it('rende il testo della voce gia\' trovata, per campo o per funzione', () => {
    expect(etichettaVoce(OPZIONI[0])).toBe('Energia elettrica — mercato libero')
    expect(etichettaVoce(OPZIONI[1], v => `${v.descrizione} (${v.codice})`)).toBe('Gas naturale (GAS)')
  })

  it('nessuna voce o testo vuoto ⇒ undefined, mai la stringa vuota', () => {
    expect(etichettaVoce(null)).toBeUndefined()
    expect(etichettaVoce(undefined)).toBeUndefined()
    expect(etichettaVoce(OPZIONI[2])).toBeUndefined()
    expect(etichettaVoce({ id: 4 }, () => '')).toBeUndefined()
  })
})
