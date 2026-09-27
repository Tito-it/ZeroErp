// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il contratto di `useListaStoreCore` — i FILTRI DI PARTENZA
//        (`limit`, nato il 2026-09-18 per la lista dentro un dialog che si
//        apre a dieci righe: vale alla nascita E dopo `reset()`) e, dallo
//        stesso giorno, la FORMA DEI PARAMETRI con cui la lista chiede pagina e
//        filtri al backend (`paramsFiltro`), che e' la ragione per cui venti
//        store scritti a mano sono entrati qui: search da tre caratteri, filtri
//        non-null col nome sul filo, ordinamento col ripiego a parametro, e le
//        tre UX della ricerca corta.
// Note: e' un composable PURO (nessuna API): dove la fetch serve, `fetchPage`
//       e' una spia che registra i parametri e risponde un envelope vuoto.
//
// Indice test:
//  — righe per pagina di partenza —
//  1. senza `limit` nasce alle righe delle liste standard
//  2. con `limit` nasce a quel numero
//  3. `reset()` riporta al `limit` di nascita, non al default
//  4. `reset()` riporta anche i filtri di dominio al loro default
//  — paramsFiltro —
//  5. la ricerca parte da tre caratteri, ed e' trimmata
//  6. i filtri di dominio viaggiano se `!= null`: `false` e `0` viaggiano
//  7. niente `limit`/`offset`: la paginazione la aggiunge la sola fetch
//  8. l'ordinamento ha il ripiego `asc` di default, e `orderDirDefault` lo cambia
//  9. `paramNames` cambia il nome sul filo, non quello nello store
//  — fetch —
// 10. la fetch manda `paramsFiltro` piu' `limit`/`offset`
// 11. con `parentField` la fetch riceve il padre come primo argomento
// 12. `ricercaCorta: 'svuota'` — 1-2 caratteri: nessuna fetch, lista svuotata
// 13. `ricercaCorta: 'ignora'` — 1-2 caratteri: nessuna fetch, lista intatta
// 14. `ricercaCorta` default — 1-2 caratteri: fetch senza `search`
//  — la soglia della lista (brief-db-be-fe-ricerca-soglia-per-lista) —
// 15. `ricercaMinCaratteri` nasce `null`: vale la soglia di progetto
// 16. a 1: `paramsFiltro` (cioe' anche l'export) e la fetch mandano «K»
// 17. a 1: con `ricercaCorta: 'svuota'` «K» non svuota, cerca
//  — il tasto che non cambia la richiesta (`ricercaCambiaLaRichiesta`) —
// 18. lista a video col filtro data (i preventivi): 1-2 caratteri non la cambiano
// 19. dal termine valido a quello corto la richiesta cambia: si torna senza `search`
// 20. lo stesso termine con uno spazio in coda non cambia la richiesta
// 21. lista non ancora caricata e `ricercaCorta: 'svuota'`: decide la fetch
// 22. dopo una richiesta fallita lo stesso termine riprova
//  — il padre composto (2026-09-27) —
// 23. piu' parti nel path: la fetch le riceve nell'ordine di `parentField`
// 24. con `emittenteParam` senza emittente non legge, ed e' in attesa
// 25. l'emittente viaggia in query col nome del backend, non nel path
// 26. `paramsEmittente` porta l'emittente agli altri verbi della view
// 27. l'emittente da solo non e' un'attesa: senza documento non c'e' padre
// 28. `reset()` azzera TUTTE le parti del padre
// ------------------------------------------------------------

import { describe, it, expect, vi } from 'vitest'

import { useListaStoreCore } from './useListaStoreCore'
import { PAGINATION } from '../constants'

const fetchMai = () => { throw new Error('fetchPage non deve essere chiamata') }

// Scopo: una `fetchPage` che registra le chiamate e risponde con `righe`.
function spiaFetch(righe = [{ id: 1 }]) {
  return vi.fn(async () => ({ data: { data: { results: righe, count: righe.length } } }))
}

