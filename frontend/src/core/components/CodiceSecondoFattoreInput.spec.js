// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il campo del codice del secondo fattore (`CodiceSecondoFattoreInput`):
//        cosa chiede secondo `usaRecupero`, il link che commuta e azzera, lo
//        slot fra campo e link, gli attributi che arrivano all'input e il
//        focus al mount.
// Note: ⚠️ Si asseriscono CHIAVI i18n (l'impalcatura `monta` rende la chiave):
//        la frase la presidia `check_i18n_keys.py`. La resa a video (il link
//        sotto il pulsante) resta materia di collaudo: qui si prova l'ordine
//        dei nodi, non il CSS.
//
// Indice test:
//   1) codice dell'app: placeholder, inputmode numerico, one-time-code, niente link
//   2) codice di recupero: placeholder e inputmode testo
//   3) il link commuta e azzera il codice (v-model:codice + v-model:usa-recupero)
//   4) lo slot sta fra il campo e il link
//   5) `id` e `disabled` arrivano all'input
//   6) `autofocus` chiede il focus all'input al mount (non l'attributo HTML)
// ------------------------------------------------------------

import { describe, it, expect, vi } from 'vitest'
import { h } from 'vue'
import { flushPromises } from '@vue/test-utils'

import CodiceSecondoFattoreInput from './CodiceSecondoFattoreInput.vue'
import { monta } from '../../../test/montaggio'

const input = (w) => w.find('input')

describe('CodiceSecondoFattoreInput', () => {
  it('1) codice dell\'app: campo numerico one-time-code, senza link di recupero', () => {
    const w = monta(CodiceSecondoFattoreInput, { codice: '' })
    expect(input(w).attributes('placeholder')).toBe('auth.secondo_fattore.codice')
    expect(input(w).attributes('aria-label')).toBe('auth.secondo_fattore.codice')
    expect(input(w).attributes('inputmode')).toBe('numeric')
    expect(input(w).attributes('autocomplete')).toBe('one-time-code')
    expect(w.find('a').exists()).toBe(false)
  })

  it('2) codice di recupero: campo testo e frase del recupero', () => {
    const w = monta(CodiceSecondoFattoreInput, { codice: '', usaRecupero: true, consentiRecupero: true })
    expect(input(w).attributes('placeholder')).toBe('auth.secondo_fattore.codice_recupero')
    expect(input(w).attributes('inputmode')).toBe('text')
    expect(w.find('a').text()).toBe('auth.secondo_fattore.usa_codice')
  })

  it('3) il link commuta il tipo di codice e azzera quanto scritto', async () => {
    const w = monta(CodiceSecondoFattoreInput, {
      codice: '123',
      usaRecupero: false,
      consentiRecupero: true,
      'onUpdate:codice': (v) => w.setProps({ codice: v }),
      'onUpdate:usaRecupero': (v) => w.setProps({ usaRecupero: v }),
    })
    expect(w.find('a').text()).toBe('auth.secondo_fattore.usa_recupero')

    await w.find('a').trigger('click')

    expect(w.emitted('update:usaRecupero')).toEqual([[true]])
    expect(w.emitted('update:codice')).toEqual([['']])
    expect(input(w).attributes('placeholder')).toBe('auth.secondo_fattore.codice_recupero')
    expect(input(w).element.value).toBe('')
  })

  it('4) lo slot (il pulsante d\'invio) sta fra il campo e il link', () => {
    const w = monta(
      CodiceSecondoFattoreInput,
      { codice: '', consentiRecupero: true },
      { slots: { default: () => h('button', { type: 'submit' }, 'invia') } },
    )
    const ordine = Array.from(w.find('.field').element.parentElement.children).map((el) => el.tagName)
    expect(ordine).toEqual(['DIV', 'BUTTON', 'A'])
  })

  it('5) `id` e `disabled` arrivano all\'input, non al contenitore', () => {
    const w = monta(CodiceSecondoFattoreInput, { codice: '', id: 'codice', disabled: true })
    expect(input(w).attributes('id')).toBe('codice')
    expect(input(w).element.disabled).toBe(true)
    expect(w.find('.field').attributes('id')).toBeUndefined()
  })

  // ⚠️ Si spia `focus` invece di leggere `document.activeElement`: `monta`
  //    non aggancia il componente al documento, e un nodo staccato non prende
  //    il focus. Conta che il focus sia CHIESTO all'input, dopo il mount.
  it('6) `autofocus` chiede il focus all\'input al mount; senza, no', async () => {
    const focus = vi.spyOn(HTMLElement.prototype, 'focus')
    try {
      const senza = monta(CodiceSecondoFattoreInput, { codice: '' })
      await flushPromises()
      expect(focus).not.toHaveBeenCalled()

      const con = monta(CodiceSecondoFattoreInput, { codice: '', autofocus: true })
      await flushPromises()
      expect(focus).toHaveBeenCalledTimes(1)
      expect(focus.mock.contexts[0]).toBe(input(con).element)
      senza.unmount()
      con.unmount()
    } finally {
      focus.mockRestore()
    }
  })
})
