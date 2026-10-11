// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: LA DICHIARAZIONE della conferma d'annullo di una bolla con legami
//        (D-8 di brief-db-ddt-righe-evase-dall-ordine): che cosa
//        `DdtAnnulloLegamiDialog` manda al chiamante quando l'operatore
//        conferma.
// Note: ⭐ Il numero dichiarato dev'essere quello LETTO dal dialog
//       (`GET …/legami/`), e il caso dei legami spariti fra la domanda del DB
//       e la lettura (zero righe) non deve lasciare l'operatore bloccato: si
//       conferma SENZA dichiarazione. Prima del 2026-10-11 il pulsante
//       restava spento.
//       ⚠️ Si monta il dialog VERO; si fingono i contorni: l'API dei legami,
//       la cornice `AppDialog` (se ne leggono `saveDisabled` e l'evento
//       `save`) e l'host del drawer del documento d'origine.
//
// Indice test:
//  1) con legami: la conferma dichiara il numero letto
//  2) legami spariti: conferma attiva, nessuna dichiarazione, frase propria
//  3) finche' la lettura non arriva, la conferma e' spenta
// ------------------------------------------------------------
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { defineComponent } from 'vue'
import { flushPromises } from '@vue/test-utils'

import DdtAnnulloLegamiDialog from './DdtAnnulloLegamiDialog.vue'
import { monta } from '../../../../../test/montaggio'

let rispostaLegami = null
vi.mock('../../api/ddtApi', () => ({
  getDdtLegami: () => rispostaLegami,
}))

const CorniceFinta = defineComponent({
  name: 'AppDialog',
  props: { saveDisabled: { type: Boolean, default: false } },
  emits: ['save', 'cancel'],
  template: '<div><slot /></div>',
})

function legami(dati) {
  return Promise.resolve({ data: { data: { ddt_id: 7, origini: [], ...dati } } })
}

async function montaDialog() {
  const wrapper = monta(
    DdtAnnulloLegamiDialog,
    { visible: true, ddtId: 7, domanda: { messaggio: 'La bolla ha 2 righe legate' } },
    { global: { stubs: { AppDialog: CorniceFinta, DocumentoDrawerHost: true } } },
  )
  await flushPromises()
  return wrapper
}

describe('DdtAnnulloLegamiDialog — la dichiarazione', () => {
  beforeEach(() => {
    rispostaLegami = null
  })

  it('con legami: la conferma dichiara il numero letto', async () => {
    rispostaLegami = legami({
      righe_legate: 2,
      legami: [
        { ddt_riga_id: 31, riga_nr: 1, origine: 'ORDINE', origine_riga_id: 5, qta: '10' },
        { ddt_riga_id: 32, riga_nr: 2, origine: 'ORDINE', origine_riga_id: 6, qta: '4' },
      ],
    })
    const wrapper = await montaDialog()
    const cornice = wrapper.findComponent(CorniceFinta)
    expect(cornice.props('saveDisabled')).toBe(false)
    cornice.vm.$emit('save')
    expect(wrapper.emitted('conferma')).toEqual([[{ righe_legate_confermate: 2 }]])
  })

  it('legami spariti: si conferma senza dichiarazione', async () => {
    rispostaLegami = legami({ righe_legate: 0, legami: [] })
    const wrapper = await montaDialog()
    const cornice = wrapper.findComponent(CorniceFinta)
    expect(cornice.props('saveDisabled')).toBe(false)
    expect(wrapper.text()).toContain('vendite.ddt.annullo_legami.nessun_legame')
    expect(wrapper.text()).not.toContain('La bolla ha 2 righe legate')
    cornice.vm.$emit('save')
    expect(wrapper.emitted('conferma')).toEqual([[{}]])
  })

  it('finche\' la lettura non arriva, la conferma e\' spenta', async () => {
    rispostaLegami = new Promise(() => {})
    const wrapper = await montaDialog()
    expect(wrapper.findComponent(CorniceFinta).props('saveDisabled')).toBe(true)
  })
})