describe('useListaStoreCore — le righe per pagina di partenza', () => {
  it('senza `limit` nasce alle righe delle liste standard', () => {
    const s = useListaStoreCore({ fetchPage: fetchMai })
    expect(s.filters.value.limit).toBe(PAGINATION.DEFAULT_ROWS)
  })

  it('con `limit` nasce a quel numero', () => {
    const s = useListaStoreCore({ fetchPage: fetchMai, limit: PAGINATION.COMPACT_ROWS })
    expect(s.filters.value.limit).toBe(PAGINATION.COMPACT_ROWS)
  })

  // ⚠️ E' il caso che conta: il picker si azzera a ogni chiusura (`reset()`
  //    dal legame col padre), e uno store che rinascesse a 25 cambierebbe
  //    passo alla seconda apertura — senza nessun errore.
  it('`reset()` riporta al `limit` di nascita, non al default', () => {
    const s = useListaStoreCore({ fetchPage: fetchMai, limit: PAGINATION.COMPACT_ROWS })
    s.filters.value.limit = 100
    s.filters.value.offset = 200
    s.reset()
    expect(s.filters.value.limit).toBe(PAGINATION.COMPACT_ROWS)
    expect(s.filters.value.offset).toBe(0)
  })

  it('`reset()` riporta anche i filtri di dominio al loro default', () => {
    const s = useListaStoreCore({
      fetchPage: fetchMai,
      filterDefaults: { solo_numerate: true, billing_account_id: null },
    })
    s.filters.value.solo_numerate = false
    s.filters.value.billing_account_id = 7
    s.reset()
    expect(s.filters.value.solo_numerate).toBe(true)
    expect(s.filters.value.billing_account_id).toBeNull()
  })
})

describe('useListaStoreCore — paramsFiltro, la forma dei parametri', () => {
  it('la ricerca parte da tre caratteri, ed e trimmata', () => {
    const s = useListaStoreCore({ fetchPage: fetchMai })
    expect(s.paramsFiltro({ search: ' ab ' })).toEqual({})
    expect(s.paramsFiltro({ search: ' abc ' })).toEqual({ search: 'abc' })
  })

  // ⚠️ `false` e' un filtro legittimo («solo i disattivati»): un truthy-check
  //    lo tratterebbe come «nessun filtro» e mostrerebbe anche gli attivi.
  it('i filtri di dominio viaggiano se != null: anche false e 0', () => {
    const s = useListaStoreCore({
      fetchPage: fetchMai,
      filterDefaults: { attivo: null, priorita_id: null, stato: null },
    })
    expect(s.paramsFiltro({ search: '', attivo: false, priorita_id: 0, stato: null }))
      .toEqual({ attivo: false, priorita_id: 0 })
    // Un filtro NON dichiarato in `filterDefaults` non viaggia, anche se sta
    // nell'oggetto: la whitelist e' la dichiarazione.
    expect(s.paramsFiltro({ search: '', attivo: true, estraneo: 1 })).toEqual({ attivo: true })
  })

  it('niente limit/offset: la paginazione la aggiunge la sola fetch', () => {
    const s = useListaStoreCore({ fetchPage: fetchMai })
    s.filters.value.offset = 50
    const p = s.paramsFiltro()
    expect(p).not.toHaveProperty('limit')
    expect(p).not.toHaveProperty('offset')
  })

  it('il ripiego del verso e asc di default, e orderDirDefault lo cambia', () => {
    const asc = useListaStoreCore({ fetchPage: fetchMai })
    expect(asc.paramsFiltro({ search: '', order_by: 'data', order_dir: null }))
      .toEqual({ order_by: 'data', order_dir: 'asc' })
    const desc = useListaStoreCore({ fetchPage: fetchMai, orderDirDefault: 'desc' })
    expect(desc.paramsFiltro({ search: '', order_by: 'data', order_dir: null }))
      .toEqual({ order_by: 'data', order_dir: 'desc' })
    // Senza `order_by` non viaggia niente, nemmeno un `order_dir` da solo.
    expect(desc.paramsFiltro({ search: '', order_by: null, order_dir: 'desc' })).toEqual({})
  })

  // ⭐ E' la divergenza che teneva in piedi le copie di offerte e preventivi:
  //    nello store il filtro si chiama `data_a` (lo azzera `useSearchTable`, lo
  //    lega il DatePicker), sul filo l'endpoint lo vuole `data_al`.
  it('paramNames cambia il nome sul filo, non quello nello store', () => {
    const s = useListaStoreCore({
      fetchPage: fetchMai,
      filterDefaults: { data_da: null, data_a: null },
      paramNames: { data_a: 'data_al' },
    })
    expect(s.filters.value).toHaveProperty('data_a')
    expect(s.filters.value).not.toHaveProperty('data_al')
    expect(s.paramsFiltro({ search: '', data_da: '2026-01-01', data_a: '2026-02-01' }))
      .toEqual({ data_da: '2026-01-01', data_al: '2026-02-01' })
  })
})

