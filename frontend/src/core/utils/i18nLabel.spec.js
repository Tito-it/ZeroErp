// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il contratto dell'etichetta di un ruolo applicativo
//        (`etichettaRuoloApplicativo`, estratto 2026-09-27): la traduzione se
//        c'e', il CODICE se la chiave manca (mai il path della chiave a video),
//        '' senza codice. Le tre copie che sostituisce divergevano proprio qui.
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'

import { etichettaRuoloApplicativo } from './i18nLabel'

// Un vocabolario minimo al posto di vue-i18n: `t` traduce, `te` dice se c'e'.
const chiavi = { 'auth.ruolo_applicativo.OPERATORE': 'Operatore' }
const t = (k) => chiavi[k] ?? k
const te = (k) => k in chiavi

describe('etichettaRuoloApplicativo', () => {
  it('traduce il ruolo che ha la chiave', () => {
    expect(etichettaRuoloApplicativo(t, te, 'OPERATORE')).toBe('Operatore')
  })

  it('senza chiave mostra il codice, non il path della chiave', () => {
    expect(etichettaRuoloApplicativo(t, te, 'RUOLO_NUOVO')).toBe('RUOLO_NUOVO')
  })

  it('senza codice rende la stringa vuota: il segnaposto lo sceglie il chiamante', () => {
    expect(etichettaRuoloApplicativo(t, te, null)).toBe('')
    expect(etichettaRuoloApplicativo(t, te, '')).toBe('')
  })
})
