// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: `motivoDaCodiceBlocco` — la frase di un verbo spento quando la riga
//        porta il SOLO codice del motivo (`<verbo>_blocco`) e la chiave e'
//        convenzione del DB (brief-db-date-consegna-righe-in-blocco §8).
//
// Indice test:
//  1) nessun codice: stringa vuota (azione accesa)
//  2) codice con chiave tradotta: la frase, dalla chiave minuscola
//  3) codice senza traduzione: il codice (fail-visible)
// ------------------------------------------------------------
import { describe, expect, it } from 'vitest'
import { motivoDaCodiceBlocco } from './bloccoMotivo'

const FRASI = { 'vendite.ordini.data_consegna_confermata_reason.riga_spedita': 'gia\' partita' }
const t = (chiave) => FRASI[chiave] ?? chiave
const te = (chiave) => chiave in FRASI

describe('motivoDaCodiceBlocco', () => {
  it('nessun codice: stringa vuota', () => {
    expect(motivoDaCodiceBlocco(t, te, null, 'vendite.ordini.data_consegna_confermata_reason')).toBe('')
  })

  it('codice con chiave tradotta: la frase', () => {
    expect(motivoDaCodiceBlocco(t, te, 'RIGA_SPEDITA', 'vendite.ordini.data_consegna_confermata_reason'))
      .toBe('gia\' partita')
  })

  it('codice senza traduzione: il codice', () => {
    expect(motivoDaCodiceBlocco(t, te, 'NUOVO_MOTIVO', 'vendite.ordini.data_consegna_confermata_reason'))
      .toBe('NUOVO_MOTIVO')
  })
})
