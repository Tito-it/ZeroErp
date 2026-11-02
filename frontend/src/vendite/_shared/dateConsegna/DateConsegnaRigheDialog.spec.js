// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: «Aggiorna date di consegna» (brief-db-date-consegna-righe-in-blocco
//        §5, §8): che cosa `DateConsegnaRigheDialog` manda al backend, e
//        quando chiede conferma. Lo spec del composable dell'azione sta in
//        `useDateConsegnaRighe.spec.js`.
// Note: ⚠️ Si monta il dialog VERO; si fingono i contorni: l'azione dello
//       store (`invia`, che ritorna la response axios), la cornice
//       `AppDialog` (se ne leggono `saveDisabled` e l'evento `save`), la
//       conferma e le notifiche.
//
// Indice test:
//  1) senza data il salvataggio e' spento
//  2) SOLO_VUOTE: una chiamata sola, senza anteprima e senza conferma
//  3) TUTTE: prima l'anteprima, poi la conferma col numero, poi la scrittura
//  4) TUTTE annullata: l'anteprima non scrive, e nient'altro parte
//  5) il toast dice le righe saltate perche' gia' spedite
//  6) una colonna sola: niente scelta, la colonna e' quella
//  7) l'esito con la chiave `data` (la data scritta) arriva intero
//  8) TUTTE rifiutata dal DB gia' nell'anteprima: nessuna conferma, niente scritto
// ------------------------------------------------------------
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent } from 'vue'
import { flushPromises } from '@vue/test-utils'

const chiamate = []
let esitoProssimo = null
const confirmAction = vi.fn()
const notifiche = { success: vi.fn(), error: vi.fn(), warn: vi.fn(), info: vi.fn() }

// L'azione dello store, come la passa il drawer: ritorna la response axios.
function invia(payload) {
  chiamate.push(payload)
  const esito = typeof esitoProssimo === 'function' ? esitoProssimo(payload) : esitoProssimo
  return Promise.resolve({ data: { data: esito } })
}
vi.mock('../../../core/composables/useConfirmAction', () => ({
  useConfirmAction: () => ({ confirmAction: (...a) => confirmAction(...a) }),
}))
vi.mock('../../../core/composables/useNotify', () => ({ useNotify: () => notifiche }))

const { monta } = await import('../../../../test/montaggio')
const { default: DateConsegnaRigheDialog } = await import('./DateConsegnaRigheDialog.vue')

const CorniceFinta = defineComponent({
  name: 'AppDialog',
  props: { saveDisabled: { type: Boolean, default: false } },
  emits: ['save', 'update:visible'],
  template: '<div><slot /></div>',
})

const DUE_COLONNE = [
  { colonna: 'data_consegna_richiesta_cliente', label: 'Richiesta' },
  { colonna: 'data_consegna_confermata', label: 'Confermata' },
]

function esito(aggiornate, saltate = 0, anteprima = false) {
  return { aggiornate, saltate_spedite: saltate, anteprima }
}

async function montaDialog(props = {}) {
  const wrapper = monta(
    DateConsegnaRigheDialog,
    { visible: true, invia, colonne: DUE_COLONNE, ...props },
    { global: { stubs: { AppDialog: CorniceFinta } } },
  )
  await flushPromises()
  return wrapper
}

// Lo stato del form, come lo lascerebbe l'operatore.
async function compila(wrapper, { colonna, modalita } = {}) {
  const vm = wrapper.vm.$
  vm.setupState.dataScelta = new Date(2026, 10, 20)
  if (colonna) vm.setupState.colonna = colonna
  if (modalita) vm.setupState.modalita = modalita
  await flushPromises()
}

async function salva(wrapper) {
  wrapper.findComponent(CorniceFinta).vm.$emit('save')
  await flushPromises()
}

