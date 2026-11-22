// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: `campoFermo` legge i due elenchi della riga e non ne inventa uno.
// ------------------------------------------------------------

import { describe, expect, it } from 'vitest'
import { campoFermo } from './campoFermo'

describe('campoFermo', () => {
  it('fermo per modello: il campo in `non_editable_fields` della riga', () => {
    const riga = { non_editable_fields: ['codice'], campi_del_software: [] }
    expect(campoFermo(riga, 'codice')).toBe(true)
    expect(campoFermo(riga, 'etichetta')).toBe(false)
  })

  it('fermo perche\' del programma: il campo in `campi_del_software`', () => {
    const riga = { non_editable_fields: [], campi_del_software: ['etichetta'] }
    expect(campoFermo(riga, 'etichetta')).toBe(true)
    expect(campoFermo(riga, 'formato')).toBe(false)
  })

  // ⛔ Nessun nome cablato: senza elenchi il `codice` non e' fermo.
  it('senza elenchi non ferma niente, `codice` compreso', () => {
    expect(campoFermo({}, 'codice')).toBe(false)
    expect(campoFermo(null, 'codice')).toBe(false)
    expect(campoFermo({ non_editable_fields: null }, 'codice')).toBe(false)
  })
})
