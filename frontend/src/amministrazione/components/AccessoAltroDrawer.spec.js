// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: «Elimina accesso» nel drawer di «Altri accessi»
//        (brief-db-elimina-credenziale-senza-veste §6): acceso sulla
//        credenziale che la check del DB ammette, spento col motivo del DB
//        sulle altre, nascosto in sola lettura; la conferma chiama il verbo, e
//        a gesto riuscito il drawer si chiude e la lista si ricarica.
// Note: si monta il drawer vero; sono finti solo i contorni — l'API (che
//       risponde come axios, `{ data: { data } }`), il guscio `AppDrawer`,
//       la conferma (si cattura la richiesta e si accetta a mano) e
//       `CredenzialeAzioni`, che parla col backend per conto suo.
//
// Indice test:
//   1) credenziale senza vesti ne' storia: acceso, nessun motivo scritto
//   2) con vesti: spento, motivo dalla chiave del DB, tooltip sull'involucro
//   3) con storia: il motivo nomina le tabelle (`dove` e' un array)
//   4) in sola lettura: il gesto non c'e'
//   5) conferma accettata: verbo chiamato, drawer chiuso, lista avvisata
//   6) verbo rifiutato: il drawer resta aperto e la lista non si ricarica
//   7) il reinvio dopo un fallimento rimanda la STESSA key del gesto
// ------------------------------------------------------------

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises } from '@vue/test-utils'

const eliminaCredenziale = vi.fn()
const confirmAction = vi.fn()

vi.mock('../../core/composables/useConfirmAction', () => ({
  useConfirmAction: () => ({ confirmAction: (...a) => confirmAction(...a) }),
}))
vi.mock('../api/amministrazione', () => ({
  eliminaCredenziale: (...a) => eliminaCredenziale(...a),
}))

const { monta } = await import('../../../test/montaggio')
const { default: AccessoAltroDrawer } = await import('./AccessoAltroDrawer.vue')

const ID = 7
const comeAxios = (data) => ({ data: { data } })

const AppDrawerFinto = defineComponent({
  name: 'AppDrawerFinto',
  setup(_, { slots }) {
    return () => h('div', slots.default?.())
  },
})
const Vuoto = defineComponent({ render: () => null })

function riga(sovrascritture = {}) {
  return {
    auth_user_id: ID, username: '_pgtap_sync_ab12', email: null, nome_visualizzato: '_pgtap_sync_ab12',
    ultimo_accesso: null, nessun_accesso: true, vesti: [],
    can_delete: true, delete_reason: null, delete_reason_key: null, delete_dettaglio: null,
    ...sovrascritture,
  }
}

function apri(dati, { readonly = false, messages = {} } = {}) {
  return monta(AccessoAltroDrawer, { visible: true, riga: dati, readonly }, {
    global: { stubs: { AppDrawer: AppDrawerFinto, CredenzialeAzioni: Vuoto } },
    messages,
  })
}

const pulsante = (w) => w.findAll('button').find(b => b.text().includes('amministrazione.accessi.elimina'))
const suggerimenti = (w) => w.findAll('.app-field-hint').map(s => s.text())

describe('AccessoAltroDrawer — «Elimina accesso»', () => {
  beforeEach(() => {
    eliminaCredenziale.mockReset()
    confirmAction.mockReset()
  })

  it('credenziale senza vesti ne\' storia: acceso, nessun motivo scritto', () => {
    const w = apri(riga())
    expect(pulsante(w).attributes('disabled')).toBeUndefined()
    expect(suggerimenti(w)).toEqual([])
  })

  it('con vesti: spento, motivo dalla chiave del DB, tooltip sull\'involucro', () => {
    const w = apri(riga({
      nessun_accesso: false, can_delete: false, delete_reason: 'CON_VESTI',
      delete_reason_key: 'amministrazione.accessi.elimina_reason.con_vesti',
      delete_dettaglio: { auth_user_id: ID },
    }))
    const b = pulsante(w)
    expect(b.attributes('disabled')).toBeDefined()
    // Un <button disabled> non emette eventi del mouse: il tooltip e' sul padre.
    expect(b.element.parentElement.classList.contains('app-action-tooltip-wrap')).toBe(true)
    // Nel test `te()` non trova la chiave: il ripiego e' il codice macchina.
    expect(suggerimenti(w)).toEqual(['CON_VESTI'])
  })

  it('con storia: il motivo nomina le tabelle (`dove` e\' un array)', () => {
    const w = apri(riga({
      can_delete: false, delete_reason: 'CON_STORIA',
      delete_reason_key: 'amministrazione.accessi.elimina_reason.con_storia',
      delete_dettaglio: { auth_user_id: ID, dove: ['config.email_log', 'vendite.event_log'] },
    }), {
      messages: {
        amministrazione: { accessi: { elimina_reason: { con_storia: 'Compare in {dove}' } } },
      },
    })
    expect(suggerimenti(w)).toEqual(['Compare in config.email_log, vendite.event_log'])
  })

  it('in sola lettura: il gesto non c\'e\'', () => {
    const w = apri(riga(), { readonly: true })
    expect(pulsante(w)).toBeFalsy()
  })

  it('conferma accettata: verbo chiamato, drawer chiuso, lista avvisata', async () => {
    eliminaCredenziale.mockResolvedValue(comeAxios({ status: 'ok', auth_user_id: ID }))
    const w = apri(riga())
    await pulsante(w).trigger('click')
    expect(confirmAction).toHaveBeenCalledTimes(1)
    expect(eliminaCredenziale).not.toHaveBeenCalled()
    await confirmAction.mock.calls[0][0].onAccept()
    await flushPromises()
    // La key del GESTO negli header (`useChiaveGesto`), non quella per chiamata.
    expect(eliminaCredenziale).toHaveBeenCalledWith(ID, { headers: { 'Idempotency-Key': expect.any(String) } })
    expect(w.emitted('update:visible')?.at(-1)).toEqual([false])
    expect(w.emitted('changed')).toHaveLength(1)
  })

  it('verbo rifiutato: il drawer resta aperto e la lista non si ricarica', async () => {
    eliminaCredenziale.mockRejectedValue({
      response: { status: 409, data: { error: { code: 'E_CREDENZIALE_CON_VESTI', message: 'ha vesti' } } },
    })
    const w = apri(riga())
    await pulsante(w).trigger('click')
    await confirmAction.mock.calls[0][0].onAccept()
    await flushPromises()
    expect(w.emitted('update:visible')).toBeUndefined()
    expect(w.emitted('changed')).toBeUndefined()
  })

  it('⭐ il reinvio dopo un fallimento rimanda la STESSA key del gesto', async () => {
    // Un timeout puo' nascondere un'eliminazione riuscita lato server: il
    // secondo clic deve ricevere l'esito del primo, non un «non esiste».
    eliminaCredenziale.mockRejectedValueOnce({ code: 'ECONNABORTED', message: 'timeout' })
    eliminaCredenziale.mockResolvedValueOnce(comeAxios({ status: 'ok', auth_user_id: ID }))
    const w = apri(riga())
    await pulsante(w).trigger('click')
    await confirmAction.mock.calls[0][0].onAccept()
    await flushPromises()
    await pulsante(w).trigger('click')
    await confirmAction.mock.calls[1][0].onAccept()
    await flushPromises()
    const [prima, seconda] = eliminaCredenziale.mock.calls.map((c) => c[1].headers['Idempotency-Key'])
    expect(prima).toBeTruthy()
    expect(seconda).toBe(prima)
    expect(w.emitted('changed')).toHaveLength(1)
  })
})
