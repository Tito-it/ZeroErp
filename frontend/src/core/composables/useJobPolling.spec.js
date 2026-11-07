// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: `seguiLavori` di useJobPolling — i lavori di UN gesto (uno per
//        azienda, BE10 a 2026-11-07) divisi in seguiti / gia' seguiti / non
//        seguiti, perche' il chiamante marchi solo le righe dei giri di cui
//        arrivera' un esito.
import { describe, expect, it, vi } from 'vitest'
import { useJobPolling } from './useJobPolling'

// Fuori da un componente gli hook di ciclo di vita avvisano e basta.
vi.spyOn(console, 'warn').mockImplementation(() => {})

function polling(maxConcurrent) {
  return useJobPolling({ fetchStatus: () => new Promise(() => {}), maxConcurrent })
}

describe('useJobPolling.seguiLavori', () => {
  it('segue ogni lavoro e passa a ciascuno il suo contesto', () => {
    const p = polling(Infinity)
    const contestoDi = vi.fn((l) => ({ jobId: l.job_id }))
    const esito = p.seguiLavori([{ job_id: 1 }, { job_id: 2 }], contestoDi)
    expect(esito.seguiti.map((l) => l.job_id)).toEqual([1, 2])
    expect(esito.giaSeguiti).toEqual([])
    expect(esito.nonSeguiti).toEqual([])
    expect(contestoDi).toHaveBeenCalledTimes(2)
    expect(p.nJobsInCorso.value).toBe(2)
    p.stop()
  })

  it('un lavoro gia\' seguito (dedup del BE) non si segue due volte', () => {
    const p = polling(Infinity)
    p.seguiLavori([{ job_id: 1 }])
    const esito = p.seguiLavori([{ job_id: 1 }, { job_id: 3 }])
    expect(esito.giaSeguiti.map((l) => l.job_id)).toEqual([1])
    expect(esito.seguiti.map((l) => l.job_id)).toEqual([3])
    expect(p.nJobsInCorso.value).toBe(2)
    p.stop()
  })

  it('oltre il tetto il lavoro e\' «non seguito», mai sostituito', () => {
    const p = polling(1)
    const esito = p.seguiLavori([{ job_id: 1 }, { job_id: 2 }])
    expect(esito.seguiti.map((l) => l.job_id)).toEqual([1])
    expect(esito.nonSeguiti.map((l) => l.job_id)).toEqual([2])
    p.stop()
  })

  it('una risposta senza lavori e\' tre liste vuote', () => {
    const p = polling(Infinity)
    expect(p.seguiLavori(undefined)).toEqual({ seguiti: [], giaSeguiti: [], nonSeguiti: [] })
  })
})
