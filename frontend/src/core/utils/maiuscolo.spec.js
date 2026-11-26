// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Presidio di `core/utils/maiuscolo.js` (brief-be-fe-BB-audit F-2): la
//        forma maiuscola e il cursore rimesso dov'era, contando solo i
//        caratteri che restano. Un input finto: qui conta il calcolo, il DOM
//        vero lo prova lo spec di `InputMaiuscolo`.
// ------------------------------------------------------------
import { nextTick } from 'vue'
import { describe, expect, it, vi } from 'vitest'
import { formaMaiuscola, riscriviDigitato } from './maiuscolo'

function inputFinto(inizio, fine = inizio) {
  return { selectionStart: inizio, selectionEnd: fine, setSelectionRange: vi.fn() }
}

describe('formaMaiuscola', () => {
  it('alza il maiuscolo; senzaSpazi toglie ogni spazio', () => {
    expect(formaMaiuscola('it60 x05')).toBe('IT60 X05')
    expect(formaMaiuscola('it60 x05\t1', { senzaSpazi: true })).toBe('IT60X051')
    expect(formaMaiuscola(null)).toBe('')
  })
})

describe('riscriviDigitato', () => {
  it('rimette il cursore contando gli spazi tolti prima di lui', async () => {
    const input = inputFinto(6, 8)
    expect(riscriviDigitato(input, 'it60 x05', { senzaSpazi: true })).toBe('IT60X05')
    await nextTick()
    expect(input.setSelectionRange).toHaveBeenCalledWith(5, 7)
  })

  it('se il testo non cambia, il cursore non si tocca', async () => {
    const input = inputFinto(2)
    expect(riscriviDigitato(input, 'ABC')).toBe('ABC')
    await nextTick()
    expect(input.setSelectionRange).not.toHaveBeenCalled()
  })

  it('senza input (o senza selezione) restituisce solo la forma', () => {
    expect(riscriviDigitato(null, 'ab')).toBe('AB')
    expect(riscriviDigitato({ selectionStart: null }, 'ab')).toBe('AB')
  })
})
