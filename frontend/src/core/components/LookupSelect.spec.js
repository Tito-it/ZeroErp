// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: La prop `voceCorrente` di `LookupSelect` (2026-10-01,
//        brief-db-esigibilita-iva-per-cassa-emittente): la voce che il record
//        ha gia', disattivata nel catalogo dopo, resta visibile e sceglibile,
//        marcata «non attiva» — invece di un campo vuoto con un valore dentro.
//        Con `voceCorrenteAttiva` (2026-11-12, brief-db-addebito-trasporto-
//        ordine §9.10) la voce e' valida e l'elenco non la propone per
//        costruzione (le sole voci libere): in coda, senza «non attiva».
// Note: si guarda cio' che arriva al `Select` di PrimeVue (`options`): e' li'
//       che una voce mancante diventa il campo vuoto.
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import Select from 'primevue/select'

import LookupSelect from './LookupSelect.vue'
import { monta } from '../../../test/montaggio'

const ATTIVE = [
  { codice_interno: 'RF01', codice: 'RF01', descrizione: 'Ordinario' },
  { codice_interno: 'RF17', codice: 'RF17', descrizione: 'IVA per cassa' },
]

// Una chiave di cache per test: la cache di `useGlobalLookup` e' di modulo.
let n = 0
function montaCon(props, { fetcher } = {}) {
  n += 1
  return monta(LookupSelect, {
    fetcher: fetcher || (() => Promise.resolve({ data: { data: ATTIVE } })),
    lookupKey: `spec.voce-corrente.${n}`,
    transform: r => r.data.data,
    valueField: 'codice_interno',
    ...props,
  })
}

const opzioni = w => w.findComponent(Select).props('options')

describe('LookupSelect — voceCorrente', () => {
  it('una voce fuori elenco si aggiunge in coda, marcata non attiva', async () => {
    const w = montaCon({
      modelValue: 'RF03',
      voceCorrente: { codice_interno: 'RF03', codice: 'RF03', descrizione: 'Soppresso' },
    })
    await flushPromises()
    const voci = opzioni(w)
    expect(voci).toHaveLength(3)
    expect(voci[2].codice_interno).toBe('RF03')
    expect(voci[2].descrizione).toBe('Soppresso — common.lookup_voce_non_attiva')
  })

  it('una voce gia\' nell\'elenco non si duplica e non si marca', async () => {
    const w = montaCon({
      modelValue: 'RF17',
      voceCorrente: { codice_interno: 'RF17', codice: 'RF17', descrizione: 'IVA per cassa' },
    })
    await flushPromises()
    expect(opzioni(w)).toEqual(ATTIVE)
  })

  it('resta sceglibile anche quando il valore e\' cambiato', async () => {
    const w = montaCon({
      modelValue: 'RF01',
      voceCorrente: { codice_interno: 'RF03', codice: 'RF03', descrizione: 'Soppresso' },
    })
    await flushPromises()
    expect(opzioni(w).map(v => v.codice_interno)).toEqual(['RF01', 'RF17', 'RF03'])
  })

  // Lettura fallita: l'elenco e' vuoto, ma non perche' la voce sia
  // disattivata — dirlo «non attiva» sarebbe falso.
  it('a elenco non caricato non marca niente', async () => {
    const w = montaCon(
      {
        modelValue: 'RF17',
        voceCorrente: { codice_interno: 'RF17', codice: 'RF17', descrizione: 'IVA per cassa' },
      },
      { fetcher: () => Promise.reject(new Error('rete')) },
    )
    await flushPromises()
    expect(opzioni(w)).toEqual([])
  })

  it('con voceCorrenteAttiva la voce va in coda senza «non attiva»', async () => {
    const w = montaCon({
      modelValue: 'RF03',
      voceCorrente: { codice_interno: 'RF03', codice: 'RF03', descrizione: 'Trasporto' },
      voceCorrenteAttiva: true,
    })
    await flushPromises()
    const voci = opzioni(w)
    expect(voci).toHaveLength(3)
    expect(voci[2]).toEqual({ codice_interno: 'RF03', codice: 'RF03', descrizione: 'Trasporto' })
  })

  // La voce valida non aspetta l'elenco: con la lettura fallita (o in corso)
  // il campo non resta vuoto con un valore dentro.
  it('con voceCorrenteAttiva la voce c\'e\' anche a elenco non caricato', async () => {
    const voce = { codice_interno: 'RF03', codice: 'RF03', descrizione: 'Trasporto' }
    const w = montaCon(
      { modelValue: 'RF03', voceCorrente: voce, voceCorrenteAttiva: true },
      { fetcher: () => Promise.reject(new Error('rete')) },
    )
    await flushPromises()
    expect(opzioni(w)).toEqual([voce])
  })

  it('senza voceCorrente l\'elenco e\' quello di sempre', async () => {
    const w = montaCon({ modelValue: 'RF01' })
    await flushPromises()
    expect(opzioni(w)).toEqual(ATTIVE)
  })
})
