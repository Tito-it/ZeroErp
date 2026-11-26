// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Presidio del segno del predefinito (`PredefinitoSegno`) e della sua
//        resa nelle liste (`formato = predefinito` di `CellaConfigurabile`):
//        la puntina `MANAGE_ICONS.PREDEFINITO` sulla sola voce predefinita,
//        niente sul falso e sul null — e in lista non e' il «Si'/No» di
//        `yesno`, che scriverebbe «No» su ogni altra riga.
//
// Indice test:
//  1. vero: la puntina, col nome per chi non vede
//  2. falso e null: niente
//  3. CellaConfigurabile `formato=predefinito`: il segno, non SiNoTag; non e' testo
// ------------------------------------------------------------
import { describe, expect, it } from 'vitest'
import PredefinitoSegno from './PredefinitoSegno.vue'
import CellaConfigurabile, { testoCella } from './CellaConfigurabile.vue'
import { MANAGE_ICONS } from '../constants'
import { monta } from '../../../test/montaggio'

const PUNTINA = `.${MANAGE_ICONS.PREDEFINITO.split(' ').pop()}`

describe('PredefinitoSegno', () => {
  it('1. vero: la puntina, col nome per chi non vede', () => {
    const segno = monta(PredefinitoSegno, { value: true }).find(PUNTINA)
    expect(segno.exists()).toBe(true)
    expect(segno.classes()).toContain('predefinito-segno')
    expect(segno.attributes('aria-label')).toBeTruthy()
  })

  it('2. falso e null: niente', () => {
    expect(monta(PredefinitoSegno, { value: false }).find(PUNTINA).exists()).toBe(false)
    expect(monta(PredefinitoSegno, { value: null }).find(PUNTINA).exists()).toBe(false)
  })

  it('3. CellaConfigurabile formato=predefinito: il segno, non SiNoTag', () => {
    const col = { codice: 'is_default', campo_sorgente: 'is_default', formato: 'predefinito', tipo_dato: 'boolean' }
    const vera = monta(CellaConfigurabile, { col, data: { is_default: true } })
    expect(vera.find(PUNTINA).exists()).toBe(true)
    expect(vera.find('.p-tag').exists()).toBe(false)
    const falsa = monta(CellaConfigurabile, { col, data: { is_default: false } })
    expect(falsa.find(PUNTINA).exists()).toBe(false)
    expect(falsa.text()).toBe('')
    expect(testoCella(col, { is_default: true })).toBeNull()
  })
})
