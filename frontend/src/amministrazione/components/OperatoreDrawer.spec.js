// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: L'interruttore «Accesso attivo» del drawer operatore dopo D-3
//        (2026-10-04, piano accessi §4.3): legge lo stato della VESTE
//        (`veste_attiva`), non `attivo` del dettaglio (la risorsa umana), e
//        SPEGNE soltanto — da spento resta fermo col perche', e si riaccende
//        col reinvio dell'invito.
// Note: si monta il drawer vero; sono finti solo i contorni — le API (che
//       rispondono come axios, `{ data: { data } }`), il guscio `AppDrawer`
//       (rende il corpo e un Salva che emette `save`) e i componenti figli
//       che parlano col backend per conto loro.
//
// Indice test:
//   1) invitato e non ancora attivato (rapporto aperto, veste spenta):
//      interruttore spento e fermo, col perche' del reinvio, e l'invito c'e'
//   2) veste accesa: interruttore acceso e libero, nessun perche'
//   3) salvare un operatore con la veste spenta manda `attivo: false`, non
//      l'`attivo` della risorsa umana
//   4) ultimo SUPER_ADMIN: vince il motivo del DB, non il perche' del reinvio
//   5) spegnere una veste accesa e' «Disabilita»: il Salva chiede conferma,
//      e si salva solo accettando
//   6) salvare senza spegnere non chiede niente
// ------------------------------------------------------------

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises } from '@vue/test-utils'

const getOperatore = vi.fn()
const updateOperatore = vi.fn()
const confirmAction = vi.fn()

vi.mock('../../core/composables/useConfirmAction', () => ({
  useConfirmAction: () => ({ confirmAction: (...a) => confirmAction(...a) }),
}))

vi.mock('../api/amministrazione', () => ({
  getOperatore: (...a) => getOperatore(...a),
  updateOperatore: (...a) => updateOperatore(...a),
  listUnitaOrganizzative: vi.fn().mockResolvedValue({ data: { data: { results: [] } } }),
  invitaOperatore: vi.fn(),
  reinviaInvito: vi.fn(),
  getCredenzialePerEmail: vi.fn(),
  listOperatori: vi.fn(),
  createOperatore: vi.fn(),
  disabilitaOperatore: vi.fn(),
  getOverrideAree: vi.fn(),
  putOverrideAree: vi.fn(),
  getOverrideAzioni: vi.fn(),
  putOverrideAzioni: vi.fn(),
}))

const { monta } = await import('../../../test/montaggio')
const { default: OperatoreDrawer } = await import('./OperatoreDrawer.vue')

const ID = 42
const comeAxios = (data) => ({ data: { data } })

// Il guscio: il corpo com'e', e un Salva che fa cio' che fa quello vero.
const AppDrawerFinto = defineComponent({
  name: 'AppDrawerFinto',
  emits: ['save', 'update:visible'],
  setup(_, { slots, emit }) {
    return () => h('div', [
      slots.default?.(),
      h('button', { class: 'salva-finto', onClick: () => emit('save') }, 'salva'),
    ])
  },
})
const Vuoto = defineComponent({ render: () => null })

function operatore(sovrascritture = {}) {
  return {
    auth_user_id: ID, username: 'mrossi', email: 'mrossi@example.invalid',
    first_name: 'Mario', last_name: 'Rossi', soggetto_nome: 'Mario', soggetto_cognome: 'Rossi',
    is_super_admin: false, ruolo_applicativo: 'OPERATORE', is_active: false,
    unita_organizzativa_id: null, valido_dal: '2026-01-01', valido_al: null,
    // `attivo` e' la RISORSA UMANA: aperta, anche con la veste spenta.
    attivo: true, veste_attiva: false,
    can_invite: true, invite_reason: null, invite_reason_key: null,
    can_disable: true, disable_reason: null, disable_reason_key: null,
    can_demote_super_admin: null, demote_reason: null, demote_reason_key: null,
    invito_inviato_at: '2026-10-01T10:00:00Z', last_login: null,
    ...sovrascritture,
  }
}

