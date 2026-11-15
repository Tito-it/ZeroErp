// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: la lettura dei motivi del cambio di natura (K-7 di
//        brief-db-cambio-natura-soggetto). I motivi hanno la forma che
//        emette `anagrafiche.fn_check_cambio_natura_soggetto`.
// ------------------------------------------------------------
import { describe, it, expect } from 'vitest'
import {
  naturaSpenta, campiDaMotivi, fraseMotivo, primoMotivoBloccante,
} from './cambioNatura'

const motivo = (codice, campo, extra = {}) => ({
  codice,
  reason_key: `anagrafiche.soggetti.cambio_natura_blocco.${codice.toLowerCase()}`,
  dettaglio: { campo, soggetto_id: 'x', ...extra },
  valori: [],
})
const PIVA = motivo('PIVA_NON_APPLICABILE', 'partita_iva')
const PA = motivo('CLIENTE_PA', 'cliente_pa')
const DATI = motivo('DATI_SOCIETARI', 'tipo_soggetto_dettaglio_id')
const TITOLI = motivo('TITOLI_IVA', 'tipo_soggetto_dettaglio_id', { titoli: 2 })

describe('naturaSpenta', () => {
  it('nessun motivo: accesa', () => {
    expect(naturaSpenta([])).toBe(false)
    expect(naturaSpenta(null)).toBe(false)
  })
  it('solo motivi su campi della riga: accesa (si correggono nello stesso salvataggio)', () => {
    expect(naturaSpenta([PIVA, PA])).toBe(false)
  })
  it('un motivo fuori dal form: spenta', () => {
    expect(naturaSpenta([PIVA, DATI])).toBe(true)
  })
  it('un motivo su un campo della riga BLOCCATO: spenta (dal form non si corregge)', () => {
    expect(naturaSpenta([PIVA, PA], ['partita_iva'])).toBe(true)
    expect(naturaSpenta([PA], ['partita_iva'])).toBe(false)
  })
  it('un motivo senza dettaglio: spenta (non si sa dove correggerlo)', () => {
    expect(naturaSpenta([{ codice: 'E_X' }])).toBe(true)
  })
})

describe('campiDaMotivi', () => {
  it('solo i campi della riga', () => {
    expect([...campiDaMotivi([PIVA, PA, DATI])].sort()).toEqual(['cliente_pa', 'partita_iva'])
  })
})

describe('primoMotivoBloccante', () => {
  it('salta i motivi sui campi della riga', () => {
    expect(primoMotivoBloccante([PIVA, DATI, TITOLI])).toBe(DATI)
    expect(primoMotivoBloccante([PIVA])).toBeNull()
  })
  it('il motivo su un campo bloccato e\' bloccante', () => {
    expect(primoMotivoBloccante([PA, PIVA, DATI], ['partita_iva'])).toBe(PIVA)
  })
})

describe('fraseMotivo', () => {
  const t = (k, p) => `${k}|${JSON.stringify(p ?? null)}`
  it('la chiave del DB coi parametri con nome di dettaglio', () => {
    expect(fraseMotivo(t, () => true, TITOLI)).toBe(
      `${TITOLI.reason_key}|${JSON.stringify(TITOLI.dettaglio)}`,
    )
  })
  it('fail-visible: senza traduzione si vede il codice', () => {
    expect(fraseMotivo(t, () => false, DATI)).toBe('DATI_SOCIETARI')
  })
})
