// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il blocco dell'amministratore su una credenziale (`CredenzialeBlocco`),
//        montato con la risposta vera del backend: i due gesti, la capability
//        che spegne «Blocca» col motivo, la sola lettura che li nasconde.
// Note: le API sono finte e rispondono come axios (`{ data: { data } }`):
//       l'unwrap lo fa `useApiHandler` vero.
//
// Indice test:
//   1) credenziale libera: «Blocca» acceso, niente «Sblocca»
//   2) ultimo SUPER_ADMIN: «Blocca» spento, e il motivo sta sull'involucro
//   3) bloccata: «Sblocca» e il dettaglio chi/quando/perche'
//   4) in sola lettura: nessun gesto
//   5) il blocco manda il motivo, aggiorna lo stato e avvisa la lista
// ------------------------------------------------------------

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'

const getCredenziale = vi.fn()
const bloccaCredenziale = vi.fn()

vi.mock('../api/amministrazione', () => ({
  getCredenziale: (...a) => getCredenziale(...a),
  bloccaCredenziale: (...a) => bloccaCredenziale(...a),
  sbloccaCredenziale: vi.fn(),
}))

const { monta } = await import('../../../test/montaggio')
const { default: CredenzialeBlocco } = await import('./CredenzialeBlocco.vue')

const ID = 7
const comeAxios = (data) => ({ data: { data } })

function cred(sovrascritture = {}) {
  return {
    auth_user_id: ID, username: 'cliente7', email: null, categoria: 'ALTRO',
    bloccata: false, bloccata_dal: null, bloccata_da: null, motivo_blocco: null,
    can_block: true, block_reason: null, block_reason_key: null,
    ...sovrascritture,
  }
}

async function apri({ readonly = false } = {}) {
  const w = monta(CredenzialeBlocco, { authUserId: ID, readonly })
  await flushPromises()
  return w
}

const pulsante = (w, chiave) => w.findAll('button').find(b => b.text().includes(chiave))

describe('CredenzialeBlocco', () => {
  beforeEach(() => {
    getCredenziale.mockReset().mockResolvedValue(comeAxios(cred()))
    bloccaCredenziale.mockReset()
  })

  it('credenziale libera: «Blocca» acceso, niente «Sblocca»', async () => {
    const w = await apri()
    expect(w.text()).toContain('amministrazione.accessi.non_bloccata')
    expect(pulsante(w, 'amministrazione.accessi.blocca').attributes('disabled')).toBeUndefined()
    expect(pulsante(w, 'amministrazione.accessi.sblocca')).toBeFalsy()
  })

  it('ultimo SUPER_ADMIN: «Blocca» spento, e il motivo sta sull\'involucro', async () => {
    getCredenziale.mockResolvedValue(comeAxios(cred({
      can_block: false, block_reason: 'ULTIMO_SUPER_ADMIN',
      block_reason_key: 'amministrazione.accessi.blocca_reason.ultimo_super_admin',
    })))
    const w = await apri()
    const blocca = pulsante(w, 'amministrazione.accessi.blocca')
    expect(blocca.attributes('disabled')).toBeDefined()
    // Un <button disabled> non emette eventi del mouse: il tooltip e' sul padre.
    expect(blocca.element.parentElement.classList.contains('app-action-tooltip-wrap')).toBe(true)
  })

  it('bloccata: «Sblocca» e il dettaglio chi/quando/perche\'', async () => {
    getCredenziale.mockResolvedValue(comeAxios(cred({
      bloccata: true, bloccata_dal: '2026-10-02T10:00:00Z', bloccata_da: 'tid', motivo_blocco: 'abuso',
    })))
    const w = await apri()
    expect(w.text()).toContain('amministrazione.accessi.bloccata_dettaglio')
    expect(pulsante(w, 'amministrazione.accessi.sblocca')).toBeTruthy()
    expect(pulsante(w, 'amministrazione.accessi.blocca ')).toBeFalsy()
  })

  it('in sola lettura: nessun gesto', async () => {
    const w = await apri({ readonly: true })
    expect(w.findAll('button')).toHaveLength(0)
  })

  it('il blocco manda il motivo, aggiorna lo stato e avvisa la lista', async () => {
    bloccaCredenziale.mockResolvedValue(comeAxios(cred({ bloccata: true, motivo_blocco: 'abuso' })))
    const w = await apri()
    // Il motivo arriva da `MotivoDialog` con `conferma`.
    await w.vm.confermaBlocca('abuso')
    await flushPromises()
    expect(bloccaCredenziale).toHaveBeenCalledWith(ID, 'abuso')
    expect(w.text()).toContain('amministrazione.accessi.bloccata')
    expect(w.emitted('changed')).toHaveLength(1)
  })
})
