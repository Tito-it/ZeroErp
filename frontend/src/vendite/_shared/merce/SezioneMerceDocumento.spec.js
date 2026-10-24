// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il BB `SezioneMerceDocumento` (prelievi della bolla, rientri
//        del reso; piano-be-fe-magazzino-lotto-3): la sezione compare solo se
//        il documento muove merce, passa ogni voce allo slot, toglie la
//        scrittura quando manca il magazzino, e una rilettura fa rinascere le
//        voci (rileggono i loro lookup coi magazzini di adesso).
// Indice test:
//   1) il documento non muove merce: niente a video
//   2) muove merce: una voce per elemento, con situazione e modificabile
//   3) senza magazzino: la frase, e le voci non si scrivono
//   4) `carica` rilegge e le voci rinascono (chiave con la lettura)
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { defineComponent, h, onMounted } from 'vue'

import SezioneMerceDocumento from './SezioneMerceDocumento.vue'
import { monta } from '../../../../test/montaggio'

const risposta = (dati) => () => Promise.resolve({ data: { data: dati } })
const VOCI = [{ id: 1 }, { id: 2 }]
let montaggi = 0
const Voce = defineComponent({
  props: { voce: Object, modificabile: Boolean },
  setup(p) {
    onMounted(() => { montaggi += 1 })
    return () => h('div', { class: 'voce', 'data-mod': String(p.modificabile) }, `voce ${p.voce.id}`)
  },
})

function montaSezione(dati, extra = {}) {
  return monta(SezioneMerceDocumento, {
    leggi: risposta(dati), titolo: 'Titolo', senzaMagazzinoTesto: 'manca il magazzino',
    chiaveVoce: (v) => String(v.id), modificabile: true, ...extra,
  }, {
    slots: { voce: ({ voce, modificabile }) => h(Voce, { voce, modificabile }) },
  })
}

describe('SezioneMerceDocumento', () => {
  it('il documento non muove merce: niente a video', async () => {
    const w = montaSezione({ muove_merce: false, magazzino_id: 5, voci: VOCI })
    await flushPromises()
    expect(w.text()).toBe('')
  })

  it('muove merce: una voce per elemento, con situazione e modificabile', async () => {
    const w = montaSezione({ muove_merce: true, magazzino_id: 5, voci: VOCI })
    await flushPromises()
    expect(w.findAll('.voce').map((v) => [v.text(), v.attributes('data-mod')])).toEqual([
      ['voce 1', 'true'], ['voce 2', 'true'],
    ])
    expect(w.text()).not.toContain('manca il magazzino')
  })

  it('senza magazzino: la frase, e le voci non si scrivono', async () => {
    const w = montaSezione({ muove_merce: true, magazzino_id: null, voci: VOCI })
    await flushPromises()
    expect(w.text()).toContain('manca il magazzino')
    expect(w.findAll('.voce').every((v) => v.attributes('data-mod') === 'false')).toBe(true)
  })

  it('`carica` rilegge e le voci rinascono (chiave con la lettura)', async () => {
    const w = montaSezione({ muove_merce: true, magazzino_id: 5, voci: VOCI })
    await flushPromises()
    const prima = montaggi
    await w.vm.carica()
    await flushPromises()
    expect(montaggi - prima).toBe(2)
  })
})
