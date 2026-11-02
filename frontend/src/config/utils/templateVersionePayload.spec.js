// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Presidio del payload della versione di template: i default di
//        colonna li decide il DB in creazione, e in modifica non si
//        inghiotte un campo svuotato.
// ------------------------------------------------------------
import { describe, expect, it } from 'vitest'
import { CAMPI_DEFAULT_DB, payloadVersione } from './templateVersionePayload'

function form(extra = {}) {
  return {
    titolo: '  v8  ', formato_template: null, html_template: '<p/>', css_template: '',
    markdown_template: '', render_engine_id: 1, versione_contesto: 5,
    page_format: null, page_orientation: null,
    margin_top_mm: null, margin_right_mm: null, margin_bottom_mm: null, margin_left_mm: null,
    valido_dal: null, valido_al: null, attivo: true, ...extra,
  }
}

describe('payloadVersione', () => {
  it('in creazione omette i campi con default di colonna lasciati vuoti', () => {
    const p = payloadVersione(form(), { nuova: true })
    for (const campo of CAMPI_DEFAULT_DB) expect(p).not.toHaveProperty(campo)
    expect(p.titolo).toBe('v8')
    expect(p.css_template).toBeNull()
  })

  it('in creazione manda i campi valorizzati, anche lo zero', () => {
    const p = payloadVersione(form({ margin_top_mm: 0, page_format: 'A3' }), { nuova: true })
    expect(p.margin_top_mm).toBe(0)
    expect(p.page_format).toBe('A3')
    expect(p).not.toHaveProperty('margin_left_mm')
  })

  it('in modifica un campo svuotato arriva al backend come null', () => {
    const p = payloadVersione(form({ margin_top_mm: null }), { nuova: false })
    expect(p).toHaveProperty('margin_top_mm', null)
  })
})
