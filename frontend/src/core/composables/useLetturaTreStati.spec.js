// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il contratto di `useLetturaTreStati` — i TRE stati, e il guard
//        di versione entrato il 2026-09-14: due letture in volo sullo stesso
//        lettore che tornano in ordine inverso non devono lasciare a video la
//        risposta STANTIA. E' il difetto che nessun test a mano vede, perche'
//        chiede due risposte che si scavalcano: qui le si costruisce.
// Note: `useApiHandler` e' mockato: qui si prova il lettore, non l'envelope
//        (quello ha il suo spec).
// ------------------------------------------------------------

import { describe, it, expect, vi } from 'vitest'

// Un `execute` fedele nel solo contratto che serve: risponde il payload sulla
// promessa risolta, `null` su quella rifiutata.
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

const { RISULTATI, useLetturaTreStati } = await import('./useLetturaTreStati')

// Una promessa che si risolve quando lo decide il test.
function differita() {
  let risolvi
  let rifiuta
  const promessa = new Promise((ok, ko) => { risolvi = ok; rifiuta = ko })
  return { promessa, risolvi, rifiuta }
}

describe('useLetturaTreStati — i tre stati', () => {
  it('parte «non letto», e un elenco vuoto letto è «vuoto», non «non letto»', async () => {
    const { dati, caricati, errore, carica } =
      useLetturaTreStati(async () => ({ results: [] }), { estrai: RISULTATI, vuoto: [] })
    expect(caricati.value).toBe(false)
    expect(dati.value).toEqual([])

    await carica(1)
    expect(caricati.value).toBe(true)
    expect(errore.value).toBe(false)
    expect(dati.value).toEqual([])
  })

  it('una lettura fallita è «tentata e fallita», e non si spaccia per vuota', async () => {
    const { caricati, errore, dati, carica } =
      useLetturaTreStati(async () => { throw new Error('rete') }, { vuoto: [] })
    const esito = await carica(1)
    expect(esito).toEqual([])
    expect(caricati.value).toBe(true)
    expect(errore.value).toBe(true)
    expect(dati.value).toEqual([])
  })

  it('`azzera` riporta a «non letto»', async () => {
    const { caricati, dati, carica, azzera } =
      useLetturaTreStati(async () => ({ results: [1] }), { estrai: RISULTATI, vuoto: [] })
    await carica(1)
    expect(dati.value).toEqual([1])
    azzera()
    expect(caricati.value).toBe(false)
    expect(dati.value).toEqual([])
  })
})

describe('useLetturaTreStati — guard di versione', () => {
  it('la risposta STANTIA che arriva dopo non sovrascrive quella corrente', async () => {
    const prima = differita()
    const seconda = differita()
    const risposte = [prima.promessa, seconda.promessa]
    const { dati, caricati, carica } =
      useLetturaTreStati(() => risposte.shift(), { estrai: RISULTATI, vuoto: [] })

    const c1 = carica('A')
    const c2 = carica('B')
    // B torna prima di A: e' la lettura corrente, e si scrive.
    seconda.risolvi({ results: ['rate di B'] })
    await expect(c2).resolves.toEqual(['rate di B'])
    expect(dati.value).toEqual(['rate di B'])

    // A torna dopo: e' stantia, torna `null` e non tocca niente.
    prima.risolvi({ results: ['rate di A'] })
    await expect(c1).resolves.toBeNull()
    expect(dati.value).toEqual(['rate di B'])
    expect(caricati.value).toBe(true)
  })

  it('`azzera` invalida una lettura in volo: la risposta non ripopola il reset', async () => {
    const unica = differita()
    const { dati, caricati, carica, azzera } =
      useLetturaTreStati(() => unica.promessa, { estrai: RISULTATI, vuoto: [] })

    const c = carica('A')
    azzera()
    unica.risolvi({ results: ['rate di A'] })
    await expect(c).resolves.toBeNull()
    expect(dati.value).toEqual([])
    expect(caricati.value).toBe(false)
  })

  it('un errore stantio non marca come fallita la lettura corrente', async () => {
    const prima = differita()
    const seconda = differita()
    const risposte = [prima.promessa, seconda.promessa]
    const { errore, dati, carica } =
      useLetturaTreStati(() => risposte.shift(), { estrai: RISULTATI, vuoto: [] })

    const c1 = carica('A')
    const c2 = carica('B')
    seconda.risolvi({ results: ['rate di B'] })
    await c2
    prima.rifiuta(new Error('rete'))
    await expect(c1).resolves.toBeNull()
    expect(errore.value).toBe(false)
    expect(dati.value).toEqual(['rate di B'])
  })
})
