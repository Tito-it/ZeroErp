// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: `useEditableCollection` espone i campi in errore dell'istanza di
//        `useApiHandler` con cui SALVA. Fino al 2026-11-22 i sei tab
//        dell'editor dei workflow li leggevano da una prop della vista, che ha
//        un `useApiHandler` suo: il rifiuto di un salvataggio del tab riempiva
//        un'istanza che nessuno guardava, e nessun campo diventava rosso.
// Note: `useApiHandler` e' finto, e registra ogni istanza creata: il caso 1
//       prova che i campi esposti sono quelli dell'istanza che ha chiamato
//       l'API, non di un'altra. Il trasporto vero di `error.fields` lo prova
//       `core/composables/useApiHandler.spec.js`.
//
// Indice test:
//   1) un salvataggio rifiutato accende i campi della collezione
//   2) un salvataggio riuscito li spegne, e chiude il form
//   3) il rifiuto del toggle di una riga non accende i campi del form
//   4) riaprire il form, o aprirne un'altra riga, li spegne
// ------------------------------------------------------------

import { describe, expect, it, vi } from 'vitest'
import { nextTick, ref } from 'vue'

// Ogni istanza finta: `execute` rifiutato riempie i SUOI campi, come il vero.
const istanze = []
vi.mock('../../core/composables/useApiHandler', () => ({
  useApiHandler: () => {
    const campiErrati = ref([])
    const execute = vi.fn(async (fn) => {
      campiErrati.value = []
      try {
        return await fn()
      } catch (err) {
        campiErrati.value = err.campi ?? []
        return null
      }
    })
    const istanza = { execute, campiErrati, loading: ref(false) }
    istanze.push(istanza)
    return istanza
  },
}))
vi.mock('../../core/composables/useConfirmAction', () => ({ useConfirmAction: () => ({ confirmAction: vi.fn() }) }))
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: (chiave) => chiave }) }))

const { useEditableCollection } = await import('./useEditableCollection')

function collezione({ create }) {
  return useEditableCollection({
    create,
    update: vi.fn(),
    del: vi.fn(),
    messages: { created: 'c', saved: 's', deleted: 'd' },
    confirmDelete: () => 'x',
    onChanged: vi.fn(),
  })
}

describe('useEditableCollection — campi in errore', () => {
  it('1) un salvataggio rifiutato accende i campi della collezione', async () => {
    const rifiuto = Object.assign(new Error('409'), { campi: ['esito_richiesto'] })
    const prima = istanze.length
    const coll = collezione({ create: () => Promise.reject(rifiuto) })
    coll.nuovaRiga()

    await coll.save({ esito_richiesto: 'OK' })

    expect(coll.campiErrati.value).toEqual(['esito_richiesto'])
    // L'istanza che ha chiamato l'API è quella creata dalla collezione.
    expect(istanze[prima].execute).toHaveBeenCalledTimes(1)
    expect(istanze[prima].campiErrati).toBe(coll.campiErrati)
    expect(coll.formMode.value).toBe('create')
  })

  it('2) un salvataggio riuscito li spegne, e chiude il form', async () => {
    let rifiuta = true
    const coll = collezione({
      create: () => (rifiuta
        ? Promise.reject(Object.assign(new Error('409'), { campi: ['attivo'] }))
        : Promise.resolve({ data: { id: 1 } })),
    })
    coll.nuovaRiga()
    await coll.save({})
    expect(coll.campiErrati.value).toEqual(['attivo'])

    rifiuta = false
    await coll.save({})

    expect(coll.campiErrati.value).toEqual([])
    expect(coll.formMode.value).not.toBe('create')
  })

  it('3) il rifiuto del toggle di una riga non accende i campi del form', async () => {
    const coll = useEditableCollection({
      create: vi.fn(),
      update: () => Promise.reject(Object.assign(new Error('409'), { campi: ['esito_richiesto'] })),
      del: vi.fn(),
      messages: { created: 'c', saved: 's', deleted: 'd' },
      confirmDelete: () => 'x',
      onChanged: vi.fn(),
    })
    coll.apriRiga({ id: 2, attivo: true })

    await coll.toggleAttivo({ id: 7, attivo: false })

    expect(coll.campiErrati.value).toEqual([])
  })

  it("4) riaprire il form, o aprirne un'altra riga, li spegne", async () => {
    const coll = collezione({
      create: () => Promise.reject(Object.assign(new Error('409'), { campi: ['esito_richiesto'] })),
    })
    coll.nuovaRiga()
    await coll.save({})
    expect(coll.campiErrati.value).toEqual(['esito_richiesto'])

    coll.chiudiForm()
    await nextTick()
    expect(coll.campiErrati.value).toEqual([])

    coll.nuovaRiga()
    await coll.save({})
    coll.apriRiga({ id: 3 })
    await nextTick()
    expect(coll.campiErrati.value).toEqual([])
  })
})
