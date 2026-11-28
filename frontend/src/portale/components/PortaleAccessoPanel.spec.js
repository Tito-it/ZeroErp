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
//  8) due referenti: una riga ciascuno, e «Disattiva» spegne quello della riga
//  9) la veste accesa che oggi non apre la porta lo dice sotto il referente
// 10) nessun referente: la frase, e «Invita un referente» resta
// ------------------------------------------------------------
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises } from '@vue/test-utils'

import PortaleAccessoPanel from './PortaleAccessoPanel.vue'
import { monta } from '../../../test/montaggio'

const risposte = { cliente: {}, fornitore: {}, vesti: null }
const chiamate = []
const disattivaPortaleCliente = vi.fn(() => Promise.resolve({ data: { data: { disattivato: true } } }))
function stato(email_suggerita) {
  const vesti = risposte.vesti || { portale: [], shop: [] }
  return Promise.resolve({ data: { data: { ...vesti, email_suggerita } } })
}
vi.mock('../api/portaleAdminApi', () => ({
  getStatoAccessiCliente: (id) => { chiamate.push(['cliente', id]); return stato(risposte.cliente[id]) },
  getStatoAccessiFornitore: (id) => { chiamate.push(['fornitore', id]); return stato(risposte.fornitore[id]) },
  disattivaPortaleCliente: (...args) => disattivaPortaleCliente(...args),
  disattivaPortaleFornitore: vi.fn(),
  disattivaShopCliente: vi.fn(),
  invitaClientePortale: vi.fn(),
  invitaClienteShop: vi.fn(),
  invitaFornitorePortale: vi.fn(),
}))

// La conferma e' un contorno: accetta subito, cosi' il gesto arriva all'API.
vi.mock('../../core/composables/useConfirmAction', () => ({
  useConfirmAction: () => ({ confirmAction: ({ onAccept }) => onAccept() }),
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
// nuovo invito, e non si «disattiva» di nuovo. Dal 2026-11-28 (giro 4, D-M7)
// i pulsanti stanno sulla riga di ogni referente.
describe('PortaleAccessoPanel — pulsanti per stato della veste', () => {
  beforeEach(() => {
    risposte.cliente = {}
    risposte.vesti = null
    disattivaPortaleCliente.mockClear()
  })
  const etichette = (w) => w.findAll('button').map(b => b.text())

  it('veste REVOCATA: «Invia invito» e niente «Disattiva», portale e shop', async () => {
    risposte.vesti = {
      portale: [{ identita_id: 1, stato: 'REVOCATA', email: 'a@x.test' }],
      shop: [{ identita_id: 2, stato: 'REVOCATA', email: 'a@x.test' }],
    }
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
    risposte.vesti = {
      portale: [{ identita_id: 1, stato: 'PENDING', email: 'a@x.test' }],
      shop: [{ identita_id: 2, stato: 'PENDING', email: 'a@x.test' }],
    }
    const w = await montaPanel({ entitaTipo: 'cliente', entitaId: 1 })
    const b = etichette(w)
    expect(b).toContain('portale.btn_reinvia_invito')
    expect(b).toContain('portale.btn_disattiva')
    expect(b).not.toContain('portale.btn_invia_invito')
  })

  it('due referenti: una riga ciascuno, e «Disattiva» spegne quello della riga', async () => {
    risposte.vesti = {
      portale: [
        { identita_id: 10, stato: 'ATTIVO', utilizzabile: true, username: 'anna', email: 'anna@x.test' },
        { identita_id: 11, stato: 'ATTIVO', utilizzabile: true, username: 'bruno', email: 'bruno@x.test' },
      ],
      shop: [],
    }
    const w = await montaPanel({ entitaTipo: 'cliente', entitaId: 1 })
    const righe = w.findAll('.portale-accesso-referenti > li')
    expect(righe).toHaveLength(2)
    expect(righe[1].text()).toContain('bruno')
    // Il pulsante della seconda riga: la conferma e' finta e accetta subito.
    const btn = righe[1].findAll('button').find(b => b.text() === 'portale.btn_disattiva')
    await btn.trigger('click')
    await flushPromises()
    expect(disattivaPortaleCliente).toHaveBeenCalledTimes(1)
    expect(disattivaPortaleCliente).toHaveBeenCalledWith(1, 11)
  })

  it('la veste accesa che oggi non apre la porta lo dice sotto il referente', async () => {
    risposte.vesti = {
      portale: [{ identita_id: 10, stato: 'ATTIVO', utilizzabile: false, valido_dal: '2099-01-01', username: 'anna' }],
      shop: [],
    }
    const w = await montaPanel({ entitaTipo: 'cliente', entitaId: 1 })
    expect(w.find('.portale-accesso-referenti').text()).toContain('amministrazione.accessi.veste_ferma_oggi')
  })

  it('nessun referente: la frase, e «Invita un referente» resta', async () => {
    const w = await montaPanel({ entitaTipo: 'fornitore', entitaId: 7 })
    expect(w.text()).toContain('portale.referenti_nessuno')
    expect(etichette(w)).toContain('portale.btn_invita_referente')
    expect(etichette(w)).not.toContain('shop.btn_invita_referente')
  })
})
