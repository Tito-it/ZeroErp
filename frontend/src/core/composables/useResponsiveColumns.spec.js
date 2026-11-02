// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il contratto del packing di `useResponsiveColumns`
//        (2026-09-18): la riserva della colonna azioni si calcola dal NUMERO
//        di pulsanti inline, le colonne di chrome fuori catalogo (selezione,
//        expander del dettaglio inline) entrano nel conto, e i tre livelli
//        (inline → kebab → ritiro per priorita') si attraversano in ordine.
// Note: il composable registra hook di ciclo di vita; qui non c'e' un
//       componente, quindi Vue avvisa e non li monta — la misura si simula
//       scrivendo `containerWidth`, che e' esposto proprio per questo.
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ref } from 'vue'

import {
  useResponsiveColumns,
  larghezzaAzioniInline,
  DEFAULT_COL_WIDTH,
  DEFAULT_EXPANDER_WIDTH,
  DEFAULT_ACTIONS_COMPACT_WIDTH,
} from './useResponsiveColumns'

// Indice test:
//  1. larghezzaAzioniInline: 1, 3, 4 (default), 6 pulsanti
//  2. livello 1: tutto entra con le azioni inline
//  3. livello 2: la riserva inline non entra, il kebab si' → nessun ritiro
//  4. livello 3: ritiro per priorita' crescente, identificatore mai
//  5. la colonna di selezione entra nel conto (48px che fanno la differenza)
//  6. con dettaglio inline l'expander e' contato gia' al livello 1
//  7. larghezza assente a catalogo → conta DEFAULT_COL_WIDTH

const col = (codice, larghezza, priorita, extra = {}) => ({
  codice, larghezza, priorita, ordine: 0, tipo_colonna: 'informazione', fissata: false, ...extra,
})

function fabbrica(cols, options = {}) {
  const columns = ref(cols)
  const api = useResponsiveColumns(ref(null), columns, { hasActions: true, ...options })
  return { ...api, columns }
}

let warn
beforeEach(() => { warn = vi.spyOn(console, 'warn').mockImplementation(() => {}) })
afterEach(() => { warn.mockRestore() })

describe('larghezzaAzioniInline — la riserva segue il numero di pulsanti', () => {
  it('padding cella + 2rem per pulsante + 0.25rem fra un pulsante e l\'altro', () => {
    expect(larghezzaAzioniInline(1)).toBe(16 + 32)
    expect(larghezzaAzioniInline(3)).toBe(16 + 3 * 32 + 2 * 4)
    expect(larghezzaAzioniInline(6)).toBe(16 + 6 * 32 + 5 * 4)
  })

  it('il default copre quattro pulsanti; un valore non numerico ricade sul default', () => {
    expect(larghezzaAzioniInline(undefined)).toBe(larghezzaAzioniInline(4))
    expect(larghezzaAzioniInline('x')).toBe(larghezzaAzioniInline(4))
  })
})

describe('useResponsiveColumns — i tre livelli del packing', () => {
  const cols = [
    col('numero', 100, 100, { tipo_colonna: 'identificatore' }),
    col('cliente', 200, 95),
    col('data', 100, 25),
    col('stato', 100, 90),
  ]
  const sommaDati = 500
  const inline = larghezzaAzioniInline(4) // 156
  const safety = 16

  it('livello 1: dati + azioni inline + safety entrano → tutto visibile, inline', () => {
    const p = fabbrica(cols)
    p.containerWidth.value = sommaDati + inline + safety
    expect(p.visibleColumns.value.map((c) => c.codice)).toEqual(['numero', 'cliente', 'data', 'stato'])
    expect(p.hiddenColumns.value).toEqual([])
    expect(p.actionsCompact.value).toBe(false)
  })

  it('livello 2: manca un pixel per l\'inline, il kebab basta → nessun ritiro, compatto', () => {
    const p = fabbrica(cols)
    p.containerWidth.value = sommaDati + inline + safety - 1
    expect(p.hiddenColumns.value).toEqual([])
    expect(p.actionsCompact.value).toBe(true)
  })

  it("livello 3: si ritira la priorita' piu' bassa per prima, mai l'identificatore", () => {
    const p = fabbrica(cols)
    // Entrano: numero(100) + cliente(200) + stato(100) + kebab(56) + expander(48) + 16 = 520.
    p.containerWidth.value = 520
    expect(p.hiddenColumns.value.map((c) => c.codice)).toEqual(['data'])
    expect(p.actionsCompact.value).toBe(true)
    // Ancora meno: cade anche `stato` (90), `cliente` (95) resta, `numero` mai.
    p.containerWidth.value = 420
    expect(p.hiddenColumns.value.map((c) => c.codice).sort()).toEqual(['data', 'stato'])
    expect(p.visibleColumns.value.map((c) => c.codice)).toEqual(['numero', 'cliente'])
  })

  it('la riserva inline e\' quella dichiarata dal chiamante (actionsInlineWidth)', () => {
    const p = fabbrica(cols, { actionsInlineWidth: larghezzaAzioniInline(6) })
    // Con 4 pulsanti entrerebbe inline; con 6 dichiarati no → kebab.
    p.containerWidth.value = sommaDati + inline + safety
    expect(p.actionsCompact.value).toBe(true)
  })
})

describe('useResponsiveColumns — il chrome fuori catalogo entra nel conto', () => {
  const cols = [col('a', 100, 100, { tipo_colonna: 'identificatore' }), col('b', 100, 50)]
  const base = 200 + larghezzaAzioniInline(4) + 16

  it('la colonna di selezione vale un expander: senza entra inline, con no', () => {
    const senza = fabbrica(cols)
    senza.containerWidth.value = base
    expect(senza.actionsCompact.value).toBe(false)

    const con = fabbrica(cols, { hasSelection: true })
    con.containerWidth.value = base
    expect(con.actionsCompact.value).toBe(true)
    con.containerWidth.value = base + DEFAULT_EXPANDER_WIDTH
    expect(con.actionsCompact.value).toBe(false)
  })

  it("con dettaglio inline l'expander c'e' sempre: contato al livello 1, non ri-aggiunto al ritiro", () => {
    const p = fabbrica(cols, { hasRowExpansion: true })
    p.containerWidth.value = base
    expect(p.actionsCompact.value).toBe(true)
    p.containerWidth.value = base + DEFAULT_EXPANDER_WIDTH
    expect(p.actionsCompact.value).toBe(false)
    // Ritiro di `b`: a(100) + kebab + expander(gia' nel chrome) + 16 = 220.
    p.containerWidth.value = 100 + DEFAULT_ACTIONS_COMPACT_WIDTH + DEFAULT_EXPANDER_WIDTH + 16
    expect(p.hiddenColumns.value.map((c) => c.codice)).toEqual(['b'])
  })
})

describe('useResponsiveColumns — larghezza assente a catalogo', () => {
  it('una colonna senza larghezza conta DEFAULT_COL_WIDTH, lo stesso numero che la lista rende', () => {
    const cols = [col('a', null, 100, { tipo_colonna: 'identificatore' }), col('b', 0, 50)]
    const p = fabbrica(cols)
    const soglia = 2 * DEFAULT_COL_WIDTH + larghezzaAzioniInline(4) + 16
    p.containerWidth.value = soglia
    expect(p.actionsCompact.value).toBe(false)
    p.containerWidth.value = soglia - 1
    expect(p.actionsCompact.value).toBe(true)
  })
})
