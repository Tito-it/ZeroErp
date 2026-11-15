// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: LA DICHIARAZIONE della conferma di chiusura di un legame coi prezzi
//        bundle (BE19 di brief-db-revisione-catalogo, giro 3): che cosa
//        `ChiusuraLegamePrezziDialog` manda al chiamante quando l'operatore
//        conferma, e che cosa mostra.
// Note: ⭐ Il numero dichiarato e' quello LETTO dal dialog (`GET …/chiusura/`,
//       `prezzi`), mai quello del messaggio. Prezzi spariti fra la domanda
//       del DB e la lettura (zero): si conferma SENZA dichiarazione.
//       ⚠️ Si monta il dialog VERO; si fingono l'API e la cornice `AppDialog`.
//
// Indice test:
//  1) con prezzi: la conferma dichiara il numero letto
//  2) la lettura va al legame e alla data della chiamata in sospeso
//  3) prezzi spariti: conferma senza dichiarazione, frase propria
//  4) finche' la lettura non arriva, la conferma e' spenta
//  5) un prezzo fuori perimetro si dice, senza i suoi dati
// ------------------------------------------------------------
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { defineComponent } from 'vue'
import { flushPromises } from '@vue/test-utils'

import ChiusuraLegamePrezziDialog from './ChiusuraLegamePrezziDialog.vue'
import { monta } from '../../../test/montaggio'

let risposta = null
const chiamate = []
vi.mock('../api/catalogo', () => ({
  getChiusuraArticoloComponente: (...args) => { chiamate.push(args); return risposta },
}))

const CorniceFinta = defineComponent({
  name: 'AppDialog',
  props: { saveDisabled: { type: Boolean, default: false } },
  emits: ['save', 'cancel'],
  template: '<div><slot /></div>',
})

function prezzi(righe) {
  return Promise.resolve({ data: { data: { valido_al: '2026-11-10', prezzi: righe.length, righe } } })
}

function prezzo(extra) {
  return {
    riga_id: 1, listino_versione_id: 3, listino_id: 2, listino_codice: 'LIST1', codice_versione: 'V1',
    stato_versione: 'ATTIVA', valido_dal: '2026-09-01', valido_al: null, prezzo: '11', importo_per_kit: '22',
    attivo: true, nel_perimetro: true, esito: 'CHIUDE',
    ...extra,
  }
}

async function montaDialog() {
  const wrapper = monta(
    ChiusuraLegamePrezziDialog,
    {
      visible: true, articoloId: 'art-1', componenteId: 'leg-1', validoAl: '2026-11-10', header: 'Chiudi',
      domanda: { messaggio: 'Chiudendo il componente F si chiudono anche 1 prezzi bundle' },
    },
    {
      messages: { catalogo: { chiusura_prezzi: { riga: 'Listino {listino} {versione}' } } },
      global: { stubs: { AppDialog: CorniceFinta } },
    },
  )
  await flushPromises()
  return wrapper
}

describe('ChiusuraLegamePrezziDialog', () => {
  beforeEach(() => { chiamate.length = 0 })

  it('1) con prezzi: la conferma dichiara il numero letto', async () => {
    risposta = prezzi([prezzo(), prezzo({ riga_id: 2, esito: 'TOGLIE' })])
    const wrapper = await montaDialog()
    wrapper.findComponent(CorniceFinta).vm.$emit('save')
    expect(wrapper.emitted('conferma')[0][0]).toEqual({ prezzi_confermati: 2 })
    expect(wrapper.text()).toContain('LIST1')
  })

  it('2) la lettura va al legame e alla data della chiamata in sospeso', async () => {
    risposta = prezzi([prezzo()])
    await montaDialog()
    expect(chiamate).toEqual([['art-1', 'leg-1', '2026-11-10']])
  })

  it('3) prezzi spariti: conferma senza dichiarazione', async () => {
    risposta = prezzi([])
    const wrapper = await montaDialog()
    wrapper.findComponent(CorniceFinta).vm.$emit('save')
    expect(wrapper.emitted('conferma')[0][0]).toEqual({})
    expect(wrapper.text()).not.toContain('Chiudendo il componente')
  })

  it('4) finche\' la lettura non arriva, la conferma e\' spenta', async () => {
    risposta = new Promise(() => {})
    const wrapper = await montaDialog()
    expect(wrapper.findComponent(CorniceFinta).props('saveDisabled')).toBe(true)
  })

  it('5) un prezzo fuori perimetro si dice, senza i suoi dati', async () => {
    risposta = prezzi([
      prezzo(),
      prezzo({ riga_id: null, listino_codice: null, codice_versione: null, nel_perimetro: false }),
    ])
    const wrapper = await montaDialog()
    const voci = wrapper.findAll('li')
    expect(voci).toHaveLength(2)
    expect(voci[1].text()).not.toContain('null')
  })
})
