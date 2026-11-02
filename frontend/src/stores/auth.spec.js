// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Test dello store `auth` sugli eventi delle altre schede (brief
//        sicurezza §2): un logout fatto altrove porta questa scheda al login
//        col SUO motivo, non con «sessione scaduta» (rilievo di Tid,
//        2026-09-29).
// Note: `core/api` è finto (niente axios, niente router); `core/sessione` è
//       quello vero tranne l'iscrizione agli eventi, catturata per poterla
//       chiamare come farebbe il BroadcastChannel.
// ------------------------------------------------------------

/*
Indice test eseguiti:
1) LOGOUT da un'altra scheda → login col motivo USCITA_ALTRA_SCHEDA
2) login col secondo fattore attivo → sfida, nessun access, nessun profilo
3) secondo passo → access in memoria, profilo, codici di recupero rimasti
4) secondo passo senza codice di recupero → rimasti null
5) obbligo del secondo fattore → dal profilo (`obblighi_pendenti`), non ricalcolato
6) la chiave d'ingresso è del canale: email per PORTALE e SHOP, nome utente per ADMIN (L-4)
7) il profilo consegna il fuso dell'azienda a `core/utils/date` (F-1)
*/

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const redirectToLogin = vi.fn()
const apiPost = vi.fn()
const apiGet = vi.fn()
vi.mock('../core/api', () => ({
  default: { post: (...a) => apiPost(...a), get: (...a) => apiGet(...a) },
  rinnovaAccess: vi.fn()
}))
vi.mock('../core/uscitaSessione', () => ({
  redirectToLogin: (...args) => redirectToLogin(...args),
}))

let suEvento = null
vi.mock('../core/sessione', async importOriginal => ({
  ...(await importOriginal()),
  suEventoAltraScheda: fn => {
    suEvento = fn
    return () => {}
  }
}))

const { useAuthStore } = await import('./auth')
const { EVENTO_SESSIONE, MOTIVO_USCITA, getAccessToken, azzeraAccess } = await import('../core/sessione')

// Un access dall'aspetto di un JWT, non scaduto (exp fra un'ora).
function accessFinto() {
  const corpo = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 }))
  return `x.${corpo}.y`
}

beforeEach(() => {
  setActivePinia(createPinia())
  redirectToLogin.mockClear()
  apiPost.mockReset()
  apiGet.mockReset()
  azzeraAccess()
  suEvento = null
})

describe('eventi delle altre schede', () => {
  it("1) LOGOUT da un'altra scheda → login col motivo USCITA_ALTRA_SCHEDA", () => {
    useAuthStore()
    expect(suEvento).toBeTypeOf('function')
    suEvento({ tipo: EVENTO_SESSIONE.LOGOUT })
    expect(redirectToLogin).toHaveBeenCalledWith(MOTIVO_USCITA.USCITA_ALTRA_SCHEDA)
  })
})

describe('login a due passi (brief sicurezza §3.4-bis, T-4)', () => {
  it('2) login col secondo fattore attivo → sfida, nessun access, nessun profilo', async () => {
    apiPost.mockResolvedValue({ data: { two_factor_required: true, sfida: 'sfida-1', scade_in_secondi: 300 } })
    const auth = useAuthStore()
    const esito = await auth.login('tid', 'pw', 'ADMIN')
    expect(esito).toEqual({ secondoPasso: true, sfida: 'sfida-1' })
    expect(apiPost).toHaveBeenCalledWith('/admin/token/', { username: 'tid', password: 'pw' })
    expect(getAccessToken()).toBeFalsy()
    expect(apiGet).not.toHaveBeenCalled()
  })

  it('3) secondo passo → access in memoria, profilo, codici di recupero rimasti', async () => {
    const access = accessFinto()
    apiPost.mockResolvedValue({ data: { data: { access, codici_recupero_rimasti: 3 } } })
    apiGet.mockResolvedValue({ data: { data: { utente: { username: 'tid' }, obblighi_pendenti: [] } } })
    const auth = useAuthStore()
    const esito = await auth.completaSecondoPasso('sfida-1', { codiceRecupero: 'AB01-CD23-EF45-GH67' })
    expect(apiPost).toHaveBeenCalledWith(
      '/admin/token/secondo-fattore/', { sfida: 'sfida-1', codice_recupero: 'AB01-CD23-EF45-GH67' },
    )
    expect(getAccessToken()).toBe(access)
    expect(apiGet).toHaveBeenCalledWith('/core/me/')
    expect(esito).toEqual({ codiciRecuperoRimasti: 3 })
  })

  it("7) il profilo consegna il fuso dell'azienda a `core/utils/date` (F-1)", async () => {
    const { fusoAziendale, impostaFusoAziendale } = await import('../core/utils/date')
    impostaFusoAziendale(null)
    apiGet.mockResolvedValue({
      data: { data: { utente: {}, obblighi_pendenti: [], fuso_aziendale: 'Asia/Tokyo' } },
    })
    await useAuthStore().fetchProfile()
    expect(fusoAziendale()).toBe('Asia/Tokyo')
    impostaFusoAziendale(null)
  })

  it('4) secondo passo senza codice di recupero → rimasti null', async () => {
    apiPost.mockResolvedValue({ data: { data: { access: accessFinto() } } })
    apiGet.mockResolvedValue({ data: { data: { utente: {}, obblighi_pendenti: [] } } })
    const auth = useAuthStore()
    const esito = await auth.completaSecondoPasso('sfida-1', { codice: '123456' })
    expect(apiPost).toHaveBeenCalledWith('/admin/token/secondo-fattore/', { sfida: 'sfida-1', codice: '123456' })
    expect(esito).toEqual({ codiciRecuperoRimasti: null })
  })

  it("6) la chiave d'ingresso è del canale: email per PORTALE e SHOP (L-4)", async () => {
    apiPost.mockResolvedValue({ data: { two_factor_required: true, sfida: 's' } })
    const auth = useAuthStore()
    await auth.login('ada@example.it', 'pw', 'PORTALE')
    expect(apiPost).toHaveBeenLastCalledWith('/portale/token/', { email: 'ada@example.it', password: 'pw' })
    await auth.login('ada@example.it', 'pw', 'SHOP')
    expect(apiPost).toHaveBeenLastCalledWith('/shop/token/', { email: 'ada@example.it', password: 'pw' })
  })

  it('5) obbligo del secondo fattore → dal profilo, non ricalcolato', () => {
    const auth = useAuthStore()
    auth.user = { obblighi_pendenti: [] }
    expect(auth.mustConfigureSecondFactor).toBe(false)
    auth.user = { obblighi_pendenti: ['SECONDO_FATTORE'] }
    expect(auth.mustConfigureSecondFactor).toBe(true)
  })
})
