// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il contratto dei quattro binder di `useStoreFilterBindings` —
//        il legame fra un widget della toolbar e `store.filters` — scritto il
//        2026-09-19 insieme ai due binder nuovi (`bindToggle`, `bindLookup`,
//        regola del 2): il file non aveva nessun presidio, e i due vecchi
//        (`bindSelect`, `bindDate`) nascono coperti nello stesso giro.
//        La disciplina comune ai quattro: `onChange` scrive lo store e
//        rilancia la fetch SOLO da un gesto utente; il `watch` va nel verso
//        opposto (store → widget), per i cambi fatti da fuori.
// Note: composable PURO (nessuna API, nessun i18n, nessun DOM): lo store e'
//       un `reactive` con `filters`, `applyFilters` un contatore. I watch
//       sono asincroni → `nextTick` dopo ogni scrittura «da fuori».
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'
import { nextTick, reactive } from 'vue'

import { useStoreFilterBindings } from './useStoreFilterBindings'

function fabbrica(filters) {
  const store = reactive({ filters })
  const chiamate = { n: 0 }
  const applyFilters = () => { chiamate.n += 1 }
  return { store, chiamate, ...useStoreFilterBindings(store, applyFilters) }
}

describe('bindSelect — il valore semplice', () => {
  it('parte dallo store, e onChange scrive lo store e rilancia', () => {
    const { store, chiamate, bindSelect } = fabbrica({ stato: 'APERTA' })
    const { value, onChange } = bindSelect('stato')
    expect(value.value).toBe('APERTA')
    value.value = 'CHIUSA'
    onChange()
    expect(store.filters.stato).toBe('CHIUSA')
    expect(chiamate.n).toBe(1)
  })

  it('un cambio FUORI dal widget si riflette nel widget senza rilanciare', async () => {
    const { store, chiamate, bindSelect } = fabbrica({ stato: 'APERTA' })
    const { value } = bindSelect('stato')
    store.filters.stato = null
    await nextTick()
    expect(value.value).toBeNull()
    expect(chiamate.n).toBe(0)
  })
})

describe('bindDate — la data ISO ↔ Date locale', () => {
  it('legge la ISO come Date locale e la riscrive come ISO', () => {
    const { store, bindDate } = fabbrica({ data_da: '2026-06-01' })
    const { value, onChange } = bindDate('data_da')
    expect(value.value).toBeInstanceOf(Date)
    expect(value.value.getDate()).toBe(1)
    expect(value.value.getMonth()).toBe(5)
    value.value = new Date(2026, 8, 19)
    onChange()
    expect(store.filters.data_da).toBe('2026-09-19')
  })

  it('svuotata con `clearTo` torna al floor, senza `clearTo` va a null', () => {
    const floor = new Date(2026, 0, 1)
    const con = fabbrica({ data_da: '2026-06-01' })
    const a = con.bindDate('data_da', { clearTo: () => floor })
    a.value.value = null
    a.onChange()
    expect(con.store.filters.data_da).toBe('2026-01-01')
    expect(a.value.value).toBe(floor)

    const senza = fabbrica({ data_a: '2026-06-01' })
    const b = senza.bindDate('data_a')
    b.value.value = null
    b.onChange()
    expect(senza.store.filters.data_a).toBeNull()
  })
})

describe('bindToggle — il booleano del widget contro i DUE valori dello store', () => {
  it('coi default scrive `true` acceso e `null` spento: mai un `false` sul filo', () => {
    const { store, chiamate, bindToggle } = fabbrica({ solo_negativa: null })
    const { value, onChange } = bindToggle('solo_negativa')
    expect(value.value).toBe(false)
    value.value = true
    onChange()
    expect(store.filters.solo_negativa).toBe(true)
    value.value = false
    onChange()
    expect(store.filters.solo_negativa).toBeNull()
    expect(chiamate.n).toBe(2)
  })

  it('`on`/`off` dichiarati coprono il filtro INVERTITO («mostra storico» ⇔ solo_ultima_revisione = false)', () => {
    const { store, bindToggle } = fabbrica({ solo_ultima_revisione: true })
    const { value, onChange } = bindToggle('solo_ultima_revisione', { on: false, off: true })
    expect(value.value).toBe(false)
    value.value = true
    onChange()
    expect(store.filters.solo_ultima_revisione).toBe(false)
    value.value = false
    onChange()
    expect(store.filters.solo_ultima_revisione).toBe(true)
  })

  it('`off: false` onora uno store che dichiara `false` come default', () => {
    const { store, bindToggle } = fabbrica({ solo_interne: false })
    const { value, onChange } = bindToggle('solo_interne', { off: false })
    value.value = true
    onChange()
    expect(store.filters.solo_interne).toBe(true)
    value.value = false
    onChange()
    expect(store.filters.solo_interne).toBe(false)
  })

  it('e\' un computed sullo store: un reset da fuori spegne il widget da se\'', () => {
    const { store, bindToggle } = fabbrica({ solo_negativa: true })
    const { value } = bindToggle('solo_negativa')
    expect(value.value).toBe(true)
    store.filters.solo_negativa = null
    expect(value.value).toBe(false)
  })
})

describe('bindLookup — il widget tiene l\'oggetto, lo store l\'id', () => {
  it('alla scelta scrive l\'id nello store e rilancia; al clear scrive null', () => {
    const { store, chiamate, bindLookup } = fabbrica({ articolo_id: null })
    const { value, onChange } = bindLookup('articolo_id')
    expect(value.value).toBeNull()
    value.value = { id: 'a1b2', codice: 'ART-1', descrizione: 'Bullone' }
    onChange()
    expect(store.filters.articolo_id).toBe('a1b2')
    value.value = null
    onChange()
    expect(store.filters.articolo_id).toBeNull()
    expect(chiamate.n).toBe(2)
  })

  it('`idField` sceglie quale campo dell\'oggetto e\' l\'id', () => {
    const { store, bindLookup } = fabbrica({ scadenza_id: null })
    const { value, onChange } = bindLookup('scadenza_id', { idField: 'scadenza_id' })
    value.value = { scadenza_id: 7, importo: 100 }
    onChange()
    expect(store.filters.scadenza_id).toBe(7)
  })

  it('lo store azzerato da fuori svuota il widget; un id NON null da fuori non lo tocca', async () => {
    const { store, chiamate, bindLookup } = fabbrica({ articolo_id: null })
    const { value, onChange } = bindLookup('articolo_id')
    value.value = { id: 'a1b2' }
    onChange()
    // ⚠️ un tick fra il gesto e il reset: due scritture nello stesso tick che
    //    si annullano (a1b2 → null) sono invisibili al watch, che confronta a
    //    flush avvenuto — a video non succede, il gesto e il reset non stanno
    //    mai nello stesso tick
    await nextTick()
    // reset dall'esterno (un deep-link, il reset dello store)
    store.filters.articolo_id = null
    await nextTick()
    expect(value.value).toBeNull()
    // un id messo da fuori: il widget non sa renderlo e resta com'e' (limite
    // dichiarato nel BB, da colmare con un `risolvi` il giorno che servira')
    store.filters.articolo_id = 'zz'
    await nextTick()
    expect(value.value).toBeNull()
    expect(chiamate.n).toBe(1)
  })
})
