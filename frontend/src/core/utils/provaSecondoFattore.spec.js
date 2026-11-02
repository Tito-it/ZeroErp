// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: La PROVA del secondo fattore, dalla scelta dell'utente al corpo sul
//        filo: `provaSecondoFattore` sceglie fra codice dell'app e codice di
//        recupero, le API di `core/api/secondoFattore.js` la traducono in
//        `codice` / `codice_recupero`.
// Note: ⛔ Un ramo sbagliato qui NON da' errore a video: manda il codice
//        dell'app come codice di recupero (o viceversa) e il backend risponde
//        «codice non valido» a un codice giusto. Per questo si prova anche il
//        TRASPORTO, un test per punto che traduce (secondo passo del login,
//        disattivazione), con `api` finto: si finge il contorno, non la
//        traduzione.
//
// Indice test:
//   1) codice dell'app → { codice }
//   2) codice di recupero → { codiceRecupero }
//   3) secondo passo del login: sfida + codice / codice_recupero sul filo
//   4) disattivazione: codice / codice_recupero sul filo, mai entrambi
// ------------------------------------------------------------
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('../api', () => ({ default: { post: vi.fn(), get: vi.fn() } }))

import api from '../api'
import { provaSecondoFattore } from './provaSecondoFattore'
import { disattivaSecondoFattore, secondoPassoLogin } from '../api/secondoFattore'

beforeEach(() => {
  api.post.mockReset()
})

describe('provaSecondoFattore', () => {
  it('1) col codice dell\'app torna { codice }', () => {
    expect(provaSecondoFattore('123456', false)).toEqual({ codice: '123456' })
  })

  it('2) col codice di recupero torna { codiceRecupero }', () => {
    expect(provaSecondoFattore('ABCD-EFGH', true)).toEqual({ codiceRecupero: 'ABCD-EFGH' })
  })
})

describe('la prova sul filo', () => {
  it('3) secondo passo del login: la sfida accanto al codice giusto', () => {
    secondoPassoLogin('/admin/token/secondo-fattore/', 'sf1', provaSecondoFattore('123456', false))
    expect(api.post).toHaveBeenLastCalledWith('/admin/token/secondo-fattore/', { sfida: 'sf1', codice: '123456' })

    secondoPassoLogin('/admin/token/secondo-fattore/', 'sf1', provaSecondoFattore('ABCD-EFGH', true))
    expect(api.post).toHaveBeenLastCalledWith('/admin/token/secondo-fattore/', { sfida: 'sf1', codice_recupero: 'ABCD-EFGH' })
  })

  it('4) disattivazione: codice OPPURE codice_recupero', () => {
    disattivaSecondoFattore(provaSecondoFattore('123456', false))
    expect(api.post).toHaveBeenLastCalledWith('/auth/secondo-fattore/disattiva/', { codice: '123456' })

    disattivaSecondoFattore(provaSecondoFattore('ABCD-EFGH', true))
    expect(api.post).toHaveBeenLastCalledWith('/auth/secondo-fattore/disattiva/', { codice_recupero: 'ABCD-EFGH' })
  })
})
