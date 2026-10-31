// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: il contratto di `ListaConFormInline` (2026-10-31, regola del 2): la
//        lista legge il SUO padre, «Nuovo» e il clic aprono il form nello
//        slot, il salvataggio lo chiude e rilegge, e col padre composto senza
//        emittente la lista aspetta invece di chiedere.
//
// ⚠️ Si fingono i CONTORNI: il guscio `DrawerTabLista` (il vero chiede la
//    config del catalogo) rende le righe cliccabili e le azioni di pagina come
//    pulsanti; la `fetchPage` dello store e' una spia. Lo store
//    (`createListaStore`), `useDrawerTabLista` e `useFormInline` sono veri.
//
// Indice test:
//   1) legge col padre nel path; senza padre non legge
//   2) «Nuovo» apre il form in creazione (riga null), il clic apre la riga
//   3) ⭐ non modificabile: «Nuovo» non c'e' e il clic non apre niente
//   4) il salvataggio chiude il form, rilegge ed emette `changed`
//   5) ⭐ padre composto senza emittente: nessuna lettura; con l'emittente, si'
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}))

const { monta } = await import('../../../test/montaggio')
const { createListaStore } = await import('../stores/createListaStore')
const { default: ListaConFormInline } = await import('./ListaConFormInline.vue')

const DrawerTabListaFinto = defineComponent({
  name: 'DrawerTabListaFinto',
  props: { rows: { type: Array, default: () => [] }, pageActions: { type: Array, default: () => [] } },
  emits: ['row-click'],
  setup(props, { emit }) {
    return () => h('div', [
      ...props.pageActions
        .filter((a) => (typeof a.visible === 'function' ? a.visible() : a.visible !== false))
        .map((a) => h('button', { class: `azione-${a.key}`, onClick: a.command }, a.key)),
      ...props.rows.map((r) => h('div', { class: 'riga', onClick: () => emit('row-click', r) }, r.nome)),
    ])
  },
})

const FormFinto = defineComponent({
  name: 'FormFinto',
  props: { riga: { type: Object, default: null } },
  emits: ['saved'],
  setup(props, { emit }) {
    return () => h('div', { class: 'form-finto' }, [
      h('span', { class: 'form-riga' }, props.riga ? props.riga.nome : 'nuova'),
      h('button', { class: 'salva', onClick: () => emit('saved') }, 'salva'),
    ])
  },
})

// Come `NotaForm` e `ArticoloUomForm`: legge `riga` SOLO alla nascita.
const FormFotografia = defineComponent({
  name: 'FormFotografia',
  props: { riga: { type: Object, default: null } },
  setup(props) {
    const nome = props.riga ? props.riga.nome : 'nuova'
    return () => h('span', { class: 'form-riga' }, nome)
  },
})

let n = 0
function creaStore(opzioni = {}) {
  const fetchPage = vi.fn(async () => ({ data: { data: { results: [{ id: 1, nome: 'Prima' }], count: 1 } } }))
  const store = createListaStore(`lista-form-spec-${++n}`, {
    fetchPage, parentField: 'padreId', startsEmpty: false, ...opzioni,
  })()
  return { store, fetchPage }
}

function apri(store, props = {}, form = FormFinto) {
  return monta(ListaConFormInline, {
    codice: 'test.lista', store, parentId: 7,
    newTooltipKey: 'k.nuovo', newLabelKey: 'k.nuova', editLabelKey: 'k.modifica',
    ...props,
  }, {
    global: { stubs: { DrawerTabLista: DrawerTabListaFinto } },
    slots: {
      form: ({ riga, onSaved }) => h(form, { riga, onSaved }),
    },
  })
}

describe('ListaConFormInline', () => {
  beforeEach(() => { setActivePinia(createPinia()) })

  it('1) legge col padre nel path; senza padre non legge', async () => {
    const { store, fetchPage } = creaStore()
    const w = apri(store)
    await flushPromises()
    expect(fetchPage).toHaveBeenCalledTimes(1)
    expect(fetchPage.mock.calls[0][0]).toBe(7)
    expect(w.findAll('.riga')).toHaveLength(1)

    const altro = creaStore()
    apri(altro.store, { parentId: null })
    await flushPromises()
    expect(altro.fetchPage).not.toHaveBeenCalled()
  })

  it('2) «Nuovo» apre il form in creazione (riga null), il clic apre la riga', async () => {
    const { store } = creaStore()
    const w = apri(store)
    await flushPromises()
    expect(w.find('.form-finto').exists()).toBe(false)
    await w.find('.azione-new').trigger('click')
    expect(w.find('.form-riga').text()).toBe('nuova')
    expect(w.text()).toContain('k.nuova')
    // A form aperto «Nuovo» sparisce (regola di `useFormInline`).
    expect(w.find('.azione-new').exists()).toBe(false)
  })

  it('3) non modificabile: «Nuovo» non c\'e\' e il clic non apre niente', async () => {
    const { store } = creaStore()
    const w = apri(store, { isModificabile: false })
    await flushPromises()
    expect(w.find('.azione-new').exists()).toBe(false)
    await w.find('.riga').trigger('click')
    expect(w.find('.form-finto').exists()).toBe(false)
  })

  it('4) il salvataggio chiude il form, rilegge ed emette `changed`', async () => {
    const { store, fetchPage } = creaStore()
    const w = apri(store)
    await flushPromises()
    await w.find('.riga').trigger('click')
    expect(w.find('.form-riga').text()).toBe('Prima')
    expect(w.text()).toContain('k.modifica')
    await w.find('.salva').trigger('click')
    await flushPromises()
    expect(w.find('.form-finto').exists()).toBe(false)
    expect(w.emitted('changed')).toHaveLength(1)
    expect(fetchPage).toHaveBeenCalledTimes(2)
  })

  it('5) padre composto senza emittente: nessuna lettura; con l\'emittente, si\'', async () => {
    const { store, fetchPage } = creaStore({ emittenteParam: 'emittente_fiscale_id' })
    const w = apri(store, { conEmittente: true, emittenteFiscaleId: null })
    await flushPromises()
    expect(fetchPage).not.toHaveBeenCalled()
    await w.setProps({ emittenteFiscaleId: 3 })
    await flushPromises()
    expect(fetchPage).toHaveBeenCalledTimes(1)
    expect(fetchPage.mock.calls[0][1]).toMatchObject({ emittente_fiscale_id: 3 })
  })

  it('6) clic su un\'altra riga a form aperto: il form rinasce sulla riga nuova', async () => {
    const fetchPage = vi.fn(async () => ({
      data: { data: { results: [{ id: 1, nome: 'Prima' }, { id: 2, nome: 'Seconda' }], count: 2 } },
    }))
    const { store } = creaStore({ fetchPage })
    const w = apri(store, {}, FormFotografia)
    await flushPromises()
    const righe = w.findAll('.riga')
    await righe[0].trigger('click')
    expect(w.find('.form-riga').text()).toBe('Prima')
    // Form non modificato: nessuna conferma, il cambio e' immediato.
    await righe[1].trigger('click')
    await flushPromises()
    expect(w.find('.form-riga').text()).toBe('Seconda')
  })
})
