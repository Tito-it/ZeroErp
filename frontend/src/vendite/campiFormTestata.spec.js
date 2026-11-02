// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: presidio delle liste `CAMPI_FORM_TESTATA_*` (brief-db-testata-dopo-
//        emissione, R-FE-3). `useTestataDocumento` dice «testata modificabile»
//        se almeno uno dei campi che il form MOSTRA e' aperto: una lista che
//        dimentica un campo lo lascerebbe spento a vita fuori bozza, una che
//        ne ha uno in piu' accenderebbe un «Salva» sopra un form tutto spento.
//        Nessuno dei due casi da' un errore: lo da' questo test.
//
// Indice test:
//   1) ogni lista dice gli stessi campi che il suo form spegne campo per campo
//      (`isLocked('…')` nei form, `testata.bloccato('…')` nei form inline)
//   (il reso e' fra questi dal 2026-10-12: col magazzino di rientro ha due
//    campi, e spegne per campo come gli altri — piano-be-fe-magazzino-lotto-3 A2)
//   2) ogni consumatore di `useTestataDocumento` e' in questo elenco
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'
import { CAMPI_FORM_TESTATA_ORDINE } from './ordini/constants'
import { CAMPI_FORM_TESTATA_DDT } from './ddt/constants'
import { CAMPI_FORM_TESTATA_RESO } from './resi/constants'
import { CAMPI_FORM_TESTATA_OFFERTA } from './offerte/constants'
import { CAMPI_FORM_TESTATA_CONTRATTO, CAMPI_FORM_TESTATA_PREVENTIVO } from './constants'

const sorgenti = import.meta.glob(['./**/*.vue'], {
  query: '?raw', import: 'default', eager: true,
})

function sorgente(percorso) {
  const testo = sorgenti[percorso]
  if (testo === undefined) throw new Error(`sorgente non trovato: ${percorso}`)
  return testo
}

function campiSpenti(testo, funzione) {
  const re = new RegExp(`${funzione}\\('([a-z_]+)'\\)`, 'g')
  return [...new Set([...testo.matchAll(re)].map((m) => m[1]))].sort()
}

// drawer → (lista, file del form, funzione con cui spegne i campi)
const FORM = [
  { drawer: './ordini/components/OrdiniDrawer.vue', campi: CAMPI_FORM_TESTATA_ORDINE, form: './ordini/components/OrdiniForm.vue', spegne: 'isLocked' },
  { drawer: './ddt/components/DdtDrawer.vue', campi: CAMPI_FORM_TESTATA_DDT, form: './ddt/components/DdtForm.vue', spegne: 'isLocked' },
  { drawer: './preventivi/components/PreventiviDrawer.vue', campi: CAMPI_FORM_TESTATA_PREVENTIVO, form: './preventivi/components/PreventiviForm.vue', spegne: 'isLocked' },
  { drawer: './offerte/components/OffertaDrawer.vue', campi: CAMPI_FORM_TESTATA_OFFERTA, form: './offerte/components/OffertaDrawer.vue', spegne: 'testata\\.bloccato' },
  { drawer: './components/ContrattoDrawer.vue', campi: CAMPI_FORM_TESTATA_CONTRATTO, form: './components/ContrattoDrawer.vue', spegne: 'testata\\.bloccato' },
  { drawer: './resi/components/ResoDrawer.vue', campi: CAMPI_FORM_TESTATA_RESO, form: './resi/components/ResoForm.vue', spegne: 'isLocked' },
]

describe('CAMPI_FORM_TESTATA_*', () => {
  it.each(FORM)('1) $drawer: la lista e il form dicono gli stessi campi', ({ campi, form, spegne }) => {
    expect([...campi].sort()).toEqual(campiSpenti(sorgente(form), spegne))
  })

  it('2) ogni consumatore di useTestataDocumento e\' qui', () => {
    const consumatori = Object.entries(sorgenti)
      .filter(([, testo]) => /\buseTestataDocumento\(/.test(testo))
      .map(([percorso]) => percorso)
      .sort()
    expect(consumatori).toEqual(FORM.map((f) => f.drawer).sort())
  })
})
