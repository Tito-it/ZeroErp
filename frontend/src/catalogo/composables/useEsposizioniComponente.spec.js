// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il contratto di `useEsposizioniComponente` (2026-10-02,
//        regola del 2 su distinta, pannello e dialog dei componenti): il
//        lookup e' `config.esposizioni_componente` chiavato su
//        `codice_interno` (il valore che la FK della distinta valida e che
//        le anteprime portano), le etichette vengono dalla riga
//        (`etichetta_key`), un codice sconosciuto resta leggibile, e la
//        gravita' del Tag distingue il solo NASCOSTO.
// Note: `useLookupEtichettato` finto: qui si prova la configurazione che il
//       composable gli passa e la resa che ne esce, non la fetch (quella e'
//       presidiata da `useLookupEtichettato.spec.js`).
// ------------------------------------------------------------

import { describe, it, expect, vi } from 'vitest'
import { computed } from 'vue'

const chiamate = []
const MODI = [
  { codice_interno: 'NASCOSTO', label: 'Nascosto' },
  { codice_interno: 'DESCRITTIVO', label: 'Descrittivo, senza prezzo' },
  { codice_interno: 'VALORIZZATO', label: 'Valorizzato, con prezzo' },
]
vi.mock('../../core/composables/useLookupEtichettato', () => ({
  useLookupEtichettato: (sorgente, opzioni) => {
    chiamate.push({ sorgente, opzioni })
    const perCodice = new Map(MODI.map((m) => [m.codice_interno, m.label]))
    return {
      opzioni: computed(() => MODI.map((m) => ({ value: m.codice_interno, label: m.label }))),
      etichetta: (codice) => (codice == null ? '' : perCodice.get(codice) ?? codice),
      loading: computed(() => false),
      loaded: computed(() => true),
    }
  },
}))

const { useEsposizioniComponente, severitaEsposizione, ESPOSIZIONE_NASCOSTO } =
  await import('./useEsposizioniComponente')

describe('useEsposizioniComponente', () => {
  // 1. Il lookup giusto, chiavato sul codice che la FK valida.
  it('chiede config.esposizioni_componente su codice_interno', () => {
    useEsposizioniComponente()
    const ultima = chiamate.at(-1)
    expect(ultima.sorgente).toEqual({ rel: 'config.esposizioni_componente' })
    expect(ultima.opzioni.campoCodice).toBe('codice_interno')
  })

  // 2. Le tre opzioni della tendina, coi codici come valore.
  it('le opzioni portano il codice come valore e l etichetta tradotta', () => {
    const { opzioni } = useEsposizioniComponente()
    expect(opzioni.value.map((o) => o.value)).toEqual(['NASCOSTO', 'DESCRITTIVO', 'VALORIZZATO'])
    expect(opzioni.value[2].label).toBe('Valorizzato, con prezzo')
  })

  // 3. La cella: etichetta per esteso, codice grezzo se sconosciuto.
  it('etichetta per esteso, ripiego sul codice', () => {
    const { etichetta } = useEsposizioniComponente()
    expect(etichetta('DESCRITTIVO')).toBe('Descrittivo, senza prezzo')
    expect(etichetta('NUOVO_MODO')).toBe('NUOVO_MODO')
  })

  // 4. Il Tag: compare in fattura (info) contro nel totale del kit (secondary).
  it('la gravita distingue il solo NASCOSTO', () => {
    expect(ESPOSIZIONE_NASCOSTO).toBe('NASCOSTO')
    expect(severitaEsposizione('NASCOSTO')).toBe('secondary')
    expect(severitaEsposizione('DESCRITTIVO')).toBe('info')
    expect(severitaEsposizione('VALORIZZATO')).toBe('info')
    expect(severitaEsposizione(null)).toBe('secondary')
  })
})
