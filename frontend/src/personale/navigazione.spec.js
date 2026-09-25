// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il dominio Personale e' visibile a OGNI operatore interno: e' la forma
//        a video dello `skip_area_check` delle rotte BE che serve (la lista
//        del log email, 2026-09-26). Chi vede quale riga lo decide la RLS.
// Note: ⛔ Il difetto che si presidia non da' errori: un `schemaDb` aggiunto al
//       dominio lo farebbe sparire (sidebar e router) a chi non ha quell'area,
//       mentre il backend risponde. Un cancello a video che il backend non ha.
//
// Indice test:
//  1. il dominio Personale non dichiara un'area e non e' riservato all'admin
//  2. le sue voci puntano a rotte sotto /personale/
// ------------------------------------------------------------

import { describe, expect, it } from 'vitest'

import { DOMAINS, DOMAIN_MENUS } from '../core/navigation'

describe('dominio Personale', () => {
  const personale = DOMAINS.find((d) => d.key === 'personale')

  it('non dichiara un\'area e non e\' riservato all\'admin', () => {
    expect(personale).toBeDefined()
    expect(personale.schemaDb).toBeUndefined()
    expect(personale.adminOnly).toBeFalsy()
  })

  it('le sue voci puntano a rotte sotto /personale/', () => {
    const voci = DOMAIN_MENUS.personale
    expect(voci.map((v) => v.key)).toContain('email')
    for (const voce of voci) {
      expect(voce.to.startsWith('/personale/')).toBe(true)
      expect(voce.requireArea).toBeUndefined()
    }
  })
})
