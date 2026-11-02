// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Un caso per RAMO di `widgetPerColonna` (drawer generico del pannello
//        config, 2026-09-21): FK ammessa al lookup, FK non ammessa, data,
//        boolean/number/json/text e il ripiego — e la chiave dell'etichetta.
//        Sono i rami che, sbagliati, non falliscono: rendono un id grezzo dove
//        serviva una tendina, o una casella dove serviva un calendario.
// ------------------------------------------------------------
import { describe, it, expect } from 'vitest'
import { PREFISSO_CAMPI, PREFISSO_TABELLE, WIDGET, chiaveEtichettaCampo, chiaveEtichettaTabella, widgetPerColonna } from './campoConfig'

describe('widgetPerColonna', () => {
  it('FK verso una tabella ammessa al lookup: LookupSelect, qualunque sia il tipo', () => {
    expect(widgetPerColonna({ name: 'tipo_id', type: 'number', references: 'config.tipi_ubicazione', references_lookup: true }))
      .toBe(WIDGET.LOOKUP)
  })

  it('FK verso una tabella NON ammessa: numero dichiarato, non un lookup vuoto', () => {
    expect(widgetPerColonna({ name: 'indirizzo_dettaglio_id', type: 'number', references: 'anagrafiche.indirizzi_dettaglio', references_lookup: false }))
      .toBe(WIDGET.FK_ID)
  })

  it('la FK vince sul tipo: un uuid verso una tabella ammessa e\' comunque un lookup', () => {
    expect(widgetPerColonna({ name: 'x_id', type: 'text', references: 'config.stati', references_lookup: true }))
      .toBe(WIDGET.LOOKUP)
  })

  it('date → DatePicker (fino al 21-09 cadeva nel ramo testo)', () => {
    expect(widgetPerColonna({ name: 'obsoleto_dal', type: 'date', references: null })).toBe(WIDGET.DATE)
  })

  it('i tipi semplici e il ripiego su testo', () => {
    expect(widgetPerColonna({ name: 'attivo', type: 'boolean', references: null })).toBe(WIDGET.BOOLEAN)
    expect(widgetPerColonna({ name: 'ordine', type: 'number', references: null })).toBe(WIDGET.NUMBER)
    expect(widgetPerColonna({ name: 'meta', type: 'json', references: null })).toBe(WIDGET.JSON)
    expect(widgetPerColonna({ name: 'codice', type: 'text', references: null })).toBe(WIDGET.TEXT)
    expect(widgetPerColonna({ name: 'data_x', type: 'datetime' })).toBe(WIDGET.TEXT)
  })
})

describe('chiaveEtichettaTabella', () => {
  it('e\' il prefisso piu\' la rel: il punto e\' il separatore di vue-i18n', () => {
    expect(chiaveEtichettaTabella('config.ambiti')).toBe(`${PREFISSO_TABELLE}.config.ambiti`)
  })
})

describe('chiaveEtichettaCampo', () => {
  it('e\' il prefisso piu\' il nome fisico della colonna', () => {
    expect(chiaveEtichettaCampo({ name: 'consente_stock_negativo' }))
      .toBe(`${PREFISSO_CAMPI}.consente_stock_negativo`)
  })
})
