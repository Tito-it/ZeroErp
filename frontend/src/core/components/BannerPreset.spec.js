// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: i due banner del preset di base (BB `BannerPreset`, regola del 2
//        del 2026-11-20: liste e dashboard).
//
// Indice test:
//   1) niente segnalato: niente banner
//   2) preset aggiornato: «Vedi novita'» e «Ignora» emettono il loro evento
//   3) base cambiata: solo «Riallinea», nessun «Ignora»
//   4) `disabled`: le azioni sono spente
// ------------------------------------------------------------

import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import BannerPreset from './BannerPreset.vue'

const TESTI = {
  aggiornato: 'Aggiornato', vediNovita: 'Vedi', ignora: 'Ignora',
  baseCambiato: 'Base cambiata', riallinea: 'Riallinea',
}

function monta(props) {
  return mount(BannerPreset, { props: { testi: TESTI, ...props } })
}

const q = (w, id) => w.find(`[data-testid="${id}"]`)

describe('BannerPreset', () => {
  it('1) niente segnalato: niente banner', () => {
    const w = monta({})
    expect(q(w, 'banner-preset-aggiornato').exists()).toBe(false)
    expect(q(w, 'banner-preset-base-cambiato').exists()).toBe(false)
  })

  it('2) preset aggiornato: «Vedi novita\'» e «Ignora» emettono il loro evento', async () => {
    const w = monta({ aggiornato: true })
    expect(q(w, 'banner-preset-aggiornato').text()).toContain('Aggiornato')
    await q(w, 'banner-preset-vedi-novita').trigger('click')
    await q(w, 'banner-preset-ignora').trigger('click')
    expect(w.emitted('vedi-novita')).toHaveLength(1)
    expect(w.emitted('ignora')).toHaveLength(1)
  })

  it('3) base cambiata: solo «Riallinea», nessun «Ignora»', async () => {
    const w = monta({ baseCambiato: true })
    expect(q(w, 'banner-preset-base-cambiato').text()).toContain('Base cambiata')
    expect(q(w, 'banner-preset-ignora').exists()).toBe(false)
    await q(w, 'banner-preset-riallinea').trigger('click')
    expect(w.emitted('riallinea')).toHaveLength(1)
  })

  it('4) `disabled`: le azioni sono spente', () => {
    const w = monta({ aggiornato: true, baseCambiato: true, disabled: true })
    for (const id of ['banner-preset-vedi-novita', 'banner-preset-ignora', 'banner-preset-riallinea']) {
      expect(q(w, id).attributes('disabled')).toBeDefined()
    }
  })
})
