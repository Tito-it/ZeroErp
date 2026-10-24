// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il contratto di `useLetturaDocumento` — QUANDO si legge. Il
//        difetto da cui nasce (passaggi stantii dopo l'annullo di una
//        commessa, 2026-10-13) non da' errore: la barra mostra un dato
//        vecchio. Qui si costruiscono i casi: rilettura del drawer ospite,
//        cambio documento con la versione vecchia ancora in mano, risposte
//        che si scavalcano.
// Note: `useApiHandler` e' mockato: qui si prova la regola, non l'envelope.
// ------------------------------------------------------------

import { describe, it, expect, vi } from 'vitest'
import { nextTick, ref } from 'vue'

vi.mock('./useApiHandler', () => ({
  useApiHandler: () => ({
    execute: async (chiamata) => {
      try {
        return await chiamata()
      } catch {
        return null
      }
    },
    loading: { value: false },
  }),
}))

const { useLetturaDocumento } = await import('./useLetturaDocumento')

// Una promessa che si risolve quando lo decide il test.
function differita() {
  let risolvi
  const promessa = new Promise((ok) => { risolvi = ok })
  return { promessa, risolvi }
}

// Svuota la coda: watcher (flush pre) + promesse del fetcher.
async function assesta() {
  await nextTick()
  await new Promise((r) => setTimeout(r, 0))
}

describe('useLetturaDocumento — agganciata alla versione del drawer ospite', () => {
  it('all\'apertura legge UNA volta, quando arriva il dettaglio — non prima', async () => {
    const fetcher = vi.fn(async (id) => ({ id }))
    const docId = ref(7)
    const versione = ref(null)
    const { dati, caricati } = useLetturaDocumento(fetcher, { docId, versione })
    await assesta()
    expect(fetcher).not.toHaveBeenCalled()
    expect(caricati.value).toBe(false)

    versione.value = { id: 7 }
    await assesta()
    expect(fetcher).toHaveBeenCalledTimes(1)
    expect(dati.value).toEqual({ id: 7 })
  })

  it('ogni rilettura del drawer (oggetto nuovo) rilegge, SENZA azzerare nel frattempo', async () => {
    const giri = [differita(), differita()]
    let n = 0
    const fetcher = vi.fn(() => giri[n++].promessa)
    const docId = ref(7)
    const versione = ref({ stato: 'EVASO' })
    const { dati, caricati } = useLetturaDocumento(fetcher, { docId, versione })
    giri[0].risolvi({ preventivo: 'EVASO' })
    await assesta()
    expect(dati.value).toEqual({ preventivo: 'EVASO' })

    // L'annullo della commessa: il drawer rilegge, il dettaglio e' un oggetto nuovo.
    versione.value = { stato: 'ANNULLATA' }
    await assesta()
    expect(fetcher).toHaveBeenCalledTimes(2)
    // In volo: il dato vecchio resta a video, la riga in testata non sparisce.
    expect(caricati.value).toBe(true)
    expect(dati.value).toEqual({ preventivo: 'EVASO' })

    giri[1].risolvi({ preventivo: 'ACCETTATO' })
    await assesta()
    expect(dati.value).toEqual({ preventivo: 'ACCETTATO' })
  })

  it('cambio documento: azzera e aspetta il dettaglio NUOVO, non legge con la versione vecchia', async () => {
    const fetcher = vi.fn(async (id) => ({ id }))
    const docId = ref(7)
    const versione = ref({ id: 7 })
    const { dati, caricati } = useLetturaDocumento(fetcher, { docId, versione })
    await assesta()
    expect(fetcher).toHaveBeenCalledTimes(1)

    docId.value = 8
    await assesta()
    expect(dati.value).toBeNull()
    expect(caricati.value).toBe(false)
    expect(fetcher).toHaveBeenCalledTimes(1)

    versione.value = { id: 8 }
    await assesta()
    expect(fetcher).toHaveBeenCalledTimes(2)
    expect(fetcher).toHaveBeenLastCalledWith(8)
    expect(dati.value).toEqual({ id: 8 })
  })

  it('una risposta del documento di PRIMA, arrivata dopo il cambio, si scarta', async () => {
    const lenta = differita()
    const fetcher = vi.fn((id) => (id === 7 ? lenta.promessa : Promise.resolve({ id })))
    const docId = ref(7)
    const versione = ref({ id: 7 })
    const { dati } = useLetturaDocumento(fetcher, { docId, versione })
    await assesta()

    docId.value = 8
    versione.value = { id: 8 }
    await assesta()
    expect(dati.value).toEqual({ id: 8 })

    lenta.risolvi({ id: 7 })
    await assesta()
    expect(dati.value).toEqual({ id: 8 })
  })

  it('senza id (CREATE) non legge, anche se la versione cambia', async () => {
    const fetcher = vi.fn(async () => ({}))
    const versione = ref(null)
    useLetturaDocumento(fetcher, { docId: ref(null), versione })
    versione.value = { bozza: true }
    await assesta()
    expect(fetcher).not.toHaveBeenCalled()
  })

  it('CREATE: il dettaglio della bozza arriva PRIMA dell\'id — si legge all\'arrivo dell\'id', async () => {
    const fetcher = vi.fn(async (id) => ({ id }))
    const docId = ref(null)
    const versione = ref(null)
    const { dati } = useLetturaDocumento(fetcher, { docId, versione })
    versione.value = { id: 9 }
    await assesta()
    expect(fetcher).not.toHaveBeenCalled()

    docId.value = 9
    await assesta()
    expect(fetcher).toHaveBeenCalledTimes(1)
    expect(dati.value).toEqual({ id: 9 })
  })

  it('stesso documento riaperto con lo stesso dettaglio in mano: si rilegge', async () => {
    const fetcher = vi.fn(async (id) => ({ id }))
    const docId = ref(7)
    const versione = ref({ id: 7 })
    const { dati } = useLetturaDocumento(fetcher, { docId, versione })
    await assesta()
    docId.value = null
    await assesta()
    docId.value = 7
    await assesta()
    expect(fetcher).toHaveBeenCalledTimes(2)
    expect(dati.value).toEqual({ id: 7 })
  })

  it('una rilettura fallita lascia il dato precedente; una prima lettura fallita resta «non letto»', async () => {
    let fallisci = true
    const fetcher = vi.fn(async (id) => {
      if (fallisci) throw new Error('rete')
      return { id }
    })
    const versione = ref({ v: 1 })
    const { dati, caricati } = useLetturaDocumento(fetcher, { docId: ref(7), versione })
    await assesta()
    expect(caricati.value).toBe(false)

    fallisci = false
    versione.value = { v: 2 }
    await assesta()
    expect(dati.value).toEqual({ id: 7 })

    fallisci = true
    versione.value = { v: 3 }
    await assesta()
    expect(caricati.value).toBe(true)
    expect(dati.value).toEqual({ id: 7 })
  })
})

describe('useLetturaDocumento — senza versione (la lettura E\' il dettaglio)', () => {
  it('legge al montaggio e a ogni cambio di documento', async () => {
    const fetcher = vi.fn(async (id) => ({ id }))
    const docId = ref(3)
    const { dati } = useLetturaDocumento(fetcher, { docId })
    await assesta()
    expect(dati.value).toEqual({ id: 3 })

    docId.value = 4
    await assesta()
    expect(fetcher).toHaveBeenCalledTimes(2)
    expect(dati.value).toEqual({ id: 4 })
  })
})
