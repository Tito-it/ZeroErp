// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Un caso per RAMO di `esitoCorsa` (2026-11-22): le cinque facce, la
//        corsa assente, e i due ordini che un `if` spostato rompe in
//        silenzio — una saltata con `ok` scritto resta saltata, una corsa
//        aperta con l'esito gia' scritto mostra l'esito.
// Note: ⛔ Si asseriscono esito, CHIAVE e SEVERITY: e' cio' che un ramo
//        sbagliato scambia senza che niente fallisca (un `null` reso rosso).
// ------------------------------------------------------------
import { describe, it, expect } from 'vitest'
import { ESITO_CORSA, esitoCorsa } from './esitoCorsa'

const faccia = (corsa) => {
  const f = esitoCorsa(corsa)
  return f && [f.esito, f.chiave, f.severity]
}

describe('esitoCorsa', () => {
  it('nessuna corsa: null, la resa del vuoto e\' di chi chiama', () => {
    expect(esitoCorsa(null)).toBeNull()
    expect(esitoCorsa(undefined)).toBeNull()
  })

  it('riuscita e fallita', () => {
    expect(faccia({ ok: true, ended_at: 'x' })).toEqual([ESITO_CORSA.OK, 'common.corsa.ok', 'success'])
    expect(faccia({ ok: false, ended_at: 'x' })).toEqual([ESITO_CORSA.ERRORE, 'common.corsa.errore', 'danger'])
  })

  it('ok nullo: aperta e\' «in corso», chiusa e\' «esito non scritto», mai rossa', () => {
    expect(faccia({ ok: null, ended_at: null })).toEqual([ESITO_CORSA.IN_CORSO, 'common.corsa.in_corso', 'secondary'])
    expect(faccia({ ok: null, ended_at: 'x' })).toEqual([ESITO_CORSA.NON_SCRITTO, 'common.corsa.non_scritto', 'warn'])
  })

  it('saltata: prima di ogni esito, col tooltip che spiega il lock', () => {
    expect(esitoCorsa({ saltata: true, ok: true, ended_at: 'x' })).toEqual({
      esito: ESITO_CORSA.SALTATA, chiave: 'common.corsa.saltata', severity: 'secondary',
      tooltip: 'common.corsa.saltata_tooltip',
    })
  })

  it('l\'esito scritto vince su una corsa senza fine', () => {
    expect(faccia({ ok: false, ended_at: null })[0]).toBe(ESITO_CORSA.ERRORE)
  })

  it('l\'ultima conclusa (forma di `corsa_conclusa`, senza `saltata`)', () => {
    expect(faccia({ started_at: 's', ended_at: 'e', ok: null })[0]).toBe(ESITO_CORSA.NON_SCRITTO)
  })
})
