// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: il BB delle misure «righe per pagina» (`core/misurePagina`).
//        Ogni test importa un modulo FRESCO (`vi.resetModules`): quello del
//        setup di Vitest ha gia' le misure registrate, e qui si prova anche
//        cio' che succede PRIMA del caricamento.
//
// Indice test:
//   1. letta prima del caricamento solleva, non ripiega
//   2. dopo la registrazione: opzioni in ordine, default per uso
//   3. uso sconosciuto solleva
//   4. risposta malformata rifiutata (default fuori elenco, elenco vuoto,
//      misure non strettamente crescenti)
//   5. carica: una richiesta sola anche con chiamate concorrenti
//   6. carica fallita: non resta in memoria, la successiva riprova
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'

const getMisurePagina = vi.fn()
vi.mock('./api/ui-api', () => ({ getMisurePagina }))

const RISPOSTA = { misure: [10, 25, 50, 100], default_compatta: 10, default_pagina: 25 }

async function moduloFresco() {
  vi.resetModules()
  return import('./misurePagina')
}

describe('misurePagina', () => {
  beforeEach(() => {
    getMisurePagina.mockReset()
  })

  it('1. letta prima del caricamento solleva, non ripiega', async () => {
    const m = await moduloFresco()
    expect(() => m.misureOpzioni()).toThrow(/prima del caricamento/)
    expect(() => m.misuraDefault(m.USO_MISURA.PAGINA)).toThrow(/prima del caricamento/)
  })

  it('2. dopo la registrazione: opzioni in ordine, default per uso', async () => {
    const m = await moduloFresco()
    m.registraMisurePagina(RISPOSTA)
    expect(m.misureOpzioni()).toEqual([10, 25, 50, 100])
    expect(m.misuraDefault(m.USO_MISURA.COMPATTA)).toBe(10)
    expect(m.misuraDefault(m.USO_MISURA.PAGINA)).toBe(25)
    expect(m.misuraDefault()).toBe(25)
  })

  it('3. uso sconosciuto solleva', async () => {
    const m = await moduloFresco()
    m.registraMisurePagina(RISPOSTA)
    expect(() => m.misuraDefault('LARGA')).toThrow(/uso sconosciuto/)
  })

  it('4. risposta malformata rifiutata', async () => {
    const m = await moduloFresco()
    expect(() => m.registraMisurePagina({ ...RISPOSTA, default_pagina: 15 })).toThrow(/non valida/)
    expect(() => m.registraMisurePagina({ ...RISPOSTA, misure: [] })).toThrow(/non valida/)
    expect(() => m.registraMisurePagina(undefined)).toThrow(/non valida/)
    // L'ordine e' quello del selettore: fuori ordine o doppia si rifiuta.
    expect(() => m.registraMisurePagina({ ...RISPOSTA, misure: [25, 10, 50, 100] })).toThrow(/non valida/)
    expect(() => m.registraMisurePagina({ ...RISPOSTA, misure: [10, 25, 25, 100] })).toThrow(/non valida/)
    expect(() => m.misureOpzioni()).toThrow(/prima del caricamento/)
  })

  it('5. carica: una richiesta sola anche con chiamate concorrenti', async () => {
    const m = await moduloFresco()
    getMisurePagina.mockResolvedValue({ data: { data: RISPOSTA } })
    await Promise.all([m.caricaMisurePagina(), m.caricaMisurePagina()])
    await m.caricaMisurePagina()
    expect(getMisurePagina).toHaveBeenCalledTimes(1)
    expect(m.misuraDefault(m.USO_MISURA.COMPATTA)).toBe(10)
  })

  it('6. carica fallita: non resta in memoria, la successiva riprova', async () => {
    const m = await moduloFresco()
    getMisurePagina.mockRejectedValueOnce(new Error('rete'))
    await expect(m.caricaMisurePagina()).rejects.toThrow('rete')
    getMisurePagina.mockResolvedValueOnce({ data: { data: RISPOSTA } })
    await m.caricaMisurePagina()
    expect(getMisurePagina).toHaveBeenCalledTimes(2)
    expect(m.misureOpzioni()).toEqual([10, 25, 50, 100])
  })
})
