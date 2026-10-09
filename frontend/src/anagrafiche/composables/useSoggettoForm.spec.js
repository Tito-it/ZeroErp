// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il contratto del sesso in `useSoggettoForm`
//        (brief-db-sesso-senza-default §6.3, 2026-10-09): QUANDO serve lo dice
//        `sesso_policy` del tipo scelto; il form PROPONE «M» solo per un
//        privato (REQUIRED) e solo in creazione, e ritira la proposta se il
//        tipo cambia. Per la ditta individuale (OPTIONAL) il valore di partenza
//        e' il vuoto; per societa' ed enti (NONE) il sesso non c'e'.
// Note: si mocka il lookup dei tipi: qui si prova il form, non l'API.
// ------------------------------------------------------------

import { describe, it, expect, vi } from 'vitest'

vi.mock('../../core/composables/useLookup', async () => {
  const { ref } = await import('vue')
  const tipi = [
    { id: 1, codice_interno: 'PR', natura_soggetto: 'PF', sesso_policy: 'REQUIRED' },
    { id: 2, codice_interno: 'DI', natura_soggetto: 'PF', sesso_policy: 'OPTIONAL' },
    { id: 4, codice_interno: 'SP', natura_soggetto: 'PG', sesso_policy: 'NONE' },
  ]
  return {
    useLookup: () => ({ items: ref(tipi), loading: ref(false), loaded: ref(true), load: async () => {} }),
  }
})

vi.mock('../../core/apiCore', () => ({
  lookupTipiSoggettoDettaglio: vi.fn(),
  lookupMatriceIndirizzi: async () => ({ data: { data: { results: [] } } }),
}))

const { useSoggettoForm } = await import('./useSoggettoForm')

const PR = 1
const DI = 2
const SP = 4

describe('useSoggettoForm — sesso dalla policy della natura', () => {
  it('nasce senza sesso: nessun default', () => {
    const { form } = useSoggettoForm()
    expect(form.sesso).toBe('')
  })

  it('privato in creazione: propone «M», a video, ed e\' obbligatorio', () => {
    const s = useSoggettoForm()
    s.form.tipo_soggetto_dettaglio_id = PR
    expect(s.form.sesso).toBe('M')
    expect([s.showSesso.value, s.requireSesso.value]).toEqual([true, true])
  })

  it('privato in modifica: non propone, e il vuoto blocca il salvataggio', () => {
    const s = useSoggettoForm({ proponiSesso: () => false })
    Object.assign(s.form, { tipo_soggetto_dettaglio_id: PR, cognome: 'Rossi', nome: 'Mario', codice_fiscale: 'X' })
    expect(s.form.sesso).toBe('')
    expect(s.validate()).toContain('sesso')
  })

  it('ditta individuale: nessuna proposta, il vuoto e\' ammesso', () => {
    const s = useSoggettoForm()
    Object.assign(s.form, { tipo_soggetto_dettaglio_id: DI, cognome: 'Rossi', nome: 'Mario', codice_fiscale: 'X' })
    expect(s.form.sesso).toBe('')
    expect([s.showSesso.value, s.requireSesso.value]).toEqual([true, false])
    expect(s.validate()).not.toContain('sesso')
  })

  it('da privato a ditta individuale: la proposta si ritira, una scelta resta', () => {
    const s = useSoggettoForm()
    s.form.tipo_soggetto_dettaglio_id = PR
    s.form.tipo_soggetto_dettaglio_id = DI
    expect(s.form.sesso).toBe('')

    s.form.tipo_soggetto_dettaglio_id = PR
    s.form.sesso = 'F'
    s.form.tipo_soggetto_dettaglio_id = DI
    expect(s.form.sesso).toBe('F')
  })

  it('societa\': il campo non c\'e\' e un sesso scelto prima si toglie', () => {
    const s = useSoggettoForm()
    s.form.tipo_soggetto_dettaglio_id = PR
    s.form.sesso = 'F'
    s.form.tipo_soggetto_dettaglio_id = SP
    expect(s.form.sesso).toBe('')
    expect(s.showSesso.value).toBe(false)
  })

  it('tipo forzato con il lookup gia\' caricato: la proposta arriva subito', () => {
    expect(useSoggettoForm({ tipoForzato: PR }).form.sesso).toBe('M')
    expect(useSoggettoForm({ tipoForzato: PR, proponiSesso: () => false }).form.sesso).toBe('')
  })

  it('reset e stesso tipo di default: la proposta torna', () => {
    const s = useSoggettoForm()
    s.form.tipo_soggetto_dettaglio_id = PR
    s.reset()
    s.form.tipo_soggetto_dettaglio_id = PR
    expect(s.form.sesso).toBe('M')
  })
})
