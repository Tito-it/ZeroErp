// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Test di `core/sessione.js` — l'access in memoria e il rinnovo
//        coordinato fra le schede (brief sicurezza §2, decisione A).
// Note: il modulo ha stato di modulo (token, rinnovo in volo, canale): ogni
//       test lo reimporta pulito. `BroadcastChannel` e `navigator.locks` sono
//       finti, così si prova il coordinamento senza un browser.
// ------------------------------------------------------------

/*
Indice test eseguiti:
1) chiamate concorrenti della stessa scheda → un solo rinnovo, stesso access
2) un'altra scheda ha già portato un access valido → nessun rinnovo
3) rinnovo fallito → la promise rifiuta e il giro dopo riprova
4) il rinnovo gira dentro il lock del browser, quando c'è
5) l'access nuovo si annuncia alle altre schede; `annuncia: false` no
6) un access annunciato da un'altra scheda arriva in memoria
7) LOGOUT e SESSIONE_NUOVA di un'altra scheda arrivano agli iscritti
8) accessValido: assente, scaduto e valido
9) rinnovo che risponde senza access → rifiuta, niente `Bearer undefined`
10) ogni motivo di uscita ha la sua frase, in italiano e in inglese
11) sessioneDichiarataChiusa: vero per ogni motivo noto, falso per gli altri
*/

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import it_ from '../locales/it.json'
import en from '../locales/en.json'

// Un JWT con la sola `exp` che serve a `isJwtExpired` (firma non verificata).
function jwt(secondiDaOra) {
  const payload = { exp: Math.floor(Date.now() / 1000) + secondiDaOra }
  const b64 = btoa(JSON.stringify(payload)).replace(/=+$/, '')
  return `h.${b64}.s`
}

// BroadcastChannel finto: i canali con lo stesso nome si parlano, ma non con
// se stessi (come nel browser).
class CanaleFinto {
  static istanze = []
  constructor(nome) {
    this.nome = nome
    this.onmessage = null
    this.inviati = []
    CanaleFinto.istanze.push(this)
  }
  postMessage(data) {
    this.inviati.push(data)
  }
  // Consegna un messaggio come se arrivasse da un'altra scheda.
  ricevi(data) {
    this.onmessage?.({ data })
  }
}

let sessione

