// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: il contratto della sede del chrome dei drawer (`AppDrawer`, riscritto
//        il 2026-10-03, work-done/analisi-fe-chrome-drawer.md).
//
// ⚠️ Il `<Drawer>` di PrimeVue qui e' un FINTO che rende i tre slot ed emette
//    gli eventi a comando: il vero teleporta sul body e si apre con
//    un'animazione che jsdom non esegue. Si prova il GUSCIO — che cosa rende,
//    da dove passa l'uscita — non PrimeVue.
//
// Indice test:
//   1) il contenuto si monta solo a fine animazione (`after-show`)
//   2) footer 'form': Annulla + Salva, e il Salva emette `save`
//   3) ⭐ l'Annulla passa da `confermaUscita`: se non conferma, non si esce
//   4) ⭐ la X (update:visible false) passa dalla STESSA conferma
//   5) footer 'chiudi': il solo Chiudi, che esce
//   6) footer 'nessuno': niente footer
//   7) `readonly` stringe la catena: corpo `app-readonly`, niente Salva
//   8) la catena readonly del padre arriva senza prop
//   9) la larghezza fuori scala non passa il validatore
//  10) lo slot `#footer` sostituisce il footer e riceve `chiudi`
//  11) `conteggio`: il numero compare accanto al titolo, a 0 no
//  12) `after-show` arriva al chiamante, insieme al montaggio del contenuto
//  13) `proteggiCorpo: false`: corpo cliccabile, ma la catena readonly arriva ai figli
//  14) il footer nasce col contenuto: niente Salva durante lo slide
//  15) `footerReadonly: false` riaccende il Salva dentro una catena in sola lettura
//  16) `#footer-azioni` aggiunge pulsanti accanto ad Annulla/Salva, che restano del guscio
//  17) ⭐ esce solo il drawer in cima: sotto un drawer aperto ESC/X non fanno niente
//  18) ⭐ la X dice il suo tasto (etichetta + aria-label) e passa dalla conferma d'uscita
// ------------------------------------------------------------

import { describe, it, expect, beforeEach } from 'vitest'
import { defineComponent, h, ref } from 'vue'
import { setActivePinia, createPinia } from 'pinia'

import AppDrawer from './AppDrawer.vue'
import { READONLY_KEY } from '../composables/useReadonlyMode'
import { DRAWER_WIDTH } from '../constants'
import { monta } from '../../../test/montaggio'

const DrawerFinto = defineComponent({
  name: 'DrawerFinto',
  props: ['visible', 'dismissable', 'position'],
  emits: ['update:visible', 'after-show'],
  setup(props, { slots, attrs, emit }) {
    // Lo slot `closebutton` riceve la callback di uscita, come in PrimeVue
    // (`hide()` emette `update:visible` false).
    return () =>
      h('div', { class: 'drawer-finto', style: attrs.style }, [
        h('nav', slots.closebutton?.({ closeCallback: () => emit('update:visible', false) })),
        h('header', slots.header?.()),
        h('main', slots.default?.()),
        slots.footer ? h('footer', slots.footer()) : null,
      ])
  },
})

function montaDrawer(props = {}, opts = {}) {
  return monta(
    AppDrawer,
    { visible: true, title: 'Canale', ...props },
    {
      slots: { default: '<p class="contenuto">campi</p>', ...opts.slots },
      provide: opts.provide || {},
      global: { stubs: { Drawer: DrawerFinto } },
    },
  )
}

async function aperto(w) {
  w.findComponent(DrawerFinto).vm.$emit('after-show')
  await w.vm.$nextTick()
}

function pulsanti(w) {
  return w.find('footer').exists() ? w.find('footer').findAll('button') : []
}

function pulsante(w, testo) {
  return pulsanti(w).find((b) => b.text() === testo)
}

