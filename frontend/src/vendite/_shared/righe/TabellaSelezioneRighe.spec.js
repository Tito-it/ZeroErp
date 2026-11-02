// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: il contratto di `TabellaSelezioneRighe` — l'impalcatura comune dei
//        tre dialog di selezione righe (evasione ordine, riconsegna reso,
//        reso da DDT), estratta il 2026-10-31.
//
// ⭐ La macchina e' quella VERA (`useRigheSelezioneQta`), montata in un
//    ospite che fa da dialog: la tabella legge chiave e residuo da li', ed e'
//    proprio il legame che si prova.
//
// Indice test:
//   1) righe lavorabili: colonna di selezione, quantità editabile solo sul residuo
//   2) readonly: niente selezione, niente campi — solo consuntivo
//   3) niente da lavorare: la colonna di selezione sparisce
//   4) ⭐ gli slot stanno al loro posto: `colonne` prima della quantità, `colonne-dopo` in fondo
//   5) ⭐ la chiave di riga viene dalla macchina (`ddt_riga_id`), anche per la quantità
//   6) «seleziona tutte» spunta le sole righe lavorabili
//   7) nessuna riga: il testo vuoto
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import Column from 'primevue/column'

import TabellaSelezioneRighe from './TabellaSelezioneRighe.vue'
import { useRigheSelezioneQta } from './useRigheSelezioneQta'
import { monta } from '../../../../test/montaggio'

const RIGHE = [
  { id: 1, articolo_codice: 'A1', descrizione: 'Vite', residuo: 3 },
  { id: 2, articolo_codice: 'A2', descrizione: 'Dado', residuo: 0 },
]

// Scopo: l'ospite — monta la macchina vera e la consegna alla tabella, come fa
//        un dialog. Espone la macchina per leggerne lo stato dal test.
function ospite({ righe = RIGHE, rowKey = 'id', readonly = false, slots = {} } = {}) {
  let macchina
  const Ospite = defineComponent({
    setup() {
      macchina = useRigheSelezioneQta({
        fetchRighe: async () => righe,
        residuoDi: (r) => r.residuo,
        rowKey,
        readonly: () => readonly,
      })
      macchina.loadRighe()
      return () => h(TabellaSelezioneRighe, {
        macchina,
        etichettaQta: 'Quantità',
        testoVuoto: 'Nessuna riga',
      }, slots)
    },
  })
  const wrapper = monta(Ospite)
  return { wrapper, macchina: () => macchina }
}

async function attesa() {
  await nextTick(); await nextTick(); await nextTick()
}

const intestazioni = (wrapper) => wrapper.findAll('thead th').map(th => th.text())

describe('TabellaSelezioneRighe', () => {
  it('1) righe lavorabili: colonna di selezione, quantità editabile solo sul residuo', async () => {
    const { wrapper } = ospite()
    await attesa()
    const righe = wrapper.findAll('tbody tr')
    expect(righe).toHaveLength(2)
    expect(righe[0].findAll('input[type="checkbox"]')).toHaveLength(1)
    expect(righe[0].find('.p-inputnumber').exists()).toBe(true)
    // La riga esaurita resta come consuntivo: niente campo, il numero.
    expect(righe[1].find('.p-inputnumber').exists()).toBe(false)
  })

  it('2) readonly: niente selezione, niente campi — solo consuntivo', async () => {
    const { wrapper } = ospite({ readonly: true })
    await attesa()
    expect(wrapper.findAll('input[type="checkbox"]')).toHaveLength(0)
    expect(wrapper.find('.p-inputnumber').exists()).toBe(false)
    expect(wrapper.findAll('tbody tr')).toHaveLength(2)
  })

  it('3) niente da lavorare: la colonna di selezione sparisce', async () => {
    const { wrapper } = ospite({ righe: [{ ...RIGHE[1] }] })
    await attesa()
    expect(wrapper.findAll('input[type="checkbox"]')).toHaveLength(0)
    expect(intestazioni(wrapper)).toHaveLength(2)
  })

  it('4) gli slot stanno al loro posto: `colonne` prima della quantità, `colonne-dopo` in fondo', async () => {
    const { wrapper } = ospite({
      slots: {
        colonne: () => h(Column, { header: 'Residuo', field: 'residuo' }),
        'colonne-dopo': () => h(Column, { header: 'Motivo' }),
      },
    })
    await attesa()
    const th = intestazioni(wrapper)
    expect(th.slice(2)).toEqual(['Residuo', 'Quantità', 'Motivo'])
  })

  it('5) la chiave di riga viene dalla macchina, anche per la quantità', async () => {
    const righe = [{ ddt_riga_id: 70, articolo_codice: 'A1', descrizione: 'Vite', residuo: 4 }]
    const { wrapper, macchina } = ospite({ righe, rowKey: 'ddt_riga_id' })
    await attesa()
    // Preselezione «tutto»: la quantità nasce dal residuo, sotto la chiave giusta.
    expect(macchina().qtaMap.value).toEqual({ 70: 4 })
    expect(wrapper.find('.p-inputnumber input').element.value).toBe('4')
  })

  it('6) «seleziona tutte» spunta le sole righe lavorabili', async () => {
    const { wrapper, macchina } = ospite()
    await attesa()
    macchina().selected.value = []
    await nextTick()
    await wrapper.find('thead input[type="checkbox"]').setValue(true)
    expect(macchina().selected.value.map(r => r.id)).toEqual([1])
  })

  it('7) nessuna riga: il testo vuoto', async () => {
    const { wrapper } = ospite({ righe: [] })
    await attesa()
    expect(wrapper.find('table').exists()).toBe(false)
    expect(wrapper.text()).toContain('Nessuna riga')
  })
})
