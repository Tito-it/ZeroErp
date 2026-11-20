// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: `campoDelSoftware` legge l'elenco della riga e non ne inventa uno.
// ------------------------------------------------------------

import { describe, expect, it } from 'vitest'
import { campoDelSoftware } from './campoDelSoftware'

describe('campoDelSoftware', () => {
  it("il campo nell'elenco della riga e' del programma, gli altri no", () => {
    const riga = { nata_dal_seed: true, campi_del_software: ['codice', 'lingua'] }
    expect(campoDelSoftware(riga, 'codice')).toBe(true)
    expect(campoDelSoftware(riga, 'oggetto')).toBe(false)
  })

  it("senza elenco non ferma niente: riga dell'installazione, creazione, dettaglio mancante", () => {
    expect(campoDelSoftware({ campi_del_software: [] }, 'codice')).toBe(false)
    expect(campoDelSoftware({}, 'codice')).toBe(false)
    expect(campoDelSoftware(null, 'codice')).toBe(false)
    expect(campoDelSoftware({ campi_del_software: null }, 'codice')).toBe(false)
  })
})
