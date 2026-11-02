// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: il BB del riallineamento delle righe per pagina (`core/allineaMisuraConfig`).
//
// Indice test:
//   1. il primo caricamento applica la misura della configurazione
//   2. una ricarica con la stessa misura non applica niente
//   3. una misura nuova della configurazione si applica
//   4. config senza misura: niente
//   5. reset: la stessa misura si riapplica
//   6. due allineatori non condividono memoria
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'
import { allineaMisuraConfig } from './allineaMisuraConfig'

describe('allineaMisuraConfig', () => {
  it('1. il primo caricamento applica la misura', () => {
    expect(allineaMisuraConfig().daApplicare({ pagina_dimensione: 10 })).toBe(10)
  })

  it('2. una ricarica con la stessa misura non applica niente', () => {
    const a = allineaMisuraConfig()
    a.daApplicare({ pagina_dimensione: 10 })
    expect(a.daApplicare({ pagina_dimensione: 10 })).toBeNull()
  })

  it('3. una misura nuova della configurazione si applica', () => {
    const a = allineaMisuraConfig()
    a.daApplicare({ pagina_dimensione: 10 })
    expect(a.daApplicare({ pagina_dimensione: 50 })).toBe(50)
  })

  it('4. config senza misura: niente', () => {
    const a = allineaMisuraConfig()
    expect(a.daApplicare(null)).toBeNull()
    expect(a.daApplicare({})).toBeNull()
  })

  it('5. reset: la stessa misura si riapplica', () => {
    const a = allineaMisuraConfig()
    a.daApplicare({ pagina_dimensione: 10 })
    a.reset()
    expect(a.daApplicare({ pagina_dimensione: 10 })).toBe(10)
  })

  it('6. due allineatori non condividono memoria', () => {
    const a = allineaMisuraConfig()
    const b = allineaMisuraConfig()
    a.daApplicare({ pagina_dimensione: 10 })
    expect(b.daApplicare({ pagina_dimensione: 10 })).toBe(10)
  })
})
