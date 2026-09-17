// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il contratto di `useSaldi` sul «prima di se'» (D19-b,
//        2026-09-17): `escludiRigaId` arriva al lettore della RATA come
//        `escludi_riga_id`, e sul DOCUMENTO non arriva — e il composable lo
//        DICHIARA (`esclusioneSupportata`), invece di lasciar credere che il
//        saldo escluda una riga che il database ha contato.
// Note: si mockano il client API e `useApiHandler`: qui si prova la base dei
//        saldi, non l'envelope.
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'

const chiamate = { rata: [], fattura: [] }

vi.mock('../../pagamenti/api/pagamenti', () => ({
  getSaldoRata: async (id, opzioni) => {
    chiamate.rata.push({ id, opzioni })
    return { data: { data: { livello: 'RATA', riferimento_id: id, residuo: '1', has_movimenti: true } } }
  },
  getSaldoFattura: async (id, opzioni) => {
    chiamate.fattura.push({ id, opzioni })
    return { data: { data: { livello: 'DOCUMENTO', riferimento_id: id, residuo: '2', has_movimenti: false } } }
  },
}))

vi.mock('./useApiHandler', () => ({
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

const { LIVELLO, useSaldi } = await import('./useSaldi')

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

  it('sul DOCUMENTO non arriva, e `esclusioneSupportata` e\' false', async () => {
    const { leggi, esclusioneSupportata } = useSaldi(LIVELLO.DOCUMENTO)
    expect(esclusioneSupportata).toBe(false)
    await leggi(820, { escludiRigaId: 91 })
    // Il lettore del documento non inoltra NIENTE al client: la rotta non ha
    // il parametro, e un `escludi_riga_id` ignorato dal server sembrerebbe
    // applicato.
    expect(chiamate.fattura).toEqual([{ id: 820, opzioni: undefined }])
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
