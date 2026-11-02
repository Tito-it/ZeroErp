// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il contratto degli store-lista dei documenti generati di una
//        sorgente (`documenti.documenti_sorgente`, lista 84): uno store per
//        sorgente, la sorgente nel path, l'emittente del documento in query
//        (`emittente_fiscale_id`, il `lista_emittente_param` della view), la
//        paginazione del core.
// Note: ⛔ Il caso che conta di piu' e' il 2: due sorgenti diverse NON
//       condividono stato. Uno store unico con la sorgente dentro si farebbe
//       scrivere addosso pagina e righe dalla prossima apertura di un'altra
//       sorgente (`feedback_estrarre_non_condividere_stato`).
//
// Indice test:
//  1. la fetch manda la sorgente nel path, l'emittente in query e i parametri di lista
//  2. due sorgenti hanno due store distinti
//  3. senza emittente la lista non legge, ed e' in attesa (padre composto)
//  4. un codice sorgente non registrato solleva
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('../../core/api', () => ({
  default: {
    get: vi.fn(() => Promise.resolve({ data: { data: { results: [{ id: 1 }], count: 1 } } })),
    post: vi.fn(),
  },
}))

import api from '../../core/api'
import { useDocumentiSorgenteListaStore } from './documentiSorgenteLista'

describe('documentiSorgenteLista store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    api.get.mockClear()
  })

  it('1. sorgente nel path, emittente in query, parametri di lista', async () => {
    const store = useDocumentiSorgenteListaStore('PREVENTIVO')
    store.sorgenteId = 7
    store.emittenteId = 3
    await store.fetchList()
    expect(api.get).toHaveBeenCalledTimes(1)
    const [url, { params }] = api.get.mock.calls[0]
    expect(url).toBe('/vendite/preventivi/7/documenti/')
    expect(params).toMatchObject({
      emittente_fiscale_id: 3,
      order_by: 'generato_at',
      order_dir: 'desc',
      limit: 25,
      offset: 0,
    })
    expect(store.items).toEqual([{ id: 1 }])
    expect(store.totalRecords).toBe(1)
  })

  it('2. due sorgenti, due store distinti', async () => {
    const preventivi = useDocumentiSorgenteListaStore('PREVENTIVO')
    const fatture = useDocumentiSorgenteListaStore('FATTURA')
    expect(preventivi).not.toBe(fatture)
    fatture.sorgenteId = 9
    fatture.emittenteId = 3
    await fatture.fetchList()
    expect(api.get.mock.calls[0][0]).toBe('/vendite/fatture/9/documenti/')
    expect(preventivi.items).toEqual([])
  })

  // ⛔ Fino al 2026-09-27 la lista partiva anche senza emittente, e al super
  //    admin su «Tutti» quella lettura tornava 422. Ora aspetta, e lo dice.
  it('3. senza emittente la lista non legge, ed e\' in attesa', async () => {
    const store = useDocumentiSorgenteListaStore('DDT_VENDITA')
    store.sorgenteId = 4
    expect(await store.fetchList()).toBe(false)
    expect(api.get).not.toHaveBeenCalled()
    expect(store.attesaPadre).toBe(true)
  })

  it('4. un codice sorgente non registrato solleva', () => {
    expect(() => useDocumentiSorgenteListaStore('INESISTENTE')).toThrow(/non mappato/)
  })
})