describe('useListaStoreCore — la fetch', () => {
  it('la fetch manda paramsFiltro piu limit e offset', async () => {
    const fetchPage = spiaFetch()
    const s = useListaStoreCore({
      fetchPage, startsEmpty: false,
      filterDefaults: { attivo: true },
      orderBy: 'codice', orderDir: 'desc',
    })
    s.filters.value.offset = 25
    expect(await s.fetchList()).toBe(true)
    expect(fetchPage).toHaveBeenCalledTimes(1)
    expect(fetchPage.mock.calls[0][0]).toEqual({
      attivo: true, order_by: 'codice', order_dir: 'desc',
      limit: PAGINATION.DEFAULT_ROWS, offset: 25,
    })
    expect(s.items.value).toEqual([{ id: 1 }])
    expect(s.totalRecords.value).toBe(1)
  })

  it('con parentField la fetch riceve il padre come primo argomento', async () => {
    const fetchPage = spiaFetch()
    const s = useListaStoreCore({ fetchPage, startsEmpty: false, parentField: 'fatturaId' })
    // ⛔ Senza padre non si chiama: l'id sta nel PATH, e `undefined` farebbe 404.
    expect(await s.fetchList()).toBe(false)
    expect(fetchPage).not.toHaveBeenCalled()
    s.fatturaId.value = 42
    await s.fetchList()
    expect(fetchPage.mock.calls[0][0]).toBe(42)
    expect(fetchPage.mock.calls[0][1]).toMatchObject({ limit: PAGINATION.DEFAULT_ROWS, offset: 0 })
  })

  it("ricercaCorta 'svuota': con 1-2 caratteri nessuna fetch e lista svuotata", async () => {
    const fetchPage = spiaFetch()
    const s = useListaStoreCore({ fetchPage, startsEmpty: false, ricercaCorta: 'svuota' })
    await s.fetchList()
    expect(s.items.value).toHaveLength(1)
    s.filters.value.search = 'ab'
    expect(await s.fetchList()).toBe(false)
    expect(fetchPage).toHaveBeenCalledTimes(1)
    expect(s.items.value).toEqual([])
  })

  it("ricercaCorta 'ignora': con 1-2 caratteri nessuna fetch e lista intatta", async () => {
    const fetchPage = spiaFetch()
    const s = useListaStoreCore({ fetchPage, startsEmpty: false, ricercaCorta: 'ignora' })
    await s.fetchList()
    s.filters.value.search = 'ab'
    expect(await s.fetchList()).toBe(false)
    expect(fetchPage).toHaveBeenCalledTimes(1)
    expect(s.items.value).toHaveLength(1)
  })

  it('ricercaCorta di default: con 1-2 caratteri si fetcha, senza search', async () => {
    const fetchPage = spiaFetch()
    const s = useListaStoreCore({ fetchPage, startsEmpty: false })
    s.filters.value.search = 'ab'
    expect(await s.fetchList()).toBe(true)
    expect(fetchPage).toHaveBeenCalledTimes(1)
    expect(fetchPage.mock.calls[0][0]).not.toHaveProperty('search')
  })
})

