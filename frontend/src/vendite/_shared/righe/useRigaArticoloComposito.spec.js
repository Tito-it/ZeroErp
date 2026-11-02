// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: il legame form ↔ riga dei form di riga dei documenti
//        (`seguiRiga` di useRigaArticoloComposito, 2026-10-03).
//
// Indice test:
//   1) riga caricata: il form si popola e non risulta modificato
//   2) ⭐ la STESSA riga riletta dal server con il form modificato non
//      cancella cio' che ha scritto l'operatore
//   3) la stessa riga riletta a form pulito si ripopola tutta
//   4) padre composito modificato: si allinea il solo prezzo (somma dei componenti)
//   5) un'altra riga si popola sempre
// ------------------------------------------------------------

import { describe, it, expect, vi } from 'vitest'
import { createApp, nextTick, ref } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { createI18n } from 'vue-i18n'
import { createRouter, createMemoryHistory } from 'vue-router'
import PrimeVue from 'primevue/config'
import ConfirmationService from 'primevue/confirmationservice'

// Le UoM e il dialog componenti non c'entrano col legame: fuori dal test.
vi.mock('../../../catalogo/composables/useArticoloUomOptions', () => ({
  useArticoloUomOptions: () => ({
    uomOptions: ref([]), uomLoading: ref(false),
    loadUomPerArticolo: async () => [], pickBaseUomId: () => null, resetUomOptions: () => {},
  }),
}))
vi.mock('../componenti/useComponentiDialog', () => ({
  useComponentiDialog: () => ({ componentiPayload: ref(null) }),
}))

const { useRigaArticoloComposito } = await import('./useRigaArticoloComposito')

// Scopo: monta il composable dentro un'app vera (la fotografia usa inject:
//        confirm, i18n, route) con un `popola` di dominio minimo.
function montaForm(rigaIniziale) {
  const riga = ref(rigaIniziale)
  const form = ref({})
  const articoloObj = ref(null)
  let api
  const app = createApp({
    setup() {
      api = useRigaArticoloComposito({ store: {}, parentId: () => 1, riga: () => riga.value, articoloObj, form })
      api.seguiRiga((r) => {
        form.value = r
          ? { descrizione: r.descrizione, qta_operativa: Number(r.qta_operativa), prezzo_unitario: Number(r.prezzo_unitario) }
          : { descrizione: '', qta_operativa: 1, prezzo_unitario: null }
      })
      return () => null
    },
  })
  const pinia = createPinia()
  setActivePinia(pinia)
  app.use(pinia)
  app.use(createI18n({ legacy: false, locale: 'it', messages: { it: {} }, missingWarn: false, fallbackWarn: false }))
  app.use(createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { render: () => null } }] }))
  app.use(PrimeVue)
  app.use(ConfirmationService)
  app.mount(document.createElement('div'))
  return { api, riga, form }
}

const RIGA = { id: 7, descrizione: 'Caldaia', qta_operativa: '2', prezzo_unitario: '100' }

async function giro() {
  await nextTick()
  await nextTick()
}

describe('useRigaArticoloComposito.seguiRiga', () => {
  it('1) riga caricata: form popolato, non modificato', async () => {
    const { api, form } = montaForm(RIGA)
    await giro()
    expect(form.value.descrizione).toBe('Caldaia')
    expect(api.modificato.value).toBe(false)
  })

  it('2) la stessa riga riletta non cancella le modifiche', async () => {
    const { api, riga, form } = montaForm(RIGA)
    await giro()
    form.value.qta_operativa = 5
    expect(api.modificato.value).toBe(true)
    riga.value = { ...RIGA, prezzo_unitario: '120' } // risincronizza: oggetto nuovo, stesso id
    await giro()
    expect(form.value.qta_operativa).toBe(5)
    expect(api.modificato.value).toBe(true)
  })

  it('3) la stessa riga riletta a form pulito si ripopola', async () => {
    const { api, riga, form } = montaForm(RIGA)
    await giro()
    riga.value = { ...RIGA, prezzo_unitario: '120' }
    await giro()
    expect(form.value.prezzo_unitario).toBe(120)
    expect(api.modificato.value).toBe(false)
  })

  it('4) padre composito modificato: si allinea il solo prezzo', async () => {
    const { api, riga, form } = montaForm({ ...RIGA, is_composito_caso_a: true })
    await giro()
    form.value.descrizione = 'Caldaia a condensazione'
    riga.value = { ...RIGA, is_composito_caso_a: true, prezzo_unitario: '130' }
    await giro()
    expect(form.value.descrizione).toBe('Caldaia a condensazione')
    expect(form.value.prezzo_unitario).toBe(130)
    expect(api.modificato.value).toBe(true)
  })

  it('5) un`altra riga si popola sempre', async () => {
    const { api, riga, form } = montaForm(RIGA)
    await giro()
    form.value.qta_operativa = 5
    riga.value = { id: 8, descrizione: 'Pompa', qta_operativa: '1', prezzo_unitario: '40' }
    await giro()
    expect(form.value.descrizione).toBe('Pompa')
    expect(api.modificato.value).toBe(false)
  })
})
