// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: presidio di `avvisaDopoAzione` (2026-11-14, brief-db-stati-
//        documento-dal-vocabolario FE-O2/FE-C3/FE-D3): l'avviso ai documenti
//        collegati parte dal VERBO dell'azione (`key` = `annulla`), mai dal
//        codice della destinazione. Lo leggono gli store di ordine, bolla,
//        preventivo e contratto.
//
// Indice test eseguiti:
//  1) l'annullo avvisa i tab dei documenti che si riaprono
//  2) un'azione con destinazione ANNULLATO ma un altro verbo non avvisa
//  3) azione assente o senza key: nessun avviso
import { describe, expect, it, vi } from 'vitest'
import { AZIONE_ANNULLA, avvisaDopoAzione } from './avvisoDocumentiCollegati'

describe('avvisaDopoAzione', () => {
  it('1) l\'annullo avvisa i tab dei documenti che si riaprono', () => {
    const emit = vi.fn()
    avvisaDopoAzione({ key: AZIONE_ANNULLA, target_state: 'QUALUNQUE' }, emit)
    expect(emit).toHaveBeenCalled()
    // Id nullo: quale documento si e' riaperto lo sa il DB.
    for (const chiamata of emit.mock.calls) expect(chiamata[1]).toBeNull()
  })

  it('2) la destinazione non conta: un altro verbo non avvisa', () => {
    const emit = vi.fn()
    avvisaDopoAzione({ key: 'conferma', target_state: 'ANNULLATO' }, emit)
    expect(emit).not.toHaveBeenCalled()
  })

  it('3) azione assente o senza key: nessun avviso', () => {
    const emit = vi.fn()
    avvisaDopoAzione(null, emit)
    avvisaDopoAzione({ target_state: 'ANNULLATO' }, emit)
    expect(emit).not.toHaveBeenCalled()
  })
})
