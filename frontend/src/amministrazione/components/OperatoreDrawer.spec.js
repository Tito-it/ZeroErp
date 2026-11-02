// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
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
//
//   Scope emittenti fiscali (nei Dati dal 2026-10-06):
//   7) cambiato solo lo scope: il Salva manda lo scope, non i dati
//   8) dati salvati e scope rifiutato: i dati restano salvati, e il Salva
//      successivo manda il solo scope
//   9) scope non modificabile: radio spente col motivo del BE
//
//   Data di fine del rapporto (brief-db-veste-utilizzabile §10):
//  10) ultimo SUPER_ADMIN senza data di fine: calendario spento col motivo
//      del DB (`can_set_valido_al`), anche se l'interruttore e' libero
//  11) salvare senza toccarla: la data non viaggia
//  12) messa viaggia come 'YYYY-MM-DD'; tolta viaggia `null`
// ------------------------------------------------------------

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises } from '@vue/test-utils'

const getOperatore = vi.fn()
const updateOperatore = vi.fn()
const getEmittentiScope = vi.fn()
const putEmittentiScope = vi.fn()
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
  getEmittentiScope: (...a) => getEmittentiScope(...a),
  putEmittentiScope: (...a) => putEmittentiScope(...a),
}))
vi.mock('../../core/apiCore', async (originale) => ({
  ...(await originale()),
  listEmittentiFiscali: () => Promise.resolve({ data: { data: { results: [{ id: 5, ragione_sociale: 'Emittente Uno' }] } } }),
}))

const { monta } = await import('../../../test/montaggio')
const { default: OperatoreDrawer } = await import('./OperatoreDrawer.vue')
const { default: Select } = await import('primevue/select')
const { default: DatePicker } = await import('primevue/datepicker')

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
    can_set_valido_al: true, valido_al_reason: null, valido_al_reason_key: null,
    invito_inviato_at: '2026-10-01T10:00:00Z', last_login: null,
    ...sovrascritture,
  }
}

const SCOPE_GLOBALE = Object.freeze({
  scope_mode: 'GLOBAL', emittenti_ids: [], allowed_scope_modes: ['GLOBAL', 'SINGLE'],
  can_change_scope: true, change_scope_reason: null,
})

