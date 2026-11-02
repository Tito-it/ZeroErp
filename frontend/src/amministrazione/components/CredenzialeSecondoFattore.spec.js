// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il secondo fattore di una credenziale nel drawer dell'amministratore
//        (`CredenzialeSecondoFattore`). ⭐ Nasce dal difetto del 2026-10-02: il
//        componente leggeva `res.data.data` da `execute`, che restituisce GIA'
//        il contenuto dell'envelope, e la sezione non compariva mai — senza
//        un errore. Qui si monta con la risposta vera del backend.
// Note: le API sono finte e rispondono come axios (`{ data: { data } }`):
//       l'unwrap lo fa `useApiHandler` vero.
//
// Indice test:
//   1) device ATTIVO di un altro: stato, interruttore e «Disattiva» compaiono
//   2) il proprio operatore: niente «Disattiva» (decisione 7: solo da Sicurezza)
//   3) in sola lettura: niente «Disattiva»
//   4) la disattivazione aggiorna lo stato con la risposta
// ------------------------------------------------------------

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'

const getSecondoFattoreCredenziale = vi.fn()
const disattivaSecondoFattoreCredenziale = vi.fn()

vi.mock('../api/amministrazione', () => ({
  getSecondoFattoreCredenziale: (...a) => getSecondoFattoreCredenziale(...a),
  impostaObbligoSecondoFattore: vi.fn(),
  disattivaSecondoFattoreCredenziale: (...a) => disattivaSecondoFattoreCredenziale(...a),
}))

const { monta } = await import('../../../test/montaggio')
const { default: CredenzialeSecondoFattore } = await import('./CredenzialeSecondoFattore.vue')
const { useAuthStore } = await import('../../stores/auth')

const IO = 1
const POCHI = 6

function stato(statoDevice) {
  return {
    stato: statoDevice, obbligatorio: true, motivo: 'PROFILO',
    codici_recupero_rimasti: 10, obbligo_sulla_credenziale: false,
  }
}

// Le API rispondono come axios: l'envelope sta in `data`.
const comeAxios = (data) => ({ data: { data } })

async function apri(authUserId, { readonly = false } = {}) {
  const wrapper = monta(CredenzialeSecondoFattore, { authUserId, readonly })
  useAuthStore().user = { utente: { auth_user_id: IO }, is_super_admin: true }
  await flushPromises()
  return wrapper
}

const pulsanteDisattiva = (w) =>
  w.findAll('button').find(b => b.text().includes('amministrazione.secondo_fattore.disattiva'))

describe('CredenzialeSecondoFattore', () => {
  beforeEach(() => {
    getSecondoFattoreCredenziale.mockReset().mockResolvedValue(comeAxios(stato('ATTIVO')))
    disattivaSecondoFattoreCredenziale.mockReset()
  })

  it('device ATTIVO di un altro: la sezione e «Disattiva» compaiono', async () => {
    const w = await apri(POCHI)
    expect(w.text()).toContain('amministrazione.secondo_fattore.stato.ATTIVO')
    expect(pulsanteDisattiva(w)).toBeTruthy()
  })

  it('il proprio operatore: niente «Disattiva»', async () => {
    const w = await apri(IO)
    expect(w.text()).toContain('amministrazione.secondo_fattore.stato.ATTIVO')
    expect(pulsanteDisattiva(w)).toBeFalsy()
  })

  it('in sola lettura: niente «Disattiva»', async () => {
    const w = await apri(POCHI, { readonly: true })
    expect(pulsanteDisattiva(w)).toBeFalsy()
  })

  it('la disattivazione aggiorna lo stato con la risposta', async () => {
    disattivaSecondoFattoreCredenziale.mockResolvedValue(comeAxios(stato('ASSENTE')))
    const w = await apri(POCHI)
    await pulsanteDisattiva(w).trigger('click')
    // Il motivo arriva da `MotivoDialog` con `conferma`.
    await w.vm.confermaDisattiva('telefono perso')
    await flushPromises()
    expect(disattivaSecondoFattoreCredenziale).toHaveBeenCalledWith(POCHI, 'telefono perso')
    expect(w.text()).toContain('amministrazione.secondo_fattore.stato.ASSENTE')
  })
})
