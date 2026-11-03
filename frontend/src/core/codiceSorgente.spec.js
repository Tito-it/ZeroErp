// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa la scelta degli indirizzi del codice sorgente e della licenza
//        (`core/codiceSorgente.js`): la variabile di build vince, e un valore
//        che non porterebbe da nessuna parte ripiega sul predefinito.
//
// Indice test:
//  1. un indirizzo http(s) si usa, senza spazi ai bordi
//  2. assente, vuoto o di soli spazi → il predefinito
//  3. uno schema che non e' http(s) → il predefinito
//  4. http(s) senza host o con spazi dentro → il predefinito
//  5. licenza: la variabile valida vince
//  6. licenza: senza variabile, il file LICENSE del sorgente (anche fork)
// ------------------------------------------------------------

import { describe, expect, it } from 'vitest'
import { CODICE_SORGENTE_URL_PREDEFINITO, risolviUrlCodiceSorgente, risolviUrlLicenza } from './codiceSorgente'

describe('risolviUrlCodiceSorgente', () => {
  it('usa un indirizzo http(s), senza spazi ai bordi', () => {
    expect(risolviUrlCodiceSorgente('  https://git.example.org/fork  ')).toBe('https://git.example.org/fork')
    expect(risolviUrlCodiceSorgente('http://intranet/zeroerp')).toBe('http://intranet/zeroerp')
  })

  it('assente, vuoto o di soli spazi → il predefinito', () => {
    for (const valore of [undefined, null, '', '   ']) {
      expect(risolviUrlCodiceSorgente(valore)).toBe(CODICE_SORGENTE_URL_PREDEFINITO)
    }
  })

  it('uno schema che non e\' http(s) → il predefinito', () => {
    for (const valore of ['javascript:alert(1)', 'git@github.com:x/y.git', '/sorgente']) {
      expect(risolviUrlCodiceSorgente(valore)).toBe(CODICE_SORGENTE_URL_PREDEFINITO)
    }
  })

  it('http(s) senza host o con spazi dentro → il predefinito', () => {
    for (const valore of ['https://', 'https://git.example.org/un fork']) {
      expect(risolviUrlCodiceSorgente(valore)).toBe(CODICE_SORGENTE_URL_PREDEFINITO)
    }
  })
})

describe('risolviUrlLicenza', () => {
  it('la variabile valida vince', () => {
    expect(risolviUrlLicenza(' https://example.org/licenza ', CODICE_SORGENTE_URL_PREDEFINITO))
      .toBe('https://example.org/licenza')
  })

  it('senza variabile, il file LICENSE del sorgente (anche fork)', () => {
    expect(risolviUrlLicenza(undefined, CODICE_SORGENTE_URL_PREDEFINITO))
      .toBe(`${CODICE_SORGENTE_URL_PREDEFINITO}/blob/HEAD/LICENSE`)
    expect(risolviUrlLicenza('javascript:alert(1)', 'https://git.example.org/fork.git/'))
      .toBe('https://git.example.org/fork/blob/HEAD/LICENSE')
  })
})
