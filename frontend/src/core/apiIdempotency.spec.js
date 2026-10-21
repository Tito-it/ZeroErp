// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Presidio di `applicaIdempotencyKey`, il BB che mette
//        l'`Idempotency-Key` su ogni chiamata che scrive (decisione di Tid del
//        2026-10-20, brief-be-verifica-documentazione-api §A5). Il backend la
//        pretende su ogni POST che scrive: una chiamata che la dimentica e' un
//        400. Fino a quel giorno la generava ogni funzione API a mano, in 69
//        punti, e solo dove l'endpoint la chiedeva.
// ------------------------------------------------------------

/*
Indice test eseguiti:
1) POST/PUT/PATCH/DELETE ricevono una key
2) GET non la riceve
3) una key gia' presente vince (headers oggetto e AxiosHeaders)
4) due chiamate, due key
5) l'interceptor e' collegato all'istanza: la POST arriva all'adapter con la key
6) il rinnovo dopo un 401 rimanda la STESSA key
*/

import { AxiosHeaders } from 'axios'
import { describe, expect, it, vi } from 'vitest'

vi.mock('./routerApp', () => ({ routerApp: { currentRoute: { value: {} }, push: vi.fn() } }))

const { default: api, applicaIdempotencyKey } = await import('./api')

const chiave = (config) =>
  typeof config.headers.get === 'function'
    ? config.headers.get('Idempotency-Key')
    : config.headers['Idempotency-Key']

describe('applicaIdempotencyKey', () => {
  it('mette la key sui quattro metodi che scrivono', () => {
    for (const method of ['post', 'put', 'patch', 'delete', 'POST']) {
      const config = applicaIdempotencyKey({ method, headers: {} })
      expect(chiave(config), method).toBeTruthy()
    }
  })

  it('non la mette su una GET', () => {
    const config = applicaIdempotencyKey({ method: 'get', headers: {} })
    expect(chiave(config)).toBeUndefined()
  })

  it('una key gia\' presente vince', () => {
    const oggetto = applicaIdempotencyKey({ method: 'post', headers: { 'idempotency-key': 'mia' } })
    expect(oggetto.headers['Idempotency-Key']).toBeUndefined()
    expect(oggetto.headers['idempotency-key']).toBe('mia')
    const axiosHeaders = new AxiosHeaders({ 'Idempotency-Key': 'mia' })
    expect(chiave(applicaIdempotencyKey({ method: 'post', headers: axiosHeaders }))).toBe('mia')
  })

  it('due chiamate, due key', () => {
    const a = chiave(applicaIdempotencyKey({ method: 'post', headers: {} }))
    const b = chiave(applicaIdempotencyKey({ method: 'post', headers: {} }))
    expect(a).not.toBe(b)
  })
})

describe('interceptor dell\'istanza condivisa', () => {
  const chiaveInviata = (config) => AxiosHeaders.from(config.headers).get('Idempotency-Key')

  it('una POST arriva all\'adapter con la key', async () => {
    const adapter = vi.fn(async (config) => ({ data: {}, status: 200, statusText: 'OK', headers: {}, config }))
    await api.post('/x/', {}, { adapter })
    expect(chiaveInviata(adapter.mock.calls[0][0])).toBeTruthy()
  })

  it('il rinnovo dopo un 401 rimanda la stessa key', async () => {
    const chiamate = []
    const adapter = vi.fn(async (config) => {
      chiamate.push(config)
      if (config.url.includes('/token/')) {
        return { data: { access: 'nuovo' }, status: 200, statusText: 'OK', headers: {}, config }
      }
      if (chiamate.filter((c) => c.url === '/x/').length === 1) {
        const error = new Error('401')
        error.config = config
        error.response = { status: 401, data: {}, headers: {}, config }
        throw error
      }
      return { data: {}, status: 200, statusText: 'OK', headers: {}, config }
    })
    api.defaults.adapter = adapter
    try {
      await api.post('/x/', {})
    } finally {
      delete api.defaults.adapter
    }
    const scritture = chiamate.filter((c) => c.url === '/x/')
    expect(scritture).toHaveLength(2)
    expect(chiaveInviata(scritture[0])).toBe(chiaveInviata(scritture[1]))
  })
})
