// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: il BB delle liste in drawer (`useListaDrawerPaginata`): la misura di
//        partenza, pagina e ordinamento, il preset applicato una volta sola, e
//        l'errore della fetch mostrato invece che perso.
// Note: nasce il 2026-09-30 col quarto consumatore (`CommessaGestioneDrawer`):
//       fino a quel giorno il BB non aveva uno spec, e le fetch che parte da
//       solo (pagina, ordinamento, preset) finivano in una promise rifiutata
//       che nessuno guardava.
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'

const notifiche = { error: vi.fn() }
vi.mock('./useNotify', () => ({ useNotify: () => notifiche }))
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: (k) => k }) }))

import { registraMisurePagina } from '../misurePagina'
import { useListaDrawerPaginata } from './useListaDrawerPaginata'

const risposta = (results, count) => ({ data: { data: { results, count } } })

describe('useListaDrawerPaginata', () => {
  beforeEach(() => {
    notifiche.error.mockReset()
    registraMisurePagina({ misure: [10, 25, 50, 100], default_compatta: 10, default_pagina: 25 })
  })

  it('parte dalla misura COMPATTA del catalogo e legge l\'envelope lista', async () => {
    const fetcher = vi.fn().mockResolvedValue(risposta([{ id: 1 }], 7))
    const l = useListaDrawerPaginata(fetcher)
    await l.carica()
    expect(fetcher).toHaveBeenCalledWith({ limit: 10, offset: 0, sortBy: null, sortDir: 'asc' })
    expect(l.righe.value).toEqual([{ id: 1 }])
    expect(l.totale.value).toBe(7)
    expect(l.paginatorOptions.value.rowsPerPageOptions).toEqual([10, 25, 50, 100])
  })

  it('ordinare riporta a pagina 1 e traduce il verso', async () => {
    const fetcher = vi.fn().mockResolvedValue(risposta([], 0))
    const l = useListaDrawerPaginata(fetcher)
    l.onPage({ first: 20, rows: 10 })
    expect(l.page.value).toBe(3)
    // ⭐ Il fetcher riceve la FINESTRA (2026-10-21, un dialetto solo).
    expect(fetcher).toHaveBeenLastCalledWith({ limit: 10, offset: 20, sortBy: null, sortDir: 'asc' })
    l.onSort({ sortField: 'data', sortOrder: -1 })
    expect(l.page.value).toBe(1)
    expect(fetcher).toHaveBeenLastCalledWith({ limit: 10, offset: 0, sortBy: 'data', sortDir: 'desc' })
  })

  it('il preset della lista si applica una volta, e di nuovo solo dopo reset', () => {
    const fetcher = vi.fn().mockResolvedValue(risposta([], 0))
    const l = useListaDrawerPaginata(fetcher)
    l.onConfigLoaded({ pagina_dimensione: 25 })
    expect(l.pageSize.value).toBe(25)
    l.onPage({ first: 0, rows: 50 })
    l.onConfigLoaded({ pagina_dimensione: 25 })
    expect(l.pageSize.value).toBe(50)
    l.reset()
    l.onConfigLoaded({ pagina_dimensione: 25 })
    expect(l.pageSize.value).toBe(25)
  })

  // ⭐ Fail-visible: un errore lo si vede, e le righe di prima restano.
  it('un errore della fetch si mostra, non rilancia e lascia le righe', async () => {
    const fetcher = vi.fn()
      .mockResolvedValueOnce(risposta([{ id: 1 }], 1))
      .mockRejectedValueOnce(new Error('rete'))
    const l = useListaDrawerPaginata(fetcher)
    await l.carica()
    await expect(l.carica()).resolves.toBeUndefined()
    expect(notifiche.error).toHaveBeenCalledTimes(1)
    expect(l.righe.value).toEqual([{ id: 1 }])
    expect(l.loading.value).toBe(false)
  })
})
