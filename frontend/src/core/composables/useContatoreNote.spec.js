// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Presidio di `useContatoreNote`, il pulsante «Gestisci note» standard:
//        il numero dal dettaglio, il totale del sotto-drawer che vale fino al
//        dettaglio successivo, lo zero che non si mostra, e la forma
//        dell'azione per `DrawerActionsBar`.
// ------------------------------------------------------------

/*
Indice test eseguiti:
1) badgeNote: zero e negativi -> null, altrimenti il numero
2) il conteggio viene dal dettaglio (`contatori.note`); dettaglio null -> 0
3) aggiorna(totale) vince sul dettaglio finche' il dettaglio non cambia
4) aggiorna con un non-numero non cambia niente
5) azzera(): zero, senza pallino
6) azione(): chiave, kind, icona e badge standard; `resto` passa intatto
*/

import { nextTick, ref } from 'vue'
import { describe, expect, it } from 'vitest'

import { MANAGE_ICONS } from '../constants'
import { AZIONE_GESTISCI_NOTE, badgeNote, useContatoreNote } from './useContatoreNote'

describe('useContatoreNote', () => {
  it('1) badgeNote: lo zero non e un pallino', () => {
    expect(badgeNote(0)).toBeNull()
    expect(badgeNote(-1)).toBeNull()
    expect(badgeNote(3)).toBe(3)
  })

  it('2) il conteggio viene dal dettaglio', () => {
    const detail = ref(null)
    const c = useContatoreNote(() => detail.value)
    expect(c.conteggio.value).toBe(0)
    expect(c.badge.value).toBeNull()
    detail.value = { contatori: { note: 4 } }
    expect(c.conteggio.value).toBe(4)
    expect(c.badge.value).toBe(4)
    detail.value = { id: 1 } // dettaglio senza contatori
    expect(c.conteggio.value).toBe(0)
  })

  it('3) il totale del sotto-drawer vale fino al dettaglio successivo', async () => {
    const detail = ref({ contatori: { note: 1 } })
    const c = useContatoreNote(detail)
    c.aggiorna(2)
    expect(c.conteggio.value).toBe(2)
    // Ricarica del dettaglio: il server porta il suo numero, fresco.
    detail.value = { contatori: { note: 5 } }
    await nextTick()
    expect(c.conteggio.value).toBe(5)
  })

  it('4) un totale che non e un numero si ignora', () => {
    const c = useContatoreNote(() => ({ contatori: { note: 3 } }))
    c.aggiorna(undefined)
    c.aggiorna('7')
    c.aggiorna(Number.NaN)
    expect(c.conteggio.value).toBe(3)
  })

  it('5) azzera(): nessun pallino', () => {
    const c = useContatoreNote()
    c.aggiorna(6)
    c.azzera()
    expect(c.conteggio.value).toBe(0)
    expect(c.badge.value).toBeNull()
  })

  it('6) azione() e il pulsante standard', () => {
    const c = useContatoreNote(() => ({ contatori: { note: 2 } }))
    const comando = () => {}
    const a = c.azione({ label: 'Gestisci note', command: comando, disabled: true })
    expect(a).toEqual({
      key: AZIONE_GESTISCI_NOTE,
      kind: 'manage',
      label: 'Gestisci note',
      icon: MANAGE_ICONS.NOTE,
      badge: 2,
      command: comando,
      disabled: true,
    })
  })
})
