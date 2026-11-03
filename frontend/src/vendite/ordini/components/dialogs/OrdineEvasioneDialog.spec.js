// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: «Genera DDT» e gli ONERI dell'ordine (brief-db-addebito-trasporto-
//        ordine K-5, §9.9): un onere non si evade, passa da solo e intero
//        nella prima bolla. In tabella sarebbe una riga «senza residuo», cioe'
//        evasa, e non lo e': il dialog lo toglie e lo dice in una nota.
// Note: ⚠️ Si monta il dialog VERO, con la macchina di selezione vera
//       (`useRigheSelezioneQta`) e la tabella vera; si fingono i contorni: lo
//       store (`loadRighe`, `generaDdt`), la cornice `AppDialog` (se ne legge
//       `closeOnly` e si emette `save`), la conferma (accetta subito) e le
//       notifiche.
//
// Indice test:
//   1) le righe-onere non sono in tabella, e la nota le conta
//   2) senza oneri, nessuna nota
//   3) «tutto il residuo»: la conferma conta le sole merci, e il DDT parte
//      col residuo (righe null) — l'onere non viaggia nel payload
//   4) un ordine di soli oneri (la merce gia' evasa): niente da generare,
//      solo chiusura
//   5) l'onere gia' partito con una bolla (`onere_in_bolla`, 20261103-65):
//      non si dice «da passare», si dice «gia' partito»
//   6) un onere partito e uno da passare: ognuno nella sua nota
// ------------------------------------------------------------

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent } from 'vue'
import { flushPromises } from '@vue/test-utils'

const loadRighe = vi.fn()
const generaDdt = vi.fn()
const confirmAction = vi.fn()
const notifiche = { success: vi.fn(), error: vi.fn(), warn: vi.fn(), info: vi.fn() }

vi.mock('../../stores/ordini', () => ({
  useOrdiniStore: () => ({ loadRighe, generaDdt }),
}))
vi.mock('../../../../core/composables/useConfirmAction', () => ({
  useConfirmAction: () => ({ confirmAction: (...a) => confirmAction(...a) }),
}))
vi.mock('../../../../core/composables/useNotify', () => ({ useNotify: () => notifiche }))

const { monta } = await import('../../../../../test/montaggio')
const { default: OrdineEvasioneDialog } = await import('./OrdineEvasioneDialog.vue')

const CorniceFinta = defineComponent({
  name: 'AppDialog',
  props: { closeOnly: { type: Boolean, default: false } },
  emits: ['save', 'update:visible', 'cancel'],
  template: '<div><slot /></div>',
})

function riga(id, sovrascritture = {}) {
  return {
    id, riga_nr: id, articolo_codice: `A${id}`, descrizione: `Riga ${id}`, uom_codice: 'PZ',
    qta_operativa: '2', qta_evasa_operativa: '0', qta_residua_operativa: '2', e_onere: false,
    ...sovrascritture,
  }
}
const MERCE = riga(1)
const ONERE = riga(2, {
  articolo_codice: 'ONERE_TRASPORTO', e_onere: true, onere_in_bolla: false,
  qta_evasa_operativa: null, qta_residua_operativa: null,
})
const ONERE_PARTITO = riga(4, {
  articolo_codice: 'ONERE_URGENZA', e_onere: true, onere_in_bolla: true,
  qta_evasa_operativa: null, qta_residua_operativa: null,
})

async function apri(righe) {
  loadRighe.mockResolvedValue(righe)
  const w = monta(OrdineEvasioneDialog, { visible: true, ordineId: 3 }, {
    global: { stubs: { AppDialog: CorniceFinta } },
  })
  await flushPromises()
  return w
}

const righeInTabella = (w) => w.findAll('tbody tr').filter((tr) => tr.find('td').exists()
  && !tr.classes().includes('p-datatable-empty-message'))
const nota = (w) => w.text().includes('vendite.ordini.evasione_oneri_nota')
const notaPartiti = (w) => w.text().includes('vendite.ordini.evasione_oneri_in_bolla_nota')

describe('OrdineEvasioneDialog — gli oneri non si evadono', () => {
  beforeEach(() => {
    loadRighe.mockReset()
    generaDdt.mockReset().mockResolvedValue({ data: { data: { ddt_id: 9 } } })
    confirmAction.mockReset().mockImplementation(({ onAccept }) => onAccept())
    Object.values(notifiche).forEach((f) => f.mockReset())
  })

  it('1) le righe-onere non sono in tabella, e la nota le conta', async () => {
    const w = await apri([ONERE, MERCE])
    const righe = righeInTabella(w)
    expect(righe).toHaveLength(1)
    expect(righe[0].text()).toContain('A1')
    expect(w.text()).not.toContain('ONERE_TRASPORTO')
    expect(nota(w)).toBe(true)
    expect(w.vm.$.setupState.oneriDaPassare).toBe(1)
    expect(notaPartiti(w)).toBe(false)
  })

  it('2) senza oneri, nessuna nota', async () => {
    const w = await apri([MERCE, riga(3)])
    expect(righeInTabella(w)).toHaveLength(2)
    expect(nota(w)).toBe(false)
    expect(notaPartiti(w)).toBe(false)
  })

  it('3) «tutto il residuo»: la conferma conta le sole merci, e parte col residuo', async () => {
    const w = await apri([ONERE, MERCE])
    w.findComponent(CorniceFinta).vm.$emit('save')
    await flushPromises()
    expect(confirmAction).toHaveBeenCalledTimes(1)
    // Il numero di righe nella conferma: l'onere non si conta.
    expect(w.vm.$.setupState.righeEvadibili).toHaveLength(1)
    expect(generaDdt).toHaveBeenCalledWith(3, null)
    expect(w.emitted('evaso')?.[0]).toEqual([{ ddtId: 9 }])
  })

  it('4) un ordine di soli oneri da evadere: solo chiusura', async () => {
    const w = await apri([ONERE, riga(1, { qta_evasa_operativa: '2', qta_residua_operativa: '0' })])
    expect(w.findComponent(CorniceFinta).props('closeOnly')).toBe(true)
    expect(nota(w)).toBe(true)
  })

  it("5) l'onere gia' partito con una bolla: nota «gia' partito», non «da passare»", async () => {
    const w = await apri([ONERE_PARTITO, MERCE])
    expect(righeInTabella(w)).toHaveLength(1)
    expect(nota(w)).toBe(false)
    expect(notaPartiti(w)).toBe(true)
  })

  it('6) un onere partito e uno da passare: ognuno nella sua nota', async () => {
    const w = await apri([ONERE, ONERE_PARTITO, MERCE])
    expect(righeInTabella(w)).toHaveLength(1)
    expect(w.vm.$.setupState.oneriDaPassare).toBe(1)
    expect(w.vm.$.setupState.oneriInBolla).toBe(1)
    expect(nota(w)).toBe(true)
    expect(notaPartiti(w)).toBe(true)
  })
})