describe('AppDrawer', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('1) il contenuto si monta solo a fine animazione', async () => {
    const w = montaDrawer()
    expect(w.find('.contenuto').exists()).toBe(false)
    await aperto(w)
    expect(w.find('.app-drawer-content .contenuto').exists()).toBe(true)
  })

  it('2) footer form: Annulla + Salva, il Salva emette save', async () => {
    const w = montaDrawer()
    await aperto(w)
    expect(pulsanti(w).map((b) => b.text())).toEqual(['common.cancel', 'common.save'])
    await pulsante(w, 'common.save').trigger('click')
    expect(w.emitted('save')).toHaveLength(1)
  })

  it('3) l`Annulla passa da confermaUscita: senza conferma non si esce', async () => {
    let chiudiRicevuto = null
    const w = montaDrawer({ confermaUscita: (chiudi) => { chiudiRicevuto = chiudi } })
    await aperto(w)
    await pulsante(w, 'common.cancel').trigger('click')
    // La domanda e' aperta: nessuno e' uscito ancora.
    expect(w.emitted('update:visible')).toBeUndefined()
    // L'operatore conferma.
    chiudiRicevuto()
    expect(w.emitted('cancel')).toHaveLength(1)
    expect(w.emitted('update:visible')).toEqual([[false]])
  })

  it('4) la X passa dalla STESSA conferma dell`Annulla', async () => {
    // 🔴 E' il difetto D-1 dell'analisi: tre drawer chiudevano dalla X con un
    //    emit diretto, e la riga in compilazione si perdeva senza domanda.
    let chiamate = 0
    const w = montaDrawer({ confermaUscita: () => { chiamate++ } })
    w.findComponent(DrawerFinto).vm.$emit('update:visible', false)
    expect(chiamate).toBe(1)
    expect(w.emitted('update:visible')).toBeUndefined()
  })

  it('5) footer chiudi: il solo Chiudi, che esce', async () => {
    const w = montaDrawer({ footer: 'chiudi' })
    await aperto(w)
    expect(pulsanti(w).map((b) => b.text())).toEqual(['common.close'])
    await pulsante(w, 'common.close').trigger('click')
    expect(w.emitted('update:visible')).toEqual([[false]])
  })

  it('6) footer nessuno: niente footer', async () => {
    const w = montaDrawer({ footer: 'nessuno' })
    await aperto(w)
    expect(w.find('footer').exists()).toBe(false)
  })

  it('7) readonly stringe la catena: corpo app-readonly, niente Salva', async () => {
    const w = montaDrawer({ readonly: true })
    await aperto(w)
    expect(w.find('.app-drawer-content').classes()).toContain('app-readonly')
    expect(pulsante(w, 'common.save')).toBeUndefined()
  })

  it('8) la catena readonly del padre arriva senza prop', async () => {
    const w = montaDrawer({}, { provide: { [READONLY_KEY]: ref(true) } })
    await aperto(w)
    expect(w.find('.app-drawer-content').classes()).toContain('app-readonly')
    expect(pulsante(w, 'common.save')).toBeUndefined()
  })

  it('9) la larghezza fuori scala non passa il validatore', () => {
    const valida = AppDrawer.props.width.validator
    expect(valida(DRAWER_WIDTH.WIDE)).toBe(true)
    expect(valida('1000px')).toBe(false)
  })

  it('10) lo slot #footer sostituisce il footer e riceve chiudi', async () => {
    const w = montaDrawer(
      {},
      { slots: { footer: '<template #footer="{ chiudi }"><button class="mio" @click="chiudi">Fine</button></template>' } },
    )
    await aperto(w)
    expect(pulsanti(w).map((b) => b.text())).toEqual(['Fine'])
    await w.find('button.mio').trigger('click')
    expect(w.emitted('update:visible')).toEqual([[false]])
  })

  it('11) conteggio: il numero compare accanto al titolo, a 0 no', () => {
    // D-10: le colonne nuove di una lista, i widget nuovi della home.
    const conNuove = montaDrawer({ conteggio: 3 })
    expect(conNuove.find('header .app-drawer-title-conteggio').text()).toBe('3')
    const senza = montaDrawer({ conteggio: 0 })
    expect(senza.find('header .app-drawer-title-conteggio').exists()).toBe(false)
  })

  it('12) after-show arriva al chiamante, insieme al montaggio del contenuto', async () => {
    // Serve a chi aspetta la fine dell'animazione per agire: l'auto-salvataggio
    // della bozza dei documenti non deve partire mentre il drawer scorre.
    const w = montaDrawer()
    expect(w.emitted('after-show')).toBeUndefined()
    await aperto(w)
    expect(w.emitted('after-show')).toHaveLength(1)
    expect(w.find('.contenuto').exists()).toBe(true)
  })

  it('13) proteggiCorpo false: corpo cliccabile, la catena readonly arriva ai figli', async () => {
    // 🔴 Con `app-readonly` sull'intero corpo, in sola lettura si spegnevano il
    //    kebab di riga e i pulsanti di consultazione dei drawer che proteggono
    //    nascondendo le azioni.
    const w = montaDrawer({ readonly: true, proteggiCorpo: false })
    await aperto(w)
    expect(w.find('.app-drawer-content').classes()).not.toContain('app-readonly')
    // ...ma il Salva resta nascosto: FormFooter legge la catena.
    expect(pulsante(w, 'common.save')).toBeUndefined()
  })

  it('14) il footer nasce col contenuto: niente Salva durante lo slide', async () => {
    // 🔴 Montato dal primo frame, Salva e Ctrl+S salvavano il form del record
    //    aperto PRIMA, che il drawer non aveva ancora sostituito.
    const w = montaDrawer()
    expect(w.find('footer').exists()).toBe(false)
    await aperto(w)
    expect(pulsante(w, 'common.save')).toBeDefined()
  })

  it('15) footerReadonly false riaccende il Salva in una catena in sola lettura', async () => {
    // L'eccezione di dominio (riferimenti dell'atto di un contratto ATTIVO):
    // il corpo resta protetto, il Salva torna; senza override resta nascosto.
    const w = montaDrawer({ readonly: true, footerReadonly: false })
    await aperto(w)
    expect(w.find('.app-drawer-content').classes()).toContain('app-readonly')
    expect(pulsante(w, 'common.save')).toBeDefined()
    const senza = montaDrawer({ readonly: true })
    await aperto(senza)
    expect(pulsante(senza, 'common.save')).toBeUndefined()
  })

  it('16) #footer-azioni aggiunge pulsanti, Annulla/Salva restano del guscio', async () => {
    const w = montaDrawer({}, { slots: { 'footer-azioni': '<button class="ripristina">Ripristina</button>' } })
    await aperto(w)
    expect(pulsanti(w).map((b) => b.text())).toEqual(['Ripristina', 'common.cancel', 'common.save'])
    await pulsante(w, 'common.save').trigger('click')
    expect(w.emitted('save')).toHaveLength(1)
  })

  it('17) esce solo il drawer in cima: il padre sotto un figlio aperto ignora ESC/X', async () => {
    // 🔴 Il difetto: ESC arriva a tutti i Drawer aperti, e il padre si
    //    chiudeva smontando il figlio con le sue modifiche, senza chiedere.
    let uscitePadre = 0
    const padre = montaDrawer({ confermaUscita: () => { uscitePadre++ } })
    const figlio = montaDrawer({ title: 'Figlio' })
    padre.findComponent(DrawerFinto).vm.$emit('update:visible', false)
    expect(uscitePadre).toBe(0)
    // Il figlio, in cima, esce.
    figlio.findComponent(DrawerFinto).vm.$emit('update:visible', false)
    expect(figlio.emitted('update:visible')).toEqual([[false]])
    // Chiuso il figlio, il padre torna in cima ed esce di nuovo.
    await figlio.setProps({ visible: false })
    padre.findComponent(DrawerFinto).vm.$emit('update:visible', false)
    expect(uscitePadre).toBe(1)
    figlio.unmount()
    padre.unmount()
  })

  it('18) la X dice il suo tasto e passa dalla stessa conferma d`uscita', async () => {
    let uscite = 0
    const w = montaDrawer({ confermaUscita: () => { uscite++ } })
    const x = w.find('nav button')
    expect(w.find('nav kbd.app-kbd').exists()).toBe(true)
    // La forma «azione (tasto)» passa dalla chiave, non e' scritta qui.
    expect(x.attributes('aria-label')).toContain('common.con_scorciatoia')
    await x.trigger('click')
    expect(uscite).toBe(1)
    expect(w.emitted('update:visible')).toBeUndefined()
    w.unmount()
  })
})