beforeEach(async () => {
  CanaleFinto.istanze = []
  vi.stubGlobal('BroadcastChannel', CanaleFinto)
  vi.resetModules()
  sessione = await import('./sessione')
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('rinnovaCoordinato', () => {
  it('1) chiamate concorrenti → un solo rinnovo, stesso access', async () => {
    const nuovo = jwt(600)
    const rinnova = vi.fn(async () => nuovo)
    const [a, b, c] = await Promise.all([
      sessione.rinnovaCoordinato(rinnova),
      sessione.rinnovaCoordinato(rinnova),
      sessione.rinnovaCoordinato(rinnova)
    ])
    expect(rinnova).toHaveBeenCalledTimes(1)
    expect([a, b, c]).toEqual([nuovo, nuovo, nuovo])
    expect(sessione.getAccessToken()).toBe(nuovo)
  })

  it('2) un\'altra scheda ha già portato un access valido → nessun rinnovo', async () => {
    const vecchio = jwt(-60)
    sessione.impostaAccess(vecchio, { annuncia: false })
    const portatoDaAltraScheda = jwt(600)
    // Il lock arriva DOPO che il messaggio dell'altra scheda è stato consegnato.
    vi.stubGlobal('navigator', {
      locks: {
        request: async (_nome, fn) => {
          sessione.accessTokenRef().value = portatoDaAltraScheda
          return fn()
        }
      }
    })
    const rinnova = vi.fn(async () => jwt(600))
    const esito = await sessione.rinnovaCoordinato(rinnova)
    expect(rinnova).not.toHaveBeenCalled()
    expect(esito).toBe(portatoDaAltraScheda)
  })

  it('3) rinnovo fallito → rifiuta, e il giro dopo riprova', async () => {
    const rinnova = vi.fn()
      .mockRejectedValueOnce(new Error('401'))
      .mockResolvedValueOnce(jwt(600))
    await expect(sessione.rinnovaCoordinato(rinnova)).rejects.toThrow('401')
    await expect(sessione.rinnovaCoordinato(rinnova)).resolves.toBeTruthy()
    expect(rinnova).toHaveBeenCalledTimes(2)
  })

  it('4) il rinnovo gira dentro il lock del browser, quando c\'è', async () => {
    const request = vi.fn(async (_nome, fn) => fn())
    vi.stubGlobal('navigator', { locks: { request } })
    await sessione.rinnovaCoordinato(async () => jwt(600))
    expect(request).toHaveBeenCalledTimes(1)
    expect(request.mock.calls[0][0]).toBe('zeroerp-rinnovo-sessione')
  })

  it('9) rinnovo senza access → rifiuta e non tocca la memoria', async () => {
    const vecchio = jwt(-60)
    sessione.impostaAccess(vecchio, { annuncia: false })
    await expect(sessione.rinnovaCoordinato(async () => undefined)).rejects.toThrow()
    expect(sessione.getAccessToken()).toBe(vecchio)
  })
})

describe('schede', () => {
  it('5) l\'access nuovo si annuncia; annuncia:false no', () => {
    const token = jwt(600)
    sessione.impostaAccess(token)
    const canale = CanaleFinto.istanze[0]
    expect(canale.inviati).toEqual([{ tipo: sessione.EVENTO_SESSIONE.ACCESS, token }])
    sessione.impostaAccess(jwt(600), { annuncia: false })
    expect(canale.inviati).toHaveLength(1)
  })

  it('6) un access annunciato da un\'altra scheda arriva in memoria', () => {
    sessione.suEventoAltraScheda(() => {})
    const token = jwt(600)
    CanaleFinto.istanze[0].ricevi({ tipo: sessione.EVENTO_SESSIONE.ACCESS, token })
    expect(sessione.getAccessToken()).toBe(token)
  })

  it('7) LOGOUT e SESSIONE_NUOVA arrivano agli iscritti', () => {
    const iscritto = vi.fn()
    sessione.suEventoAltraScheda(iscritto)
    const canale = CanaleFinto.istanze[0]
    canale.ricevi({ tipo: sessione.EVENTO_SESSIONE.LOGOUT })
    canale.ricevi({ tipo: sessione.EVENTO_SESSIONE.SESSIONE_NUOVA })
    expect(iscritto.mock.calls.map(([e]) => e.tipo)).toEqual([
      sessione.EVENTO_SESSIONE.LOGOUT,
      sessione.EVENTO_SESSIONE.SESSIONE_NUOVA
    ])
  })
})

describe('accessValido', () => {
  it('8) assente, scaduto e valido', () => {
    expect(sessione.accessValido()).toBe(false)
    sessione.impostaAccess(jwt(-60), { annuncia: false })
    expect(sessione.accessValido()).toBe(false)
    sessione.impostaAccess(jwt(600), { annuncia: false })
    expect(sessione.accessValido()).toBe(true)
  })
})

// Una chiave `a.b` nel file di traduzioni.
function frase(traduzioni, chiave) {
  return chiave.split('.').reduce((nodo, parte) => nodo?.[parte], traduzioni)
}

describe('motivi di uscita', () => {
  it('10) ogni motivo di uscita ha la sua frase, in italiano e in inglese', () => {
    const motivi = Object.values(sessione.MOTIVO_USCITA)
    expect(motivi.length).toBeGreaterThan(1)
    for (const motivo of motivi) {
      const chiave = sessione.FRASE_MOTIVO_USCITA[motivo]
      expect(chiave, motivo).toBeTruthy()
      expect(frase(it_, chiave), `it: ${chiave}`).toEqual(expect.any(String))
      expect(frase(en, chiave), `en: ${chiave}`).toEqual(expect.any(String))
    }
    // Due motivi diversi, due frasi diverse: è il senso del motivo nuovo.
    const frasi = motivi.map(m => frase(it_, sessione.FRASE_MOTIVO_USCITA[m]))
    expect(new Set(frasi).size).toBe(motivi.length)
  })

  it('11) sessioneDichiarataChiusa: vero per ogni motivo noto, falso per gli altri', () => {
    for (const motivo of Object.values(sessione.MOTIVO_USCITA)) {
      expect(sessione.sessioneDichiarataChiusa(motivo), motivo).toBe(true)
    }
    expect(sessione.sessioneDichiarataChiusa(undefined)).toBe(false)
    expect(sessione.sessioneDichiarataChiusa('qualunque')).toBe(false)
  })
})
