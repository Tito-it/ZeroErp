// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: il corpo di un documento dopo la bozza (`useCorpoDocumento`,
//        brief-db-stati-documento-dal-vocabolario FE-P1 … FE-R3): chiuso
//        dalle chiavi della capability, mai dal codice dello stato.
//
// Indice test:
//   1) in creazione (nessun documento) aperto, nessuna sezione chiusa
//   2) in bozza (chiavi accese): aperto
//   3) fuori bozza (`can_edit_righe` spento): chiuso, banner acceso
//   4) ⭐ una sezione chiusa che non e' del corpo: corpo aperto, banner acceso
//   5) ⭐ capability vuota con documento presente (dettaglio in caricamento):
//      chiuso (fail-closed)
//   6) ⭐ lo stato non si legge: un `stato_codice_interno` 'DRAFT' con le
//      chiavi spente resta chiuso
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'
import { ref } from 'vue'
import { useEntityCapabilities } from './useEntityCapabilities'
import { useCorpoDocumento } from './useCorpoDocumento'

function corpo({ detail, presente = true }) {
  const caps = useEntityCapabilities(ref(detail))
  return useCorpoDocumento({
    caps,
    corpo: ['can_edit_righe'],
    sezioni: ['can_edit_righe', 'can_edit_indirizzi'],
    presente: () => presente,
  })
}

describe('useCorpoDocumento', () => {
  it('1) in creazione aperto', () => {
    const c = corpo({ detail: null, presente: false })
    expect(c.corpoChiuso.value).toBe(false)
    expect(c.sezioneChiusa.value).toBe(false)
  })

  it('2) in bozza aperto', () => {
    const c = corpo({ detail: { capabilities: { can_edit_righe: true, can_edit_indirizzi: true } } })
    expect(c.corpoChiuso.value).toBe(false)
    expect(c.sezioneChiusa.value).toBe(false)
  })

  it('3) fuori bozza chiuso', () => {
    const c = corpo({ detail: { capabilities: { can_edit_righe: false, can_edit_indirizzi: false } } })
    expect(c.corpoChiuso.value).toBe(true)
    expect(c.sezioneChiusa.value).toBe(true)
  })

  it('4) sezione chiusa fuori dal corpo: corpo aperto, banner acceso', () => {
    const c = corpo({ detail: { capabilities: { can_edit_righe: true, can_edit_indirizzi: false } } })
    expect(c.corpoChiuso.value).toBe(false)
    expect(c.sezioneChiusa.value).toBe(true)
  })

  it('5) capability vuota con documento presente: chiuso', () => {
    const c = corpo({ detail: null, presente: true })
    expect(c.corpoChiuso.value).toBe(true)
  })

  it('6) lo stato non si legge', () => {
    const c = corpo({ detail: { stato_codice_interno: 'DRAFT', capabilities: { can_edit_righe: false } } })
    expect(c.corpoChiuso.value).toBe(true)
  })
})
