// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il contratto degli store della STORIA di un'entita'
//        (`vendite.giornale` su una fattura o su un lotto): il padre COMPOSTO
//        del core (entita' + emittente) — l'id nel path, l'emittente in query
//        come `emittente_soggetto_ruolo_id`, cioe' il `lista_emittente_param`
//        delle due view.
// Note: ⛔ Il caso che conta e' l'emittente mancante: nessuna fetch, perche'
//       verrebbe rifiutata (422) a chi ne vede piu' d'uno.
//
// Indice test:
//  1. senza emittente la lista non legge, ed e' in attesa
//  2. fattura: id nel path, emittente in query, ordine del preset (quando desc)
//  3. lotto: il filtro «solo problemi» viaggia come `info=false`, e «tutto» e' neutro
//  4. i contatori di cio' che il filtro nasconde arrivano dal payload
//  5. i due store sono DUE: la pagina di uno non tocca l'altro
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('../api/fatture', () => ({
  listFatturaGiornale: vi.fn(() => Promise.resolve({
    data: { data: { results: [], count: 0, ritirate_count: 2 } },
  })),
}))
vi.mock('../api/lotti', () => ({
  listLottoGiornale: vi.fn(() => Promise.resolve({
    data: { data: { results: [], count: 0, ritirate_count: 1, info_count: 173 } },
  })),
}))

import { listFatturaGiornale } from '../api/fatture'
import { listLottoGiornale } from '../api/lotti'
import {
  useFatturaGiornaleStore,
  useLottoGiornaleStore,
} from './giornaleEntita'

describe('giornaleEntita store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    listFatturaGiornale.mockClear()
    listLottoGiornale.mockClear()
  })

  it('1. senza emittente la lista non legge, ed e\' in attesa', async () => {
    const store = useFatturaGiornaleStore()
    store.entitaId = 7
    expect(await store.fetchList()).toBe(false)
    expect(listFatturaGiornale).not.toHaveBeenCalled()
    expect(store.attesaPadre).toBe(true)
  })

  it('2. fattura: id nel path, emittente in query, ordine del preset', async () => {
    const store = useFatturaGiornaleStore()
    store.entitaId = 7
    store.emittenteId = 3
    await store.fetchList()
    expect(listFatturaGiornale).toHaveBeenCalledTimes(1)
    const [fatturaId, params] = listFatturaGiornale.mock.calls[0]
    expect(fatturaId).toBe(7)
    expect(params).toMatchObject({
      emittente_soggetto_ruolo_id: 3, order_by: 'quando', order_dir: 'desc', offset: 0,
    })
    // La Storia della fattura non ha filtri propri: `info` e' del lotto.
    expect(params).not.toHaveProperty('info')
  })

  it('3. lotto: «solo problemi» viaggia come info=false, «tutto» e\' neutro', async () => {
    const store = useLottoGiornaleStore()
    store.entitaId = 6260
    store.emittenteId = 3
    await store.fetchList()
    const [lottoId, params] = listLottoGiornale.mock.calls[0]
    expect(lottoId).toBe(6260)
    expect(params).toMatchObject({ info: false, emittente_soggetto_ruolo_id: 3 })
    expect(store.chiaviFiltro).toEqual(['info'])
    expect(store.filtriNeutri).toEqual({ info: true })
  })

  it('4. i contatori di cio\' che il filtro nasconde arrivano dal payload', async () => {
    const store = useLottoGiornaleStore()
    store.entitaId = 6260
    store.emittenteId = 3
    await store.fetchList()
    expect(store.infoCount).toBe(173)
    expect(store.ritirateCount).toBe(1)
    store.reset()
    expect(store.infoCount).toBe(0)
    expect(store.ritirateCount).toBe(0)
  })

  it('5. i due store sono DUE: la pagina di uno non tocca l\'altro', () => {
    const fattura = useFatturaGiornaleStore()
    const lotto = useLottoGiornaleStore()
    expect(fattura).not.toBe(lotto)
    lotto.filters.offset = 50
    expect(fattura.filters.offset).toBe(0)
  })
})
