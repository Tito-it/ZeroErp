// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il contratto che una lista offre ai suoi filtri — `chiaviFiltro`,
//        `filtriDefault`, `azzeraFiltri` — estratto da `useListaStoreCore` il
//        2026-09-23 (regola del 2) perche' quattordici store scritti a mano
//        dovevano poterlo offrire senza cedere il proprio `buildParams`.
// Note: composable PURO (un `ref` e una funzione): niente API, niente i18n,
//       niente DOM. I casi qui sotto sono i tre che, sbagliati, NON danno
//       errore — il segno resterebbe spento, o «Pulisci filtri» pulirebbe piu'
//       di quanto deve.
// ------------------------------------------------------------

import { describe, it, expect, vi } from 'vitest'
import { ref } from 'vue'

import { useContrattoFiltriLista } from './useContrattoFiltriLista'

function fabbrica(filterDefaults, extra = {}, filtriNeutri = {}) {
  const filters = ref({ ...filterDefaults, ...extra })
  const chiamate = { n: 0 }
  const fetchList = () => { chiamate.n += 1; return 'letta' }
  return {
    filters,
    chiamate,
    ...useContrattoFiltriLista({ filters, filterDefaults, filtriNeutri, fetchList }),
  }
}

describe('il contratto dichiarato', () => {
  it('espone le chiavi dei soli filtri di dominio, nell-ordine di dichiarazione', () => {
    const { chiaviFiltro } = fabbrica(
      { stato: null, data_da: '2026-01-01' },
      { search: '', limit: 25, offset: 0, order_by: 'data', order_dir: 'desc' },
    )
    // ⛔ `search`/`limit`/`offset`/`order_*` NON sono filtri: contarli
    //    accenderebbe il segno sulla paginazione di una lista intera.
    expect([...chiaviFiltro]).toEqual(['stato', 'data_da'])
  })

  it('congela i default: un consumatore non puo- cambiare il metro', () => {
    const { filtriDefault } = fabbrica({ stato: 'APERTA' })
    expect(Object.isFrozen(filtriDefault)).toBe(true)
    expect(() => { filtriDefault.stato = 'CHIUSA' }).toThrow()
    expect(filtriDefault.stato).toBe('APERTA')
  })

  // ⛔ IL CASO ARRAY — quello che lo spread non copre e che il contratto
  //    dichiara ammesso (`segnoFiltri.uguale()` tratta apposta gli array). Con
  //    `{ ...defaults }` il default resterebbe LO STESSO array del letterale.
  it('un default ad ARRAY e- staccato dal letterale, e la `push` non passa', () => {
    const DEFAULTS = { stati: ['APERTA'] }
    const { filtriDefault } = fabbrica(DEFAULTS)
    expect(filtriDefault.stati).not.toBe(DEFAULTS.stati)
    expect(() => { filtriDefault.stati.push('CHIUSA') }).toThrow()
    expect(DEFAULTS.stati).toEqual(['APERTA'])
  })

  it('«Pulisci» riconsegna una COPIA dell-array, non il metro', () => {
    const DEFAULTS = { stati: ['APERTA'] }
    const c = fabbrica(DEFAULTS)
    c.filters.value.stati = ['CHIUSA', 'ANNULLATA']
    c.azzeraFiltri()
    expect(c.filters.value.stati).toEqual(['APERTA'])
    // Il valore vivo si puo' mutare (lo fa una multi-select) e il default resta.
    c.filters.value.stati.push('CHIUSA')
    expect(c.filtriDefault.stati).toEqual(['APERTA'])
    expect(DEFAULTS.stati).toEqual(['APERTA'])
  })

  it('i default sono una COPIA: mutare i filtri vivi non li sposta', () => {
    const { filters, filtriDefault } = fabbrica({ stato: 'APERTA' })
    filters.value.stato = 'CHIUSA'
    expect(filtriDefault.stato).toBe('APERTA')
  })

  // ⛔ I NEUTRI SONO UN METRO COME I DEFAULT, quindi si staccano e si congelano
  //    allo stesso modo: con un neutro ad array lo spread lascerebbe lo STESSO
  //    array del letterale, e la prima `push` di un widget sposterebbe il metro.
  it('un neutro ad ARRAY e- staccato dal letterale e congelato', () => {
    const NEUTRI = { stati: [] }
    const { filtriNeutri } = fabbrica({ stati: ['APERTA'] }, {}, NEUTRI)
    expect(filtriNeutri.stati).not.toBe(NEUTRI.stati)
    expect(Object.isFrozen(filtriNeutri)).toBe(true)
    expect(() => { filtriNeutri.stati.push('CHIUSA') }).toThrow()
  })

  // ⛔ IL REFUSO CHE NON FALLISCE: un neutro dichiarato su una chiave che non e'
  //    un filtro non fa niente — il segno continua a contare quello vero, e
  //    nessuno lo dice. E' la forma del difetto gia' visto nel drawer BoM (una
  //    chiave nei valori e non nelle chiavi), qui presa dal lato del contratto.
  it('un neutro su una chiave che NON e- un filtro si fa sentire', () => {
    const spia = vi.spyOn(console, 'error').mockImplementation(() => {})
    const { filtriNeutri } = fabbrica({ ambito: 'miei' }, {}, { ambitto: 'tutti' })
    expect(spia).toHaveBeenCalledTimes(1)
    expect(String(spia.mock.calls[0][0])).toContain('ambitto')
    // Il contratto resta valido: il neutro sbagliato non inventa un filtro.
    expect(filtriNeutri.ambito).toBeUndefined()
    spia.mockRestore()
  })
})