async function apri(dettaglio, scope = SCOPE_GLOBALE) {
  getOperatore.mockResolvedValue(comeAxios(dettaglio))
  getEmittentiScope.mockResolvedValue(comeAxios(scope))
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

describe('OperatoreDrawer — scope emittenti fiscali nei Dati', () => {
  beforeEach(() => {
    getOperatore.mockReset()
    confirmAction.mockReset()
    updateOperatore.mockReset().mockImplementation((_id, payload) =>
      Promise.resolve(comeAxios(operatore({ ...payload, veste_attiva: true }))))
    putEmittentiScope.mockReset().mockImplementation((_id, payload) =>
      Promise.resolve(comeAxios({ ...SCOPE_GLOBALE, ...payload })))
  })

  // Scopo: porta lo scope a SINGLE sull'emittente 5, come farebbe l'operatore.
  async function scegliEmittente(w) {
    await w.find('#scope-mode-SINGLE').setValue(true)
    const tendine = w.findAllComponents(Select)
    tendine[tendine.length - 1].vm.$emit('update:modelValue', 5)
    await flushPromises()
  }

  it('cambiato solo lo scope: si manda lo scope, non i dati', async () => {
    const w = await apri(operatore({ veste_attiva: true, can_invite: false }))
    await scegliEmittente(w)
    await w.find('.salva-finto').trigger('click')
    await flushPromises()
    expect(updateOperatore).not.toHaveBeenCalled()
    expect(putEmittentiScope).toHaveBeenCalledTimes(1)
    expect(putEmittentiScope.mock.calls[0][1]).toEqual({ scope_mode: 'SINGLE', emittenti_ids: [5] })
    expect(w.emitted('saved')).toHaveLength(1)
  })

  it('dati salvati e scope rifiutato: il Salva dopo manda il solo scope', async () => {
    const w = await apri(operatore({ veste_attiva: true, can_invite: false }))
    await w.find('input[type="text"]:not([disabled])').setValue('Bianchi')
    await scegliEmittente(w)
    putEmittentiScope.mockRejectedValueOnce(new Error('rifiutato'))
    await w.find('.salva-finto').trigger('click')
    await flushPromises()
    expect(updateOperatore).toHaveBeenCalledTimes(1)
    expect(putEmittentiScope).toHaveBeenCalledTimes(1)
    // I dati sono salvati: la lista lo deve sapere.
    expect(w.emitted('saved')).toHaveLength(1)

    await w.find('.salva-finto').trigger('click')
    await flushPromises()
    expect(updateOperatore).toHaveBeenCalledTimes(1)
    expect(putEmittentiScope).toHaveBeenCalledTimes(2)
  })

  it('scope non modificabile: radio spente col motivo del BE', async () => {
    const w = await apri(operatore({ veste_attiva: true, can_invite: false }), {
      ...SCOPE_GLOBALE, can_change_scope: false, change_scope_reason: 'Motivo del BE',
    })
    expect(w.find('#scope-mode-GLOBAL').attributes('disabled')).toBeDefined()
    expect(w.find('#scope-mode-SINGLE').attributes('disabled')).toBeDefined()
  })
})

describe('OperatoreDrawer — data di fine del rapporto', () => {
  beforeEach(() => {
    getOperatore.mockReset()
    confirmAction.mockReset()
    updateOperatore.mockReset().mockImplementation((_id, payload) =>
      Promise.resolve(comeAxios(operatore({ ...payload, veste_attiva: true }))))
  })

  const calendario = (w) => w.find('#dp-valido-al')
  // Scopo: sceglie (o svuota) la data come farebbe il calendario.
  async function scegliData(w, valore) {
    w.findComponent(DatePicker).vm.$emit('update:modelValue', valore)
    await flushPromises()
  }
  async function salva(w) {
    await w.find('.salva-finto').trigger('click')
    await flushPromises()
  }

  it('ultimo SUPER_ADMIN senza data di fine: calendario spento col motivo del DB', async () => {
    const w = await apri(operatore({
      veste_attiva: true, can_invite: false, is_super_admin: true,
      can_set_valido_al: false, valido_al_reason: 'ULTIMO_SUPER_ADMIN',
      valido_al_reason_key: 'amministrazione.operatori.valido_al_reason.ultimo_super_admin',
    }))
    expect(calendario(w).attributes('disabled')).toBeDefined()
    expect(interruttore(w).attributes('disabled')).toBeUndefined()
    // Nei test nessuna chiave esiste (`te` falso): `bloccoMotivo` mostra il codice.
    expect(suggerimenti(w)).toContain('ULTIMO_SUPER_ADMIN')
    expect(suggerimenti(w)).not.toContain('amministrazione.valido_al_hint')
  })

  it('salvare senza toccarla: la data non viaggia', async () => {
    const w = await apri(operatore({ veste_attiva: true, can_invite: false, valido_al: '2026-12-31' }))
    expect(calendario(w).attributes('disabled')).toBeUndefined()
    expect(suggerimenti(w)).toContain('amministrazione.valido_al_hint')
    await salva(w)
    expect(updateOperatore).toHaveBeenCalledTimes(1)
    expect(updateOperatore.mock.calls[0][1]).not.toHaveProperty('valido_al')
  })

  it('messa viaggia come data ISO, tolta viaggia null', async () => {
    const w = await apri(operatore({ veste_attiva: true, can_invite: false }))
    await scegliData(w, new Date(2026, 11, 31))
    await salva(w)
    expect(updateOperatore.mock.calls[0][1].valido_al).toBe('2026-12-31')

    const w2 = await apri(operatore({ veste_attiva: true, can_invite: false, valido_al: '2026-12-31' }))
    updateOperatore.mockClear()
    await scegliData(w2, null)
    await salva(w2)
    expect(updateOperatore.mock.calls[0][1]).toHaveProperty('valido_al', null)
  })
})
