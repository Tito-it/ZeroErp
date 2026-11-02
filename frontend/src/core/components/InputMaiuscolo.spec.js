// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il contratto di `InputMaiuscolo`: cio' che si digita arriva al
//        v-model in maiuscolo, il vuoto resta stringa vuota, e gli attributi
//        (`maxlength`, `disabled`) arrivano davvero all'input.
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'
import { nextTick } from 'vue'

import InputMaiuscolo from './InputMaiuscolo.vue'
import { monta } from '../../../test/montaggio'

describe('InputMaiuscolo', () => {
  it('emette in maiuscolo cio\' che si digita', async () => {
    const w = monta(InputMaiuscolo, { modelValue: '' })
    await w.find('input').setValue('abc12x')
    expect(w.emitted('update:modelValue').at(-1)).toEqual(['ABC12X'])
  })

  it('il vuoto resta stringa vuota', async () => {
    const w = monta(InputMaiuscolo, { modelValue: 'AB' })
    await w.find('input').setValue('')
    expect(w.emitted('update:modelValue').at(-1)).toEqual([''])
  })

  it('una correzione in mezzo al testo lascia il cursore dov\'era', async () => {
    let w
    w = monta(InputMaiuscolo, {
      modelValue: 'ABC',
      'onUpdate:modelValue': (v) => w.setProps({ modelValue: v }),
    })
    const input = w.find('input').element
    input.value = 'AxBC'
    input.setSelectionRange(2, 2)
    await w.find('input').trigger('input')
    await nextTick()
    expect(input.value).toBe('AXBC')
    expect(input.selectionStart).toBe(2)
  })

  it('passa gli attributi all\'input', () => {
    const w = monta(InputMaiuscolo, { modelValue: 'X', maxlength: '7', disabled: true })
    const input = w.find('input')
    expect(input.attributes('maxlength')).toBe('7')
    expect(input.element.disabled).toBe(true)
  })
})
