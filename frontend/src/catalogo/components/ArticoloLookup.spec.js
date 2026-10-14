// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa `ArticoloLookup` sulla riga di un documento (brief-db-articoli-
//        ammessi-per-documento §9.6, Lotto 4): chiede al backend col contesto
//        della riga e senza filtri suoi, mostra l'escluso SPENTO col motivo, e
//        lascia sceglibile il motivo che la maschera gestisce (il composito
//        come bundle nella versione di listino).
// Note: sono difetti che non danno errore — un escluso acceso si sceglie e il
//       guard lo rifiuta dopo; un filtro rimasto nasconde un articolo che il
//       DB ammette. Le risposte arrivano a mano.
// Indice test:
//   1) con `documento` manda il contesto della riga, e niente filtri liberi
//   2) l'escluso e' spento e porta il testo del motivo; l'ammesso no
//   3) un motivo dichiarato selezionabile non spegne l'opzione
//   4) senza `documento` restano i filtri della consultazione
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { flushPromises } from '@vue/test-utils'

const chiamate = []
let risposta = []
vi.mock('../api/catalogo', () => ({
  lookupArticoli: (params) => {
    chiamate.push(params)
    return Promise.resolve({ data: { data: { results: risposta, troncato: false } } })
  },
}))

import ArticoloLookup from './ArticoloLookup.vue'
import { monta } from '../../../test/montaggio'

const AMMESSO = { id: 'a', codice: 'A', descrizione: 'Ammesso', motivo: null }
const ESCLUSO = {
  id: 'b', codice: 'B', descrizione: 'Escluso',
  motivo: { codice: 'E_ARTICOLO_SOLO_COMPONENTE', reason: 'SOLO_COMPONENTE', reason_key: null, valori: ['B'] },
}
const KIT = {
  id: 'k', codice: 'K', descrizione: 'Kit',
  motivo: { codice: 'E_LISTINO_RIGA_COMPOSITO_VIETATO', reason: 'COMPOSITO_COME_BUNDLE', reason_key: null },
}

const autocomplete = (w) => w.findComponent({ name: 'AutoComplete' })

// Scopo: una ricerca come la fa l'operatore, oltre il debounce.
async function cerca(w, query = 'abc') {
  autocomplete(w).vm.$emit('complete', { query })
  await vi.advanceTimersByTimeAsync(400)
  await flushPromises()
}

describe('ArticoloLookup — la riga di un documento', () => {
  beforeEach(() => {
    chiamate.length = 0
    risposta = []
    vi.useFakeTimers()
  })
  afterEach(() => { vi.useRealTimers() })

  it('con `documento` manda il contesto della riga, e niente filtri liberi', async () => {
    const w = monta(ArticoloLookup, {
      modelValue: null, documento: 'CONTRATTO', documentoId: 7, tipoEccezione: 'AGGIUNTA',
    })
    await cerca(w)
    expect(chiamate).toEqual([{
      search: 'abc', limit: 20, documento: 'CONTRATTO', documento_id: 7, tipo_eccezione: 'AGGIUNTA',
    }])
  })

  it('l\'escluso e\' spento e porta il testo del motivo; l\'ammesso no', async () => {
    risposta = [AMMESSO, ESCLUSO]
    const w = monta(ArticoloLookup, { modelValue: null, documento: 'PREVENTIVO', documentoId: 1 })
    await cerca(w)
    const ac = autocomplete(w)
    expect(ac.props('optionDisabled')).toBe('_escluso')
    const [a, b] = ac.props('suggestions')
    expect(a._escluso).toBe(false)
    expect(a._motivoTesto).toBe('')
    expect(b._escluso).toBe(true)
    // Senza chiave i18n il testo ripiega sul codice del motivo: mai vuoto.
    expect(b._motivoTesto).toBe('SOLO_COMPONENTE')
  })

  it('un motivo dichiarato selezionabile non spegne l\'opzione', async () => {
    risposta = [KIT, ESCLUSO]
    const w = monta(ArticoloLookup, {
      modelValue: null, documento: 'LISTINO_VERSIONE', documentoId: 3,
      motiviSelezionabili: ['COMPOSITO_COME_BUNDLE'],
    })
    await cerca(w)
    const [kit, escluso] = autocomplete(w).props('suggestions')
    expect(kit._escluso).toBe(false)
    expect(kit._motivoTesto).toBe('COMPOSITO_COME_BUNDLE')
    expect(escluso._escluso).toBe(true)
  })

  it('senza `documento` restano i filtri della consultazione', async () => {
    const w = monta(ArticoloLookup, { modelValue: null, filtri: { gestitiAMagazzino: 'solo' } })
    await cerca(w)
    expect(chiamate).toEqual([{ search: 'abc', attivo: true, limit: 20, gestito_a_magazzino: true }])
  })
})
