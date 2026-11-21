// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: il BB della voce del regime fiscale del record (`voceRegimeFiscale`).
//
// Indice test:
//   1. il codice a video e' `regime_fiscale_codice`, non il codice interno
//   2. record senza regime (fornitore privato) o dettaglio assente: null
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'
import { voceRegimeFiscale } from './voceRegimeFiscale'

describe('voceRegimeFiscale', () => {
  it('1. il codice a video e\' regime_fiscale_codice, non il codice interno', () => {
    // Costruito apposta con le due colonne diverse: nel seed di oggi coincidono.
    expect(voceRegimeFiscale({
      regime_fiscale_rf: 'RF93',
      regime_fiscale_codice: 'E2E-RF93',
      regime_fiscale_descrizione: 'Regime di prova',
    })).toEqual({
      codice_interno: 'RF93',
      codice: 'E2E-RF93',
      descrizione: 'Regime di prova',
    })
  })

  it('2. record senza regime o dettaglio assente: null', () => {
    expect(voceRegimeFiscale({ regime_fiscale_rf: null })).toBeNull()
    expect(voceRegimeFiscale(null)).toBeNull()
    expect(voceRegimeFiscale(undefined)).toBeNull()
  })
})
