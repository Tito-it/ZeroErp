// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: I codici sorgente del motore documentale stanno in un punto solo
//        (`SORGENTE_CODES`), e la chiave E' il codice di `config.sorgenti`.
//        Il 2026-10-19 tre dialog di emissione si tenevano una costante locale
//        (`const SORGENTE_CODE = 'CONTRATTO'`) e tre liste un attributo scritto
//        a mano (`sorgente-code="PREVENTIVO"`), accanto ai gemelli che usavano
//        gia' `SORGENTE_CODES`; e la chiave del DDT era `DDT`, un nome corto
//        per il codice `DDT_VENDITA` (brief-db-grammatica-unica-documenti).
//        Un codice scritto male non da' errore: l'anteprima e la lista dei
//        documenti generati restano vuote.
//
// Indice test:
//  1. la chiave di ogni codice e' il codice
//  2. nessun componente scrive a mano un codice sorgente in `sorgente-code`
// ------------------------------------------------------------
import { describe, it, expect } from 'vitest'
import { SORGENTE_CODES } from './constants'

const sorgenti = import.meta.glob(
  ['../**/*.vue', '../**/*.js', '!../**/*.spec.js', '!../**/*.test.js'],
  { query: '?raw', import: 'default', eager: true },
)

// Un codice passato a `sorgente-code` come letterale: l'attributo statico
// (`sorgente-code="X"`) o una costante locale col nome della prop.
const LETTERALE = /\bsorgente-code="[A-Z_]+"|\bconst SORGENTE_CODE\s*=\s*['"]/g

describe('SORGENTE_CODES', () => {
  it('la chiave di ogni codice e\' il codice', () => {
    for (const [chiave, codice] of Object.entries(SORGENTE_CODES)) {
      expect(chiave, `SORGENTE_CODES.${chiave}`).toBe(codice)
    }
  })

  it('nessun componente scrive a mano un codice sorgente in sorgente-code', () => {
    expect(Object.keys(sorgenti).length).toBeGreaterThan(100)
    const violazioni = []
    for (const [file, testo] of Object.entries(sorgenti)) {
      const trovati = testo.match(LETTERALE) ?? []
      if (trovati.length) violazioni.push(`${file}: ${trovati.join(', ')}`)
    }
    expect(violazioni, 'usare SORGENTE_CODES di documenti/constants').toEqual([])
  })
})
