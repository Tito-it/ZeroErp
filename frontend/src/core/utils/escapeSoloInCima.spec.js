// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: La RETE sotto «ESC chiude solo l'overlay in cima» (2026-09-18). Fissa
//        le tre decisioni della regola pura: ingoia SOLO Escape, SOLO se c'e'
//        un dialog aperto, e lo fa con `stopImmediatePropagation` — che e'
//        l'unica primitiva che ferma anche i listener gia' registrati su
//        `document` (quelli di Drawer e Dialog di PrimeVue).
//        Fissa anche l'ESC da una tendina CHIUSA (2026-09-26): il Select di
//        PrimeVue lo fermerebbe sempre, e il drawer non si chiudeva.
// Note: niente jsdom nel progetto: `event` e `doc` sono oggetti finti con la
//        sola superficie che la regola tocca.
// ------------------------------------------------------------

import { describe, it, expect, vi } from 'vitest'

import { escapeDaTendinaChiusa, escapeSoloInCima, installaEscapeSoloInCima } from './escapeSoloInCima'

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

describe('escapeDaTendinaChiusa — il Select che ferma ESC anche da chiuso', () => {
  // Il fuoco dentro una tendina: `aria-expanded` dice se e' aperta.
  function scenario({ aperta = false, dentroTendina = true } = {}) {
    const contenitore = { dispatchEvent: vi.fn() }
    const tendina = { parentElement: contenitore }
    const bersaglio = {
      closest: (sel) => (dentroTendina && sel === '.p-select' ? tendina : null),
      getAttribute: (a) => (a === 'aria-expanded' ? String(aperta) : null),
    }
    const e = { code: 'Escape', target: bersaglio, stopImmediatePropagation: vi.fn() }
    return { e, contenitore }
  }
  const crea = (init) => ({ copia: true, ...init })

  it('⭐ tendina chiusa: ESC si toglie al Select e riparte dal suo contenitore', () => {
    const { e, contenitore } = scenario()
    expect(escapeDaTendinaChiusa(e, crea)).toBe(true)
    expect(e.stopImmediatePropagation).toHaveBeenCalledTimes(1)
    expect(contenitore.dispatchEvent).toHaveBeenCalledWith(
      expect.objectContaining({ copia: true, code: 'Escape', bubbles: true }),
    )
  })

  it('tendina aperta: non si tocca, il primo ESC chiude la tendina', () => {
    const { e, contenitore } = scenario({ aperta: true })
    expect(escapeDaTendinaChiusa(e, crea)).toBe(false)
    expect(e.stopImmediatePropagation).not.toHaveBeenCalled()
    expect(contenitore.dispatchEvent).not.toHaveBeenCalled()
  })

  it('fuoco fuori da una tendina, o tasto diverso: non si tocca', () => {
    const fuori = scenario({ dentroTendina: false })
    expect(escapeDaTendinaChiusa(fuori.e, crea)).toBe(false)
    const invio = scenario()
    invio.e.code = 'Enter'
    expect(escapeDaTendinaChiusa(invio.e, crea)).toBe(false)
    expect(invio.contenitore.dispatchEvent).not.toHaveBeenCalled()
  })
})

describe('installaEscapeSoloInCima — l\'aggancio', () => {
  it('registra la regola in bubble e quella della tendina in capture, e le sgancia', () => {
    const add = vi.fn()
    const remove = vi.fn()
    const doc = { addEventListener: add, removeEventListener: remove, querySelector: () => ({}) }
    const sgancia = installaEscapeSoloInCima(doc)
    expect(add).toHaveBeenCalledTimes(2)
    // ⚠️ Terzo argomento assente = bubble. In capture l'evento non arriverebbe
    //    al bersaglio, e un Select dentro il dialog non chiuderebbe la tendina.
    const [tipo, listener, opzioni] = add.mock.calls[0]
    expect(tipo).toBe('keydown')
    expect(opzioni).toBeUndefined()
    const e = evento('Escape')
    listener(e)
    expect(e.stopImmediatePropagation).toHaveBeenCalledTimes(1)
    // La tendina va in CAPTURE: deve arrivare prima del Select.
    const [, tendina, capture] = add.mock.calls[1]
    expect(capture).toBe(true)
    sgancia()
    expect(remove).toHaveBeenCalledWith('keydown', listener)
    expect(remove).toHaveBeenCalledWith('keydown', tendina, true)
  })
})
