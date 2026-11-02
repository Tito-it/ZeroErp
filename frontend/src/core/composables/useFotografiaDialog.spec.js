// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: la fotografia dei dialog con campi (`useFotografiaDialog`, D-14 di
//        work-done/analisi-fe-chrome-drawer.md).
//
// Indice test:
//   1) all'apertura la fotografia e' lo stato preparato: niente da chiedere
//   2) un campo cambiato e' una modifica; rimesso com'era, non piu'
//   3) ⭐ con `fissaAllApertura: false` i dati caricati dopo NON sono modifiche,
//      se il dialog chiama `fissa()` a caricamento finito
//   4) alla chiusura la fotografia si azzera: la riapertura riparte pulita
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'
import { createApp, nextTick, ref } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { createI18n } from 'vue-i18n'
import { createRouter, createMemoryHistory } from 'vue-router'
import PrimeVue from 'primevue/config'
import ConfirmationService from 'primevue/confirmationservice'
import { useFotografiaDialog } from './useFotografiaDialog'

// Scopo: esegue `fn` dentro il setup di un'app vera (il BB usa inject: confirm,
//        i18n, route), e ne restituisce il risultato.
function nelSetup(fn) {
  let risultato
  const app = createApp({ setup() { risultato = fn(); return () => null } })
  const pinia = createPinia()
  setActivePinia(pinia)
  app.use(pinia)
  app.use(createI18n({ legacy: false, locale: 'it', messages: { it: {} }, missingWarn: false, fallbackWarn: false }))
  app.use(createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { render: () => null } }] }))
  app.use(PrimeVue)
  app.use(ConfirmationService)
  app.mount(document.createElement('div'))
  return risultato
}

describe('useFotografiaDialog', () => {
  it('1) all`apertura lo stato preparato non e` una modifica', async () => {
    const visibile = ref(false)
    const data = ref(null)
    const f = nelSetup(() => useFotografiaDialog(() => ({ data: data.value }), { visibile: () => visibile.value }))
    visibile.value = true
    data.value = '2026-10-03' // il dialog si prepara all'apertura
    await nextTick()
    await nextTick()
    expect(f.modificato.value).toBe(false)
  })

  it('2) un campo cambiato e` una modifica; rimesso com`era, no', async () => {
    const visibile = ref(true)
    const motivo = ref('')
    const f = nelSetup(() => useFotografiaDialog(() => ({ motivo: motivo.value }), { visibile: () => visibile.value }))
    await nextTick()
    await nextTick()
    motivo.value = 'reso danneggiato'
    expect(f.modificato.value).toBe(true)
    motivo.value = ''
    expect(f.modificato.value).toBe(false)
  })

  it('3) con fissaAllApertura false i dati caricati non sono modifiche', async () => {
    const visibile = ref(true)
    const prezzi = ref({})
    const f = nelSetup(() => useFotografiaDialog(
      () => ({ prezzi: prezzi.value }),
      { visibile: () => visibile.value, fissaAllApertura: false },
    ))
    // Arriva la fetch: il dialog scrive i prezzi e POI fissa.
    prezzi.value = { 10: 5.5 }
    f.fissa()
    expect(f.modificato.value).toBe(false)
    prezzi.value = { 10: 6 }
    expect(f.modificato.value).toBe(true)
  })

  it('4) alla chiusura la fotografia si azzera', async () => {
    const visibile = ref(true)
    const motivo = ref('')
    const f = nelSetup(() => useFotografiaDialog(() => ({ motivo: motivo.value }), { visibile: () => visibile.value }))
    await nextTick()
    await nextTick()
    motivo.value = 'abbandonato'
    visibile.value = false
    await nextTick()
    expect(f.modificato.value).toBe(false)
  })
})
