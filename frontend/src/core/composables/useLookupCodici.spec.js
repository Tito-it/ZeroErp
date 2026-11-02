// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il contratto di `useLookupCodici` (2026-09-19): la chiave di
//        cache di un `rel` e' il `rel` stesso, e con gli obsoleti esclusi e'
//        un ALTRO insieme quindi un'altra chiave (`::no-obsoleti`); la fetch
//        chiama il lookup generico con il cap di pagina e manda
//        `includi_obsoleti` solo quando e' `false`. E' il contratto che
//        quattro siti ricopiavano a mano: se cambia qui, cambia per tutti.
// Note: `lookupCodici` e `useGlobalLookup` finti: si prova la composizione.
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'

const chiamate = []
vi.mock('../apiCore', () => ({
  lookupCodici: (rel, params) => {
    chiamate.push({ rel, params })
    return Promise.resolve({ data: { data: { results: [] } } })
  },
}))

const registrate = []
vi.mock('./useGlobalLookup', () => ({
  useGlobalLookup: (chiave, fetchFn, opzioni) => {
    registrate.push({ chiave, fetchFn, opzioni })
    return { chiave }
  },
}))

const { useLookupCodici, chiaveLookupCodici, fetchLookupCodici, LOOKUP_CODICI_LIMIT } =
  await import('./useLookupCodici')

describe('useLookupCodici', () => {
  beforeEach(() => {
    chiamate.length = 0
    registrate.length = 0
  })

  it('la chiave: il rel; con gli obsoleti esclusi un altro insieme, un\'altra chiave', () => {
    expect(chiaveLookupCodici('config.iva')).toBe('config.iva')
    expect(chiaveLookupCodici('config.iva', { includiObsoleti: true })).toBe('config.iva')
    expect(chiaveLookupCodici('config.iva', { includiObsoleti: false })).toBe('config.iva::no-obsoleti')
  })

  it('la fetch: cap di pagina, e `includi_obsoleti` solo quando e\' false', async () => {
    await fetchLookupCodici('config.iva')()
    await fetchLookupCodici('config.iva', { includiObsoleti: false, limit: 50 })()
    expect(chiamate).toEqual([
      { rel: 'config.iva', params: { limit: LOOKUP_CODICI_LIMIT } },
      { rel: 'config.iva', params: { limit: 50, includi_obsoleti: false } },
    ])
    expect(LOOKUP_CODICI_LIMIT).toBe(200)
  })

  it('il composable registra su useGlobalLookup chiave, fetch e opzioni', async () => {
    useLookupCodici('pratiche.tipi_prestazione', { includiObsoleti: false, immediate: true })
    useLookupCodici('config.priorita_pratiche')
    expect(registrate.map((r) => r.chiave)).toEqual([
      'pratiche.tipi_prestazione::no-obsoleti',
      'config.priorita_pratiche',
    ])
    expect(registrate[0].opzioni).toEqual({ immediate: true })
    expect(registrate[1].opzioni).toEqual({ immediate: false })
    await registrate[0].fetchFn()
    expect(chiamate[0]).toEqual({
      rel: 'pratiche.tipi_prestazione',
      params: { limit: 200, includi_obsoleti: false },
    })
    // `transform` passa solo se dato: il default resta quello di useGlobalLookup.
    const transform = (r) => r
    useLookupCodici('config.iva', { transform })
    expect(registrate[2].opzioni).toEqual({ immediate: false, transform })
  })
})

// ⛔ Una tendina che legge un `rel` senza `limit` prende la finestra di default
//    del backend (25) e si tronca in silenzio oltre quella (trovato il
//    2026-10-21: sette siti, decisione Tid di correggerli). Il presidio legge
//    il CODICE: la tendina passa dal BB, che manda `LOOKUP_CODICI_LIMIT`.
//    Una chiamata con un oggetto di parametri (es. la ricerca di un codice)
//    resta ammessa: e' una scelta dichiarata, non un default subito.
const sorgenti = import.meta.glob(
  ['../../**/*.vue', '../../**/*.js', '!../../**/*.spec.js'],
  { query: '?raw', import: 'default', eager: true },
)

describe('nessuna tendina legge un rel senza limit', () => {
  it('niente `lookupCodici(rel)` con il solo rel', () => {
    const trovate = Object.entries(sorgenti)
      .filter(([, testo]) => /\blookupCodici\(\s*['"`][^'"`]+['"`]\s*\)/.test(
        testo.replace(/\/\/[^\n]*/g, ''),
      ))
      .map(([file]) => file)
    expect(trovate).toEqual([])
  })
})
