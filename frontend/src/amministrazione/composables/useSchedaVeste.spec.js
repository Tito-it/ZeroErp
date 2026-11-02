// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Dove porta una veste della lista «Altri accessi» (`destinazioneVeste`):
//        la scheda del cliente se ce n'e' UNA, del fornitore, altrimenti del
//        soggetto — mai un id scelto a caso fra piu' schede cliente (§7.4).
//
// Indice test:
//   1) un cliente: la sua scheda
//   2) piu' clienti: la scheda del soggetto, che li elenca
//   3) un fornitore: la sua scheda
//   4) nessun soggetto: nessuna destinazione
// ------------------------------------------------------------

import { describe, expect, it } from 'vitest'
import { destinazioneVeste } from './useSchedaVeste'

const SOGGETTO = { soggetto_id: 'u-1', soggetto_ruolo_id: 9, soggetto: 'ACME' }

describe('destinazioneVeste', () => {
  it('un cliente: la sua scheda', () => {
    expect(destinazioneVeste({ ...SOGGETTO, cliente_ids: [5], fornitore_id: null }))
      .toEqual({ rotta: 'anagrafiche-clienti', tipoRuolo: 'CL', entitaId: 5 })
  })

  it('piu\' clienti: la scheda del soggetto, che li elenca', () => {
    expect(destinazioneVeste({ ...SOGGETTO, cliente_ids: [5, 6], fornitore_id: null }))
      .toEqual({ rotta: 'anagrafiche-soggetti', tipoRuolo: null, entitaId: null })
  })

  it('un fornitore: la sua scheda', () => {
    expect(destinazioneVeste({ ...SOGGETTO, cliente_ids: [], fornitore_id: 77 }))
      .toEqual({ rotta: 'anagrafiche-fornitori', tipoRuolo: 'FO', entitaId: 77 })
  })

  it('nessun soggetto: nessuna destinazione', () => {
    expect(destinazioneVeste({ cliente_ids: [] })).toBeNull()
    expect(destinazioneVeste(null)).toBeNull()
  })
})
