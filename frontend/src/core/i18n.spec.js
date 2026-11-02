// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il contratto di `intlLocale` (estratto 2026-10-09, regola del 2):
//        ogni lingua UI supportata ha la sua locale Intl, e una lingua non
//        nota cade su quella di default invece di dare `undefined` (che
//        `toLocaleDateString` leggerebbe come la lingua del browser).
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'

import { DEFAULT_LOCALE, SUPPORTED_LOCALES, intlLocale } from './i18n'

describe('intlLocale', () => {
  it('ogni lingua supportata ha una locale Intl valida', () => {
    for (const lingua of SUPPORTED_LOCALES) {
      const loc = intlLocale(lingua)
      expect(loc.startsWith(`${lingua}-`)).toBe(true)
      expect(Intl.DateTimeFormat.supportedLocalesOf([loc])).toEqual([loc])
    }
  })

  it('una lingua non nota cade sulla locale di default', () => {
    expect(intlLocale('xx')).toBe(intlLocale(DEFAULT_LOCALE))
    expect(intlLocale(undefined)).toBe(intlLocale(DEFAULT_LOCALE))
  })
})
