// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Test di `descriviDovuto`: ogni `ogni` ha la sua chiave e i suoi
//        valori, e le chiavi esistono nei locales veri (it, en).
//
// Indice test:
//  1. giorno, settimana (col nome del giorno) e mese
//  2. le tre chiavi esistono in it.json e en.json
// ------------------------------------------------------------
import { describe, it, expect } from 'vitest'
import { descriviDovuto } from './dovutoSveglia'
import it_ from '../locales/it.json'
import en from '../locales/en.json'

const t = (chiave, valori) => `${chiave}|${JSON.stringify(valori)}`

describe('descriviDovuto', () => {
  it('giorno, settimana (col nome del giorno) e mese', () => {
    expect(descriviDovuto({ ogni: 'giorno', giorno: null, dalle: '07:00' }, t, 'it-IT'))
      .toBe('amministrazione.processi.sveglia_dovuto_giorno|{"dalle":"07:00"}')
    expect(descriviDovuto({ ogni: 'settimana', giorno: 0, dalle: '07:30' }, t, 'it-IT'))
      .toBe('amministrazione.processi.sveglia_dovuto_settimana|{"giorno":"lunedì","dalle":"07:30"}')
    expect(descriviDovuto({ ogni: 'mese', giorno: 1, dalle: '00:00' }, t, 'it-IT'))
      .toBe('amministrazione.processi.sveglia_dovuto_mese|{"giorno":1,"dalle":"00:00"}')
  })

  it('le tre chiavi esistono in it.json e en.json', () => {
    for (const locale of [it_, en]) {
      const processi = locale.amministrazione.processi
      for (const chiave of ['sveglia_dovuto_giorno', 'sveglia_dovuto_settimana', 'sveglia_dovuto_mese']) {
        expect(processi[chiave]).toBeTruthy()
      }
    }
  })
})