describe('azzeraFiltri — «Pulisci filtri»', () => {
  it('riporta i filtri al default, torna a pagina 1 e rilegge', () => {
    const { filters, chiamate, azzeraFiltri } = fabbrica(
      { stato: null, data_da: '2026-01-01' },
      { search: 'pippo', limit: 25, offset: 50 },
    )
    filters.value.stato = 'CHIUSA'
    filters.value.data_da = '2026-06-30'
    const esito = azzeraFiltri()
    expect(filters.value.stato).toBe(null)
    expect(filters.value.data_da).toBe('2026-01-01')
    expect(filters.value.offset).toBe(0)
    expect(chiamate.n).toBe(1)
    expect(esito).toBe('letta')
  })

  it('NON tocca la ricerca: «pulisci filtri» non e- «annulla la ricerca» (D2)', () => {
    const { filters, azzeraFiltri } = fabbrica({ stato: 'APERTA' }, { search: 'pippo', offset: 0 })
    filters.value.stato = 'CHIUSA'
    azzeraFiltri()
    expect(filters.value.search).toBe('pippo')
  })

  it('un default VALORIZZATO torna al suo valore, non a null', () => {
    const { filters, azzeraFiltri } = fabbrica({ annullati: false, coda: 'DA_ABBINARE' }, { offset: 0 })
    filters.value.annullati = true
    filters.value.coda = 'SOSPESE'
    azzeraFiltri()
    expect(filters.value.annullati).toBe(false)
    expect(filters.value.coda).toBe('DA_ABBINARE')
  })

  it('senza `offset` dichiarato non lo inventa (liste non paginate)', () => {
    const { filters, azzeraFiltri } = fabbrica({ tipo_prestazione_id: 7 })
    filters.value.tipo_prestazione_id = 9
    azzeraFiltri()
    expect(filters.value.tipo_prestazione_id).toBe(7)
    expect('offset' in filters.value).toBe(false)
  })
})

describe('il caso limite che non fallisce da solo', () => {
  it('una lista senza filtri dichiarati non ha chiavi, e azzerare non rompe', () => {
    const { chiaviFiltro, chiamate, azzeraFiltri } = fabbrica({}, { offset: 30 })
    expect([...chiaviFiltro]).toEqual([])
    azzeraFiltri()
    // ⚠️ La fetch parte comunque: «pulisci» e' un gesto dell'operatore, e una
    //    lista che non si ricarica dopo un gesto sembra guasta.
    expect(chiamate.n).toBe(1)
  })
})
