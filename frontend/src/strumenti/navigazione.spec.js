// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il dominio Strumenti raccoglie voci di aree DIVERSE (code: `strumenti`,
//        giornale: `vendite`, email dell'operatore: nessuna — `skip_area_check`
//        BE). Il cancello d'area sta quindi sulla voce, non sul dominio
//        (Tid 2026-09-26, assorbito il dominio «Personale»).
// Note: ⛔ Il difetto che si presidia non da' errori: un `schemaDb` rimesso sul
//       dominio farebbe sparire le email (sidebar e router) a chi non ha
//       l'area `strumenti`, mentre il backend risponde. Un cancello a video
//       che il backend non ha.
//
// Indice test:
//  1. il dominio Strumenti non dichiara un'area e non e' riservato all'admin
//  2. ogni voce porta l'area del suo endpoint (email: nessuna)
//  3. le voci puntano a rotte sotto /strumenti/
//  4. il dominio Personale non esiste piu'
//  5. Diagnostica: gruppo adminOnly con i quattro diari, figli senza cancello
//     proprio
//  6. Amm. software non porta piu' i quattro diari
// ------------------------------------------------------------

import { describe, expect, it } from 'vitest'

import { DOMAINS, DOMAIN_MENUS, flattenMenu } from '../core/navigation'

describe('dominio Strumenti', () => {
  const strumenti = DOMAINS.find((d) => d.key === 'strumenti')
  const voce = (key) => DOMAIN_MENUS.strumenti.find((v) => v.key === key)

  it('non dichiara un\'area e non e\' riservato all\'admin', () => {
    expect(strumenti).toBeDefined()
    expect(strumenti.schemaDb).toBeUndefined()
    expect(strumenti.adminOnly).toBeFalsy()
  })

  it('ogni voce porta l\'area del suo endpoint (email: nessuna)', () => {
    expect(voce('code-lavoro').requireArea).toBe('strumenti')
    expect(voce('giornale').requireArea).toBe('vendite')
    expect(voce('email')).toBeDefined()
    expect(voce('email').requireArea).toBeUndefined()
  })

  it('le voci puntano a rotte sotto /strumenti/', () => {
    for (const v of flattenMenu(DOMAIN_MENUS.strumenti).filter((v) => v.to)) {
      expect(v.to.startsWith('/strumenti/')).toBe(true)
    }
  })

  it('il dominio Personale non esiste piu\'', () => {
    expect(DOMAINS.find((d) => d.key === 'personale')).toBeUndefined()
    expect(DOMAIN_MENUS.personale).toBeUndefined()
  })

  const DIARI = ['processi-automatici', 'audit-log', 'error-log', 'email-log']

  it('Diagnostica: gruppo adminOnly con i quattro diari', () => {
    // ⛔ Il cancello sta sul GRUPPO: un figlio che ne dichiarasse uno suo
    //    sarebbe la copia che diverge.
    const diagnostica = voce('diagnostica')
    expect(diagnostica.adminOnly).toBe(true)
    expect(diagnostica.children.map((c) => c.key)).toEqual(DIARI)
    for (const c of diagnostica.children) {
      expect(c.to).toBe(`/strumenti/diagnostica/${c.key}`)
      expect(c.adminOnly).toBeUndefined()
    }
  })

  it('Amm. software non porta piu\' i quattro diari', () => {
    const chiavi = flattenMenu(DOMAIN_MENUS['amm-software']).map((v) => v.key)
    for (const k of DIARI) expect(chiavi).not.toContain(k)
  })
})
