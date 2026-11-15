// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: `CopiaIndirizzoDialog` — la scelta dei tipi di «Copia come…» (R-4 di
//        brief-db-copia-indirizzo-soggetto).
//
// ⚠️ Il `<Dialog>` di PrimeVue qui e' un FINTO che rende slot e footer: si
//    prova il componente, non PrimeVue.
//
// Indice test:
//   1) il tipo NON ammesso resta visibile, spento, con la frase della sua
//      `reason_key` riempita coi `reason_valori` posizionali
//   2) senza una scelta il pulsante e' spento; `confirm` porta i codici
//      nell'ordine dell'elenco, non in quello dei clic
//   3) alla riapertura nessun tipo resta scelto
// ------------------------------------------------------------

import { describe, it, expect, beforeEach } from 'vitest'
import { defineComponent, h } from 'vue'
import { setActivePinia, createPinia } from 'pinia'

import CopiaIndirizzoDialog from './CopiaIndirizzoDialog.vue'
import { monta } from '../../../test/montaggio'

const DialogFinto = defineComponent({
  name: 'DialogFinto',
  props: ['visible', 'header', 'pt'],
  emits: ['update:visible'],
  setup(props, { slots }) {
    return () =>
      h('div', { class: 'dialog-finto' }, [
        h('main', slots.default?.()),
        h('footer', slots.footer?.()),
      ])
  },
})

const TIPI = [
  { codice_interno: 'SEDELEG', descrizione: 'Sede legale', ammesso: false,
    reason: 'TIPO_GIA_PRESENTE', reason_key: 'anagrafiche.indirizzi.tipo_blocco.gia_presente',
    reason_valori: ['Sede legale'] },
  { codice_interno: 'FATT', descrizione: 'Fatturazione', ammesso: true },
  { codice_interno: 'SPED', descrizione: 'Spedizione', ammesso: true },
]

const MESSAGGI = {
  anagrafiche: { indirizzi: {
    tipo_blocco: { gia_presente: 'C\'è già un indirizzo «{0}»' },
    copia: { conferma: 'Copia' },
  } },
}

function montaCopia(props = {}) {
  return monta(
    CopiaIndirizzoDialog,
    { visible: true, tipi: TIPI, ...props },
    { messages: MESSAGGI, global: { stubs: { Dialog: DialogFinto } } },
  )
}

const salva = (w) => w.find('footer').findAll('button').find((b) => b.text() === 'Copia')
const casella = (w, codice) => w.find(`#copia-${codice}`)

describe('CopiaIndirizzoDialog', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('1) il tipo non ammesso resta, spento, con la frase e il suo valore', () => {
    const w = montaCopia()
    expect(casella(w, 'SEDELEG').attributes('disabled')).toBeDefined()
    expect(w.find('.copia-tipo-motivo').text()).toBe('C\'è già un indirizzo «Sede legale»')
    expect(casella(w, 'FATT').attributes('disabled')).toBeUndefined()
  })

  it('2) senza scelta spento; i codici arrivano nell\'ordine dell\'elenco', async () => {
    const w = montaCopia()
    expect(salva(w).attributes('disabled')).toBeDefined()
    await casella(w, 'SPED').setValue(true)
    await casella(w, 'FATT').setValue(true)
    expect(salva(w).attributes('disabled')).toBeUndefined()
    await salva(w).trigger('click')
    expect(w.emitted('confirm')).toEqual([[['FATT', 'SPED']]])
  })

  it('3) alla riapertura nessun tipo resta scelto', async () => {
    const w = montaCopia()
    await casella(w, 'FATT').setValue(true)
    await w.setProps({ visible: false })
    await w.setProps({ visible: true })
    expect(salva(w).attributes('disabled')).toBeDefined()
  })
})
