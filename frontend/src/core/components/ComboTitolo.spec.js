// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il CABLAGGIO di A4 (brief-fe-filtri-lista-su-schermo-compatto):
//        il testo intero del valore selezionato arriva davvero nel `title` del
//        `Select` di PrimeVue, nelle DUE combo `md` dei filtri di lista.
// Note: la decisione «quale testo, e quando nessuno» la prova
//       `utils/etichettaSelezionata.spec.js`. Qui si prova il TRASPORTO, che
//       quella spec non vede: un `:title` scritto sul tag sbagliato, o un
//       `Select` che non lo inoltra alla radice, lascerebbe verde il BB e
//       spento il tooltip — senza nessun errore.
// ------------------------------------------------------------

import { describe, it, expect, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'

vi.mock('../apiCore', () => ({
  lookupUtilitiesPerEmittente: () => Promise.resolve({
    data: { data: { results: [{ id: 7, codice: 'EE', descrizione: 'Energia elettrica — mercato libero' }] } },
  }),
}))

import LookupSelect from './LookupSelect.vue'
import UtilityPerRuoloSelect from './UtilityPerRuoloSelect.vue'
import { monta } from '../../../test/montaggio'

describe('LookupSelect — title del valore selezionato', () => {
  const fetcher = () => Promise.resolve({
    data: { data: [{ id: 1, codice: 'CT', descrizione: 'Conto transitorio incassi' }] },
  })

  it('porta nel title cio\' che si legge a video (show-code compreso)', async () => {
    const w = monta(LookupSelect, {
      modelValue: 1, fetcher, lookupKey: 'spec.combo-titolo', transform: r => r.data.data, showCode: true,
    })
    await flushPromises()
    expect(w.element.getAttribute('title')).toBe('Conto transitorio incassi (CT)')
  })

  it('senza selezione non stampa l\'attributo', async () => {
    const w = monta(LookupSelect, {
      modelValue: null, fetcher, lookupKey: 'spec.combo-titolo', transform: r => r.data.data,
    })
    await flushPromises()
    expect(w.element.hasAttribute('title')).toBe(false)
  })
})

describe('UtilityPerRuoloSelect — title del valore selezionato', () => {
  it('porta nel title la descrizione intera', async () => {
    const w = monta(UtilityPerRuoloSelect, { modelValue: 7 })
    await flushPromises()
    expect(w.element.getAttribute('title')).toBe('Energia elettrica — mercato libero')
  })

  it('senza selezione non stampa l\'attributo', async () => {
    const w = monta(UtilityPerRuoloSelect, { modelValue: null })
    await flushPromises()
    expect(w.element.hasAttribute('title')).toBe(false)
  })
})
