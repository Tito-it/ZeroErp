// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il contratto dei quattro binder di `useStoreFilterBindings` —
//        il legame fra un widget della toolbar e `store.filters` — scritto il
//        2026-09-18 insieme ai due binder nuovi (`bindToggle`, `bindLookup`,
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

describe('bindPeriodo — UN filtro con due estremi', () => {
  it('scrive l\'estremo toccato, come due bindDate separati', () => {
    const { store, chiamate, bindPeriodo } = fabbrica({ data_da: '2026-06-01', data_a: null })
    const periodo = bindPeriodo()
    expect(periodo.da.value).toBeInstanceOf(Date)
    periodo.setA(new Date(2026, 8, 30))
    expect(store.filters.data_a).toBe('2026-09-30')
    expect(store.filters.data_da).toBe('2026-06-01')
    expect(chiamate.n).toBe(1)
  })

  it('⛔ `da` oltre `a`: il periodo si APRE dall\'altra parte, e la fetch e\' UNA', () => {
    const { store, chiamate, bindPeriodo } = fabbrica({ data_da: '2026-01-01', data_a: '2026-01-31' })
    const periodo = bindPeriodo()
    // Sposto la finestra in avanti: il vecchio `a` non descrive piu' niente.
    periodo.setDa(new Date(2026, 1, 1))
    expect(store.filters.data_da).toBe('2026-02-01')
    expect(store.filters.data_a).toBeNull()
    expect(periodo.a.value).toBeNull()
    // ⛔ UNA sola fetch: due vorrebbero dire che la prima e' partita con
    //    l'intervallo ancora invertito — una lista vuota che lampeggia.
    expect(chiamate.n).toBe(1)
  })

  it('⛔ simmetrico: `a` prima di `da` apre l\'inizio', () => {
    const { store, bindPeriodo } = fabbrica({ data_da: '2026-01-01', data_a: '2026-01-31' })
    const periodo = bindPeriodo()
    periodo.setA(new Date(2025, 11, 15))
    expect(store.filters.data_a).toBe('2025-12-15')
    expect(store.filters.data_da).toBeNull()
    expect(periodo.da.value).toBeNull()
  })

  it('due estremi UGUALI sono un periodo di un giorno, non un errore', () => {
    const { store, bindPeriodo } = fabbrica({ data_da: '2026-01-01', data_a: '2026-01-31' })
    const periodo = bindPeriodo()
    periodo.setDa(new Date(2026, 0, 31))
    expect(store.filters.data_da).toBe('2026-01-31')
    expect(store.filters.data_a).toBe('2026-01-31')
  })

  it('con un estremo vuoto non c\'e\' niente da correggere', () => {
    const { store, bindPeriodo } = fabbrica({ data_da: null, data_a: '2026-01-31' })
    const periodo = bindPeriodo()
    periodo.setDa(new Date(2026, 0, 1))
    expect(store.filters.data_da).toBe('2026-01-01')
    expect(store.filters.data_a).toBe('2026-01-31')
  })

  it('⚠️ la correzione porta l\'altro estremo a NULL, mai al suo `clearTo`', () => {
    const floor = () => new Date(2026, 5, 1)
    const { store, bindPeriodo } = fabbrica({ data_da: '2026-06-01', data_a: '2026-06-30' })
    // Il floor sta su `da`, come nei contratti.
    const periodo = bindPeriodo('data_da', 'data_a', { clearToDa: floor })
    periodo.setA(new Date(2026, 0, 15))
    // Se la correzione usasse il `clearTo`, `data_da` tornerebbe al 2026-06-01
    // — cioe' di nuovo DOPO `data_a`, e il guard non avrebbe concluso niente.
    expect(store.filters.data_a).toBe('2026-01-15')
    expect(store.filters.data_da).toBeNull()
  })

  it('`clearTo` resta vivo per il gesto dell\'operatore che SVUOTA', () => {
    const floor = () => new Date(2026, 5, 1)
    const { store, bindPeriodo } = fabbrica({ data_da: '2026-08-01', data_a: null })
    const periodo = bindPeriodo('data_da', 'data_a', { clearToDa: floor })
    periodo.setDa(null)
    expect(store.filters.data_da).toBe('2026-06-01')
  })

  it('⛔ svuotare `da` col floor NON puo\' lasciare un intervallo invertito', () => {
    // Il caso che il guard non vedeva: `setDa(null)` emette `null`, e `null` non
    // inverte niente — ma il valore che finisce nel filtro e' il FLOOR, che qui
    // cade DOPO `data_a`. L'invariante va controllata sul valore RISOLTO.
    const floor = () => new Date(2026, 6, 1) // 2026-07-01
    const { store, chiamate, bindPeriodo } = fabbrica({ data_da: '2026-08-01', data_a: '2026-01-15' })
    const periodo = bindPeriodo('data_da', 'data_a', { clearToDa: floor })
    periodo.setDa(null)
    expect(store.filters.data_da).toBe('2026-07-01')
    expect(store.filters.data_a).toBeNull()
    expect(periodo.a.value).toBeNull()
    expect(chiamate.n).toBe(1)
  })

  it('⛔ simmetrico: svuotare `a` col floor non lascia `a` prima di `da`', () => {
    const floor = () => new Date(2026, 0, 1) // 2026-01-01
    const { store, chiamate, bindPeriodo } = fabbrica({ data_da: '2026-08-01', data_a: '2026-09-01' })
    const periodo = bindPeriodo('data_da', 'data_a', { clearToA: floor })
    periodo.setA(null)
    expect(store.filters.data_a).toBe('2026-01-01')
    expect(store.filters.data_da).toBeNull()
    expect(periodo.da.value).toBeNull()
    expect(chiamate.n).toBe(1)
  })

  it('il floor che NON inverte lascia l\'altro estremo dov\'era', () => {
    const floor = () => new Date(2026, 0, 1)
    const { store, bindPeriodo } = fabbrica({ data_da: '2026-03-01', data_a: '2026-06-30' })
    const periodo = bindPeriodo('data_da', 'data_a', { clearToDa: floor })
    periodo.setDa(null)
    expect(store.filters.data_da).toBe('2026-01-01')
    expect(store.filters.data_a).toBe('2026-06-30')
  })

  it('le chiavi non sono cablate: una lista puo\' chiamarle a modo suo', () => {
    const { store, bindPeriodo } = fabbrica({ validita_dal_min: null, validita_dal_max: '2026-03-31' })
    const periodo = bindPeriodo('validita_dal_min', 'validita_dal_max')
    periodo.setDa(new Date(2026, 6, 1))
    expect(store.filters.validita_dal_min).toBe('2026-07-01')
    expect(store.filters.validita_dal_max).toBeNull()
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

  it('lo store azzerato da fuori svuota il widget; un id da fuori SENZA oggetto non si rende', async () => {
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
    // un id messo da fuori SENZA l'oggetto: il widget non sa renderlo e resta
    // com'e' (limite dichiarato nel BB, da colmare con un `risolvi` il giorno
    // che servira')
    store.filters.articolo_id = 'zz'
    await nextTick()
    expect(value.value).toBeNull()
    expect(chiamate.n).toBe(1)
  })

  it('l\'oggetto scelto si ricorda nello store (`<chiave>_obj`) e un widget che RIMONTA lo ritrova', () => {
    const { store, bindLookup } = fabbrica({ articolo_id: null })
    const primo = bindLookup('articolo_id')
    const articolo = { id: 'a1b2', codice: 'ART-1', descrizione: 'Bullone' }
    primo.value.value = articolo
    primo.onChange()
    expect(store.filters.articolo_id_obj).toEqual(articolo)
    // la scheda di un `<Tabs lazy>` rimonta: un binder nuovo, stesso store
    const secondo = bindLookup('articolo_id')
    expect(secondo.value.value).toEqual(articolo)
    // il clear dal widget rimontato azzera ENTRAMBE le chiavi
    secondo.value.value = null
    secondo.onChange()
    expect(store.filters.articolo_id).toBeNull()
    expect(store.filters.articolo_id_obj).toBeNull()
  })

  it('un oggetto ricordato che NON corrisponde all\'id dello store non si rende', async () => {
    const { store, bindLookup } = fabbrica({ articolo_id: 'altro', articolo_id_obj: { id: 'a1b2' } })
    const { value } = bindLookup('articolo_id')
    expect(value.value).toBeNull()
    // e l'azzeramento da fuori pulisce anche la memoria
    store.filters.articolo_id = null
    await nextTick()
    expect(store.filters.articolo_id_obj).toBeNull()
  })

  it('un id DIVERSO messo da fuori svuota il widget invece di lasciargli l\'oggetto vecchio', async () => {
    const { store, bindLookup } = fabbrica({ articolo_id: null })
    const { value, onChange } = bindLookup('articolo_id')
    value.value = { id: 'a1b2', codice: 'ART-1' }
    onChange()
    await nextTick()
    // un deep-link (o un altro widget sullo stesso store) scrive un altro id:
    // il picker NON deve continuare a mostrare ART-1 sopra una lista filtrata
    // da 'zz' — meglio vuoto che una bugia
    store.filters.articolo_id = 'zz'
    await nextTick()
    expect(value.value).toBeNull()
    // e se da fuori arriva ANCHE l'oggetto coerente, il widget lo rende
    store.filters.articolo_id_obj = { id: 'c3', codice: 'ART-3' }
    store.filters.articolo_id = 'c3'
    await nextTick()
    expect(value.value).toEqual({ id: 'c3', codice: 'ART-3' })
  })
})
