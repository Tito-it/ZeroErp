// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: il motivo sotto un campo che lo stabilisce il programma (BB
//        `MotivoDelProgramma`, regola del 2 del 2026-11-20).
//
// Indice test:
//   1) campo fermo: il motivo c'e', col testid dal nome del campo
//   2) campo libero: niente motivo
//   3) il predicato riceve il nome del FORM (il drawer traduce in colonna)
// ------------------------------------------------------------

import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import MotivoDelProgramma from './MotivoDelProgramma.vue'

const TESTO = 'Lo stabilisce il programma'

function monta(campo, fermo) {
  return mount(MotivoDelProgramma, { props: { campo, fermo, testo: TESTO } })
}

describe('MotivoDelProgramma', () => {
  it('1) campo fermo: il motivo c\'e\', col testid dal nome del campo', () => {
    const w = monta('codice', () => true)
    const motivo = w.find('[data-testid="motivo-codice"]')
    expect(motivo.exists()).toBe(true)
    expect(motivo.text()).toBe(TESTO)
    expect(motivo.classes()).toContain('app-motivo-campo')
  })

  it('2) campo libero: niente motivo', () => {
    expect(monta('descrizione', () => false).find('small').exists()).toBe(false)
  })

  it('3) il predicato riceve il nome del FORM (il drawer traduce in colonna)', () => {
    const fermo = vi.fn((campo) => campo === 'smtp_password')
    expect(monta('smtp_password', fermo).find('small').exists()).toBe(true)
    expect(fermo).toHaveBeenCalledWith('smtp_password')
  })
})
