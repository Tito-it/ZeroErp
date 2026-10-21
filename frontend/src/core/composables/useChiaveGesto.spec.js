// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Presidio di `useChiaveGesto`, la key di idempotenza di un GESTO:
//        riusata nei reinvii con lo stesso payload, azzerata a successo, a
//        payload cambiato, su `azzera()` e oltre la durata. E la prova che la
//        key arriva all'adapter axios e che l'interceptor non la sostituisce.
// ------------------------------------------------------------

/*
Indice test eseguiti:
1) improntaStabile: l'ordine delle chiavi non conta, quello degli array si'
2) due reinvii falliti con lo stesso payload: la stessa key
3) successo: la key si azzera, il gesto dopo ne ha una nuova
4) payload cambiato: key nuova
5) azzera(): key nuova
6) oltre la durata: key nuova
7) l'errore risale invariato al chiamante
8) la key del gesto arriva all'adapter (l'interceptor non la sovrascrive)
*/

import { AxiosHeaders } from 'axios'
import { describe, expect, it, vi } from 'vitest'

vi.mock('../routerApp', () => ({ routerApp: { currentRoute: { value: {} }, push: vi.fn() } }))

const { useChiaveGesto, improntaStabile, HEADER_IDEMPOTENCY_KEY } = await import('./useChiaveGesto')
const { default: api } = await import('../api')

const keyDi = (config) => config.headers[HEADER_IDEMPOTENCY_KEY]

// Una chiamata che fallisce come un timeout di axios e registra la config.
function chiamataCheFallisce(registro) {
  return (config) => {
    registro.push(keyDi(config))
    return Promise.reject(Object.assign(new Error('timeout of 10000ms exceeded'), { code: 'ECONNABORTED' }))
  }
}

describe('improntaStabile', () => {
  it('l’ordine delle chiavi non conta, quello degli array si', () => {
    expect(improntaStabile({ a: 1, b: { c: 2, d: 3 } })).toBe(improntaStabile({ b: { d: 3, c: 2 }, a: 1 }))
    expect(improntaStabile({ x: [1, 2] })).not.toBe(improntaStabile({ x: [2, 1] }))
    expect(improntaStabile({ a: 1, b: undefined })).toBe(improntaStabile({ a: 1 }))
  })
})

describe('useChiaveGesto', () => {
  it('⭐ due reinvii falliti con lo stesso payload portano la STESSA key', async () => {
    const gesto = useChiaveGesto()
    const keys = []
    await expect(gesto.invia({ id: 1, data: '2026-10-21' }, chiamataCheFallisce(keys))).rejects.toThrow()
    await expect(gesto.invia({ data: '2026-10-21', id: 1 }, chiamataCheFallisce(keys))).rejects.toThrow()
    expect(keys[0]).toBeTruthy()
    expect(keys[1]).toBe(keys[0])
  })

  it('a successo la key si azzera: il gesto dopo ne ha una nuova', async () => {
    const gesto = useChiaveGesto()
    const keys = []
    await expect(gesto.invia({ id: 1 }, chiamataCheFallisce(keys))).rejects.toThrow()
    const risposta = { data: { data: { ok: true } } }
    const out = await gesto.invia({ id: 1 }, (config) => {
      keys.push(keyDi(config))
      return Promise.resolve(risposta)
    })
    expect(out).toBe(risposta)
    expect(keys[1]).toBe(keys[0])
    await expect(gesto.invia({ id: 1 }, chiamataCheFallisce(keys))).rejects.toThrow()
    expect(keys[2]).not.toBe(keys[0])
  })

  it('un payload diverso è un’operazione diversa: key nuova', async () => {
    const gesto = useChiaveGesto()
    const keys = []
    await expect(gesto.invia({ id: 1, data: '2026-10-21' }, chiamataCheFallisce(keys))).rejects.toThrow()
    await expect(gesto.invia({ id: 1, data: '2026-10-22' }, chiamataCheFallisce(keys))).rejects.toThrow()
    expect(keys[1]).not.toBe(keys[0])
  })

  it('azzera() chiude il gesto: key nuova', async () => {
    const gesto = useChiaveGesto()
    const keys = []
    await expect(gesto.invia({ id: 1 }, chiamataCheFallisce(keys))).rejects.toThrow()
    gesto.azzera()
    await expect(gesto.invia({ id: 1 }, chiamataCheFallisce(keys))).rejects.toThrow()
    expect(keys[1]).not.toBe(keys[0])
  })

  it('oltre la durata un nuovo clic è un gesto nuovo', () => {
    let adesso = 0
    const gesto = useChiaveGesto({ durataMs: 1000, ora: () => adesso })
    const a = keyDi(gesto.configDi({ id: 1 }))
    adesso = 999
    expect(keyDi(gesto.configDi({ id: 1 }))).toBe(a)
    adesso = 2001
    expect(keyDi(gesto.configDi({ id: 1 }))).not.toBe(a)
  })

  it('l’errore risale invariato: lo gestisce chi chiama (useApiHandler)', async () => {
    const gesto = useChiaveGesto()
    const errore = { response: { status: 409, data: { error: { code: 'E_IDEMPOTENCY_IN_PROGRESS' } } } }
    await expect(gesto.invia({ id: 1 }, () => Promise.reject(errore))).rejects.toBe(errore)
  })

  it('⭐ la key del gesto arriva all’adapter: l’interceptor non la sostituisce', async () => {
    const gesto = useChiaveGesto()
    const viste = []
    const adapter = vi.fn(async (config) => {
      viste.push(AxiosHeaders.from(config.headers).get('Idempotency-Key'))
      if (viste.length === 1) {
        throw Object.assign(new Error('timeout'), { code: 'ECONNABORTED', config })
      }
      return { data: { data: {} }, status: 200, statusText: 'OK', headers: {}, config }
    })
    const invio = () => gesto.invia({ id: 7 }, (config) => api.post('/x/7/registra/', {}, { ...config, adapter }))
    await expect(invio()).rejects.toThrow()
    await invio()
    expect(viste[0]).toBeTruthy()
    expect(viste[1]).toBe(viste[0])
  })
})
