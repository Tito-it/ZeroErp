// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Un caso per RAMO di `scegliRamoBanner` (F2-bis, 2026-09-12), piu' i
//        limiti: tutto a zero, congelato con soli esiti, precedenza delle
//        critiche vive sugli esiti. E' la rete che manca al drawer: la scelta
//        del ramo viveva dentro il componente e si provava solo a occhio.
// Note: ⛔ Niente `t()`, niente i18n: si asseriscono CHIAVE, ARGOMENTI e forma
//        PLURALE, che sono le tre cose che un `if` sbagliato scambia senza che
//        niente fallisca. ⚠️ Le chiavi qui sono quelle dei locales: se una
//        cambia, `check_i18n_keys.py` la vede da un lato e questa spec
//        dall'altro.
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'

import { LOTTO_SCHEDE } from '../../constants'
import { conteggiDaSegnalazioni, scegliRamoBanner } from './ramoBannerLotto'

const K = (nome) => `vendite.lotti.${nome}`

describe('scegliRamoBanner — giro rimediabile', () => {
  it('documenti con critica viva: una frase, sul denominatore dei presi in carico', () => {
    const r = scegliRamoBanner({ critiche: 3, documenti: 2, presi: 4, rimediabile: true })
    expect(r.scheda).toBe(LOTTO_SCHEDE.SEGNALAZIONI)
    expect(r.parti).toEqual([
      { chiave: K('segnalazioni_bloccanti_documenti'), argomenti: { n: 2, m: 4 }, plurale: 2 },
    ])
  })

  it('documenti E critiche del giro: due frasi intere, ognuna col suo plurale', () => {
    const r = scegliRamoBanner({ critiche: 3, documenti: 1, presi: 4, giro: 2, rimediabile: true })
    expect(r.parti).toEqual([
      { chiave: K('segnalazioni_bloccanti_documenti'), argomenti: { n: 1, m: 4 }, plurale: 1 },
      { chiave: K('segnalazioni_bloccanti_piu_giro'), argomenti: { k: 2 }, plurale: 2 },
    ])
  })

  it('solo critiche del giro: niente da togliere, si corregge la causa', () => {
    const r = scegliRamoBanner({ critiche: 1, giro: 1, rimediabile: true })
    expect(r.scheda).toBe(LOTTO_SCHEDE.SEGNALAZIONI)
    expect(r.parti).toEqual([
      { chiave: K('segnalazioni_bloccanti_giro'), argomenti: { k: 1 }, plurale: 1 },
    ])
  })

  it('critiche del canale FATTURA senza documento ne\' giro: la frase storica', () => {
    const r = scegliRamoBanner({ critiche: 2, rimediabile: true })
    expect(r.scheda).toBe(LOTTO_SCHEDE.SEGNALAZIONI)
    expect(r.parti).toEqual([
      { chiave: K('segnalazioni_bloccanti'), argomenti: { n: 2 }, plurale: undefined },
    ])
  })

  // ⭐ Il link va su «Presi in carico», NON su «Documenti»: se il pull e'
  //    fallito una fattura non e' mai nata, e la riga con l'esito ERRORE sta
  //    nella lista degli esiti (`gruppi`) — su Documenti non ci sarebbe.
  it('D2 — esiti in ERRORE e ZERO critiche: il ramo nuovo, e il link va su Presi in carico', () => {
    const r = scegliRamoBanner({ esitiErrore: 2, presi: 2, rimediabile: true })
    expect(r.scheda).toBe(LOTTO_SCHEDE.PRESI_IN_CARICO)
    expect(r.parti).toEqual([
      { chiave: K('segnalazioni_bloccanti_esiti'), argomenti: { n: 2 }, plurale: 2 },
    ])
  })

  it('fatture in ERRORE nel ponte senza critica viva (PRE-1): stessa specie, altro canale', () => {
    const r = scegliRamoBanner({ fattureErrore: 1, rimediabile: true })
    expect(r.scheda).toBe(LOTTO_SCHEDE.DOCUMENTI)
    expect(r.parti).toEqual([
      { chiave: K('segnalazioni_bloccanti_fatture'), argomenti: { n: 1 }, plurale: 1 },
    ])
  })

  // ⭐ LA PRECEDENZA: un documento con critica viva ha ANCHE l'esito ERRORE. Se
  //    gli esiti vincessero, la frase parlerebbe di «ultimo tentativo fallito»
  //    su un documento che ha una critica viva da leggere ADESSO — e il link
  //    porterebbe sulla scheda sbagliata.
  it('critiche vive ED esiti in errore insieme: parlano le critiche, mai la somma', () => {
    const r = scegliRamoBanner({ critiche: 2, documenti: 2, presi: 2, esitiErrore: 2, rimediabile: true })
    expect(r.scheda).toBe(LOTTO_SCHEDE.SEGNALAZIONI)
    expect(r.parti.map((p) => p.chiave)).toEqual([K('segnalazioni_bloccanti_documenti')])
    expect(r.parti[0].argomenti).toEqual({ n: 2, m: 2 })
  })

  it('tutto a zero: nessun ramo — il componente rende la frase generica, non il vuoto', () => {
    expect(scegliRamoBanner({ rimediabile: true })).toBeNull()
  })
})

