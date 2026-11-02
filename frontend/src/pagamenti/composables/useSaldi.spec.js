// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il contratto di `useSaldi` sul «prima di se'» (D19-b,
//        2026-09-17): `escludiRigaId` arriva ai lettori di RATA e — dal
//        2026-09-18, P-6 — di DOCUMENTO come `escludi_riga_id`, e un livello
//        che non lo sa fare lo DICHIARA (`esclusioneSupportata`), invece di
//        lasciar credere che il saldo escluda una riga che il database ha
//        contato. Fino al 18/09 il documento era quel livello.
// Note: si mockano il client API e `useApiHandler`: qui si prova la base dei
//        saldi, non l'envelope.
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'

const chiamate = { rata: [], fattura: [] }

vi.mock('../api/pagamenti', () => ({
  getSaldoRata: async (id, opzioni) => {
    chiamate.rata.push({ id, opzioni })
    return { data: { data: { livello: 'RATA', riferimento_id: id, residuo: '1', has_movimenti: true } } }
  },
  getSaldoFattura: async (id, opzioni) => {
    chiamate.fattura.push({ id, opzioni })
    return { data: { data: { livello: 'DOCUMENTO', riferimento_id: id, residuo: '2', has_movimenti: false } } }
  },
}))

vi.mock('../../core/composables/useApiHandler', () => ({
  useApiHandler: () => ({
    execute: async (chiamata) => {
      try {
        const r = await chiamata()
        return r.data.data
      } catch {
        return null
      }
    },
    loading: { value: false },
  }),
}))

const { LIVELLO, spazioSaldo, useSaldi } = await import('./useSaldi')

beforeEach(() => {
  chiamate.rata.length = 0
  chiamate.fattura.length = 0
})

describe('useSaldi — «prima di se\'»', () => {
  it('sulla RATA `escludiRigaId` arriva al lettore, e il livello lo dichiara', async () => {
    const { leggi, esclusioneSupportata, saldo } = useSaldi(LIVELLO.RATA)
    expect(esclusioneSupportata).toBe(true)
    await leggi(1301, { escludiRigaId: 91 })
    expect(chiamate.rata).toEqual([{ id: 1301, opzioni: { escludiRigaId: 91 } }])
    expect(saldo.value.riferimento_id).toBe(1301)
  })

  // ⭐ P-6 (2026-09-18): il documento ha imparato il parametro. Fino a quel
  //    giorno questo test asseriva il contrario — `opzioni: undefined` — ed era
  //    la cosa giusta: un `escludi_riga_id` ignorato dal server sarebbe
  //    sembrato applicato.
  it('sul DOCUMENTO arriva come sulla rata, e il livello lo dichiara', async () => {
    const { leggi, esclusioneSupportata, saldo } = useSaldi(LIVELLO.DOCUMENTO)
    expect(esclusioneSupportata).toBe(true)
    await leggi(820, { escludiRigaId: 91 })
    expect(chiamate.fattura).toEqual([{ id: 820, opzioni: { escludiRigaId: 91 } }])
    expect(saldo.value.riferimento_id).toBe(820)
  })

  it('senza opzione il lettore riceve opzioni vuote, non `undefined`', async () => {
    const { leggi } = useSaldi(LIVELLO.RATA)
    await leggi(1301)
    expect(chiamate.rata).toEqual([{ id: 1301, opzioni: {} }])
  })

  it('un riferimento nullo azzera e non chiama nessuno', async () => {
    const { leggi, caricato } = useSaldi(LIVELLO.RATA)
    const esito = await leggi(null, { escludiRigaId: 91 })
    expect(esito).toBeNull()
    expect(caricato.value).toBe(false)
    expect(chiamate.rata).toEqual([])
  })

  it('il livello CLIENTE e\' dichiarato e non ancora leggibile', async () => {
    const { livelloSupportato, esclusioneSupportata, leggi } = useSaldi(LIVELLO.CLIENTE)
    expect(livelloSupportato).toBe(false)
    expect(esclusioneSupportata).toBe(false)
    expect(await leggi(1)).toBeNull()
  })
})

// ⭐ Lo SPAZIO (Q-B, Tid 2026-09-17): residuo − in lavorazione, calcolato in
//    una sede sola. E' l'importo proposto e il predicato «selezionabile».
describe('spazioSaldo — residuo meno in lavorazione', () => {
  it('sottrae cio\' che e\' gia\' digitato e non registrato', () => {
    expect(spazioSaldo({ residuo: '400.00', in_lavorazione: '150.00' })).toBe(250)
  })

  it('tiene il SEGNO: su una nota di credito lo spazio e\' negativo, non zero', () => {
    expect(spazioSaldo({ residuo: '-20.00', in_lavorazione: '0.00' })).toBe(-20)
  })

  // 🔴 Il caso che il guard rifiutava: in virgola mobile `100.30 − 100.00` non
  //    e' `0.30`, e l'importo proposto usciva con quattordici decimali.
  it('sottrae in centesimi: nessun residuo di virgola mobile sull\'importo proposto', () => {
    expect(spazioSaldo({ residuo: '100.30', in_lavorazione: '100.00' })).toBe(0.3)
    expect(spazioSaldo({ residuo: '0.30', in_lavorazione: '0.10' })).toBe(0.2)
    expect(spazioSaldo({ residuo: '400.10', in_lavorazione: '400.10' })).toBe(0)
  })

  it('e\' null se manca uno dei due numeri: «non so» non e\' zero', () => {
    expect(spazioSaldo({ residuo: '400.00' })).toBeNull()
    expect(spazioSaldo({ residuo: null, in_lavorazione: '1' })).toBeNull()
    expect(spazioSaldo(null)).toBeNull()
  })
})
