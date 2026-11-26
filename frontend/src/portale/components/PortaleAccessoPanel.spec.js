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
//  6) veste REVOCATA: «Invia invito» e niente «Disattiva», portale e shop
//  7) veste PENDING: «Reinvia» e «Disattiva» (il ramo opposto, per contrasto)
// ------------------------------------------------------------
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises } from '@vue/test-utils'

import PortaleAccessoPanel from './PortaleAccessoPanel.vue'
import { monta } from '../../../test/montaggio'

const risposte = { cliente: {}, fornitore: {}, vesti: null }
const chiamate = []
function stato(email_suggerita) {
  const vesti = risposte.vesti || { portale: { stato: 'NESSUNO' }, shop: { stato: 'NESSUNO' } }
  return Promise.resolve({ data: { data: { ...vesti, email_suggerita } } })
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
    risposte.vesti = null
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

// I pulsanti del pannello sullo stato della veste (2026-11-26, passo 3b del
// brief-db-accessi-area-clienti): una veste revocata si riapre solo con un
// nuovo invito, e non si «disattiva» di nuovo.
describe('PortaleAccessoPanel — pulsanti per stato della veste', () => {
  beforeEach(() => {
    risposte.cliente = {}
    risposte.vesti = null
  })
  const etichette = (w) => w.findAll('button').map(b => b.text())

  it('veste REVOCATA: «Invia invito» e niente «Disattiva», portale e shop', async () => {
    risposte.vesti = { portale: { stato: 'REVOCATA' }, shop: { stato: 'REVOCATA' } }
    const w = await montaPanel({ entitaTipo: 'cliente', entitaId: 1 })
    const b = etichette(w)
    expect(b).toContain('portale.btn_invia_invito')
    expect(b).toContain('shop.btn_invia_invito')
    expect(b).not.toContain('portale.btn_reinvia_invito')
    expect(b).not.toContain('shop.btn_reinvia_invito')
    expect(b).not.toContain('portale.btn_disattiva')
    expect(b).not.toContain('shop.btn_disattiva')
  })

  it('veste PENDING: «Reinvia» e «Disattiva» (il ramo opposto, per contrasto)', async () => {
    risposte.vesti = { portale: { stato: 'PENDING' }, shop: { stato: 'PENDING' } }
    const w = await montaPanel({ entitaTipo: 'cliente', entitaId: 1 })
    const b = etichette(w)
    expect(b).toContain('portale.btn_reinvia_invito')
    expect(b).toContain('portale.btn_disattiva')
    expect(b).not.toContain('portale.btn_invia_invito')
  })
})