describe('useListaStoreCore — la soglia della ricerca e della lista', () => {
  it('ricercaMinCaratteri nasce null, e vale la soglia di progetto', () => {
    const s = useListaStoreCore({ fetchPage: fetchMai })
    expect(s.ricercaMinCaratteri.value).toBeNull()
    expect(s.paramsFiltro({ search: 'KG' })).toEqual({})
  })

  // ⭐ Il caso del cantiere: «KG» su unita' di misura partiva senza `search`.
  it('a 1: paramsFiltro (anche per l export) e la fetch mandano un carattere', async () => {
    const fetchPage = spiaFetch()
    const s = useListaStoreCore({ fetchPage, startsEmpty: false })
    s.ricercaMinCaratteri.value = 1
    expect(s.paramsFiltro({ search: ' K ' })).toEqual({ search: 'K' })
    s.filters.value.search = 'K'
    expect(await s.fetchList()).toBe(true)
    expect(fetchPage.mock.calls[0][0].search).toBe('K')
  })

  it("a 1: con ricercaCorta 'svuota' un carattere non svuota, cerca", async () => {
    const fetchPage = spiaFetch()
    const s = useListaStoreCore({ fetchPage, startsEmpty: false, ricercaCorta: 'svuota' })
    s.ricercaMinCaratteri.value = 1
    s.filters.value.search = 'K'
    expect(await s.fetchList()).toBe(true)
    expect(fetchPage.mock.calls[0][0].search).toBe('K')
  })
})

describe('useListaStoreCore — il tasto che non cambia la richiesta', () => {
  // ⭐ Il caso di Tid (2026-09-26): la lista dei preventivi parte col filtro
  //    data di default, che conta come filtro attivo. Digitare «a» e «ab»
  //    ricaricava la STESSA lista pesante senza `search`, e a video sembrava
  //    una ricerca partita al primo carattere.
  function listaPreventivi(fetchPage) {
    return useListaStoreCore({
      fetchPage,
      filterDefaults: { data_da: '2026-07-01' },
      gateKeys: ['data_da'],
    })
  }

  it('lista a video col filtro data: 1-2 caratteri non cambiano la richiesta', async () => {
    const s = listaPreventivi(spiaFetch())
    expect(await s.fetchList()).toBe(true)
    expect(s.ricercaCambiaLaRichiesta('a')).toBe(false)
    expect(s.ricercaCambiaLaRichiesta('ab')).toBe(false)
    expect(s.ricercaCambiaLaRichiesta('abc')).toBe(true)
  })

  it('dal termine valido a quello corto la richiesta cambia', async () => {
    const s = listaPreventivi(spiaFetch())
    s.filters.value.search = 'abc'
    await s.fetchList()
    // La lista a video e' filtrata per «abc»: con «ab» nella casella non lo e' piu'.
    expect(s.ricercaCambiaLaRichiesta('ab')).toBe(true)
    expect(s.ricercaCambiaLaRichiesta('abcd')).toBe(true)
  })

  it('lo stesso termine con uno spazio in coda non cambia la richiesta', async () => {
    const s = listaPreventivi(spiaFetch())
    s.filters.value.search = 'abc'
    await s.fetchList()
    expect(s.ricercaCambiaLaRichiesta('abc ')).toBe(false)
  })

  it("lista non ancora caricata e ricercaCorta 'svuota': decide la fetch", async () => {
    // Non ancora caricata: la guardia empty-state e' della fetch.
    expect(listaPreventivi(spiaFetch()).ricercaCambiaLaRichiesta('a')).toBe(true)
    // 'svuota': il termine corto svuota per scelta, e lo svuotamento e' della fetch.
    const s = useListaStoreCore({ fetchPage: spiaFetch(), startsEmpty: false, ricercaCorta: 'svuota' })
    await s.fetchList()
    expect(s.ricercaCambiaLaRichiesta('a')).toBe(true)
  })

  it('dopo una richiesta fallita lo stesso termine riprova', async () => {
    const fetchPage = spiaFetch()
    const s = listaPreventivi(fetchPage)
    await s.fetchList()
    fetchPage.mockRejectedValueOnce(new Error('rete'))
    // Il core non ri-solleva: l'errore diventa `erroreCaricamento`.
    expect(await s.fetchList()).toBe(false)
    expect(s.erroreCaricamento.value).toBe(true)
    // La lista a video e' ancora quella di prima, ma la richiesta non e' nota.
    expect(s.ricercaCambiaLaRichiesta('a')).toBe(true)
  })
})

