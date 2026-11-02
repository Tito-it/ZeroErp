// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: la regola del footer dei drawer documento (`useFooterDocumento`,
//        D-11 di work-done/analisi-fe-chrome-drawer.md).
//
// Indice test:
//   1) testata modificabile → 'form'
//   2) documento presente ma non modificabile → 'chiudi'
//   3) documento non ancora letto e non modificabile → 'nessuno'
//   4) ⭐ il form di una riga aperto vince su tutto → 'nessuno'
//   5) `formRigaAperto` e' facoltativo (contratto, offerta)
//   6) e' reattiva: segue lo stato quando cambia
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'
import { ref } from 'vue'
import { useFooterDocumento } from './useFooterDocumento'

function stato({ riga = false, modificabile = false, presente = false } = {}) {
  const s = { riga: ref(riga), modificabile: ref(modificabile), presente: ref(presente) }
  const footer = useFooterDocumento({
    formRigaAperto: () => s.riga.value,
    modificabile: () => s.modificabile.value,
    presente: () => s.presente.value,
  })
  return { s, footer }
}

describe('useFooterDocumento', () => {
  it('1) testata modificabile → form', () => {
    expect(stato({ modificabile: true, presente: true }).footer.value).toBe('form')
    // In creazione il documento non c'e' ancora, ma la testata si scrive.
    expect(stato({ modificabile: true }).footer.value).toBe('form')
  })

  it('2) presente ma non modificabile → chiudi', () => {
    expect(stato({ presente: true }).footer.value).toBe('chiudi')
  })

  it('3) non letto e non modificabile → nessuno', () => {
    expect(stato().footer.value).toBe('nessuno')
  })

  it('4) il form di una riga aperto vince su tutto', () => {
    // 🔴 Un secondo footer sotto il form della riga duplicherebbe il suo
    //    Annulla e spingerebbe il form sotto il fold.
    expect(stato({ riga: true, modificabile: true, presente: true }).footer.value).toBe('nessuno')
    expect(stato({ riga: true, presente: true }).footer.value).toBe('nessuno')
  })

  it('5) formRigaAperto e` facoltativo', () => {
    const footer = useFooterDocumento({ modificabile: () => false, presente: () => true })
    expect(footer.value).toBe('chiudi')
  })

  it('6) segue lo stato quando cambia', () => {
    const { s, footer } = stato({ modificabile: true, presente: true })
    expect(footer.value).toBe('form')
    s.riga.value = true
    expect(footer.value).toBe('nessuno')
    s.riga.value = false
    s.modificabile.value = false
    expect(footer.value).toBe('chiudi')
  })
})
