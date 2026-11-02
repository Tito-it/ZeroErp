// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: L'indirizzo libero nel form: la forma decisa dal flag dello stato, la
//        validazione e il payload (specchio del guard
//        `trgfn_indirizzi_guard_forma_libera`, D-2 di Tid, 2026-10-18).
//
// Indice test:
//   1) la forma la decide il flag dello stato, non il codice
//   2) forma del catalogo: comune e CAP obbligatori, nell'ordine del guard
//   3) forma estera: la localita' obbligatoria, il resto facoltativo
//   4) senza stato manca lo stato, e non si giudica altro; uno stato che la
//      tendina non porta (non caricata) non si indovina: manca lo stato
//   5) il payload porta solo i campi della forma dello stato, vuoti a null
//   6) campiLiberi completa coi vuoti
// ------------------------------------------------------------

import { describe, expect, it } from 'vitest'
import {
  campiLiberi, isFormaCatalogo, payloadLibero, statoDi, validaLibero,
} from './indirizzoLibero'

const ITALIA = { id: 1, codice_iso2: 'IT', catalogo_comuni_completo: true }
const GERMANIA = { id: 2, codice_iso2: 'DE', catalogo_comuni_completo: false }

describe('indirizzoLibero', () => {
  it('1) la forma la decide il flag dello stato', () => {
    expect(isFormaCatalogo(ITALIA)).toBe(true)
    expect(isFormaCatalogo(GERMANIA)).toBe(false)
    expect(isFormaCatalogo({ codice_iso2: 'IT' })).toBe(false)
    expect(isFormaCatalogo(null)).toBe(false)
    expect(statoDi([ITALIA, GERMANIA], 2)).toBe(GERMANIA)
    expect(statoDi(undefined, 2)).toBeNull()
  })

  it('2) forma del catalogo: comune e CAP', () => {
    const dati = { indirizzo_libero: 'Localita Prato', stato_id: 1, locality: 'X' }
    expect(validaLibero(dati, ITALIA)).toEqual(['comune_id', 'codice_postale_id'])
    expect(validaLibero({ ...dati, comune_id: 5, codice_postale_id: 9 }, ITALIA)).toEqual([])
  })

  it('3) forma estera: la localita\'', () => {
    const dati = { indirizzo_libero: 'Hauptstrasse 5', stato_id: 2, locality: '  ' }
    expect(validaLibero(dati, GERMANIA)).toEqual(['locality'])
    expect(validaLibero({ ...dati, locality: 'Berlin' }, GERMANIA)).toEqual([])
  })

  it('4) senza stato manca lo stato', () => {
    expect(validaLibero({ indirizzo_libero: '' }, null)).toEqual(['indirizzo_libero', 'stato_id'])
    // Stato scelto ma la sua riga non c'e': ne' 'comune_id' ne' 'locality'.
    expect(validaLibero({ indirizzo_libero: 'Via Roma 1', stato_id: 1 }, null)).toEqual(['stato_id'])
  })

  it('5) il payload porta solo la forma dello stato', () => {
    const dati = {
      indirizzo_libero: ' Via 1 ', stato_id: 1, comune_id: 5, codice_postale_id: 9,
      locality: 'X', postal_code: '00100', administrative_area: 'RM', sublocality: '',
    }
    expect(payloadLibero(dati, ITALIA)).toEqual({
      indirizzo_libero: 'Via 1', stato_id: 1, sublocality: null, comune_id: 5, codice_postale_id: 9,
    })
    expect(payloadLibero({ ...dati, stato_id: 2 }, GERMANIA)).toEqual({
      indirizzo_libero: 'Via 1', stato_id: 2, sublocality: null,
      locality: 'X', postal_code: '00100', administrative_area: 'RM',
    })
  })

  it('6) campiLiberi completa coi vuoti', () => {
    expect(campiLiberi({ locality: 'Berlin', stato_id: null })).toEqual({
      indirizzo_libero: '', stato_id: null, locality: 'Berlin',
      postal_code: '', administrative_area: '', sublocality: '',
    })
  })
})
