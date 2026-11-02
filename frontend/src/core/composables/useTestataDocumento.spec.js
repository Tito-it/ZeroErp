// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: la testata di un documento dopo la bozza (`useTestataDocumento`,
//        brief-db-testata-dopo-emissione R-FE-3): quali campi del form si
//        cambiano, letti dalla capability.
//
// Indice test:
//   1) in creazione (nessun documento) tutto aperto, nessun campo fermo
//   2) in bozza: aperto, fermi i soli campi della capability
//   3) ⭐ fuori bozza con un campo del form aperto (bolla emessa): modificabile,
//      il form esce dal corpo protetto e il footer libera il Salva
//   4) ⭐ fuori bozza con `can_edit_testata` vero ma nessun campo DEL FORM
//      aperto (ordine confermato: si cambiano solo le note) → non modificabile
//   5) documento chiuso (`can_edit_testata` falso) → tutto fermo
//   6) i permessi vincono su tutto
//   7) capability vuota (fail-closed) → tutto fermo
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'
import { ref } from 'vue'
import { useEntityCapabilities } from './useEntityCapabilities'
import { useTestataDocumento } from './useTestataDocumento'

const CAMPI = ['data', 'valuta_id', 'tracking_code']

function testata({ capabilities, presente = true, readonlyPuro = false, corpoProtetto = false }) {
  const detail = ref(presente ? { capabilities } : null)
  const caps = useEntityCapabilities(detail)
  return useTestataDocumento({
    caps,
    campi: CAMPI,
    readonlyPuro: () => readonlyPuro,
    presente: () => presente,
    corpoProtetto: () => corpoProtetto,
  })
}

describe('useTestataDocumento', () => {
  it('1) in creazione tutto aperto', () => {
    const t = testata({ presente: false })
    expect(t.modificabile.value).toBe(true)
    expect(t.campiBloccati.value).toEqual([])
    expect(t.bloccato('data')).toBe(false)
  })

  it('2) in bozza: fermi i soli campi della capability', () => {
    const t = testata({ capabilities: { can_edit_testata: true, non_editable_fields: ['numero'] } })
    expect(t.modificabile.value).toBe(true)
    expect(t.bloccato('data')).toBe(false)
    expect(t.bloccato('numero')).toBe(true)
    // Corpo non protetto: niente escape.
    expect(t.sopraCorpoProtetto.value).toBe(false)
  })

  it('3) fuori bozza con un campo del form aperto', () => {
    const t = testata({
      capabilities: { can_edit_testata: true, non_editable_fields: ['data', 'valuta_id'] },
      corpoProtetto: true,
    })
    expect(t.modificabile.value).toBe(true)
    expect(t.bloccato('tracking_code')).toBe(false)
    expect(t.bloccato('data')).toBe(true)
    expect(t.sopraCorpoProtetto.value).toBe(true)
    expect(t.footerReadonly.value).toBe(false)
  })

  it('4) can_edit_testata vero ma nessun campo del form aperto', () => {
    const t = testata({
      capabilities: { can_edit_testata: true, non_editable_fields: CAMPI },
      corpoProtetto: true,
    })
    expect(t.modificabile.value).toBe(false)
    expect(t.bloccato('tracking_code')).toBe(true)
    expect(t.sopraCorpoProtetto.value).toBe(false)
    expect(t.footerReadonly.value).toBeUndefined()
  })

  it('5) documento chiuso: tutto fermo', () => {
    const t = testata({ capabilities: { can_edit_testata: false, non_editable_fields: [] } })
    expect(t.modificabile.value).toBe(false)
    expect(t.bloccato('tracking_code')).toBe(true)
  })

  it('6) i permessi vincono', () => {
    const t = testata({
      capabilities: { can_edit_testata: true, non_editable_fields: [] },
      readonlyPuro: true,
    })
    expect(t.modificabile.value).toBe(false)
    expect(t.bloccato('data')).toBe(true)
    // Anche in creazione.
    expect(testata({ presente: false, readonlyPuro: true }).modificabile.value).toBe(false)
  })

  it('7) capability vuota: tutto fermo (fail-closed)', () => {
    const t = testata({ capabilities: {} })
    expect(t.modificabile.value).toBe(false)
    expect(t.bloccato('tracking_code')).toBe(true)
  })
})
