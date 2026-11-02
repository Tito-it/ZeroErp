// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
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
// 26b. `paramsExport` = filtri della videata + emittente (l'export passa dal cancello)
// 27. l'emittente da solo non e' un'attesa: senza documento non c'e' padre
// 28. `reset()` azzera TUTTE le parti del padre
//  — la pagina che non c'e' piu' (2026-09-28) —
// 29. oltre l'ultima pagina, col totale vero: rilegge dall'ULTIMA pagina reale
// 30. oltre l'ultima col totale 0 (backend che non sa contare li'): da capo
// 31. pagina piena: nessuna rilettura
// 32. prima pagina vuota: e' la lista vuota, nessuna rilettura
// 33. una rilettura sola, anche se la seconda risposta e' ancora vuota
// 34. `PADRE_SENZA_EMITTENTE`: la lista legge, e l'emittente non viaggia
// ------------------------------------------------------------

import { describe, it, expect, vi } from 'vitest'

import { useListaStoreCore, PADRE_SENZA_EMITTENTE } from './useListaStoreCore'
import { USO_MISURA, misuraDefault } from '../misurePagina'

// Le misure le fabbrica il setup di Vitest; qui si legge l'USO, e i due usi
// devono dare numeri DIVERSI o i test sotto non distinguerebbero niente.
const PAGINA = () => misuraDefault(USO_MISURA.PAGINA)
const COMPATTA = () => misuraDefault(USO_MISURA.COMPATTA)

const fetchMai = () => { throw new Error('fetchPage non deve essere chiamata') }

// Scopo: una `fetchPage` che registra le chiamate e risponde con `righe`.
function spiaFetch(righe = [{ id: 1 }]) {
  return vi.fn(async () => ({ data: { data: { results: righe, count: righe.length } } }))
}

