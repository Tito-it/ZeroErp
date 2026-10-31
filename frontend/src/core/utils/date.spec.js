// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Test di `core/utils/date.js` sul FUSO DELL'AZIENDA (brief
//        un-solo-fuso-aziendale F-1/F-2/F-4): «oggi», l'ora mostrata, il
//        giorno di un istante e l'ora digitata sono quelli dell'azienda, non
//        del PC. Il processo dei test gira a Pago Pago (−11, `vite.config.js`)
//        e l'azienda e' a Roma: gli istanti di confine si COSTRUISCONO.
//
// Indice test:
//  1. il processo dei test e' davvero in un fuso ostile
//  2. oggi: le 23:30 UTC sono gia' domani a Roma (e ancora ieri a New York)
//  3. ore a video nel fuso dell'azienda (estate e inverno)
//  4. il giorno di un istante, anche dentro `displayDate`
//  5. l'ora digitata nel DatePicker e l'istante, andata e ritorno
//  6. il cambio legale: l'ora che non esiste diventa quella dopo il salto
//  7. addDaysToToday, giornoDi, toMeseString, giorno della settimana
//  8. un fuso sconosciuto al browser non si imposta
// ------------------------------------------------------------
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import {
  addDaysToToday, displayDate, displayTime, displayTimestamp, fusoAziendale,
  giornoAziendale, giornoDi, impostaFusoAziendale, istanteComeOraAziendale,
  nomeGiornoSettimana, nomiMesi, oggiAziendale, oggiAziendaleString, oraAziendaleComeIstante,
  toDateString, toMeseString,
} from './date'

// Scopo: ferma l'orologio all'istante `iso`.
function adessoE(iso) {
  vi.setSystemTime(new Date(iso))
}

describe('date nel fuso dell\'azienda', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    impostaFusoAziendale('Europe/Rome')
  })
  afterEach(() => {
    vi.useRealTimers()
    impostaFusoAziendale(null)
  })

  it('il processo dei test e\' davvero in un fuso ostile', () => {
    expect(Intl.DateTimeFormat().resolvedOptions().timeZone).toBe('Pacific/Pago_Pago')
  })

  it('oggi: le 23:30 UTC sono gia\' domani a Roma (e ancora ieri a New York)', () => {
    adessoE('2026-09-14T23:30:00Z')
    expect(oggiAziendaleString()).toBe('2026-09-15')
    expect(toDateString(oggiAziendale())).toBe('2026-09-15')
    impostaFusoAziendale('America/New_York')
    adessoE('2026-09-15T02:00:00Z')
    expect(oggiAziendaleString()).toBe('2026-09-14')
  })

  it('ore a video nel fuso dell\'azienda (estate e inverno)', () => {
    expect(displayTimestamp('2026-09-14T09:47:32Z')).toBe('14/09/2026, 11:47:32')
    expect(displayTime('2026-09-14T09:47:32Z')).toBe('11:47')
    expect(displayTimestamp('2026-01-15T09:00:00+00:00')).toBe('15/01/2026, 10:00:00')
    expect(displayTimestamp('non una data')).toBe('')
  })

  it('il giorno di un istante, anche dentro `displayDate`', () => {
    expect(giornoAziendale('2026-09-14T23:30:00Z')).toBe('2026-09-15')
    expect(displayDate('2026-09-14T23:30:00Z')).toBe('15/09/2026')
    // La forma di un `timestamptz::text` (spazio, offset `+00`) e' un istante uguale.
    expect(displayDate('2026-09-14 23:30:00+00')).toBe('15/09/2026')
    // Una data senza ora non si sposta.
    expect(displayDate('2026-09-14')).toBe('14/09/2026')
  })

  it('l\'ora digitata nel DatePicker e l\'istante, andata e ritorno', () => {
    const inverno = oraAziendaleComeIstante(new Date(2026, 0, 15, 10, 0))
    expect(inverno.toISOString()).toBe('2026-01-15T09:00:00.000Z')
    const estate = oraAziendaleComeIstante(new Date(2026, 6, 15, 10, 0))
    expect(estate.toISOString()).toBe('2026-07-15T08:00:00.000Z')
    const orologio = istanteComeOraAziendale('2026-07-15T08:00:00Z')
    expect([orologio.getHours(), orologio.getMinutes()]).toEqual([10, 0])
    expect(oraAziendaleComeIstante(orologio).toISOString()).toBe('2026-07-15T08:00:00.000Z')
  })

  it('il cambio legale: l\'ora che non esiste diventa quella dopo il salto', () => {
    // A Roma il 29/03/2026 le 02:00 diventano 03:00: le 02:30 non esistono.
    expect(oraAziendaleComeIstante(new Date(2026, 2, 29, 2, 30)).toISOString())
      .toBe('2026-03-29T01:30:00.000Z')
    // Il 25/10/2026 le 03:00 tornano 02:00: le 01:30 esistono una volta sola.
    expect(oraAziendaleComeIstante(new Date(2026, 9, 25, 1, 30)).toISOString())
      .toBe('2026-10-24T23:30:00.000Z')
  })

  it('addDaysToToday, giornoDi, toMeseString, giorno della settimana', () => {
    adessoE('2026-09-14T23:30:00Z')
    expect(toDateString(addDaysToToday(0))).toBe('2026-09-15')
    expect(toDateString(addDaysToToday(1))).toBe('2026-09-16')
    expect(toDateString(giornoDi('2026-09-14'))).toBe('2026-09-14')
    expect(toDateString(giornoDi(new Date(2026, 8, 14, 18, 30)))).toBe('2026-09-14')
    expect(giornoDi(null)).toBeNull()
    expect(toMeseString(new Date(2026, 8, 14))).toBe('2026-09')
    expect(toMeseString('2026-09-14')).toBe('2026-09')
    expect(nomeGiornoSettimana(0, 'it-IT')).toBe('lunedì')
    expect(nomiMesi('it-IT')).toHaveLength(12)
    expect(nomiMesi('it-IT')[0]).toBe('gennaio')
    expect(nomiMesi('it-IT')[11]).toBe('dicembre')
  })

  it('un fuso sconosciuto al browser non si imposta', () => {
    const errore = vi.spyOn(console, 'error').mockImplementation(() => {})
    impostaFusoAziendale('Marte/Olympus')
    expect(fusoAziendale()).toBeNull()
    expect(errore).toHaveBeenCalled()
    errore.mockRestore()
  })
})
