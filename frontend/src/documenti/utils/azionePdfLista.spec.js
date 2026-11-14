// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: la voce «PDF» del kebab delle liste documento (`azionePdfLista`).
//
// Indice test:
//   1) pdf_mode ARCHIVE: voce accesa, `apri` riceve la riga
//   2) ⭐ pdf_mode PREVIEW o NONE: voce spenta col suo tooltip, `apri` mai
//      chiamata — lo stato non si legge (un 'DRAFT' con ARCHIVE e' acceso)
//   3) ⭐ le cinque liste hanno i tre testi, in it e in en
// ------------------------------------------------------------

import { describe, it, expect, vi } from 'vitest'
import it_ from '../../locales/it.json'
import en from '../../locales/en.json'
import { azionePdfLista, pdfArchiviato } from './azionePdfLista'

const t = (k) => k

describe('azionePdfLista', () => {
  it('1) ARCHIVE: accesa', () => {
    const apri = vi.fn()
    const riga = { id: 5, pdf_mode: 'ARCHIVE', stato_codice_interno: 'DRAFT' }
    const voce = azionePdfLista(t, riga, { prefisso: 'vendite.ddt', apri })
    expect(voce).toMatchObject({ key: 'documenti-pdf', disabled: false, tooltip: 'vendite.ddt.pdf.tooltip_lista' })
    voce.command()
    expect(apri).toHaveBeenCalledWith(riga)
  })

  it('2) PREVIEW / NONE: spenta', () => {
    for (const pdf_mode of ['PREVIEW', 'NONE', undefined]) {
      const apri = vi.fn()
      const voce = azionePdfLista(t, { id: 5, pdf_mode }, { prefisso: 'vendite.ordini', apri })
      expect(voce.disabled).toBe(true)
      expect(voce.tooltip).toBe('vendite.ordini.pdf.tooltip_lista_disabilitato')
      voce.command()
      expect(apri).not.toHaveBeenCalled()
    }
    expect(pdfArchiviato(null)).toBe(false)
  })

  it('3) i testi delle cinque liste', () => {
    for (const locale of [it_, en]) {
      for (const dominio of ['ordini', 'preventivi', 'offerte', 'contratti', 'ddt']) {
        const pdf = locale.vendite[dominio].pdf
        for (const k of ['label_scarica', 'tooltip_lista', 'tooltip_lista_disabilitato']) {
          expect(typeof pdf[k], `${dominio}.${k}`).toBe('string')
        }
      }
    }
  })
})
