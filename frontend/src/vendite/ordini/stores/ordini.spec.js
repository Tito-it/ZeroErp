// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa l'emissione cross-tab di `generaDdt`: il verbo che evade un
//        ordine scrive su DUE entita' e lo store le avvisa entrambe
//        (frontend-standards §«Producer cross-tab», 2026-09-26). Fino a quel
//        giorno l'avviso al DDT stava nella dialog che lanciava il verbo.
// Note: l'api e' una spia che risponde l'envelope standard.
//
// Indice test:
//  1. avvisa ORDINE e DDT, con gli id giusti
//  2. senza `ddt_id` nella risposta avvisa solo l'ORDINE
//  3. se l'api fallisce l'errore risale e non parte nessun avviso
// ------------------------------------------------------------

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useOrdiniStore } from './ordini'
import { generaDdtFromOrdine } from '../api/ordiniApi'
import { useTabEvents } from '../../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../../core/constants'

// Tutti gli export che lo store importa: il modulo vero caricherebbe il
// client HTTP, che in ambiente node non ha `localStorage`.
vi.mock('../api/ordiniApi', () => ({
  cambiaStatoOrdine: vi.fn(),
  confermaOrdine: vi.fn(),
  createOrdine: vi.fn(),
  createRiga: vi.fn(),
  deleteOrdine: vi.fn(),
  deleteRiga: vi.fn(),
  emettiOrdine: vi.fn(),
  generaDdtFromOrdine: vi.fn(),
  getOrdine: vi.fn(),
  getRiepilogoIva: vi.fn(),
  listOrdini: vi.fn(),
  listRighe: vi.fn(),
  pushOrdineACommessa: vi.fn(),
  updateOrdine: vi.fn(),
  updateRiga: vi.fn(),
}))

// Scopo: raccoglie gli eventi emessi durante il test, come [entita', id].
function ascolta() {
  const eventi = []
  const stop = useTabEvents().onDataChanged(e => eventi.push([e.entityType, e.entityId]))
  return { eventi, stop }
}

describe('store ordini — generaDdt', () => {
  beforeEach(() => { setActivePinia(createPinia()) })

  it('avvisa ORDINE e DDT, con gli id giusti', async () => {
    generaDdtFromOrdine.mockResolvedValue({ data: { data: { ddt_id: 55 } } })
    const { eventi, stop } = ascolta()
    const esito = await useOrdiniStore().generaDdt(12, [{ riga_id: 1, qta: 2 }])
    stop()
    expect(generaDdtFromOrdine).toHaveBeenCalledWith(12, [{ riga_id: 1, qta: 2 }])
    expect(esito).toEqual({ ddt_id: 55 })
    expect(eventi).toEqual([[TAB_ENTITIES.ORDINE, 12], [TAB_ENTITIES.DDT, 55]])
  })

  it('senza ddt_id nella risposta avvisa solo l\'ORDINE', async () => {
    generaDdtFromOrdine.mockResolvedValue({ data: { data: {} } })
    const { eventi, stop } = ascolta()
    await useOrdiniStore().generaDdt(12)
    stop()
    expect(eventi).toEqual([[TAB_ENTITIES.ORDINE, 12]])
  })

  it('se l\'api fallisce l\'errore risale e non parte nessun avviso', async () => {
    generaDdtFromOrdine.mockRejectedValue(new Error('rifiutato'))
    const { eventi, stop } = ascolta()
    await expect(useOrdiniStore().generaDdt(12)).rejects.toThrow('rifiutato')
    stop()
    expect(eventi).toEqual([])
  })
})
