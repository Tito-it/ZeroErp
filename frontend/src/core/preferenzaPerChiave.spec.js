// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: il BB della preferenza per chiave (`core/preferenzaPerChiave`).
//
// Indice test:
//   1. nessuna preferenza, nulla toccato: nessuna chiave
//   2. toccata una chiave: solo quella (le altre restano allo standard)
//   3. le chiavi gia' della preferenza restano, anche non toccate
//   4. null = «come lo standard»: si toglie anche se veniva dalla preferenza
//   5. chiavi fuori elenco ignorate; config assente → nessuna chiave
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'
import { chiaviScelte } from './preferenzaPerChiave'

const CHIAVI = ['colonne', 'ordinamento', 'filtri', 'pagina_dimensione']

function caricata(origine = {}) {
  return {
    colonne: [{ codice: 'codice', visibile: true }],
    ordinamento: [{ col: 'codice', dir: 'asc' }],
    filtri: {},
    pagina_dimensione: 10,
    colonne_nuove: 0,
    origine: {
      colonne: 'sistema', ordinamento: 'sistema', filtri: 'sistema', pagina_dimensione: 'sistema',
      ...origine,
    },
  }
}

const clona = (o) => JSON.parse(JSON.stringify(o))

describe('chiaviScelte', () => {
  it('1. nessuna preferenza, nulla toccato: nessuna chiave', () => {
    const snap = caricata()
    expect(chiaviScelte(clona(snap), snap, CHIAVI)).toEqual({})
  })

  it('2. toccata una chiave: solo quella', () => {
    const snap = caricata()
    const config = clona(snap)
    config.colonne = [{ codice: 'codice', visibile: false }]
    expect(chiaviScelte(config, snap, CHIAVI)).toEqual({ colonne: config.colonne })
  })

  it('3. le chiavi gia\' della preferenza restano, anche non toccate', () => {
    const snap = caricata({ colonne: 'preferenza' })
    const config = clona(snap)
    config.pagina_dimensione = 50
    expect(chiaviScelte(config, snap, CHIAVI)).toEqual({
      colonne: snap.colonne,
      pagina_dimensione: 50,
    })
  })

  it('4. null = come lo standard, anche se veniva dalla preferenza', () => {
    const snap = caricata({ colonne: 'preferenza', pagina_dimensione: 'preferenza' })
    const config = clona(snap)
    config.pagina_dimensione = null
    expect(chiaviScelte(config, snap, CHIAVI)).toEqual({ colonne: snap.colonne })
  })

  it('5. chiavi fuori elenco ignorate; config assente', () => {
    const snap = caricata()
    const config = clona(snap)
    config.colonne_nuove = 3
    expect(chiaviScelte(config, snap, CHIAVI)).toEqual({})
    expect(chiaviScelte(null, snap, CHIAVI)).toEqual({})
  })
})
