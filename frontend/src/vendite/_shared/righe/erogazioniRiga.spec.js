// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: le tendine erogazione/fonte del form delle righe mettono in forma le
//        combinazioni che il DB dichiara per l'articolo, senza aggiungere ne'
//        togliere niente (brief-db-offerta-emissione-ed-erogazione B-R4).
// Note: le combinazioni sono quelle di un articolo composito SERVIZI letto da
//        `vendite.fn_documento_riga_erogazioni` su dbdev il 2026-10-07, nel suo
//        ordine (default in testa, poi erogazione e fonte): un fatto datato,
//        usato come forma d'esempio, non come regola.
//
// Indice test:
//  1. erogazioni: quelle dell'articolo, una volta sola, nell'ordine del DB
//  2. fonti: solo quelle ammesse con l'erogazione scelta
//  3. il valore gia' scritto sulla riga resta fra le opzioni (B-D6)
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

const COMBINAZIONI = [
  c('UNA_TANTUM', 'FISSA', true),
  c('CANONE', 'DERIVATA_COMPONENTI'),
  c('CANONE', 'FISSA'),
  c('CONSUMO', 'DERIVATA_COMPONENTI'),
  c('CONSUMO', 'MANUALE'),
  c('UNA_TANTUM', 'DERIVATA_COMPONENTI'),
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
      .toEqual(['DERIVATA_COMPONENTI', 'MANUALE'])
    expect(valori(opzioniFonte(COMBINAZIONI, null, null, etichetta))).toEqual([])
  })

  it('3. il valore gia\' scritto sulla riga resta fra le opzioni (B-D6)', () => {
    expect(valori(opzioniErogazione(COMBINAZIONI, 'ORARIO', etichetta)))
      .toEqual(['UNA_TANTUM', 'CANONE', 'CONSUMO', 'ORARIO'])
    expect(valori(opzioniFonte(COMBINAZIONI, 'CONSUMO', 'LETTURE', etichetta)))
      .toEqual(['DERIVATA_COMPONENTI', 'MANUALE', 'LETTURE'])
    // Un valore ammesso non si ripete.
    expect(valori(opzioniFonte(COMBINAZIONI, 'CONSUMO', 'MANUALE', etichetta)))
      .toEqual(['DERIVATA_COMPONENTI', 'MANUALE'])
  })

  it("4. il default e' la combinazione `e_default`; nessuna → null", () => {
    expect(combinazioneDefault(COMBINAZIONI)).toEqual(c('UNA_TANTUM', 'FISSA', true))
    expect(combinazioneDefault([c('CANONE', 'FISSA')])).toBeNull()
    expect(combinazioneDefault(null)).toBeNull()
  })

  it("5. cambio d'erogazione: resta se ammessa, l'unica se sola, altrimenti vuota", () => {
    expect(fonteDopoCambioErogazione(COMBINAZIONI, 'CANONE', 'FISSA')).toBe('FISSA')
    expect(fonteDopoCambioErogazione([c('CANONE', 'FISSA')], 'CANONE', 'MANUALE')).toBe('FISSA')
    // Due fonti ammesse e la corrente no: la sceglie l'operatore.
    expect(fonteDopoCambioErogazione(COMBINAZIONI, 'CONSUMO', 'FISSA')).toBeNull()
  })

  it('6. nessuna combinazione (articolo fuori dalla utility): tendine vuote', () => {
    expect(opzioniErogazione([], null, etichetta)).toEqual([])
    expect(opzioniFonte([], 'CANONE', null, etichetta)).toEqual([])
    expect(fonteDopoCambioErogazione([], 'CANONE', 'FISSA')).toBeNull()
  })
})
