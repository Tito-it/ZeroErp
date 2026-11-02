// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il contratto di `useLookupEtichettato` (2026-09-19, regola
//        del 2 sulle due tendine del giornale): l'etichetta viene dalla
//        chiave che la RIGA porta (`etichetta_key`), il ripiego e' il codice
//        grezzo e mai il path della chiave o una stringa vuota, il campo del
//        codice si sceglie (`codice` / `codice_interno`), la voce «tutti» sta
//        in testa solo se chiesta, e la cache condivisa e' quella di
//        `useGlobalLookup` (stessa chiave, stesso insieme).
// Note: `vue-i18n` e `useGlobalLookup` finti: qui si prova la resa, non la
//        fetch. `useGlobalLookup` finto restituisce la stessa forma del vero
//        (`items` ref condivisa per chiave) — e registra le chiavi chieste.
//        `useLookupCodici` NON e' finto: la forma `{ rel }` deve arrivare
//        alla cache con la chiave che quel BB compone (`<rel>::no-obsoleti`).
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'

// Il dizionario del `useI18n` finto: `te` = «c'e'», `t` = il testo.
const dizionario = {
  'config.registri_giornale.event_log': 'Eventi di dominio',
  'config.tipi_entita.lotto': 'Lotto',
  'vendite.giornale.filtro_registro_tutti': 'Tutti i registri',
}
vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    te: (chiave) => chiave in dizionario,
    t: (chiave) => dizionario[chiave] ?? chiave,
  }),
}))

// `apiCore` finto: `useLookupCodici` lo importa, e il vero trascina il client
// axios e l'i18n dell'app — qui la fetch non parte mai.
vi.mock('../apiCore', () => ({ lookupCodici: vi.fn(() => Promise.resolve({ data: { data: { results: [] } } })) }))

// `useGlobalLookup` finto: una cache per chiave, come il vero.
const cache = new Map()
const chiaviChieste = []
vi.mock('./useGlobalLookup', () => ({
  useGlobalLookup: (chiave) => {
    chiaviChieste.push(chiave)
    if (!cache.has(chiave)) cache.set(chiave, ref([]))
    return { items: cache.get(chiave), loading: ref(false), loaded: ref(true), error: ref(null), load: vi.fn(), reload: vi.fn() }
  },
}))

const { useLookupEtichettato } = await import('./useLookupEtichettato')

const SORGENTE_K = { chiave: 'k', fetcher: vi.fn() }

const REGISTRI = [
  { id: 1, codice: 'EVENT_LOG', codice_interno: 'EVENT_LOG', etichetta_key: 'config.registri_giornale.event_log' },
  // Chiave dichiarata ma ASSENTE dai locales: deve uscire il codice.
  { id: 3, codice: 'TASK_RUN', codice_interno: 'TASK_RUN', etichetta_key: 'config.registri_giornale.task_run' },
]

describe('useLookupEtichettato', () => {
  beforeEach(() => {
    cache.clear()
    chiaviChieste.length = 0
  })

  it('etichetta dalla chiave della riga, ripiego sul CODICE grezzo (mai il path, mai vuoto)', () => {
    const { etichetta } = useLookupEtichettato(SORGENTE_K, { campoCodice: 'codice_interno' })
    cache.get('k').value = REGISTRI
    expect(etichetta('EVENT_LOG')).toBe('Eventi di dominio')
    expect(etichetta('TASK_RUN')).toBe('TASK_RUN')
    // Un codice non piu' fra i vivi (riga vecchia del diario): si legge lo stesso.
    expect(etichetta('RITIRATO')).toBe('RITIRATO')
    expect(etichetta(null)).toBe('')
  })

  it('il campo del codice si sceglie: `codice` di default, `codice_interno` per il lookup generico', () => {
    const perCodice = useLookupEtichettato({ chiave: 'a', fetcher: vi.fn() })
    cache.get('a').value = [{ codice: 'LOTTO', etichetta_key: 'config.tipi_entita.lotto' }]
    expect(perCodice.etichetta('LOTTO')).toBe('Lotto')
    const perInterno = useLookupEtichettato({ chiave: 'b', fetcher: vi.fn() }, { campoCodice: 'codice_interno' })
    cache.get('b').value = [{ codice: 'X', codice_interno: 'EVENT_LOG', etichetta_key: 'config.registri_giornale.event_log' }]
    expect(perInterno.etichetta('EVENT_LOG')).toBe('Eventi di dominio')
    expect(perInterno.etichetta('X')).toBe('X')
  })

  it('le opzioni: la voce «tutti» in testa solo se chiesta, poi il catalogo etichettato', () => {
    const senza = useLookupEtichettato(SORGENTE_K, { campoCodice: 'codice_interno' })
    cache.get('k').value = REGISTRI
    expect(senza.opzioni.value).toEqual([
      { value: 'EVENT_LOG', label: 'Eventi di dominio' },
      { value: 'TASK_RUN', label: 'TASK_RUN' },
    ])
    const con = useLookupEtichettato(SORGENTE_K, {
      campoCodice: 'codice_interno',
      tutti: () => dizionario['vendite.giornale.filtro_registro_tutti'],
    })
    expect(con.opzioni.value[0]).toEqual({ value: null, label: 'Tutti i registri' })
    expect(con.opzioni.value).toHaveLength(3)
    // Anche come stringa o ref.
    expect(useLookupEtichettato(SORGENTE_K, { tutti: 'Tutti' }).opzioni.value[0].label).toBe('Tutti')
    expect(useLookupEtichettato(SORGENTE_K, { tutti: ref('Tutti!') }).opzioni.value[0].label).toBe('Tutti!')
  })

  it('le opzioni seguono il catalogo: una riga nuova compare senza toccare codice', () => {
    const { opzioni } = useLookupEtichettato(SORGENTE_K, { campoCodice: 'codice_interno' })
    cache.get('k').value = REGISTRI
    expect(opzioni.value).toHaveLength(2)
    cache.get('k').value = [...REGISTRI, { codice_interno: 'PRATICHE_GIORNALE', etichetta_key: 'config.registri_giornale.pratiche_giornale' }]
    expect(opzioni.value).toHaveLength(3)
    expect(opzioni.value[2]).toEqual({ value: 'PRATICHE_GIORNALE', label: 'PRATICHE_GIORNALE' })
  })

  it('la cache e\' quella di useGlobalLookup: chiave passata com\'e\' col fetcher, composta da useLookupCodici col rel', () => {
    useLookupEtichettato({ chiave: 'config.tipi_entita', fetcher: vi.fn() })
    useLookupEtichettato({ rel: 'config.registri_giornale', includiObsoleti: false })
    useLookupEtichettato({ rel: 'config.registri_giornale' })
    expect(chiaviChieste).toEqual([
      'config.tipi_entita',
      'config.registri_giornale::no-obsoleti',
      'config.registri_giornale',
    ])
  })
})
