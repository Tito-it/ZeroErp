// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il form del conto bancario dopo il giro T8a di
//        brief-db-revisione-anagrafiche (2026-11-27): niente copia della
//        forma dell'IBAN, e il PATCH del legame senza i campi che il DB blocca,
//        letti dalla riga (`non_editable_fields`), non scritti qui.
// ------------------------------------------------------------
import { describe, it, expect } from 'vitest'
import { useContoBancarioForm } from './useContoBancarioForm'

const RIGA = {
  id: 10,
  conto_bancario_id: 5,
  iban: 'IT60X0542811101000000123456',
  bank_branch_id: 3,
  uso: 'INCASSO',
  predefinito: true,
  bloccato: false,
  verificato: false,
  valido_dal: '2026-11-01',
  valido_al: null,
  non_editable_fields: ['conto_bancario_id', 'soggetto_id', 'uso'],
}

describe('useContoBancarioForm', () => {
  it("l'IBAN scritto a gruppi non e' un errore a video: il formato lo giudica il DB", () => {
    const conto = useContoBancarioForm()
    conto.reset('Rossi')
    conto.form.iban = 'it60-x054 2811 1010 0000 0123 456'
    conto.form.bank_branch_id = 3
    expect(conto.validate()).toEqual([])
    expect(conto.toCreatePayload().iban).toBe('it60-x054 2811 1010 0000 0123 456')
  })

  it("l'IBAN vuoto resta un campo obbligatorio", () => {
    const conto = useContoBancarioForm()
    conto.reset()
    conto.form.bank_branch_id = 3
    expect(conto.validate()).toEqual(['iban'])
  })

  it('in modifica i campi fermi della riga escono dal PATCH', () => {
    const conto = useContoBancarioForm()
    conto.populate(RIGA)
    expect(conto.fermo('uso')).toBe(true)
    expect(conto.fermo('predefinito')).toBe(false)
    const patch = conto.toUpdatePayload()
    expect(patch).not.toHaveProperty('uso')
    expect(patch.predefinito).toBe(true)
  })

  it('una riga senza campi fermi manda anche l\'uso', () => {
    const conto = useContoBancarioForm()
    conto.populate({ ...RIGA, non_editable_fields: [] })
    expect(conto.toUpdatePayload().uso).toBe('INCASSO')
  })

  it('in creazione niente e\' fermo, anche dopo una modifica', () => {
    const conto = useContoBancarioForm()
    conto.populate(RIGA)
    conto.reset()
    expect(conto.fermo('uso')).toBe(false)
  })
})
