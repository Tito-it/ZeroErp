// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: le tendine erogazione/fonte del form delle righe mettono in forma le
//        combinazioni che il DB dichiara per l'articolo, senza aggiungere ne'
//        togliere niente (brief-db-offerta-emissione-ed-erogazione B-R4).
// Note: le combinazioni hanno la forma di quelle di un articolo SERVIZI letto da
//        `vendite.fn_documento_riga_erogazioni`, nel suo ordine (default in
//        testa, poi erogazione e fonte): una forma d'esempio, non una regola.
//        Fino al 2026-10-21 l'esempio era un composito con la
//        DERIVATA_COMPONENTI, ritirata (I-D1).
//
// Indice test:
//  1. erogazioni: quelle dell'articolo, una volta sola, nell'ordine del DB
//  2. fonti: solo quelle ammesse con l'erogazione scelta
//  3. il valore gia' scritto sulla riga resta fra le opzioni
//  4. il default e' la combinazione `e_default`; nessuna → null
//  5. cambio d'erogazione: la fonte resta se ancora ammessa, l'unica se sola,
//     altrimenti vuota (il form non sceglie fra piu' fonti)
//  6. nessuna combinazione (articolo fuori dalla utility): tendine vuote
// ------------------------------------------------------------
import { describe, it, expect } from 'vitest'
import {
  combinazioneDefault, fonteDopoCambioErogazione, opzioniErogazione, opzioniFonte,
} from './erogazioniRiga'

const c = (tipo, fonte, eDefault = false) => ({
  tipo_erogazione: tipo, fonte_quantita_attesa: fonte, e_default: eDefault,
})

// Nell'ordine del DB (`ordine` di vendite.fn_articolo_erogazioni): il default in
// testa, poi per erogazione e fonte.
const COMBINAZIONI = [
  c('UNA_TANTUM', 'FISSA', true),
  c('CANONE', 'FISSA'),
  c('CONSUMO', 'MANUALE'),
  c('CONSUMO', 'LETTURE'),
  c('UNA_TANTUM', 'MANUALE'),
]

const etichetta = (v) => `label:${v}`
const valori = (opzioni) => opzioni.map((o) => o.value)

describe('erogazioniRiga', () => {
  it("1. erogazioni: quelle dell'articolo, una volta sola, nell'ordine del DB", () => {
    const opz = opzioniErogazione(COMBINAZIONI, null, etichetta)
    expect(valori(opz)).toEqual(['UNA_TANTUM', 'CANONE', 'CONSUMO'])
    expect(opz[0].label).toBe('label:UNA_TANTUM')
  })

  it("2. fonti: solo quelle ammesse con l'erogazione scelta", () => {
    expect(valori(opzioniFonte(COMBINAZIONI, 'CONSUMO', null, etichetta)))
      .toEqual(['MANUALE', 'LETTURE'])
    expect(valori(opzioniFonte(COMBINAZIONI, null, null, etichetta))).toEqual([])
  })

  it('3. il valore gia\' scritto sulla riga resta fra le opzioni', () => {
    expect(valori(opzioniErogazione(COMBINAZIONI, 'ORARIO', etichetta)))
      .toEqual(['UNA_TANTUM', 'CANONE', 'CONSUMO', 'ORARIO'])
    expect(valori(opzioniFonte(COMBINAZIONI, 'CONSUMO', 'TIMESHEET', etichetta)))
      .toEqual(['MANUALE', 'LETTURE', 'TIMESHEET'])
    // Un valore ammesso non si ripete.
    expect(valori(opzioniFonte(COMBINAZIONI, 'CONSUMO', 'MANUALE', etichetta)))
      .toEqual(['MANUALE', 'LETTURE'])
  })

  it("4. il default e' la combinazione `e_default`; nessuna → null", () => {
    expect(combinazioneDefault(COMBINAZIONI)).toEqual(c('UNA_TANTUM', 'FISSA', true))
    expect(combinazioneDefault([c('CANONE', 'FISSA')])).toBeNull()
    expect(combinazioneDefault(null)).toBeNull()
  })

  it("5. cambio d'erogazione: resta se ammessa, altrimenti la prima del DB", () => {
    expect(fonteDopoCambioErogazione(COMBINAZIONI, 'CANONE', 'FISSA')).toBe('FISSA')
    expect(fonteDopoCambioErogazione([c('CANONE', 'FISSA')], 'CANONE', 'MANUALE')).toBe('FISSA')
    // Piu' fonti ammesse e la corrente no: la prima della lista del DB, cioe'
    // quella che il trigger d'eredita' scriverebbe (§D.4 punto 1).
    expect(fonteDopoCambioErogazione(COMBINAZIONI, 'CONSUMO', 'FISSA')).toBe('MANUALE')
    expect(fonteDopoCambioErogazione(COMBINAZIONI, 'CANONE', 'MANUALE')).toBe('FISSA')
  })

  it('6. nessuna combinazione (articolo fuori dalla utility): tendine vuote', () => {
    expect(opzioniErogazione([], null, etichetta)).toEqual([])
    expect(opzioniFonte([], 'CANONE', null, etichetta)).toEqual([])
    expect(fonteDopoCambioErogazione([], 'CANONE', 'FISSA')).toBeNull()
  })
})
