// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Presidio della regola delle scorciatoie (`useScorciatoie`): agisce
//        solo l'UNICO iscritto a video, al livello davanti (dialog in cima,
//        poi drawer in cima, poi pagina), con l'azione visibile; F5 e Ctrl+S
//        non arrivano mai al browser sopra un lavoro aperto.
// ------------------------------------------------------------
import { describe, expect, it } from 'vitest'
import {
  SCORCIATOIE, codiceTasto, conTastoDiAzione, livelloDavanti, scegliIscritto, suTasto, tastoDiAzione,
} from './useScorciatoie'

function iscritto({ aVideo = true, davanti = true, azioni = ['reload', 'new', 'salva'], spente = [] } = {}) {
  const eseguite = []
  return {
    eseguite,
    aVideo: () => aVideo,
    davanti: () => davanti,
    azione: (k) => (azioni.includes(k) ? { key: k } : null),
    spenta: (a) => spente.includes(a.key),
    esegui: (a) => eseguite.push(a.key),
  }
}

function tasto(key, extra = {}) {
  const e = { key, ctrlKey: false, altKey: false, shiftKey: false, metaKey: false, repeat: false, ...extra }
  e.prevenuto = false
  e.preventDefault = () => { e.prevenuto = true }
  return e
}

// Un documento finto con N maschere di dialog; `contiene` = gli elementi
// dentro l'ULTIMA.
function docConDialog(contiene = []) {
  const maschera = { contains: (el) => contiene.includes(el) }
  return { querySelectorAll: () => [{ contains: () => false }, maschera] }
}
const docSenzaDialog = { querySelectorAll: () => [] }

describe('useScorciatoie', () => {
  it('la tabella: F2 F4 F5 F6 F8 F9 alle azioni di lista, Ctrl+S al Salva', () => {
    expect(SCORCIATOIE).toEqual({
      'pulisci-filtri': 'F2', export: 'F4', reload: 'F5', new: 'F6',
      'espandi-tutte': 'F8', 'personalizza-colonne': 'F9', salva: 'SALVA',
    })
    expect(tastoDiAzione('pubblica')).toBeNull()
  })

  it('codiceTasto: F senza modificatori, Salva con Ctrl o Cmd e basta', () => {
    expect(codiceTasto(tasto('F5'))).toBe('F5')
    expect(codiceTasto(tasto('F5', { shiftKey: true }))).toBeNull()
    expect(codiceTasto(tasto('F5', { ctrlKey: true }))).toBeNull()
    expect(codiceTasto(tasto('s', { ctrlKey: true }))).toBe('SALVA')
    expect(codiceTasto(tasto('S', { metaKey: true }))).toBe('SALVA')
    expect(codiceTasto(tasto('s', { ctrlKey: true, shiftKey: true }))).toBeNull()
    expect(codiceTasto(tasto('s'))).toBeNull()
  })

  it('agisce il solo iscritto a video e davanti; una tab in KeepAlive no', () => {
    const vista = iscritto()
    const nascosta = iscritto({ aVideo: false })
    const e = tasto('F6')
    expect(suTasto(e, { elenco: [nascosta, vista] })).toBe(true)
    expect(vista.eseguite).toEqual(['new'])
    expect(nascosta.eseguite).toEqual([])
    expect(e.prevenuto).toBe(true)
  })

  it('🔴 Ctrl+S con due form a livelli diversi salva solo quello davanti', () => {
    const template = iscritto({ davanti: false })
    const versione = iscritto()
    suTasto(tasto('s', { ctrlKey: true }), { elenco: [template, versione] })
    expect(template.eseguite).toEqual([])
    expect(versione.eseguite).toEqual(['salva'])
  })

  it('due iscritti candidati: il tasto ambiguo non fa niente', () => {
    expect(scegliIscritto([iscritto(), iscritto()], 'reload')).toBeNull()
  })

  it('F5 e Ctrl+S si ingoiano anche quando nessuno esegue; F6 no', () => {
    const sotto = iscritto({ davanti: false })
    const e5 = tasto('F5')
    const es = tasto('s', { ctrlKey: true })
    const e6 = tasto('F6')
    for (const e of [e5, es, e6]) suTasto(e, { elenco: [sotto] })
    expect(sotto.eseguite).toEqual([])
    expect(e5.prevenuto).toBe(true)
    expect(es.prevenuto).toBe(true)
    expect(e6.prevenuto).toBe(false)
  })

  it('azione spenta: ingoia il tasto e non esegue', () => {
    const i = iscritto({ spente: ['salva'] })
    const e = tasto('s', { ctrlKey: true })
    suTasto(e, { elenco: [i] })
    expect(e.prevenuto).toBe(true)
    expect(i.eseguite).toEqual([])
  })

  it('senza iscritti a video F5 resta del browser', () => {
    const e = tasto('F5')
    suTasto(e, { elenco: [iscritto({ aVideo: false })] })
    expect(e.prevenuto).toBe(false)
  })

  it('livelloDavanti: il dialog in cima vince, poi il drawer in cima, poi la pagina', () => {
    const elNelDialog = {}
    const elFuori = {}
    const drawerSotto = { value: true }
    // Dialog aperto: davanti solo cio' che sta nel dialog IN CIMA, anche se il
    // suo drawer e' in cima alla pila dei drawer.
    expect(livelloDavanti(elNelDialog, drawerSotto, { doc: docConDialog([elNelDialog]) })).toBe(true)
    expect(livelloDavanti(elFuori, drawerSotto, { doc: docConDialog([elNelDialog]) })).toBe(false)
    // Senza dialog: il drawer decide per chi ci vive dentro...
    expect(livelloDavanti(elFuori, { value: false }, { doc: docSenzaDialog })).toBe(false)
    // ...e la pagina e' davanti solo senza drawer aperti.
    expect(livelloDavanti(elFuori, null, { doc: docSenzaDialog, aperti: () => 0 })).toBe(true)
    expect(livelloDavanti(elFuori, null, { doc: docSenzaDialog, aperti: () => 1 })).toBe(false)
  })

  it('conTastoDiAzione: col tasto se l\'azione ne ha uno, il testo com\'e\' altrimenti', () => {
    const t = (k, p) => (k === 'common.con_scorciatoia' ? `${p.azione} (${p.tasto})` : k.split('.').pop())
    const te = () => false
    expect(conTastoDiAzione(t, te, 'Ricarica', 'reload')).toBe('Ricarica (F5)')
    expect(conTastoDiAzione(t, te, 'Pubblica', 'pubblica')).toBe('Pubblica')
  })
})
