// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: `risolviBersaglio` — dal bersaglio di un errore a una destinazione,
//        con l'id nella FORMA dichiarata (2026-11-11, S-BE-1: ARTICOLO e
//        PROMO_ARTICOLO, il padre spento del require ATTIVO).
//
// Indice test:
//  1) ARTICOLO: l'id uuid resta stringa, si va alla lista col deep-link `?open=`
//  2) ARTICOLO: un id numerico non e' un articolo → nessun pulsante
//  3) PROMO_ARTICOLO: l'id diventa numero, lista promo col deep-link
//  4) un tipo numerico (FATTURA) con un uuid → nessun pulsante
//  5) area bloccata a chi legge → nessun pulsante
//  6) un tipo che nessuna schermata apre dal solo id (LISTINO_VERSIONE) → nessun pulsante
// ------------------------------------------------------------
import { describe, expect, it } from 'vitest'
import { BERSAGLIO_TIPI, risolviBersaglio } from './bersagli'

const UUID = '019bbee2-5f6a-704f-bbd0-34ed84db252d'
const libero = { isAreaBlocked: () => false, isSuperAdmin: false }

describe('risolviBersaglio', () => {
  it('1) ARTICOLO: uuid, lista articoli col deep-link', () => {
    const r = risolviBersaglio({ tipo: BERSAGLIO_TIPI.ARTICOLO, id: UUID }, libero)
    expect(r).toMatchObject({
      tipo: 'ARTICOLO', id: UUID, rotta: { name: 'catalogo-articoli', queryKey: 'open' },
    })
  })

  it('2) ARTICOLO: un id numerico non e\' un articolo', () => {
    expect(risolviBersaglio({ tipo: 'ARTICOLO', id: '42' }, libero)).toBeNull()
  })

  it('3) PROMO_ARTICOLO: id numerico, lista promo', () => {
    const r = risolviBersaglio({ tipo: BERSAGLIO_TIPI.PROMO_ARTICOLO, id: '12' }, libero)
    expect(r).toMatchObject({ id: 12, rotta: { name: 'vendite-promo-articoli', queryKey: 'open' } })
  })

  it('4) un tipo numerico con un uuid → null', () => {
    expect(risolviBersaglio({ tipo: 'FATTURA', id: UUID }, libero)).toBeNull()
  })

  it('5) area bloccata → null', () => {
    const bloccato = { isAreaBlocked: (area) => area === 'catalogo', isSuperAdmin: false }
    expect(risolviBersaglio({ tipo: 'ARTICOLO', id: UUID }, bloccato)).toBeNull()
  })

  it('6) LISTINO_VERSIONE non si apre dal solo id → null', () => {
    expect(risolviBersaglio({ tipo: 'LISTINO_VERSIONE', id: '3' }, libero)).toBeNull()
  })
})
