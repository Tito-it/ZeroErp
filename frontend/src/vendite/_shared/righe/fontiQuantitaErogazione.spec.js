// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: la matrice erogazione × fonte del BB resta lo specchio del DB:
//        nessuna combinazione vietata dal CHECK in tendina, ogni erogazione
//        del vocabolario con le sue fonti, e il default del trigger.
// Note: le combinazioni vietate e i default sono ricopiati qui DI PROPOSITO,
//        dalla definizione dei CHECK `chk_contrighe_coerenza_fonte_erogazione`
//        / `chk_offerte_eccezioni_coerenza_fonte_erogazione` e dal corpo di
//        `script.trgfn_righe_default_fonte_qta` (2026-10-04): e' il termine
//        di confronto, non una seconda sede.
//
// Indice test:
//  1. ogni erogazione del vocabolario ha le sue fonti
//  2. nessuna combinazione vietata dal CHECK
//  3. il default e' quello del trigger, uno solo per erogazione
//  4. erogazione assente o sconosciuta: nessuna fonte, nessun default
// ------------------------------------------------------------
import { describe, it, expect } from 'vitest'
import { FONTE_QUANTITA_ATTESA as F, TIPO_EROGAZIONE as E } from '../../constants'
import {
  FONTI_PER_TIPO_EROGAZIONE, fontiPerErogazione, fonteDefaultPerErogazione,
} from './fontiQuantitaErogazione'

const VIETATE = {
  [E.CANONE]: [F.TIMESHEET, F.LETTURE],
  [E.UNA_TANTUM]: [F.TIMESHEET, F.LETTURE],
  [E.ORARIO]: [F.LETTURE],
  [E.CONSUMO]: [F.FISSA, F.TIMESHEET],
}

const DEFAULT_DEL_TRIGGER = {
  [E.CANONE]: F.FISSA,
  [E.UNA_TANTUM]: F.FISSA,
  [E.ORARIO]: F.MANUALE,
  [E.CONSUMO]: F.LETTURE,
}

describe('fontiQuantitaErogazione', () => {
  it('ogni erogazione del vocabolario ha le sue fonti', () => {
    expect(Object.keys(FONTI_PER_TIPO_EROGAZIONE).sort()).toEqual(Object.values(E).sort())
    for (const tipo of Object.values(E)) {
      expect(fontiPerErogazione(tipo).length).toBeGreaterThan(0)
    }
  })

  it('nessuna combinazione vietata dal CHECK', () => {
    for (const tipo of Object.values(E)) {
      const offerte = fontiPerErogazione(tipo).map((f) => f.value)
      expect(offerte.filter((v) => VIETATE[tipo].includes(v))).toEqual([])
      expect(offerte.every((v) => Object.values(F).includes(v))).toBe(true)
    }
  })

  it("il default e' quello del trigger, uno solo per erogazione", () => {
    for (const tipo of Object.values(E)) {
      expect(fontiPerErogazione(tipo).filter((f) => f.default)).toHaveLength(1)
      expect(fonteDefaultPerErogazione(tipo)).toBe(DEFAULT_DEL_TRIGGER[tipo])
    }
  })

  it('erogazione assente o sconosciuta: nessuna fonte, nessun default', () => {
    for (const tipo of [null, undefined, '', 'MISTERO']) {
      expect(fontiPerErogazione(tipo)).toEqual([])
      expect(fonteDefaultPerErogazione(tipo)).toBeNull()
    }
  })
})
