// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: `collegaIndirizzoSoggettoForm` — il collegamento copre OGNI prop e
//        ogni evento di `IndirizzoSoggettoForm`, tranne quelli che restano al
//        chiamante; e gli eventi aggiornano il composable. Una prop nuova del
//        form che non entra qui fa rosso il caso 1: prima dell'estrazione
//        (2026-11-18) andava aggiunta in cinque componenti, in silenzio.
//
// Indice test:
//   1) copre le prop e gli eventi del form, tranne quelli del chiamante
//   2) gli eventi aggiornano il composable; i valori seguono i suoi ref
// ------------------------------------------------------------

import { describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import IndirizzoSoggettoForm from '../components/IndirizzoSoggettoForm.vue'
import { collegaIndirizzoSoggettoForm } from './collegaIndirizzoSoggettoForm'

// Del chiamante: cambiano da un componente all'altro. `formModifiers` e
// `update:form` li genera `defineModel`: il form muta l'oggetto condiviso e
// non riassegna mai il modello.
const DEL_CHIAMANTE = new Set([
  'campiErrati', 'tipiEsistenti', 'comuneInitialItem', 'mostraAutoClone', 'disabled', 'formModifiers',
])
const EVENTI_ESCLUSI = new Set(['update:form'])

function composableFinto() {
  return {
    form: { tipo_indirizzo_codice_interno: 'FATT' },
    isLibera: ref(false),
    tipiStato: ref([{ codice_interno: 'FATT' }]),
    statiLookup: { items: ref([]) },
    capOptions: ref([]),
    loadingCap: ref(false),
    autoClone: ref(true),
    switchTipo: vi.fn(),
    indirizzoWarnings: ref([]),
    addressNotFound: ref(false),
  }
}

const nomeListener = (evento) => `on${evento[0].toUpperCase()}${evento.slice(1)}`

describe('collegaIndirizzoSoggettoForm', () => {
  it('1) copre le prop e gli eventi del form, tranne quelli del chiamante', () => {
    const legame = collegaIndirizzoSoggettoForm(composableFinto()).value
    const props = Object.keys(IndirizzoSoggettoForm.props).filter(p => !DEL_CHIAMANTE.has(p))
    const eventi = (IndirizzoSoggettoForm.emits ?? []).filter(e => !EVENTI_ESCLUSI.has(e))
    for (const p of props) expect(legame, `prop ${p}`).toHaveProperty([p])
    for (const e of eventi) expect(legame[nomeListener(e)], `evento ${e}`).toBeTypeOf('function')
  })

  it('2) gli eventi aggiornano il composable; i valori seguono i suoi ref', () => {
    const indirizzo = composableFinto()
    const legame = collegaIndirizzoSoggettoForm(indirizzo)
    legame.value['onUpdate:isLibera'](true)
    legame.value['onUpdate:autoClone'](false)
    legame.value.onSwitchTipo('SPED')
    expect(indirizzo.isLibera.value).toBe(true)
    expect(indirizzo.autoClone.value).toBe(false)
    expect(indirizzo.switchTipo).toHaveBeenCalledWith('SPED')
    indirizzo.addressNotFound.value = true
    expect(legame.value.isLibera).toBe(true)
    expect(legame.value.addressNotFound).toBe(true)
  })
})