// ⭐ IL PADRE COMPOSTO (2026-09-27, regola del 2): piu' id nel path e/o
//    l'emittente del documento in query. La semantica e' UNA: senza tutte le
//    parti la lista non legge — e lo dice (`attesaPadre`).
describe('useListaStoreCore — il padre composto', () => {
  it('piu\' parti nel path: la fetch le riceve nell\'ordine di `parentField`', async () => {
    const fetchPage = spiaFetch()
    const s = useListaStoreCore({
      fetchPage, startsEmpty: false, parentField: ['soggettoId', 'titoloId'],
    })
    s.soggettoId.value = 'uuid-1'
    // ⛔ Una parte sola non basta: l'altra finirebbe `undefined` nel path.
    expect(await s.fetchList()).toBe(false)
    expect(fetchPage).not.toHaveBeenCalled()
    s.titoloId.value = 7
    await s.fetchList()
    const [soggettoId, titoloId, params] = fetchPage.mock.calls[0]
    expect([soggettoId, titoloId]).toEqual(['uuid-1', 7])
    expect(params).toMatchObject({ limit: PAGINATION.DEFAULT_ROWS, offset: 0 })
  })

  it('con `emittenteParam` senza emittente non legge, ed e\' in attesa', async () => {
    const fetchPage = spiaFetch()
    const s = useListaStoreCore({
      fetchPage, startsEmpty: false, parentField: 'documentoId',
      emittenteParam: 'emittente_fiscale_id',
    })
    expect(s.attesaPadre.value).toBe(false)
    s.documentoId.value = 12
    expect(s.attesaPadre.value).toBe(true)
    expect(await s.fetchList()).toBe(false)
    expect(fetchPage).not.toHaveBeenCalled()
  })

  it('l\'emittente viaggia in query col nome del backend, non nel path', async () => {
    const fetchPage = spiaFetch()
    const s = useListaStoreCore({
      fetchPage, startsEmpty: false, parentField: 'entitaId',
      emittenteParam: 'emittente_soggetto_ruolo_id',
    })
    s.entitaId.value = 7
    s.emittenteId.value = 3
    expect(s.attesaPadre.value).toBe(false)
    await s.fetchList()
    expect(fetchPage.mock.calls[0]).toHaveLength(2)
    const [entitaId, params] = fetchPage.mock.calls[0]
    expect(entitaId).toBe(7)
    expect(params).toMatchObject({ emittente_soggetto_ruolo_id: 3, offset: 0 })
    // ⚠️ Non e' un filtro: `paramsFiltro` (e quindi il segno dei filtri e
    //    l'export) non lo vede.
    expect(s.paramsFiltro()).not.toHaveProperty('emittente_soggetto_ruolo_id')
    expect(s.chiaviFiltro).not.toContain('emittenteId')
  })

  it('`paramsEmittente` porta l\'emittente agli altri verbi della view', () => {
    const s = useListaStoreCore({
      fetchPage: fetchMai, parentField: 'templateId', emittenteParam: 'emittente_fiscale_id',
    })
    expect(s.paramsEmittente()).toEqual({})
    s.emittenteId.value = 5
    expect(s.paramsEmittente()).toEqual({ emittente_fiscale_id: 5 })
    // Senza `emittenteParam` non c'e' niente da portare.
    expect(useListaStoreCore({ fetchPage: fetchMai }).paramsEmittente()).toEqual({})
  })

  it('l\'emittente da solo non e\' un\'attesa: senza documento non c\'e\' padre', () => {
    const s = useListaStoreCore({
      fetchPage: fetchMai, parentField: 'documentoId', emittenteParam: 'emittente_fiscale_id',
    })
    s.emittenteId.value = 3
    expect(s.attesaPadre.value).toBe(false)
  })

  it('`reset()` azzera TUTTE le parti del padre', () => {
    const s = useListaStoreCore({
      fetchPage: fetchMai, parentField: ['soggettoId', 'titoloId'],
      emittenteParam: 'emittente_fiscale_id',
    })
    s.soggettoId.value = 'uuid-1'
    s.titoloId.value = 7
    s.emittenteId.value = 3
    s.reset()
    expect([s.soggettoId.value, s.titoloId.value, s.emittenteId.value]).toEqual([null, null, null])
    expect(s.attesaPadre.value).toBe(false)
  })
})
