// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Un caso per RAMO di `segnoFiltri` (segno dei filtri attivi, D4 di
//        Tid 2026-09-22): niente, solo default, almeno uno modificato, piu' i
//        limiti che un `if` sbagliato attraversa in silenzio — `false` e `0`
//        come valori legittimi, la stringa vuota che NON e' un filtro, un
//        default svuotato a mano, un filtro ad array.
// Note: ⛔ Sono i rami che, sbagliati, NON falliscono: mostrano il segno
//        sbagliato. Un numero al posto del pallino toglie al segno la sua sola
//        informazione («ristretta da te» contro «ristretta come nasce»); un
//        `vuoto` di troppo e' una lista ristretta che si presenta come intera.
// ------------------------------------------------------------
import { describe, it, expect } from 'vitest'
import {
  SEGNO_DEFAULT,
  SEGNO_MODIFICATO,
  SEGNO_VUOTO,
  segnoFiltri,
} from './segnoFiltri'

const CHIAVI = ['stato_codice_interno', 'billing_account_id', 'data_da', 'data_a']
const DEFAULTS = {
  stato_codice_interno: null,
  billing_account_id: null,
  data_da: '2026-07-01',
  data_a: null,
}

describe('segnoFiltri', () => {
  it('nessun filtro con valore: niente segno — la lista non e\' ristretta', () => {
    const r = segnoFiltri({ ...DEFAULTS, data_da: null }, CHIAVI, DEFAULTS)
    expect(r).toEqual({ stato: SEGNO_VUOTO, conteggio: 0 })
  })

  it('solo i default: pallino, e il conteggio c\'e\' lo stesso', () => {
    const r = segnoFiltri({ ...DEFAULTS }, CHIAVI, DEFAULTS)
    expect(r).toEqual({ stato: SEGNO_DEFAULT, conteggio: 1 })
  })

  it('uno scelto dall\'operatore: numero, e conta ANCHE i default', () => {
    const r = segnoFiltri(
      { ...DEFAULTS, stato_codice_interno: 'BOZZA' },
      CHIAVI,
      DEFAULTS,
    )
    expect(r).toEqual({ stato: SEGNO_MODIFICATO, conteggio: 2 })
  })

  it('default svuotato a mano (deep-link che azzera le date): modificato', () => {
    const r = segnoFiltri(
      { ...DEFAULTS, data_da: null, billing_account_id: 12 },
      CHIAVI,
      DEFAULTS,
    )
    expect(r).toEqual({ stato: SEGNO_MODIFICATO, conteggio: 1 })
  })

  it('`false` e `0` sono filtri veri, non «niente»', () => {
    const chiavi = ['attivo', 'giacenza']
    const defaults = { attivo: true, giacenza: null }
    const r = segnoFiltri({ attivo: false, giacenza: 0 }, chiavi, defaults)
    expect(r).toEqual({ stato: SEGNO_MODIFICATO, conteggio: 2 })
  })

  it('stringa vuota: non e\' un filtro — non si manda e non si conta', () => {
    const r = segnoFiltri(
      { ...DEFAULTS, data_da: null, stato_codice_interno: '' },
      CHIAVI,
      DEFAULTS,
    )
    expect(r).toEqual({ stato: SEGNO_VUOTO, conteggio: 0 })
  })

  it('filtro ad ARRAY uguale al default: pallino, non numero', () => {
    const chiavi = ['stati']
    const defaults = { stati: ['BOZZA', 'EMESSO'] }
    // Stesso contenuto, altro riferimento: un `===` direbbe «modificato».
    const r = segnoFiltri({ stati: ['BOZZA', 'EMESSO'] }, chiavi, defaults)
    expect(r).toEqual({ stato: SEGNO_DEFAULT, conteggio: 1 })
  })

  it('nessuna chiave dichiarata: `vuoto`, mai un numero inventato', () => {
    expect(segnoFiltri({ pippo: 3 }, [], {})).toEqual({
      stato: SEGNO_VUOTO,
      conteggio: 0,
    })
    expect(segnoFiltri(null, null)).toEqual({ stato: SEGNO_VUOTO, conteggio: 0 })
  })
})
