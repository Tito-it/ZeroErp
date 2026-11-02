// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Presidio di `scorciatoie.js`: il nome del tasto viene dai locales
//        (anche per lingua), la variante Mac vale solo se esiste, e ogni
//        tasto dichiarato ha la sua chiave in it ed en.
// ------------------------------------------------------------
import { describe, expect, it } from 'vitest'
import { createI18n } from 'vue-i18n'
import it_ from '../../locales/it.json'
import en from '../../locales/en.json'
import { TASTO, conScorciatoia, nomeTasto } from './scorciatoie'

function lingua(messages) {
  const i18n = createI18n({ legacy: false, locale: 'x', messages: { x: messages } })
  return { t: i18n.global.t, te: i18n.global.te }
}

describe('scorciatoie', () => {
  it('ogni tasto dichiarato ha il suo nome in it ed en', () => {
    for (const codice of Object.values(TASTO)) {
      expect(it_.common.tasti[codice]).toBeTruthy()
      expect(en.common.tasti[codice]).toBeTruthy()
    }
  })

  it('il nome del tasto e la forma vengono dai locales della lingua', () => {
    const { t, te } = lingua({
      common: { con_scorciatoia: '{azione} [{tasto}]', tasti: { SALVA: 'Strg+S' } },
    })
    expect(conScorciatoia(t, te, 'Speichern', TASTO.SALVA, false)).toBe('Speichern [Strg+S]')
  })

  it('su Mac la variante _MAC se c\'e\', altrimenti il nome comune', () => {
    const { t, te } = lingua({ common: { tasti: { SALVA: 'Ctrl+S', SALVA_MAC: '⌘S', ESC: 'Esc' } } })
    expect(nomeTasto(t, te, TASTO.SALVA, true)).toBe('⌘S')
    expect(nomeTasto(t, te, TASTO.ESC, true)).toBe('Esc')
    expect(nomeTasto(t, te, TASTO.SALVA, false)).toBe('Ctrl+S')
  })

  it('nessun testo dei locales scrive un tasto fra parentesi: lo aggiunge la sede', () => {
    // 🔴 «Ricarica lista (F5)» era scritto nel testo, e col tooltip della
    //    sede diventava «Ricarica lista (F5) (F5)» (2026-10-04).
    const TASTO_SCRITTO = /\((F\d{1,2}|Esc|Ctrl\+\w|⌘\w)\)/
    const trovati = []
    function visita(nodo, percorso) {
      if (typeof nodo === 'string') {
        if (TASTO_SCRITTO.test(nodo)) trovati.push(percorso)
      } else if (nodo && typeof nodo === 'object') {
        for (const [k, v] of Object.entries(nodo)) visita(v, `${percorso}.${k}`)
      }
    }
    visita(it_, 'it')
    visita(en, 'en')
    expect(trovati).toEqual([])
  })
})
