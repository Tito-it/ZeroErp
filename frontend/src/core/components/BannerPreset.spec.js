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
//   5) giro 1b: le parti cambiate, tradotte; una chiave senza etichetta col
//      suo codice; nessuna chiave = nessuna riga
// ------------------------------------------------------------

import { describe, expect, it } from 'vitest'
import BannerPreset from './BannerPreset.vue'
import { monta as montaComponente } from '../../../test/montaggio'

const TESTI = {
  aggiornato: 'Aggiornato', vediNovita: 'Vedi', ignora: 'Ignora',
  baseCambiato: 'Base cambiata', riallinea: 'Riallinea',
}

// Le etichette di due parti: la terza chiave del test 5 resta senza, come
// una chiave che il DB aggiunge prima della sua traduzione.
const MESSAGGI = {
  common: {
    banner_preset: {
      parti_cambiate: 'Cambiato: {parti}.',
      parte: { colonne: 'colonne', pagina_dimensione: 'righe per pagina' },
    },
  },
}

function monta(props) {
  return montaComponente(BannerPreset, { testi: TESTI, ...props }, { messages: MESSAGGI })
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

  it('5) giro 1b: le parti cambiate, tradotte; una chiave senza etichetta col suo codice', () => {
    const w = monta({ aggiornato: true, chiavi: ['colonne', 'pagina_dimensione', 'chiave_nuova'] })
    expect(q(w, 'banner-preset-parti').text())
      .toBe('Cambiato: colonne, righe per pagina, chiave_nuova.')
    expect(q(monta({ aggiornato: true }), 'banner-preset-parti').exists()).toBe(false)
  })
})
