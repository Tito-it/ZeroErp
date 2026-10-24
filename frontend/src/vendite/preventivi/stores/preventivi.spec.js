// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa l'emissione cross-tab di `generaOrdine` (ramo merce dello
//        smistamento): il verbo scrive sul preventivo e fa nascere un ordine,
//        e lo store avvisa entrambe le entita' (frontend-standards §«Producer
//        cross-tab», 2026-09-26). Fino a quel giorno l'avviso all'ordine stava
//        nel drawer che apriva la dialog di smistamento.
// Note: l'api e' una spia che risponde l'envelope standard.
//
// Indice test:
//  1. avvisa PREVENTIVO e ORDINE, con gli id giusti
//  2. senza `ordine_id` nella risposta avvisa solo il PREVENTIVO
//  3. se l'api fallisce l'errore risale e non parte nessun avviso
//  4. date in blocco: scrivere avvisa il PREVENTIVO, l'anteprima no
// ------------------------------------------------------------

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { usePreventiviStore } from './preventivi'
import { aggiornaDateConsegna, generaOrdineFromPreventivo } from '../api/preventiviApi'
import { useTabEvents } from '../../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../../core/constants'

// Tutti gli export che lo store importa: il modulo vero caricherebbe il
// client HTTP, che in ambiente node non ha `localStorage`.
vi.mock('../api/preventiviApi', () => ({
  aggiornaDateConsegna: vi.fn(),
  listPreventivi: vi.fn(),
  getPreventivo: vi.fn(),
  createPreventivo: vi.fn(),
  updatePreventivo: vi.fn(),
  deletePreventivo: vi.fn(),
  cambiaStatoPreventivo: vi.fn(),
  emettiPreventivo: vi.fn(),
  creaRevisione: vi.fn(),
  listRevisioni: vi.fn(),
  createRiga: vi.fn(),
  updateRiga: vi.fn(),
  deleteRiga: vi.fn(),
  getRiepilogoIva: vi.fn(),
  pushCommessa: vi.fn(),
  getSmistamento: vi.fn(),
  generaPratica: vi.fn(),
  generaOrdineFromPreventivo: vi.fn(),
}))

// Scopo: raccoglie gli eventi emessi durante il test, come [entita', id].
function ascolta() {
  const eventi = []
  const stop = useTabEvents().onDataChanged(e => eventi.push([e.entityType, e.entityId]))
  return { eventi, stop }
}

describe('store preventivi — generaOrdine', () => {
  beforeEach(() => { setActivePinia(createPinia()) })

  it('avvisa PREVENTIVO e ORDINE, con gli id giusti', async () => {
    generaOrdineFromPreventivo.mockResolvedValue({ data: { data: { ordine_id: 31, numero: 'OV-1' } } })
    const { eventi, stop } = ascolta()
    const esito = await usePreventiviStore().generaOrdine(8, [101, 102])
    stop()
    expect(generaOrdineFromPreventivo).toHaveBeenCalledWith(8, [101, 102])
    expect(esito).toEqual({ ordine_id: 31, numero: 'OV-1' })
    expect(eventi).toEqual([[TAB_ENTITIES.PREVENTIVO, 8], [TAB_ENTITIES.ORDINE, 31]])
  })

  it('senza ordine_id nella risposta avvisa solo il PREVENTIVO', async () => {
    generaOrdineFromPreventivo.mockResolvedValue({ data: { data: {} } })
    const { eventi, stop } = ascolta()
    await usePreventiviStore().generaOrdine(8)
    stop()
    expect(eventi).toEqual([[TAB_ENTITIES.PREVENTIVO, 8]])
  })

  it('se l\'api fallisce l\'errore risale e non parte nessun avviso', async () => {
    generaOrdineFromPreventivo.mockRejectedValue(new Error('rifiutato'))
    const { eventi, stop } = ascolta()
    await expect(usePreventiviStore().generaOrdine(8)).rejects.toThrow('rifiutato')
    stop()
    expect(eventi).toEqual([])
  })
})

// brief-db-date-consegna-righe-in-blocco: fino al 2026-10-12 il dialog
// chiamava l'api senza avvisare la lista.
describe('store preventivi — date di consegna in blocco', () => {
  beforeEach(() => { setActivePinia(createPinia()) })

  it('scrivere avvisa il PREVENTIVO, l\'anteprima no', async () => {
    const response = { data: { data: { aggiornate: 1, data: '2026-11-20' } } }
    aggiornaDateConsegna.mockResolvedValue(response)
    const { eventi, stop } = ascolta()
    const store = usePreventiviStore()
    await store.aggiornaDateConsegna(8, { anteprima: true })
    expect(eventi).toEqual([])
    expect(await store.aggiornaDateConsegna(8, { anteprima: false })).toBe(response)
    stop()
    expect(eventi).toEqual([[TAB_ENTITIES.PREVENTIVO, 8]])
  })
})