describe('useListaStoreCore — le righe per pagina di partenza', () => {
  it('i due usi danno misure diverse (premessa dei test sotto)', () => {
    expect(COMPATTA()).not.toBe(PAGINA())
  })

  it('senza `misura` nasce alla misura di pagina', () => {
    const s = useListaStoreCore({ fetchPage: fetchMai })
    expect(s.filters.value.limit).toBe(PAGINA())
  })

  it('con `misura: COMPATTA` nasce alla misura compatta', () => {
    const s = useListaStoreCore({ fetchPage: fetchMai, misura: USO_MISURA.COMPATTA })
    expect(s.filters.value.limit).toBe(COMPATTA())
  })

  // ⚠️ E' il caso che conta: il picker si azzera a ogni chiusura (`reset()`
  //    dal legame col padre), e uno store che rinascesse a 25 cambierebbe
  //    passo alla seconda apertura — senza nessun errore.
  it('`reset()` riporta alla misura di nascita, non al default', () => {
    const s = useListaStoreCore({ fetchPage: fetchMai, misura: USO_MISURA.COMPATTA })
    s.filters.value.limit = 100
    s.filters.value.offset = 200
    s.reset()
    expect(s.filters.value.limit).toBe(COMPATTA())
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
      limit: PAGINA(), offset: 25,
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
    expect(fetchPage.mock.calls[0][1]).toMatchObject({ limit: PAGINA(), offset: 0 })
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
    expect(params).toMatchObject({ limit: PAGINA(), offset: 0 })
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

  // ⭐ Il padre che un emittente suo non ce l'ha (il modello standard): con
  //    `null` resterebbe in attesa per sempre (il difetto del 2026-10-20).
  it('`PADRE_SENZA_EMITTENTE`: la lista legge, e l\'emittente non viaggia', async () => {
    const fetchPage = spiaFetch()
    const s = useListaStoreCore({
      fetchPage, startsEmpty: false, parentField: 'templateId',
      emittenteParam: 'emittente_fiscale_id',
    })
    s.templateId.value = 2728
    s.emittenteId.value = PADRE_SENZA_EMITTENTE
    expect(s.attesaPadre.value).toBe(false)
    expect(s.paramsEmittente()).toEqual({})
    await s.fetchList()
    const [templateId, params] = fetchPage.mock.calls[0]
    expect(templateId).toBe(2728)
    expect(params).not.toHaveProperty('emittente_fiscale_id')
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

  it('`paramsExport` porta i filtri della videata E l\'emittente', () => {
    const s = useListaStoreCore({
      fetchPage: fetchMai, parentField: 'documentoId', emittenteParam: 'emittente_fiscale_id',
    })
    s.filters.value.search = 'vite'
    s.emittenteId.value = 5
    expect(s.paramsExport()).toEqual({ ...s.paramsFiltro(), emittente_fiscale_id: 5 })
    expect(s.paramsExport()).toMatchObject({ search: 'vite' })
    // Senza `emittenteParam` coincide con `paramsFiltro`.
    const semplice = useListaStoreCore({ fetchPage: fetchMai })
    expect(semplice.paramsExport()).toEqual(semplice.paramsFiltro())
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

describe('useListaStoreCore — la pagina che non c\'e\' piu\'', () => {
  // Scopo: una `fetchPage` che risponde in sequenza le buste date, e registra.
  function risposte(...buste) {
    const coda = [...buste]
    return vi.fn(async () => {
      const [results, count] = coda.shift() ?? [[], 0]
      return { data: { data: { results, count } } }
    })
  }

  // ⭐ Il caso che l'ha fatta nascere: pagina 3 (offset 20, 10 per pagina),
  //    l'operatore elimina l'unica riga che c'era. Restano 20 righe: la
  //    pagina giusta e' la 2, non la 1.
  it('oltre l\'ultima pagina, col totale vero: rilegge dall\'ULTIMA pagina reale', async () => {
    const fetchPage = risposte([[], 20], [[{ id: 11 }], 20])
    const s = useListaStoreCore({ fetchPage, startsEmpty: false })
    s.filters.value.limit = 10 // il passo del caso: aritmetica di pagina, non una misura del catalogo
    s.filters.value.offset = 20
    expect(await s.fetchList()).toBe(true)
    expect(fetchPage).toHaveBeenCalledTimes(2)
    expect(fetchPage.mock.calls[1][0]).toMatchObject({ offset: 10, limit: 10 })
    expect(s.filters.value.offset).toBe(10)
    expect(s.items.value).toEqual([{ id: 11 }])
  })

  it('oltre l\'ultima col totale 0 (backend che non sa contare li\'): da capo', async () => {
    const fetchPage = risposte([[], 0], [[{ id: 1 }], 3])
    const s = useListaStoreCore({ fetchPage, startsEmpty: false })
    s.filters.value.limit = 10 // il passo del caso: aritmetica di pagina, non una misura del catalogo
    s.filters.value.offset = 30
    await s.fetchList()
    expect(fetchPage.mock.calls[1][0]).toMatchObject({ offset: 0 })
    expect(s.totalRecords.value).toBe(3)
  })

  it('pagina piena: nessuna rilettura', async () => {
    const fetchPage = risposte([[{ id: 21 }], 21])
    const s = useListaStoreCore({ fetchPage, startsEmpty: false })
    s.filters.value.limit = 10 // il passo del caso: aritmetica di pagina, non una misura del catalogo
    s.filters.value.offset = 20
    await s.fetchList()
    expect(fetchPage).toHaveBeenCalledTimes(1)
  })

  it('prima pagina vuota: e\' la lista vuota, nessuna rilettura', async () => {
    const fetchPage = risposte([[], 0])
    const s = useListaStoreCore({ fetchPage, startsEmpty: false })
    await s.fetchList()
    expect(fetchPage).toHaveBeenCalledTimes(1)
  })

  it('una rilettura sola, anche se la seconda risposta e\' ancora vuota', async () => {
    const fetchPage = risposte([[], 20], [[], 0], [[{ id: 1 }], 1])
    const s = useListaStoreCore({ fetchPage, startsEmpty: false })
    s.filters.value.limit = 10 // il passo del caso: aritmetica di pagina, non una misura del catalogo
    s.filters.value.offset = 20
    await s.fetchList()
    expect(fetchPage).toHaveBeenCalledTimes(2)
  })
})