describe('DateConsegnaRigheDialog — che cosa parte', () => {
  beforeEach(() => {
    chiamate.length = 0
    esitoProssimo = null
    confirmAction.mockReset()
    Object.values(notifiche).forEach((f) => f.mockReset())
  })

  it('senza data il salvataggio e\' spento', async () => {
    const wrapper = await montaDialog()
    expect(wrapper.findComponent(CorniceFinta).props('saveDisabled')).toBe(true)
    await compila(wrapper)
    expect(wrapper.findComponent(CorniceFinta).props('saveDisabled')).toBe(false)
  })

  it('SOLO_VUOTE: una chiamata sola, senza anteprima e senza conferma', async () => {
    esitoProssimo = esito(2)
    const wrapper = await montaDialog()
    await compila(wrapper, { colonna: 'data_consegna_confermata' })
    await salva(wrapper)
    expect(chiamate).toEqual([{
      colonna: 'data_consegna_confermata', data: '2026-11-20', modalita: 'SOLO_VUOTE', anteprima: false,
    }])
    expect(confirmAction).not.toHaveBeenCalled()
    expect(wrapper.emitted('aggiornate')).toEqual([[esito(2)]])
    expect(wrapper.emitted('update:visible')).toEqual([[false]])
  })

  it('TUTTE: prima l\'anteprima, poi la conferma col numero, poi la scrittura', async () => {
    esitoProssimo = (payload) => esito(3, 1, payload.anteprima)
    const wrapper = await montaDialog()
    await compila(wrapper, { colonna: 'data_consegna_confermata', modalita: 'TUTTE' })
    await salva(wrapper)
    expect(chiamate.map((c) => c.anteprima)).toEqual([true])
    expect(confirmAction).toHaveBeenCalledTimes(1)
    expect(confirmAction.mock.calls[0][0].message)
      .toBe('vendite.date_consegna.conferma_tutte_con_saltate')
    await confirmAction.mock.calls[0][0].onAccept()
    await flushPromises()
    expect(chiamate.map((c) => [c.modalita, c.anteprima])).toEqual([['TUTTE', true], ['TUTTE', false]])
    expect(wrapper.emitted('aggiornate')).toHaveLength(1)
  })

  it('TUTTE annullata: l\'anteprima non scrive, e nient\'altro parte', async () => {
    esitoProssimo = esito(3, 0, true)
    const wrapper = await montaDialog()
    await compila(wrapper, { modalita: 'TUTTE' })
    await salva(wrapper)
    expect(confirmAction.mock.calls[0][0].message).toBe('vendite.date_consegna.conferma_tutte')
    expect(chiamate).toHaveLength(1)
    expect(wrapper.emitted('aggiornate')).toBeUndefined()
  })

  it('il toast dice le righe saltate perche\' gia\' spedite', async () => {
    esitoProssimo = esito(1, 2)
    const wrapper = await montaDialog()
    await compila(wrapper)
    await salva(wrapper)
    expect(notifiche.success).toHaveBeenCalledWith('vendite.date_consegna.esito_con_saltate')
  })

  it('una colonna sola: niente scelta, la colonna e\' quella', async () => {
    esitoProssimo = esito(1)
    const wrapper = await montaDialog({ colonne: [DUE_COLONNE[0]] })
    expect(wrapper.find('#date-consegna-colonna').exists()).toBe(false)
    expect(wrapper.text()).toContain('Richiesta')
    await compila(wrapper)
    await salva(wrapper)
    expect(chiamate[0].colonna).toBe('data_consegna_richiesta_cliente')
    expect(notifiche.success).toHaveBeenCalledWith('vendite.date_consegna.esito')
  })

  it('l\'esito con la chiave `data` (la data scritta) arriva intero', async () => {
    // L'esito vero porta `data`: se lo store ritornasse l'esito spacchettato,
    // `execute` lo prenderebbe per un envelope e darebbe la sola data.
    esitoProssimo = { ...esito(2), data: '2026-11-20' }
    const wrapper = await montaDialog()
    await compila(wrapper)
    await salva(wrapper)
    expect(wrapper.emitted('aggiornate')).toEqual([[{ ...esito(2), data: '2026-11-20' }]])
    expect(notifiche.success).toHaveBeenCalledWith('vendite.date_consegna.esito')
  })

  it('TUTTE rifiutata dal DB gia\' nell\'anteprima: nessuna conferma, niente scritto', async () => {
    // L'anteprima e' l'UPDATE vero annullato: il 409 del lock arriva li'.
    const rifiuto = Object.assign(new Error('409'), {
      response: { status: 409, data: { error: { code: 'E_RIGA_DOC_NON_BOZZA', message: 'stato' } } },
    })
    const wrapper = await montaDialog({ invia: (p) => { chiamate.push(p); return Promise.reject(rifiuto) } })
    await compila(wrapper, { modalita: 'TUTTE' })
    await salva(wrapper)
    expect(chiamate.map((c) => c.anteprima)).toEqual([true])
    expect(confirmAction).not.toHaveBeenCalled()
    expect(wrapper.emitted('aggiornate')).toBeUndefined()
  })
})
