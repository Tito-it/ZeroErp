// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: L'email con cui parte l'invito di `PortaleAccessoPanel`: la propone
//        il BE con lo stato degli accessi (`email_suggerita`, 2026-11-21).
// Note: ⚠️ Si monta il pannello VERO; si finge l'API di portale. La regola
//       di scelta dell'email (identita', PRINCIPALE, default) e' del BE e ha
//       i suoi test (test_invito_portale_service, test_email_suggerita_db):
//       qui si prova solo che il pannello la usa e non scavalca l'operatore.
//
// Indice test:
//  1) cliente: il campo parte dall'email suggerita
//  2) fornitore: stessa regola, dall'endpoint del fornitore
//  3) senza suggerita il campo resta vuoto
//  4) cio' che l'operatore ha scritto non si sovrascrive al ricarico
//  5) un'altra entita' riparte dalla sua email, non da quella precedente
// ------------------------------------------------------------
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises } from '@vue/test-utils'

import PortaleAccessoPanel from './PortaleAccessoPanel.vue'
import { monta } from '../../../test/montaggio'

const risposte = { cliente: {}, fornitore: {} }
const chiamate = []
function stato(email_suggerita) {
  return Promise.resolve({ data: { data: {
    portale: { stato: 'NESSUNO' }, shop: { stato: 'NESSUNO' }, email_suggerita,
  } } })
}
vi.mock('../api/portaleAdminApi', () => ({
  getStatoAccessiCliente: (id) => { chiamate.push(['cliente', id]); return stato(risposte.cliente[id]) },
  getStatoAccessiFornitore: (id) => { chiamate.push(['fornitore', id]); return stato(risposte.fornitore[id]) },
  disattivaPortaleCliente: vi.fn(),
  disattivaPortaleFornitore: vi.fn(),
  disattivaShopCliente: vi.fn(),
  invitaClientePortale: vi.fn(),
  invitaClienteShop: vi.fn(),
  invitaFornitorePortale: vi.fn(),
}))

async function montaPanel(props) {
  const wrapper = monta(PortaleAccessoPanel, props)
  await flushPromises()
  return wrapper
}
const campoEmail = (w) => w.find('#portale-email').element.value

describe('PortaleAccessoPanel — email suggerita', () => {
  beforeEach(() => {
    risposte.cliente = {}
    risposte.fornitore = {}
    chiamate.length = 0
  })

  it('cliente: il campo parte dall\'email suggerita', async () => {
    risposte.cliente[1] = 'principale@cliente.test'
    const w = await montaPanel({ entitaTipo: 'cliente', entitaId: 1 })
    expect(chiamate).toEqual([['cliente', 1]])
    expect(campoEmail(w)).toBe('principale@cliente.test')
  })

  it('fornitore: stessa regola, dall\'endpoint del fornitore', async () => {
    risposte.fornitore[7] = 'principale@fornitore.test'
    const w = await montaPanel({ entitaTipo: 'fornitore', entitaId: 7 })
    expect(chiamate).toEqual([['fornitore', 7]])
    expect(campoEmail(w)).toBe('principale@fornitore.test')
  })

  it('senza suggerita il campo resta vuoto', async () => {
    risposte.fornitore[7] = null
    const w = await montaPanel({ entitaTipo: 'fornitore', entitaId: 7 })
    expect(campoEmail(w)).toBe('')
  })

  it('cio\' che l\'operatore ha scritto non si sovrascrive al ricarico', async () => {
    risposte.fornitore[7] = 'principale@fornitore.test'
    const w = await montaPanel({ entitaTipo: 'fornitore', entitaId: 7 })
    await w.find('#portale-email').setValue('scritta@a.mano')
    // Il ricarico dello stato (lo stesso che segue ogni mutazione).
    await w.vm.$.setupState.loadStato()
    await flushPromises()
    expect(campoEmail(w)).toBe('scritta@a.mano')
  })

  it('un\'altra entita\' riparte dalla sua email, non da quella precedente', async () => {
    risposte.fornitore[7] = 'primo@fornitore.test'
    risposte.fornitore[8] = 'secondo@fornitore.test'
    const w = await montaPanel({ entitaTipo: 'fornitore', entitaId: 7 })
    await w.setProps({ entitaId: 8 })
    await flushPromises()
    expect(campoEmail(w)).toBe('secondo@fornitore.test')
  })
})
