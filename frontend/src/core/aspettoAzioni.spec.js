// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa la mappa `verbo -> { icona, severity }` delle azioni di stato
//        (brief-db-icone-azioni-per-significato: D-1 e §6.4 riaperta, Tid
//        2026-09-27). Il DB manda il verbo e non come si disegna: un verbo
//        senza voce qui non darebbe errore, mostrerebbe il ripiego.
//
// Indice test:
//  1. ogni verbo noto delle `fn_available_actions_*` ha la sua voce
//  2. ogni icona e' una costante di MANAGE_ICONS, ogni severity e' ammessa
//  3. le decisioni di Tid del 2026-09-27
//  4. verbo sconosciuto o assente -> ripiego visibile, mai undefined
// ------------------------------------------------------------
import { describe, it, expect } from 'vitest'
import { MANAGE_ICONS } from './constants'
import { ASPETTO_AZIONE, RIPIEGO, aspettoAzione } from './aspettoAzioni'

// I verbi che il DB emette, dall'inventario del brief (§6.1 e §6.2): quindici
// dalle matrici di transizione e cinque scritti nelle funzioni. Un verbo nuovo
// a DB entra QUI e nella mappa, insieme.
const VERBI_DB = [
  'annulla', 'accetta', 'conferma', 'emetti', 'spedisci', 'consegna', 'reso',
  'rifiuta', 'attiva', 'cessa', 'rendi_pronta', 'chiudi', 'riapri', 'numera',
  'riporta_a_draft',
  'ristampa', 'crea_revisione', 'push_commessa', 'push_contratto', 'genera_ordine',
]

// Le severity dei pulsanti PrimeVue che le barre sanno rendere.
const SEVERITY = ['success', 'info', 'warn', 'danger', 'secondary']

describe('aspettoAzioni', () => {
  it('1) ogni verbo noto ha la sua voce, e la mappa non ne ha di orfane', () => {
    expect(Object.keys(ASPETTO_AZIONE).sort()).toEqual([...VERBI_DB].sort())
  })

  it('2) icona da MANAGE_ICONS, severity fra quelle ammesse', () => {
    const costanti = new Set(Object.values(MANAGE_ICONS))
    const fuori = [...Object.entries(ASPETTO_AZIONE), ['RIPIEGO', RIPIEGO]]
      .filter(([, a]) => !costanti.has(a.icona) || !SEVERITY.includes(a.severity))
      .map(([k]) => k)
    expect(fuori).toEqual([])
  })

  it('3) le decisioni di Tid del 2026-09-27', () => {
    expect(aspettoAzione('emetti').icona).toBe(MANAGE_ICONS.SEND)
    expect(aspettoAzione('numera').icona).toBe(MANAGE_ICONS.NUMERA)
    // `riapri` e `riporta_a_draft`: lo stesso gesto, in tutto.
    expect(aspettoAzione('riapri')).toEqual(aspettoAzione('riporta_a_draft'))
    expect(aspettoAzione('riapri')).toEqual({ icona: MANAGE_ICONS.RIPORTA_A_BOZZA, severity: 'warn' })
    expect(aspettoAzione('conferma').severity).toBe('info')
    // Nel preventivo `emetti` e il push stanno nello stesso drawer.
    expect(aspettoAzione('push_commessa').icona).toBe(MANAGE_ICONS.INVIA_A_COMMESSA)
    expect(aspettoAzione('push_commessa').icona).not.toBe(aspettoAzione('emetti').icona)
  })

  it('4) verbo sconosciuto o assente -> ripiego', () => {
    expect(aspettoAzione('verbo_nuovo')).toBe(RIPIEGO)
    expect(aspettoAzione(undefined)).toBe(RIPIEGO)
    // Un nome del prototipo non e' un verbo.
    expect(aspettoAzione('toString')).toBe(RIPIEGO)
  })
})
