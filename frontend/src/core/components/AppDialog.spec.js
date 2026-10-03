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
// ------------------------------------------------------------

import { describe, it, expect, beforeEach } from 'vitest'
import { defineComponent, h } from 'vue'
import { setActivePinia, createPinia } from 'pinia'

import AppDialog from './AppDialog.vue'
import { monta } from '../../../test/montaggio'

const DialogFinto = defineComponent({
  name: 'DialogFinto',
  props: ['visible', 'header', 'pt'],
  emits: ['update:visible'],
  setup(props, { slots }) {
    return () =>
      h('div', { class: 'dialog-finto', ...props.pt?.root }, [
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
})
