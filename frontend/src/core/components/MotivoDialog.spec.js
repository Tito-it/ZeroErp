// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: `MotivoDialog` — confermare un gesto dandone il motivo (2026-10-03,
//        regola del 2).
//
// ⚠️ Il `<Dialog>` di PrimeVue qui e' un FINTO che rende slot e footer: si
//    prova il BB, non PrimeVue.
//
// Indice test:
//   1) obbligatorio: senza motivo il pulsante d'azione e' spento
//   2) `conferma` porta il motivo ripulito degli spazi; vuoto → null
//   3) ⭐ alla riapertura il motivo riparte vuoto (mai residui del giro prima)
//   4) ⭐ `altriCampi` entra nella fotografia: cambiato solo lui, uscire chiede
// ------------------------------------------------------------

import { describe, it, expect, beforeEach } from 'vitest'
import { defineComponent, h, nextTick, ref } from 'vue'
import { setActivePinia, createPinia } from 'pinia'

import MotivoDialog from './MotivoDialog.vue'
import AppDialog from './AppDialog.vue'
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

function montaMotivo(props = {}) {
  return monta(
    MotivoDialog,
    { visible: true, header: 'Blocca', label: 'Motivo', saveLabel: 'Blocca', ...props },
    { global: { stubs: { Dialog: DialogFinto } } },
  )
}

function salva(w) {
  return w.find('footer').findAll('button').find((b) => b.text() === 'Blocca')
}

describe('MotivoDialog', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('1) obbligatorio: senza motivo il pulsante e` spento', async () => {
    const w = montaMotivo({ obbligatorio: true })
    expect(salva(w).attributes('disabled')).toBeDefined()
    await w.find('textarea').setValue('telefono perso')
    expect(salva(w).attributes('disabled')).toBeUndefined()
  })

  it('2) conferma porta il motivo ripulito; vuoto → null', async () => {
    const w = montaMotivo()
    await salva(w).trigger('click')
    expect(w.emitted('conferma')).toEqual([[null]])
    await w.find('textarea').setValue('  credenziale ceduta  ')
    await salva(w).trigger('click')
    expect(w.emitted('conferma')[1]).toEqual(['credenziale ceduta'])
  })

  it('3) alla riapertura il motivo riparte vuoto', async () => {
    const w = montaMotivo()
    await w.find('textarea').setValue('motivo di ieri')
    await w.setProps({ visible: false })
    await w.setProps({ visible: true })
    expect(w.find('textarea').element.value).toBe('')
  })

  it('4) altriCampi entra nella fotografia: cambiato solo lui, uscire chiede', async () => {
    const prezzo = ref(10)
    const w = montaMotivo({ altriCampi: () => ({ prezzo: prezzo.value }) })
    await nextTick()
    await nextTick()
    const esci = w.findComponent(AppDialog).props('confermaUscita')
    let chiuso = 0
    esci(() => { chiuso += 1 })
    expect(chiuso).toBe(1) // niente di cambiato: si esce subito
    prezzo.value = 12
    esci(() => { chiuso += 1 })
    expect(chiuso).toBe(1) // il prezzo cambiato: si chiede, non si esce
  })
})