describe('scegliRamoBanner — giro congelato (critiche = storia, nessun gesto)', () => {
  it('critiche: la frase al passato, plurale sulle critiche', () => {
    const r = scegliRamoBanner({ critiche: 3, documenti: 2, presi: 4, rimediabile: false })
    expect(r.scheda).toBe(LOTTO_SCHEDE.SEGNALAZIONI)
    expect(r.parti).toEqual([
      { chiave: K('segnalazioni_giro_chiuso'), argomenti: { n: 3 }, plurale: 3 },
    ])
  })

  // Il limite che il vecchio codice sbagliava per costruzione: con zero
  // critiche e soli esiti diceva «si era fermato per 0 segnalazioni critiche».
  it('soli esiti in errore: la gemella al passato, mai «0 segnalazioni critiche»', () => {
    const r = scegliRamoBanner({ esitiErrore: 1, rimediabile: false })
    expect(r.scheda).toBe(LOTTO_SCHEDE.PRESI_IN_CARICO)
    expect(r.parti).toEqual([
      { chiave: K('segnalazioni_giro_chiuso_esiti'), argomenti: { n: 1 }, plurale: 1 },
    ])
  })

  it('sole fatture in errore: la gemella al passato sul canale fattura', () => {
    const r = scegliRamoBanner({ fattureErrore: 2, rimediabile: false })
    expect(r.parti[0].chiave).toBe(K('segnalazioni_giro_chiuso_fatture'))
    expect(r.parti[0].plurale).toBe(2)
  })

  it('tutto a zero: nessun ramo', () => {
    expect(scegliRamoBanner({ rimediabile: false })).toBeNull()
  })

  // `rimediabile` e' FAIL-CLOSED: un dettaglio non ancora arrivato non conta
  // come «si puo' rimediare». Un valore mancante deve cadere sul congelato.
  it('rimediabile assente = congelato', () => {
    const r = scegliRamoBanner({ critiche: 1 })
    expect(r.parti[0].chiave).toBe(K('segnalazioni_giro_chiuso'))
  })
})

describe('conteggiDaSegnalazioni — l\'unico punto che conosce i nomi dell\'envelope', () => {
  it('legge critical_count in testa e il resto da summary, con ripiego a zero', () => {
    const segnalazioni = {
      critical_count: 2,
      summary: {
        documenti_bloccanti_count: 1,
        documenti_presi_in_carico_count: 3,
        critiche_giro_count: 0,
        fatture_stato_esecuzione_errore_count: 0,
        esiti_stato_esecuzione_errore_count: 1,
      },
    }
    expect(conteggiDaSegnalazioni(segnalazioni, true)).toEqual({
      critiche: 2, documenti: 1, presi: 3, giro: 0, fattureErrore: 0, esitiErrore: 1, rimediabile: true,
    })
  })

  it('payload assente: tutto a zero e congelato (fail-closed)', () => {
    expect(conteggiDaSegnalazioni(null, undefined)).toEqual({
      critiche: 0, documenti: 0, presi: 0, giro: 0, fattureErrore: 0, esitiErrore: 0, rimediabile: false,
    })
  })
})
