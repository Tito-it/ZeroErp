// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: l'uscita di `AppDialog` passa da `confermaUscita` (2026-10-03, D-14 di
//        work-done/analisi-fe-chrome-drawer.md).
//
// ⚠️ Il `<Dialog>` di PrimeVue qui e' un FINTO che rende slot e footer ed
//    emette `update:visible` a comando: si prova il guscio, non PrimeVue.
//
// Indice test:
//   1) senza `confermaUscita` l'Annulla esce subito (com'era)
//   2) ⭐ l'Annulla passa da `confermaUscita`: senza conferma non si esce
//   3) ⭐ la X (update:visible false) passa dalla STESSA conferma
//   4) ⭐ l'ESC passa dalla stessa conferma
//   5) lo slot `#footer` riceve `chiudi`, che passa dalla conferma
//   6) ⭐ all'apertura il fuoco entra nel dialog (senza, ESC non si sente)
//   7) un fuoco gia' dentro il dialog (un `autofocus`) resta dov'e'
//   8) ⭐ in testa il tasto «Esc», il titolo e' quello di `aria-labelledby`
//   9) dove ESC e' spento il tasto non si dice
// ------------------------------------------------------------

import { describe, it, expect, beforeEach } from 'vitest'
import { defineComponent, h, ref } from 'vue'
import { setActivePinia, createPinia } from 'pinia'

import AppDialog from './AppDialog.vue'
import { monta } from '../../../test/montaggio'

const DialogFinto = defineComponent({
  name: 'DialogFinto',
  props: ['visible', 'header', 'pt'],
  emits: ['update:visible', 'show'],
  setup(props, { slots, expose }) {
    // Come PrimeVue: la radice e' esposta come `container`.
    const container = ref(null)
    expose({ container })
    return () =>
      h('div', { ref: container, class: 'dialog-finto', ...props.pt?.root }, [
        h('header', slots.header?.({ class: 'p-dialog-title' })),
        h('main', slots.default?.()),
        h('footer', slots.footer?.()),
      ])
  },
})

function montaDialog(props = {}, opts = {}) {
  return monta(
    AppDialog,
    { visible: true, header: 'Prova', ...props },
    {
      slots: { default: '<p class="contenuto">campi</p>', ...opts.slots },
      global: { stubs: { Dialog: DialogFinto } },
      attachTo: opts.attachTo,
    },
  )
}

function pulsante(w, testo) {
  return w.find('footer').findAll('button').find((b) => b.text() === testo)
}

describe('AppDialog — uscita', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('1) senza confermaUscita l`Annulla esce subito', async () => {
    const w = montaDialog()
    await pulsante(w, 'common.cancel').trigger('click')
    expect(w.emitted('cancel')).toHaveLength(1)
    expect(w.emitted('update:visible')).toEqual([[false]])
  })

  it('2) l`Annulla passa da confermaUscita: senza conferma non si esce', async () => {
    // 🔴 D-14: i dialog con campi si chiudevano in silenzio, buttando cio' che
    //    si era scritto (il dialog dei componenti BoM, rilievo di Tid).
    let procedi = null
    const w = montaDialog({ confermaUscita: (chiudi) => { procedi = chiudi } })
    await pulsante(w, 'common.cancel').trigger('click')
    expect(w.emitted('update:visible')).toBeUndefined()
    procedi()
    expect(w.emitted('update:visible')).toEqual([[false]])
  })

  it('3) la X passa dalla stessa conferma', () => {
    let chiamate = 0
    const w = montaDialog({ confermaUscita: () => { chiamate++ } })
    w.findComponent(DialogFinto).vm.$emit('update:visible', false)
    expect(chiamate).toBe(1)
    expect(w.emitted('update:visible')).toBeUndefined()
  })

  it('4) l`ESC passa dalla stessa conferma', async () => {
    let chiamate = 0
    const w = montaDialog({ confermaUscita: () => { chiamate++ } })
    await w.find('.dialog-finto').trigger('keydown', { code: 'Escape' })
    expect(chiamate).toBe(1)
    expect(w.emitted('update:visible')).toBeUndefined()
  })

  it('5) lo slot #footer riceve chiudi, che passa dalla conferma', async () => {
    let chiamate = 0
    const w = montaDialog(
      { confermaUscita: () => { chiamate++ } },
      { slots: { footer: '<template #footer="{ chiudi }"><button class="mio" @click="chiudi">Esci</button></template>' } },
    )
    await w.find('button.mio').trigger('click')
    expect(chiamate).toBe(1)
  })

  it('6) all`apertura il fuoco entra nel dialog', () => {
    // 🔴 Rilievo di Tid (2026-10-11): senza un campo `autofocus` il fuoco
    //    restava fuori, l'ESC arrivava a `document` e non chiudeva niente.
    const fuori = document.createElement('button')
    document.body.appendChild(fuori)
    fuori.focus()
    const w = montaDialog({}, { attachTo: document.body })
    w.findComponent(DialogFinto).vm.$emit('show')
    expect(document.activeElement).toBe(w.find('.dialog-finto').element)
    fuori.remove()
  })

  it('7) un fuoco gia` dentro il dialog resta dov`e`', () => {
    const w = montaDialog(
      {},
      { attachTo: document.body, slots: { default: '<input class="campo" />' } },
    )
    const campo = w.find('input.campo').element
    campo.focus()
    w.findComponent(DialogFinto).vm.$emit('show')
    expect(document.activeElement).toBe(campo)
  })

  it('8) in testa il tasto Esc, e il titolo e` quello di aria-labelledby', () => {
    const w = montaDialog()
    expect(w.find('header kbd.app-kbd').exists()).toBe(true)
    const titolo = w.find('header .p-dialog-title')
    expect(titolo.text()).toBe('Prova')
    expect(w.find('.dialog-finto').attributes('aria-labelledby')).toBe(titolo.attributes('id'))
  })

  it('9) dove ESC e` spento il tasto non si dice', () => {
    const w = montaDialog({ closeOnEscape: false })
    expect(w.find('header kbd').exists()).toBe(false)
  })
})
