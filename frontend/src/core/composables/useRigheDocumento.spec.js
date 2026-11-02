// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: il legame drawer documento ↔ tabella-righe (`useRigheDocumento`).
//
// Indice test:
//   1) form di riga aperto → footer 'nessuno'; chiuso → torna 'form'
//   2) la fotografia unisce testata e riga aperta (esposta dalla tabella)
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'
import { computed, ref } from 'vue'
import { useRigheDocumento } from './useRigheDocumento'

function testataPulita() {
  return { modificato: computed(() => false), chiudiConConferma: (chiudi) => chiudi() }
}

describe('useRigheDocumento', () => {
  it('1) il form di riga aperto toglie il footer della testata', () => {
    const r = useRigheDocumento({ testata: testataPulita(), modificabile: () => true, presente: () => true })
    expect(r.footerDrawer.value).toBe('form')
    r.onFormAperto(true)
    expect(r.footerDrawer.value).toBe('nessuno')
    r.onFormAperto(false)
    expect(r.footerDrawer.value).toBe('form')
  })

  it('2) la riga aperta modificata conta per il documento', () => {
    const r = useRigheDocumento({ testata: testataPulita(), modificabile: () => true, presente: () => true })
    expect(r.documento.modificato.value).toBe(false)
    const rigaModificata = ref(true)
    r.righeTableRef.value = { modificato: rigaModificata, chiudiConConferma: () => {} }
    expect(r.documento.modificato.value).toBe(true)
  })
})
