// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Test dell'interceptor di risposta di `core/api` sui 403 del cancello
//        degli obblighi del backend: un obbligo nato a sessione aperta
//        (l'amministratore accende il secondo fattore, un reparto lo
//        richiede) rilegge il profilo e rifà la navigazione, perché il guard
//        porti alla pagina che lo chiude. Prima ogni chiamata rispondeva 403
//        finché non si ricaricava.
// Note: il router e lo store `auth` sono finti; l'interceptor è quello vero,
//       chiamato come lo chiama axios.
// ------------------------------------------------------------

/*
Indice test eseguiti:
1) 403 E_TOTP_CONFIGURAZIONE_RICHIESTA → profilo riletto, stessa rotta rinavigata con force
2) più 403 insieme → una sola rilettura e una sola navigazione
3) 403 sulla pagina che chiude l'obbligo → nessuna navigazione
4) 403 d'altro tipo → nessuna rilettura
*/

import { beforeEach, describe, expect, it, vi } from 'vitest'

const fetchProfile = vi.fn()
const push = vi.fn()
const rottaCorrente = { value: { name: 'clienti', fullPath: '/clienti?q=1' } }

vi.mock('./routerApp', () => ({
  routerApp: () => ({ currentRoute: rottaCorrente, push })
}))
vi.mock('../stores/auth', () => ({
  useAuthStore: () => ({ fetchProfile })
}))

const { default: api } = await import('./api')

// L'handler di errore dell'interceptor di risposta, come lo chiama axios.
const suErrore = api.interceptors.response.handlers[0].rejected

function errore403(code) {
  return { config: { url: '/vendite/clienti/' }, response: { status: 403, data: { error: { code } } } }
}

describe('core/api — 403 del cancello degli obblighi', () => {
  beforeEach(() => {
    fetchProfile.mockReset().mockResolvedValue(undefined)
    push.mockReset().mockResolvedValue(undefined)
    rottaCorrente.value = { name: 'clienti', fullPath: '/clienti?q=1' }
  })

  it('rilegge il profilo e rinaviga la rotta corrente', async () => {
    const err = errore403('E_TOTP_CONFIGURAZIONE_RICHIESTA')
    await expect(suErrore(err)).rejects.toBe(err)
    expect(fetchProfile).toHaveBeenCalledTimes(1)
    expect(push).toHaveBeenCalledWith({ path: '/clienti?q=1', force: true })
  })

  it('con più 403 insieme rilegge e naviga una volta sola', async () => {
    await Promise.allSettled([
      suErrore(errore403('E_TOTP_CONFIGURAZIONE_RICHIESTA')),
      suErrore(errore403('E_CAMBIO_PASSWORD_RICHIESTO'))
    ])
    expect(fetchProfile).toHaveBeenCalledTimes(1)
    expect(push).toHaveBeenCalledTimes(1)
  })

  it('sulla pagina che chiude l\'obbligo non naviga', async () => {
    rottaCorrente.value = { name: 'sicurezza', fullPath: '/sicurezza' }
    await expect(suErrore(errore403('E_TOTP_CONFIGURAZIONE_RICHIESTA'))).rejects.toBeTruthy()
    expect(fetchProfile).not.toHaveBeenCalled()
    expect(push).not.toHaveBeenCalled()
  })

  it('un 403 d\'altro tipo non rilegge il profilo', async () => {
    await expect(suErrore(errore403('E_PERMESSO_NEGATO'))).rejects.toBeTruthy()
    expect(fetchProfile).not.toHaveBeenCalled()
    expect(push).not.toHaveBeenCalled()
  })
})
