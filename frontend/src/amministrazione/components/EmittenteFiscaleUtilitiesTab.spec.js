// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: il tab «Gestisci utilities» di un'azienda (brief-db-utility-gestite-
//        dall-emittente §10 R-3, 2026-11-27): attivare e' una POST col solo
//        `utility_id`; i parametri sono facoltativi e si scrivono in PATCH;
//        «togli i parametri» li riporta a NULL; disattivare e' la DELETE.
//
// 🔴 Il difetto del 2026-10-31 resta presidiato (test 2): `InputNumber` di
//    PrimeVue aggiorna il `v-model` SOLO all'uscita dal campo, e il Salva e'
//    acceso dal modello. Senza l'`@input` del tab il Salva restava fermo
//    finche' il cursore era nel campo, e un pulsante disabilitato non toglie
//    il fuoco: non si accendeva mai.
//
// ⚠️ Si fingono i contorni (store, router, conferma); la digitazione e' quella
//    vera (keypress sul campo), mai un `update:modelValue` emesso a mano.
//
// Indice test:
//   1) non gestita: «Attiva» manda la POST col solo utility_id, senza form
//   2) ⭐ gestita: «Modifica parametri», decimali scritti e cursore nel campo: il
//      Salva si accende e la PATCH porta i decimali
//   3) decimali oltre il vincolo del DB (0..2): il Salva resta spento
//   4) un parametro non scritto mostra l'effettivo, sottotono
//   5) «Togli i parametri»: PATCH coi quattro a null; «Disattiva»: DELETE
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'
import { flushPromises } from '@vue/test-utils'

const NON_GESTITA = {
  utility_id: 4, utility_codice: 'EE', utility_descrizione: 'Energia',
  record_id: null, gestita: false, personalizzata: false,
  arrotondamento_importi_dec: null, metodo_arrotondamento_importi: null,
  minimo_soglia_min: null, minimo_soglia_max: null,
  effettivo_arrotondamento_importi_dec: 2, effettivo_metodo_arrotondamento_importi: 'HALF_UP',
  can_attivare: true, can_update: false, can_reset: false, can_remove: false,
}
const GESTITA = {
  ...NON_GESTITA, record_id: 9, gestita: true, personalizzata: true,
  metodo_arrotondamento_importi: 'HALF_DOWN', effettivo_metodo_arrotondamento_importi: 'HALF_DOWN',
  can_attivare: false, can_update: true, can_reset: true, can_remove: true,
}

const records = ref([])
const righe = ref([])
const addUtilityRecord = vi.fn(async () => ({ id: 77 }))
const patchUtilityRecord = vi.fn(async () => ({ updated: true }))
const removeUtilityRecord = vi.fn(async () => undefined)
vi.mock('../stores/emittentiFiscali', () => ({
  useEmittentiFiscaliStore: () => ({
    get utilitiesRecords() { return records.value },
    fetchUtilitiesRecords: async () => { records.value = righe.value },
    clearUtilitiesRecords: () => { records.value = [] },
    addUtilityRecord: (...a) => addUtilityRecord(...a),
    patchUtilityRecord: (...a) => patchUtilityRecord(...a),
    removeUtilityRecord: (...a) => removeUtilityRecord(...a),
  }),
}))
vi.mock('../api/amministrazione', async (originale) => ({
  ...(await originale()),
  lookupEmittenteRoundingModes: () => Promise.resolve({ data: { data: [
    { codice: 'HALF_UP', descrizione: 'Mezzo in su', ordering: 1 },
  ] } }),
}))
vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))
// La conferma si accetta subito: qui si prova cosa parte, non la dialog.
vi.mock('../../core/composables/useConfirmAction', () => ({
  useConfirmAction: () => ({ confirmAction: ({ onAccept }) => onAccept() }),
}))

const { monta } = await import('../../../test/montaggio')
const { default: Tab } = await import('./EmittenteFiscaleUtilitiesTab.vue')
const { default: RowActionsMenu } = await import('../../core/components/RowActionsMenu.vue')
const { default: InputNumber } = await import('primevue/inputnumber')

