// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: la fotografia di `useRigheSelezioneQta` (D-14, 2026-10-03): selezione
//        e quantita' sono lavoro dell'operatore, i dati caricati no.
//
// Indice test:
//   1) righe caricate (preselezionate): niente da chiedere
//   2) una quantita' cambiata e' una modifica
//   3) ⭐ la RICARICA rifissa: la selezione riscritta e' la nuova base
//   4) lo stato extra del chiamante entra nella fotografia
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'
import { createApp, nextTick, ref } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { createI18n } from 'vue-i18n'
import { createRouter, createMemoryHistory } from 'vue-router'
import PrimeVue from 'primevue/config'
import ConfirmationService from 'primevue/confirmationservice'
import { useRigheSelezioneQta } from './useRigheSelezioneQta'

const RIGHE = [{ id: 1, residuo: 3 }, { id: 2, residuo: 5 }]

// Scopo: il BB dentro un'app vera (la fotografia usa inject: confirm, i18n, route).
function monta(opzioni = {}) {
  let api
  const app = createApp({
    setup() {
      api = useRigheSelezioneQta({
        fetchRighe: async () => RIGHE.map((r) => ({ ...r })),
        residuoDi: (r) => r.residuo,
        visibile: () => true,
        ...opzioni,
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
  return api
}

describe('useRigheSelezioneQta — fotografia', () => {
  it('1) righe caricate: niente da chiedere', async () => {
    const api = monta()
    await api.loadRighe()
    expect(api.selected.value).toHaveLength(2)
    expect(api.modificato.value).toBe(false)
  })

  it('2) una quantita` cambiata e` una modifica', async () => {
    const api = monta()
    await api.loadRighe()
    api.qtaMap.value = { ...api.qtaMap.value, 1: 2 }
    await nextTick()
    expect(api.modificato.value).toBe(true)
  })

  it('3) la ricarica rifissa la fotografia', async () => {
    const api = monta()
    await api.loadRighe()
    api.qtaMap.value = { ...api.qtaMap.value, 1: 2 }
    await api.loadRighe()
    expect(api.modificato.value).toBe(false)
  })

  it('4) lo stato extra del chiamante entra nella fotografia', async () => {
    const motivo = ref({})
    const api = monta({ statoExtra: () => ({ motivo: motivo.value }) })
    await api.loadRighe()
    motivo.value = { 1: 'rotto' }
    await nextTick()
    expect(api.modificato.value).toBe(true)
  })
})
