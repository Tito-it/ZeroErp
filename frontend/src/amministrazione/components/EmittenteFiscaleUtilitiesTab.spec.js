// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: il «Salva riga» della matrice utility di un emittente si accende
//        mentre si scrive (2026-10-31, segnalazione di Tid: «premo configura,
//        il salva non si attiva mai»).
//
// 🔴 Il difetto: `InputNumber` di PrimeVue aggiorna il `v-model` SOLO
//    all'uscita dal campo (`onInputBlur`) o con le frecce, non a ogni tasto.
//    Il Salva e' acceso da `isRowValid`, che legge il modello: scelto il
//    metodo e scritti i decimali, il cursore resta nel campo e il modello e'
//    ancora vuoto. E un pulsante DISABILITATO non toglie il fuoco al campo,
//    quindi il clic sul Salva non fa mai partire il blur che lo accenderebbe.
//
// ⚠️ Si fingono i contorni (store, router); la digitazione e' quella vera
//    (keypress sul campo), mai un `update:modelValue` emesso a mano: e' il
//    passaggio che un test sintetico salta, ed e' dove stava il difetto.
//
// Indice test:
//   1) appena configurata la riga il Salva e' spento
//   2) ⭐ metodo scelto, decimali scritti e cursore ancora nel campo: il Salva si accende
//   3) ⭐ riga NUOVA con i gesti veri (Select sul mousedown, tasti): Salva manda la POST
//   4) decimali oltre il vincolo del DB (0..2): il Salva resta spento, nessuna POST
// ------------------------------------------------------------

import { describe, it, expect, vi } from 'vitest'
import { ref } from 'vue'
import { flushPromises } from '@vue/test-utils'

const records = ref([])
const addUtilityRecord = vi.fn(async () => ({ id: 77 }))
vi.mock('../stores/emittentiFiscali', () => ({
  useEmittentiFiscaliStore: () => ({
    get utilitiesRecords() { return records.value },
    fetchUtilitiesRecords: async () => {
      records.value = [{ utility_id: 4, utility_codice: 'EE', utility_descrizione: 'Energia', record_id: null }]
    },
    addUtilityRecord: (...a) => addUtilityRecord(...a),
  }),
}))
vi.mock('../api/amministrazione', async (originale) => ({
  ...(await originale()),
  lookupEmittenteRoundingModes: () => Promise.resolve({ data: { data: [
    { codice: 'HALF_UP', descrizione: 'Mezzo in su', ordering: 1 },
  ] } }),
}))
vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))

const { monta } = await import('../../../test/montaggio')
const { default: Tab } = await import('./EmittenteFiscaleUtilitiesTab.vue')
const { default: RowActionsMenu } = await import('../../core/components/RowActionsMenu.vue')
const { default: InputNumber } = await import('primevue/inputnumber')
const { default: RoundingSelect } = await import('./EmittenteRoundingModeSelect.vue')

async function configura() {
  const w = monta(Tab, { emittenteId: 1 }, { attachTo: document.body })
  await flushPromises()
  w.findComponent(RowActionsMenu).props('actions').find(a => a.key === 'configura').command()
  await flushPromises()
  return w
}

const salva = (w) => w.find('tbody button.p-button-success')
// La terza InputNumber della riga: i decimali (dopo soglia min e max).
const campoDecimali = (w) => w.findAllComponents(InputNumber)[2].find('input')

describe('EmittenteFiscaleUtilitiesTab — Salva riga', () => {
  it('1) appena configurata la riga il Salva e\' spento', async () => {
    const w = await configura()
    expect(salva(w).attributes('disabled')).toBeDefined()
  })

  it('2) metodo scelto, decimali scritti e cursore ancora nel campo: il Salva si accende', async () => {
    const w = await configura()
    w.findComponent(RoundingSelect).vm.$emit('update:modelValue', 'HALF_UP')
    await flushPromises()
    const input = campoDecimali(w)
    await input.trigger('focus')
    await input.trigger('keypress', { key: '2', code: 'Digit2' })
    await flushPromises()
    expect(input.element.value).toBe('2')
    expect(salva(w).attributes('disabled')).toBeUndefined()
  })
  it('3) ⭐ riga NUOVA, gesti veri: scelgo il metodo, scrivo i decimali, Salva manda la POST', async () => {
    addUtilityRecord.mockClear()
    const w = await configura()
    await w.find('.p-select').trigger('click')
    await flushPromises()
    const opzione = document.body.querySelector('.p-select-option')
    expect(opzione).not.toBeNull()
    // PrimeVue sceglie l'opzione sul MOUSEDOWN, non sul click.
    opzione.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }))
    await flushPromises()
    const input = campoDecimali(w)
    await input.trigger('focus')
    await input.trigger('keypress', { key: '2', code: 'Digit2' })
    await flushPromises()
    expect(salva(w).attributes('disabled')).toBeUndefined()
    await salva(w).trigger('click')
    await flushPromises()
    expect(addUtilityRecord).toHaveBeenCalledTimes(1)
    expect(addUtilityRecord.mock.calls[0][1]).toMatchObject({
      utility_id: 4, arrotondamento_importi_dec: 2, metodo_arrotondamento_importi: 'HALF_UP',
    })
  })

  it('4) decimali oltre il vincolo del DB (0..2): il Salva resta spento, nessuna POST', async () => {
    addUtilityRecord.mockClear()
    const w = await configura()
    w.findComponent(RoundingSelect).vm.$emit('update:modelValue', 'HALF_UP')
    await flushPromises()
    const input = campoDecimali(w)
    await input.trigger('focus')
    await input.trigger('keypress', { key: '4', code: 'Digit4' })
    await flushPromises()
    expect(salva(w).attributes('disabled')).toBeDefined()
    expect(addUtilityRecord).not.toHaveBeenCalled()
  })
})