async function apri(riga) {
  righe.value = [riga]
  const w = monta(Tab, { emittenteId: 1 }, { attachTo: document.body })
  await flushPromises()
  return w
}
const azione = (w, key) => w.findComponent(RowActionsMenu).props('actions').find(a => a.key === key)
const salva = (w) => w.find('tbody button.p-button-success')
// La terza InputNumber della riga: i decimali (dopo soglia min e max).
const campoDecimali = (w) => w.findAllComponents(InputNumber)[2].find('input')

async function scriviDecimali(w, tasto) {
  const input = campoDecimali(w)
  await input.trigger('focus')
  await input.trigger('keypress', { key: tasto, code: `Digit${tasto}` })
  await flushPromises()
  return input
}

describe('EmittenteFiscaleUtilitiesTab', () => {
  beforeEach(() => {
    addUtilityRecord.mockClear()
    patchUtilityRecord.mockClear()
    removeUtilityRecord.mockClear()
  })

  it('1) non gestita: «Attiva» manda la POST col solo utility_id, senza form', async () => {
    const w = await apri(NON_GESTITA)
    expect(azione(w, 'attiva').visible).toBe(true)
    expect(azione(w, 'disattiva').visible).toBe(false)
    await azione(w, 'attiva').command()
    await flushPromises()
    expect(addUtilityRecord).toHaveBeenCalledWith(1, { utility_id: 4 })
    expect(w.findAllComponents(InputNumber)).toHaveLength(0)
  })

  it('2) ⭐ gestita: decimali scritti col cursore nel campo, il Salva si accende e la PATCH li porta', async () => {
    const w = await apri(GESTITA)
    azione(w, 'modifica').command()
    await flushPromises()
    const input = await scriviDecimali(w, '1')
    expect(input.element.value).toBe('1')
    expect(salva(w).attributes('disabled')).toBeUndefined()
    await salva(w).trigger('click')
    await flushPromises()
    expect(patchUtilityRecord).toHaveBeenCalledTimes(1)
    expect(patchUtilityRecord.mock.calls[0][1]).toBe(9)
    expect(patchUtilityRecord.mock.calls[0][2]).toMatchObject({
      arrotondamento_importi_dec: 1, metodo_arrotondamento_importi: 'HALF_DOWN',
    })
    expect(patchUtilityRecord.mock.calls[0][2]).not.toHaveProperty('attivo')
  })

  it('3) decimali oltre il vincolo del DB (0..2): il Salva resta spento', async () => {
    const w = await apri(GESTITA)
    azione(w, 'modifica').command()
    await flushPromises()
    await scriviDecimali(w, '4')
    expect(salva(w).attributes('disabled')).toBeDefined()
  })

  it('4) un parametro non scritto mostra l\'effettivo, sottotono', async () => {
    const w = await apri(GESTITA)
    const muti = w.findAll('tbody span.app-text-muted').map(s => s.text())
    // I decimali non sono scritti: si vede il 2 effettivo, in grigio; il
    // metodo e' scritto e non e' sottotono.
    expect(muti).toContain('2')
    expect(muti).not.toContain('HALF_DOWN')
    expect(w.text()).toContain('HALF_DOWN')
  })

  it('5) «Togli i parametri» li porta a null; «Disattiva» e\' la DELETE', async () => {
    const w = await apri(GESTITA)
    await azione(w, 'reset').command()
    await flushPromises()
    expect(patchUtilityRecord).toHaveBeenCalledWith(1, 9, {
      minimo_soglia_min: null, minimo_soglia_max: null,
      arrotondamento_importi_dec: null, metodo_arrotondamento_importi: null,
    })
    await azione(w, 'disattiva').command()
    await flushPromises()
    expect(removeUtilityRecord).toHaveBeenCalledWith(1, 9)
  })
})
