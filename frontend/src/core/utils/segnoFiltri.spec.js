// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Un caso per RAMO di `segnoFiltri` (segno dei filtri attivi, D4 di
//        Tid 2026-09-22): niente, solo default, almeno uno modificato, piu' i
//        limiti che un `if` sbagliato attraversa in silenzio — `false` e `0`
//        come valori legittimi, la stringa vuota che NON e' un filtro, un
//        default svuotato a mano, un filtro ad array.
// Note: ⛔ Sono i rami che, sbagliati, NON falliscono: mostrano il segno
//        sbagliato. Un numero blu al posto di uno grigio toglie al segno la sua sola
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
    // ⚠️ `modificato` resta VERO: il floor `data_da` e' stato svuotato a mano,
    //    quindi non c'e' niente da segnalare ma c'e' eccome da ripulire.
    expect(r).toEqual({ stato: SEGNO_VUOTO, conteggio: 0, modificato: true })
  })

  it('solo i default: numero GRIGIO, e il conteggio c\'e\' lo stesso', () => {
    const r = segnoFiltri({ ...DEFAULTS }, CHIAVI, DEFAULTS)
    expect(r).toEqual({ stato: SEGNO_DEFAULT, conteggio: 1, modificato: false })
  })

  it('uno scelto dall\'operatore: numero, e conta ANCHE i default', () => {
    const r = segnoFiltri(
      { ...DEFAULTS, stato_codice_interno: 'BOZZA' },
      CHIAVI,
      DEFAULTS,
    )
    expect(r).toEqual({ stato: SEGNO_MODIFICATO, conteggio: 2, modificato: true })
  })

  it('default svuotato a mano (deep-link che azzera le date): modificato', () => {
    const r = segnoFiltri(
      { ...DEFAULTS, data_da: null, billing_account_id: 12 },
      CHIAVI,
      DEFAULTS,
    )
    expect(r).toEqual({ stato: SEGNO_MODIFICATO, conteggio: 1, modificato: true })
  })

  it('`false` e `0` sono filtri veri, non «niente»', () => {
    const chiavi = ['attivo', 'giacenza']
    const defaults = { attivo: true, giacenza: null }
    const r = segnoFiltri({ attivo: false, giacenza: 0 }, chiavi, defaults)
    expect(r).toEqual({ stato: SEGNO_MODIFICATO, conteggio: 2, modificato: true })
  })

  it('stringa vuota: non e\' un filtro — non si manda e non si conta', () => {
    const r = segnoFiltri(
      { ...DEFAULTS, data_da: null, stato_codice_interno: '' },
      CHIAVI,
      DEFAULTS,
    )
    expect(r).toEqual({ stato: SEGNO_VUOTO, conteggio: 0, modificato: true })
  })

  it('filtro ad ARRAY uguale al default: grigio, non blu', () => {
    const chiavi = ['stati']
    const defaults = { stati: ['BOZZA', 'EMESSO'] }
    // Stesso contenuto, altro riferimento: un `===` direbbe «modificato».
    const r = segnoFiltri({ stati: ['BOZZA', 'EMESSO'] }, chiavi, defaults)
    expect(r).toEqual({ stato: SEGNO_DEFAULT, conteggio: 1, modificato: false })
  })

  it('nessuna chiave dichiarata: `vuoto`, mai un numero inventato', () => {
    expect(segnoFiltri({ pippo: 3 }, [], {})).toEqual({
      stato: SEGNO_VUOTO,
      conteggio: 0,
      modificato: false,
    })
    expect(segnoFiltri(null, null)).toEqual({ stato: SEGNO_VUOTO, conteggio: 0, modificato: false })
  })

  // ⛔ I VALORI CHE NON RESTRINGONO, dichiarati (2026-09-23, rilievo in-app di
  //    Tid). Prima il segno conosceva un solo «tutto»: l'assenza. Per i filtri
  //    il cui «tutto» deve viaggiare sul filo il numero SALIVA allargando.
  it('un valore NEUTRO dichiarato non conta, anche se non e- assente', () => {
    const chiavi = ['solo_ultima_revisione', 'stato']
    const neutri = { solo_ultima_revisione: false }
    const defaults = { solo_ultima_revisione: true, stato: null }

    // «solo l'ultima revisione» (default): restringe, conta.
    expect(segnoFiltri({ solo_ultima_revisione: true, stato: null }, chiavi, defaults, neutri))
      .toEqual({ stato: SEGNO_DEFAULT, conteggio: 1, modificato: false })

    // «mostra storico»: la lista e' la piu' larga possibile, non conta piu'.
    // ⭐ `modificato` VERO: nessun segno, ma «Pulisci filtri» ha da fare.
    expect(segnoFiltri({ solo_ultima_revisione: false, stato: null }, chiavi, defaults, neutri))
      .toEqual({ stato: SEGNO_VUOTO, conteggio: 0, modificato: true })
  })

  it('il valore neutro NON spegne `modificato`: l-operatore ci ha messo le mani', () => {
    const chiavi = ['solo_ultima_revisione', 'stato']
    const neutri = { solo_ultima_revisione: false }
    const defaults = { solo_ultima_revisione: true, stato: null }
    // Storico acceso + uno stato scelto: una cosa sola restringe (lo stato),
    // ma il segno e' «modificato» perche' due filtri sono fuori dal default.
    expect(segnoFiltri(
      { solo_ultima_revisione: false, stato: 'APERTA' }, chiavi, defaults, neutri,
    )).toEqual({ stato: SEGNO_MODIFICATO, conteggio: 1, modificato: true })
  })

  it('un neutro non `null`: `ambito: tutti` delle code di lavoro', () => {
    const chiavi = ['ambito']
    const neutri = { ambito: 'tutti' }
    const defaults = { ambito: 'miei' }
    expect(segnoFiltri({ ambito: 'miei' }, chiavi, defaults, neutri).conteggio).toBe(1)
    expect(segnoFiltri({ ambito: 'tutti' }, chiavi, defaults, neutri).conteggio).toBe(0)
  })

  it('senza `neutri` si comporta esattamente come prima', () => {
    const chiavi = ['solo_ultima_revisione']
    const defaults = { solo_ultima_revisione: true }
    expect(segnoFiltri({ solo_ultima_revisione: false }, chiavi, defaults).conteggio).toBe(1)
  })
})
