// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: presidio di `core/utils/listParams` — `paramsOrdinamento`
//        (2026-09-18, estratto alla dodicesima copia) e `paramsPagina`, che
//        da quel giorno lo consuma. I casi sono quelli che le copie avevano
//        scritto in modo diverso: il ripiego del verso, e l'assenza di
//        ordinamento che NON deve mandare niente.
//
// Indice test:
//  1. senza order_by non manda niente (nemmeno order_dir)
//  2. con order_by e order_dir li passa com'e'
//  3. il ripiego di default e' desc
//  4. il ripiego e' un parametro (asc per gli store di useListaStoreCore)
//  5. filtri assenti: oggetto vuoto, non un errore
//  6. paramsPagina porta pagina e ordinamento nella stessa forma
//  7. paramsPagina: order_by assente => nessuna chiave di ordinamento
import { describe, expect, it } from 'vitest'
import { paramsOrdinamento, paramsPagina } from './listParams'

describe('paramsOrdinamento', () => {
  it('senza order_by non manda niente, nemmeno order_dir', () => {
    // ⚠️ Un `order_dir` da solo chiederebbe al backend un ordinamento che poi
    //    lui scarta: la cosa giusta per il motivo sbagliato.
    expect(paramsOrdinamento({ order_by: null, order_dir: 'desc' })).toEqual({})
    expect(paramsOrdinamento({ order_by: '', order_dir: 'asc' })).toEqual({})
  })

  it('con order_by e order_dir li passa come sono', () => {
    expect(paramsOrdinamento({ order_by: 'importo', order_dir: 'asc' }))
      .toEqual({ order_by: 'importo', order_dir: 'asc' })
  })

  it('il ripiego di default del verso e desc', () => {
    expect(paramsOrdinamento({ order_by: 'data', order_dir: null }))
      .toEqual({ order_by: 'data', order_dir: 'desc' })
  })

  it('il ripiego e un parametro: asc per gli store di useListaStoreCore', () => {
    // ⛔ Le copie non erano identiche, e l'estrazione appiana la duplicazione,
    //    non le differenze.
    expect(paramsOrdinamento({ order_by: 'data' }, { orderDirDefault: 'asc' }))
      .toEqual({ order_by: 'data', order_dir: 'asc' })
  })

  it('filtri assenti: oggetto vuoto, non un errore', () => {
    expect(paramsOrdinamento(undefined)).toEqual({})
    expect(paramsOrdinamento(null)).toEqual({})
  })
})

describe('paramsPagina', () => {
  it('porta pagina e ordinamento nella stessa forma di paramsOrdinamento', () => {
    expect(paramsPagina({ limit: 25, offset: 50, order_by: 'codice', order_dir: null }))
      .toEqual({ page: 3, page_size: 25, order_by: 'codice', order_dir: 'desc' })
    expect(paramsPagina(
      { limit: 10, offset: 0, order_by: 'codice' }, { orderDirDefault: 'asc' },
    )).toEqual({ page: 1, page_size: 10, order_by: 'codice', order_dir: 'asc' })
  })

  it('senza order_by non ha nessuna chiave di ordinamento', () => {
    const p = paramsPagina({ limit: 25, offset: 0, order_by: null, order_dir: 'desc' })
    expect(p).toEqual({ page: 1, page_size: 25 })
  })
})
