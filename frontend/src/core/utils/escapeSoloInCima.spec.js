// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: La RETE sotto «ESC chiude solo l'overlay in cima» (2026-09-18). Fissa
//        le tre decisioni della regola pura: ingoia SOLO Escape, SOLO se c'e'
//        un dialog aperto, e lo fa con `stopImmediatePropagation` — che e'
//        l'unica primitiva che ferma anche i listener gia' registrati su
//        `document` (quelli di Drawer e Dialog di PrimeVue).
// Note: niente jsdom nel progetto: `event` e `doc` sono oggetti finti con la
//        sola superficie che la regola tocca.
// ------------------------------------------------------------

import { describe, it, expect, vi } from 'vitest'

import { escapeSoloInCima, installaEscapeSoloInCima } from './escapeSoloInCima'

const evento = (code) => ({ code, stopImmediatePropagation: vi.fn() })
const docCon = (dialogAperto) => ({ querySelector: (sel) => (dialogAperto && sel === '.p-dialog-mask' ? {} : null) })

describe('escapeSoloInCima — la regola', () => {
  it('⭐ con un dialog aperto ESC viene ingoiato (i listener di PrimeVue non lo vedono)', () => {
    const e = evento('Escape')
    expect(escapeSoloInCima(e, docCon(true))).toBe(true)
    expect(e.stopImmediatePropagation).toHaveBeenCalledTimes(1)
  })

  it('senza dialog aperti non si tocca niente: il Drawer si chiude con ESC come sempre', () => {
    const e = evento('Escape')
    expect(escapeSoloInCima(e, docCon(false))).toBe(false)
    expect(e.stopImmediatePropagation).not.toHaveBeenCalled()
  })

  it('un tasto che non e\' Escape passa sempre, dialog o no', () => {
    const e = evento('Enter')
    expect(escapeSoloInCima(e, docCon(true))).toBe(false)
    expect(e.stopImmediatePropagation).not.toHaveBeenCalled()
  })
})

describe('installaEscapeSoloInCima — l\'aggancio', () => {
  it('registra UN listener keydown in fase bubble e lo sgancia', () => {
    const add = vi.fn()
    const remove = vi.fn()
    const doc = { addEventListener: add, removeEventListener: remove, querySelector: () => ({}) }
    const sgancia = installaEscapeSoloInCima(doc)
    expect(add).toHaveBeenCalledTimes(1)
    // ⚠️ Terzo argomento assente = bubble. In capture l'evento non arriverebbe
    //    al bersaglio, e un Select dentro il dialog non chiuderebbe la tendina.
    const [tipo, listener, opzioni] = add.mock.calls[0]
    expect(tipo).toBe('keydown')
    expect(opzioni).toBeUndefined()
    const e = evento('Escape')
    listener(e)
    expect(e.stopImmediatePropagation).toHaveBeenCalledTimes(1)
    sgancia()
    expect(remove).toHaveBeenCalledWith('keydown', listener)
  })
})
