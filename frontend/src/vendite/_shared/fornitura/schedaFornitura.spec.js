// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: la scheda di fornitura del form di contratto e offerta (BB
//        `schedaFornitura`, R-FE-3 di brief-db-indirizzi-documento-seguono-il-
//        cliente): da dove si riempie e cosa parte verso il backend.
//
// Indice test:
//  1. scheda del backend → campi del form; il parametro numerico da testo a numero
//  2. nessuna scheda → campi vuoti
//  3. form-defaults: la scheda del cliente nuovo sostituisce quella di prima,
//     anche quando il cliente nuovo non ne ha (D-7: la scheda segue il cliente)
//  4. form-defaults senza la chiave `fornitura`: il form non si tocca
//  5. verso il backend: i campi della scheda, mai la coppia (istanza, utility);
//     il parametro numerico come testo, i vuoti come null
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'
import {
  applicaFornituraDaDefaults, schedaDaForm, schedaDaFornitura, schedaVuota,
} from './schedaFornitura'

const SCHEDA = {
  istanza_dati_precontrattuali_id: 55, classe_utenza_id: 4, tipo_utenza_id: 2,
  param_1_num: '3.500000', param_2_txt: 'B1', meta: {},
}

describe('schedaFornitura', () => {
  it('1) scheda del backend → campi del form', () => {
    expect(schedaDaFornitura(SCHEDA)).toEqual({
      utility_istanza_dati_precontrattuali_id: 55,
      utility_tipo_utenza_id: 2,
      utility_classe_utenza_id: 4,
      utility_param_1_num: 3.5,
      utility_param_2_txt: 'B1',
    })
  })

  it('2) nessuna scheda → campi vuoti', () => {
    expect(schedaDaFornitura(null)).toEqual(schedaVuota())
    expect(Object.values(schedaVuota()).every((v) => v === null)).toBe(true)
  })

  it('3) la scheda segue il cliente scelto, anche quando e\' vuota', () => {
    const form = { billing_account_id: 7, ...schedaDaFornitura(SCHEDA) }
    applicaFornituraDaDefaults({ fornitura: null }, form)
    expect(form).toEqual({ billing_account_id: 7, ...schedaVuota() })
    applicaFornituraDaDefaults({ fornitura: { ...SCHEDA, param_2_txt: 'C2' } }, form)
    expect(form.utility_param_2_txt).toBe('C2')
    expect(form.billing_account_id).toBe(7)
  })

  it('4) senza la chiave `fornitura` il form non si tocca', () => {
    const form = schedaDaFornitura(SCHEDA)
    applicaFornituraDaDefaults({ valuta_id: 1 }, form)
    expect(form).toEqual(schedaDaFornitura(SCHEDA))
  })

  it('5) verso il backend: la scheda, senza la coppia', () => {
    const form = {
      istanza_utility_id: 20, utility_id: 3,
      ...schedaDaFornitura(SCHEDA), utility_param_2_txt: '',
    }
    expect(schedaDaForm(form)).toEqual({
      istanza_dati_precontrattuali_id: 55,
      tipo_utenza_id: 2,
      classe_utenza_id: 4,
      param_1_num: '3.5',
      param_2_txt: null,
    })
    expect(schedaDaForm({ ...form, utility_param_1_num: 0 }).param_1_num).toBe('0')
  })
})
