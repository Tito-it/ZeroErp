// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il cambio di stato della commessa nello store: la
//        dichiarazione arriva all'api, e l'annullo avvisa i tab dei documenti
//        che riapre (brief-db-annullo-a-valle-riapre-a-monte; frontend-
//        standards §«Producer cross-tab»).
// Note: l'api e' una spia che risponde l'envelope standard.
//
// Indice test:
//  1. annullo: la dichiarazione arriva all'api e si avvisano i documenti che si riaprono
//  2. un'altra transizione non avvisa nessuno
//  3. se l'api rifiuta (la domanda del DB) l'errore risale e non parte nessun avviso
// ------------------------------------------------------------

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useCommesseStore } from './commesse'
import { cambiaStatoCommessa } from '../api/commesse'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../core/constants'

// Il modulo vero caricherebbe il client HTTP, che in ambiente node non ha
// `localStorage`.
vi.mock('../api/commesse', () => ({
  cambiaStatoCommessa: vi.fn(),
}))

// Scopo: raccoglie gli eventi emessi durante il test, come [entita', id].
function ascolta() {
  const eventi = []
  const stop = useTabEvents().onDataChanged(e => eventi.push([e.entityType, e.entityId]))
  return { eventi, stop }
}

describe('store commesse — cambiaStato', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    cambiaStatoCommessa.mockReset()
  })

  it('annullo: la dichiarazione arriva all\'api e si avvisano i documenti che si riaprono', async () => {
    cambiaStatoCommessa.mockResolvedValue({ data: { data: { stato_a: 'ANNULLATA' } } })
    const { eventi, stop } = ascolta()
    const esito = await useCommesseStore().cambiaStato(7, 'ANNULLATA', { legami_confermati: 3 })
    stop()
    expect(cambiaStatoCommessa).toHaveBeenCalledWith(7, 'ANNULLATA', { legami_confermati: 3 })
    expect(esito).toEqual({ stato_a: 'ANNULLATA' })
    const avvisate = eventi.map(([entita]) => entita)
    for (const entita of [
      TAB_ENTITIES.PREVENTIVO, TAB_ENTITIES.ORDINE, TAB_ENTITIES.CONTRATTO,
      TAB_ENTITIES.DDT, TAB_ENTITIES.RESO,
    ]) expect(avvisate).toContain(entita)
  })

  it('un\'altra transizione non avvisa nessuno', async () => {
    cambiaStatoCommessa.mockResolvedValue({ data: { data: { stato_a: 'CHIUSA' } } })
    const { eventi, stop } = ascolta()
    await useCommesseStore().cambiaStato(7, 'CHIUSA')
    stop()
    expect(cambiaStatoCommessa).toHaveBeenCalledWith(7, 'CHIUSA', {})
    expect(eventi).toEqual([])
  })

  it('se l\'api rifiuta (la domanda del DB) l\'errore risale e non parte nessun avviso', async () => {
    cambiaStatoCommessa.mockRejectedValue(new Error('409'))
    const { eventi, stop } = ascolta()
    await expect(useCommesseStore().cambiaStato(7, 'ANNULLATA')).rejects.toThrow('409')
    stop()
    expect(eventi).toEqual([])
  })
})
