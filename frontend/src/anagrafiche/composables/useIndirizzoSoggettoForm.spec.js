// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa la CHIAVE D'INGRESSO del tipo nel payload degli indirizzi
//        (`toPayloadArray`, il solo punto da cui i drawer soggetto, cliente,
//        fornitore e indirizzi inviano): `tipo_indirizzo_codice_interno`, nelle
//        due forme. Dal 2026-11-01 (regola C del naming) le madri del DB
//        rifiutano la vecchia `tipo_indirizzo_codice` con E_CAMPO_NON_AMMESSO,
//        senza alias: un form che la mandasse non creerebbe piu' nessun indirizzo.
// Note: si mockano i lookup: qui si prova il payload, non l'API.
// ------------------------------------------------------------

import { describe, it, expect, vi } from 'vitest'

vi.mock('../../core/composables/useLookup', async () => {
  const { ref } = await import('vue')
  return {
    useLookup: () => ({ items: ref([]), loading: ref(false), loaded: ref(true), load: async () => {} }),
  }
})

vi.mock('../api/anagrafiche', () => ({
  lookupStati: vi.fn(),
  lookupCodiciPostaliByComune: async () => ({ data: { data: { results: [] } } }),
}))

vi.mock('../../core/apiCore', () => ({
  lookupMatriceIndirizzi: vi.fn(),
  lookupMatriceIndirizziRuolo: vi.fn(),
}))

const { useIndirizzoSoggettoForm } = await import('./useIndirizzoSoggettoForm')

const MATRICE = [
  { codice: 'RES', descrizione: 'Residenza', obbligatorio: true },
  { codice: 'FATT', descrizione: 'Fatturazione', obbligatorio: false },
]

describe('useIndirizzoSoggettoForm — chiave d\'ingresso del tipo', () => {
  it('ogni indirizzo inviato porta `tipo_indirizzo_codice_interno`, mai la chiave vecchia', () => {
    const s = useIndirizzoSoggettoForm()
    s.setMatrice(MATRICE)
    // RES con la via del catalogo (forma normalizzata).
    s.form.comune_id = 10
    s.switchTipo('FATT')
    // FATT in forma libera.
    s.form._isLibera = true
    s.form.indirizzo_libero = 'Hauptstrasse 5'
    s.form.stato_id = 2

    const payload = s.toPayloadArray()

    expect(payload.map((p) => p.tipo_indirizzo_codice_interno)).toEqual(['RES', 'FATT'])
    for (const p of payload) expect(p).not.toHaveProperty('tipo_indirizzo_codice')
  })
})