async function apri(dettaglio) {
  getOperatore.mockResolvedValue(comeAxios(dettaglio))
  const w = monta(OperatoreDrawer, { visible: false, mode: 'edit', authUserId: ID }, {
    global: {
      stubs: {
        AppDrawer: AppDrawerFinto,
        AppDialog: Vuoto,
        OperatorePermessiTab: Vuoto,
        CredenzialeAzioni: Vuoto,
        SoggettoResolver: Vuoto,
      },
    },
  })
  await w.setProps({ visible: true })
  await flushPromises()
  return w
}

const interruttore = (w) => w.find('#tg-attivo')
const suggerimenti = (w) => w.findAll('.app-field-hint').map(s => s.text())

describe('OperatoreDrawer — interruttore «Accesso attivo» (D-3)', () => {
  beforeEach(() => {
    getOperatore.mockReset()
    confirmAction.mockReset()
    updateOperatore.mockReset().mockImplementation((_id, payload) =>
      Promise.resolve(comeAxios(operatore({ ...payload }))))
  })

  it('invitato e non ancora attivato: spento e fermo, col perche\' del reinvio', async () => {
    const w = await apri(operatore())
    expect(interruttore(w).element.checked).toBe(false)
    expect(interruttore(w).attributes('disabled')).toBeDefined()
    expect(suggerimenti(w)).toContain('amministrazione.accesso_attivo.da_invito')
    expect(w.findAll('button').some(b => b.text().includes('amministrazione.reinvia_invito'))).toBe(true)
  })

  it('veste accesa: acceso e libero, nessun perche\'', async () => {
    const w = await apri(operatore({ veste_attiva: true, can_invite: false }))
    expect(interruttore(w).element.checked).toBe(true)
    expect(interruttore(w).attributes('disabled')).toBeUndefined()
    expect(suggerimenti(w)).not.toContain('amministrazione.accesso_attivo.da_invito')
  })

  it('salvare con la veste spenta manda `attivo: false`, non la risorsa umana', async () => {
    const w = await apri(operatore())
    await w.find('.salva-finto').trigger('click')
    await flushPromises()
    expect(updateOperatore).toHaveBeenCalledTimes(1)
    expect(updateOperatore.mock.calls[0][1].attivo).toBe(false)
  })

  it('spegnere una veste accesa chiede conferma, e salva solo accettando', async () => {
    const w = await apri(operatore({ veste_attiva: true, can_invite: false }))
    await interruttore(w).setValue(false)
    await w.find('.salva-finto').trigger('click')
    await flushPromises()
    expect(confirmAction).toHaveBeenCalledTimes(1)
    expect(confirmAction.mock.calls[0][0].header).toBe('amministrazione.disabilita_title')
    expect(updateOperatore).not.toHaveBeenCalled()

    await confirmAction.mock.calls[0][0].onAccept()
    await flushPromises()
    expect(updateOperatore).toHaveBeenCalledTimes(1)
    expect(updateOperatore.mock.calls[0][1].attivo).toBe(false)
  })

  it('salvare senza spegnere non chiede conferma', async () => {
    const w = await apri(operatore({ veste_attiva: true, can_invite: false }))
    await w.find('.salva-finto').trigger('click')
    await flushPromises()
    expect(confirmAction).not.toHaveBeenCalled()
    expect(updateOperatore).toHaveBeenCalledTimes(1)
  })

  it('ultimo SUPER_ADMIN: vince il motivo del DB', async () => {
    const w = await apri(operatore({
      veste_attiva: true, can_invite: false, is_super_admin: true,
      can_disable: false, disable_reason: 'ULTIMO_SUPER_ADMIN',
      disable_reason_key: 'amministrazione.operatori.disabilita_reason.ultimo_super_admin',
    }))
    expect(interruttore(w).attributes('disabled')).toBeDefined()
    // Nei test nessuna chiave esiste (`te` falso): `bloccoMotivo` mostra il codice.
    expect(suggerimenti(w)).toContain('ULTIMO_SUPER_ADMIN')
    expect(suggerimenti(w)).not.toContain('amministrazione.accesso_attivo.da_invito')
  })
})
