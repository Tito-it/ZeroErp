// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa `useDrawerListaConForm`, la colla fra un drawer e il BB
//        `ListaConFormInline` (2026-10-31, regola del 2: `NoteDrawer` e
//        `ArticoloUomDrawer`).
//
// Indice test:
//  1. il padre c'e' SOLO a drawer aperto (alla chiusura la lista si azzera)
//  2. il footer segue il form: 'nessuno' a form aperto, 'chiudi' altrimenti
//  3. modifiche e uscita: dalla shell se montata, uscita diretta senza
// ------------------------------------------------------------

import { describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { useDrawerListaConForm } from './useDrawerListaConForm'

describe('useDrawerListaConForm', () => {
  it('1. il padre c\'e\' SOLO a drawer aperto', () => {
    const visible = ref(false)
    const id = ref('art-1')
    const { padre } = useDrawerListaConForm({ visible: () => visible.value, padre: () => id.value })
    expect(padre.value).toBeNull()
    visible.value = true
    expect(padre.value).toBe('art-1')
    id.value = 'art-2'
    expect(padre.value).toBe('art-2')
    visible.value = false
    expect(padre.value).toBeNull()
  })

  it('2. il footer segue il form', () => {
    const { footer, formAperto, onFormAperto } = useDrawerListaConForm({ visible: () => true, padre: () => 1 })
    expect(footer.value).toBe('chiudi')
    onFormAperto(true)
    expect(formAperto.value).toBe(true)
    expect(footer.value).toBe('nessuno')
    onFormAperto(false)
    expect(footer.value).toBe('chiudi')
  })

  it('3. modifiche e uscita: dalla shell se montata, uscita diretta senza', () => {
    const { listaRef, modificato, chiudiConConferma } = useDrawerListaConForm({ visible: () => true, padre: () => 1 })
    const chiudi = vi.fn()
    // Senza la shell: niente da confermare, si esce.
    expect(modificato.value).toBe(false)
    chiudiConConferma(chiudi)
    expect(chiudi).toHaveBeenCalledTimes(1)
    // Con la shell: l'expose (gia' scartato dai ref) decide.
    const shell = { modificato: true, chiudiConConferma: vi.fn() }
    listaRef.value = shell
    expect(modificato.value).toBe(true)
    chiudiConConferma(chiudi)
    expect(shell.chiudiConConferma).toHaveBeenCalledWith(chiudi)
    expect(chiudi).toHaveBeenCalledTimes(1)
  })
})
