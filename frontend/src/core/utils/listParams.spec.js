// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: presidio di `core/utils/listParams` — `paramsOrdinamento`
//        (2026-09-18, estratto alla dodicesima copia) e `paramsPagina` (dal 2026-10-21 `paramsFinestra`), che
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
//  6. paramsFinestra porta limit/offset e ordinamento nella stessa forma
//  7. paramsFinestra: order_by assente => nessuna chiave di ordinamento;
//     limit/offset non validi => il ripiego, mai uno 0 o un negativo
//  8. paramsRicerca: vuoto o sotto soglia non manda niente, sopra manda trimmato
//  9. paramsRicerca: la soglia e' un parametro (liste da un carattere)
// 10. termineCorto: vuoto NON e' corto (sono due stati diversi)
// 11. la soglia di default e' `RICERCA.MIN_CARATTERI`, non un numero sul posto
// 12. soglia `null` (configurazione non ancora arrivata) = soglia di progetto
import { describe, expect, it } from 'vitest'
import { RICERCA } from '../constants'
import { paramsOrdinamento, paramsFinestra, paramsRicerca, termineCorto } from './listParams'

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

describe('paramsFinestra', () => {
  it('porta limit/offset e ordinamento nella stessa forma di paramsOrdinamento', () => {
    expect(paramsFinestra({ limit: 25, offset: 50, order_by: 'codice', order_dir: null }))
      .toEqual({ limit: 25, offset: 50, order_by: 'codice', order_dir: 'desc' })
    expect(paramsFinestra(
      { limit: 10, offset: 0, order_by: 'codice' }, { orderDirDefault: 'asc' },
    )).toEqual({ limit: 10, offset: 0, order_by: 'codice', order_dir: 'asc' })
  })

  it('senza order_by non ha nessuna chiave di ordinamento', () => {
    const p = paramsFinestra({ limit: 25, offset: 0, order_by: null, order_dir: 'desc' })
    expect(p).toEqual({ limit: 25, offset: 0 })
  })

  // ⛔ Un dialetto solo (2026-10-21): `page`/`page_size` il backend li rifiuta.
  it('non manda mai page/page_size, e ripiega su limit/offset non validi', () => {
    const p = paramsFinestra({ limit: 0, offset: -5 }, { limitDefault: 20 })
    expect(p).toEqual({ limit: 20, offset: 0 })
    expect(p).not.toHaveProperty('page')
    expect(p).not.toHaveProperty('page_size')
  })
})

// ⭐ La ricerca libera (2026-09-24, regola del 2): la stessa riga `trim` +
//    `>= 3` viveva in sei store. Ogni ramo che le copie scrivevano sta qui.
describe('paramsRicerca e termineCorto', () => {
  it('vuoto o sotto soglia non manda niente, sopra manda il termine trimmato', () => {
    expect(paramsRicerca({ search: '' })).toEqual({})
    expect(paramsRicerca({ search: null })).toEqual({})
    expect(paramsRicerca({})).toEqual({})
    expect(paramsRicerca({ search: '   ' })).toEqual({})
    expect(paramsRicerca({ search: ' ab ' })).toEqual({})
    expect(paramsRicerca({ search: '  abc  ' })).toEqual({ search: 'abc' })
  })

  it('la soglia e un parametro', () => {
    expect(paramsRicerca({ search: 'K' }, { minCaratteri: 1 })).toEqual({ search: 'K' })
    expect(paramsRicerca({ search: ' ' }, { minCaratteri: 1 })).toEqual({})
  })

  it('termineCorto: vuoto non e corto, sotto soglia si, a soglia no', () => {
    expect(termineCorto('')).toBe(false)
    expect(termineCorto('ab')).toBe(true)
    expect(termineCorto('abc')).toBe(false)
    expect(termineCorto('a', { minCaratteri: 1 })).toBe(false)
  })

  it('la soglia di default e RICERCA.MIN_CARATTERI', () => {
    const giusto = 'x'.repeat(RICERCA.MIN_CARATTERI)
    expect(paramsRicerca({ search: giusto })).toEqual({ search: giusto })
    expect(paramsRicerca({ search: giusto.slice(1) })).toEqual({})
  })

  // ⚠️ Lo store tiene `null` finche' la configurazione non arriva: un default
  //    di parametro non scatterebbe, e `length < null` non e' mai vero —
  //    ogni lettera partirebbe.
  it('soglia null = soglia di progetto', () => {
    const corto = 'x'.repeat(RICERCA.MIN_CARATTERI - 1)
    expect(paramsRicerca({ search: corto }, { minCaratteri: null })).toEqual({})
    expect(termineCorto(corto, { minCaratteri: null })).toBe(true)
  })
})
