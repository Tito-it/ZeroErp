// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa la regola di proposta del kebab della lista lotti
//        (`verbiPlausibili`): i verbi di stato vengono da `azioni_permesse`
//        della riga — i passaggi che l'operatore può fare, letti dal DB
//        (brief-modello-documento-vendita §15.14) — e non dal codice dello
//        stato. Gli esempi sono quelli del pgTAP del team DB.
// Note: dipendenze finte: qui si prova la regola, non le chiamate.
//
// Indice test:
//   1) EMESSA senza concessione: `azioni_permesse` vuoto -> nessun verbo di stato
//   2) EMESSA con concessione: numera e riporta in bozza
//   3) DRAFT: annulla accanto al verbo di pipeline
//   4) campo assente (riga vecchia) -> nessun verbo di stato (fail-closed)
//   5) chiave senza verbo nel frontend, o di pipeline -> non diventa una voce
//   6) `ristampabile`: la ristampa resta, non è un passaggio di stato
//   7) senza `ristampabile` niente ristampa, qualunque sia il codice dello stato
// ------------------------------------------------------------

import { describe, it, expect, vi } from 'vitest'

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: (k) => k, te: () => false }) }))
vi.mock('../../core/composables/useApiHandler', () => ({
  useApiHandler: () => ({ execute: vi.fn(), loading: false }),
}))
vi.mock('../../core/composables/useChiaveGesto', () => ({
  useChiaveGesto: () => ({ invia: vi.fn(), azzera: vi.fn() }),
}))
vi.mock('../../stores/auth', () => ({ useAuthStore: () => ({}) }))
vi.mock('../../core/composables/useConfirmAction', () => ({
  useConfirmAction: () => ({ confirmAction: vi.fn() }),
}))
vi.mock('../../core/composables/useNotify', () => ({ useNotify: () => ({}) }))
vi.mock('../api/lotti', () => ({}))
vi.mock('../../core/bersaglioGesto', () => ({ azioniDaBersagli: vi.fn() }))

const { useLottoAzioni } = await import('./useLottoAzioni')

// Riga di lotto non congelato, ultimo giro completato: la base di ogni caso.
function riga(campi) {
  return { stato_congela_fiscale: false, stato_lotto: 'COMPLETATO', riaperto: false, ...campi }
}

describe('useLottoAzioni.verbiPlausibili', () => {
  const { verbiPlausibili } = useLottoAzioni()

  it('1) EMESSA senza concessione: nessun verbo di stato', () => {
    expect(verbiPlausibili(riga({ stato_doc_fiscale_codice: 'EMESSA', azioni_permesse: [] })))
      .toEqual([])
  })

  it('2) EMESSA con concessione: numera e riporta in bozza', () => {
    expect(verbiPlausibili(riga({
      stato_doc_fiscale_codice: 'EMESSA', azioni_permesse: ['numera', 'riporta_a_draft'],
    }))).toEqual(['numera', 'riporta_a_draft'])
  })

  it('3) DRAFT: annulla accanto al verbo di pipeline', () => {
    expect(verbiPlausibili(riga({ stato_doc_fiscale_codice: 'DRAFT', azioni_permesse: ['annulla'] })))
      .toEqual(['avanza_step', 'annulla'])
  })

  it('4) campo assente: nessun verbo di stato (fail-closed)', () => {
    expect(verbiPlausibili(riga({ stato_doc_fiscale_codice: 'EMESSA' }))).toEqual([])
    expect(verbiPlausibili(riga({ stato_doc_fiscale_codice: 'DRAFT' }))).toEqual(['avanza_step'])
  })

  it('5) chiave sconosciuta o di pipeline: non diventa una voce', () => {
    expect(verbiPlausibili(riga({
      stato_doc_fiscale_codice: 'EMESSA', azioni_permesse: ['passaggio_nuovo', 'rilancia_step', 'numera'],
    }))).toEqual(['numera'])
  })

  it('6) ristampabile: la ristampa resta', () => {
    expect(verbiPlausibili(riga({
      stato_doc_fiscale_codice: 'DEFINITIVA', stato_congela_fiscale: true, azioni_permesse: [],
      ristampabile: true,
    }))).toEqual(['ristampa'])
  })

  // ⛔ Il codice dello stato non decide più: lo dice la riga.
  it('7) senza ristampabile niente ristampa', () => {
    expect(verbiPlausibili(riga({
      stato_doc_fiscale_codice: 'DEFINITIVA', stato_congela_fiscale: true, azioni_permesse: [],
    }))).toEqual([])
  })
})
