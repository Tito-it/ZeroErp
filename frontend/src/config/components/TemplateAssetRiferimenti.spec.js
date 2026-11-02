// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa il contratto di `TemplateAssetRiferimenti` (2026-10-01,
//        brief-be-documenti-risorse-esterne-render-pdf §5.2): chiede al
//        backend SOLO gli asset che il render accetta, scrive il riferimento
//        col `codice_interno`, sceglie la forma dal `mime_type`, e non tronca
//        in silenzio.
//
// Indice test:
//  1. chiede gli asset utilizzabili dell'emittente del template
//  2. senza emittente non chiede niente
//  3. il riferimento usa il codice_interno, non il codice
//  4. immagine: <img> nell'HTML, url() nel CSS
//  5. CSS: <link rel=stylesheet> e @import; PDF: solo HTML
//  6. in sola lettura nessun pulsante
//  7. piu' asset di una pagina: l'avviso, non un elenco muto
//  8. le miniature si chiedono a /miniatura/, mai il file intero; solo immagini
// ------------------------------------------------------------

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'

const listTemplateAssetDocumenti = vi.fn()
const miniaturaTemplateAssetDocumento = vi.fn()
const downloadTemplateAssetDocumento = vi.fn()
vi.mock('../api/templateAssetDocumenti', () => ({
  listTemplateAssetDocumenti: (...args) => listTemplateAssetDocumenti(...args),
  miniaturaTemplateAssetDocumento: (...args) => miniaturaTemplateAssetDocumento(...args),
  downloadTemplateAssetDocumento: (...args) => downloadTemplateAssetDocumento(...args),
}))

import TemplateAssetRiferimenti from './TemplateAssetRiferimenti.vue'
import { monta } from '../../../test/montaggio'

// jsdom non ha gli object URL: la lacuna e' dell'ambiente, non del componente.
URL.createObjectURL = () => 'blob:prova'
URL.revokeObjectURL = () => {}

const asset = (id, codiceInterno, mime, codice = `ETICHETTA_${id}`) => ({
  id, codice, codice_interno: codiceInterno, descrizione: `Asset ${id}`, mime_type: mime,
})
const risposta = (results, count = results.length) =>
  Promise.resolve({ data: { data: { results, count } } })

async function montaCon(results, props = {}, count) {
  listTemplateAssetDocumenti.mockReturnValue(risposta(results, count))
  const w = monta(TemplateAssetRiferimenti, { emittenteFiscaleId: 11, ...props })
  await flushPromises()
  return w
}

const pulsanti = (w) => w.findAll('button')
const inseriti = (w) => w.emitted('inserisci')?.map(([e]) => e) ?? []

describe('TemplateAssetRiferimenti', () => {
  beforeEach(() => {
    listTemplateAssetDocumenti.mockReset()
    downloadTemplateAssetDocumento.mockReset()
    miniaturaTemplateAssetDocumento.mockReset()
    miniaturaTemplateAssetDocumento.mockResolvedValue({ data: new Blob(['x']) })
  })

  it('chiede gli asset utilizzabili dell\'emittente del template', async () => {
    await montaCon([])
    expect(listTemplateAssetDocumenti).toHaveBeenCalledTimes(1)
    expect(listTemplateAssetDocumenti.mock.calls[0][0]).toMatchObject({
      emittente_fiscale_id: 11,
      utilizzabili: true,
    })
  })

  it('senza emittente non chiede niente', async () => {
    await montaCon([], { emittenteFiscaleId: null })
    expect(listTemplateAssetDocumenti).not.toHaveBeenCalled()
  })

  it('il riferimento usa il codice_interno, non il codice', async () => {
    const w = await montaCon([asset(1, 'LOGO_INT', 'image/png', 'Logo rinominabile')])
    expect(w.text()).toContain('asset:LOGO_INT')
    expect(w.text()).not.toContain('asset:Logo rinominabile')
  })

  it('immagine: <img> nell\'HTML, url() nel CSS', async () => {
    const w = await montaCon([asset(1, 'LOGO', 'image/png')])
    const [html, css] = pulsanti(w)
    await html.trigger('click')
    await css.trigger('click')
    expect(inseriti(w)).toEqual([
      { campo: 'html_template', testo: '<img src="asset:LOGO">' },
      { campo: 'css_template', testo: 'url("asset:LOGO")' },
    ])
  })

  it('CSS: <link rel=stylesheet> e @import; PDF: solo HTML', async () => {
    const w = await montaCon([
      asset(1, 'STILE', 'text/css'),
      asset(2, 'CONDIZIONI', 'application/pdf'),
    ])
    // Tre pulsanti: due per il CSS, uno solo per il PDF.
    expect(pulsanti(w)).toHaveLength(3)
    for (const b of pulsanti(w)) await b.trigger('click')
    expect(inseriti(w)).toEqual([
      { campo: 'html_template', testo: '<link rel="stylesheet" href="asset:STILE">' },
      { campo: 'css_template', testo: '@import url("asset:STILE");' },
      { campo: 'html_template', testo: '<link rel="attachment" href="asset:CONDIZIONI">' },
    ])
  })

  it('in sola lettura nessun pulsante', async () => {
    const w = await montaCon([asset(1, 'LOGO', 'image/png')], { readonly: true })
    expect(w.text()).toContain('asset:LOGO')
    expect(pulsanti(w)).toHaveLength(0)
  })

  it('piu\' asset di una pagina: l\'avviso, non un elenco muto', async () => {
    const w = await montaCon([asset(1, 'LOGO', 'image/png')], {}, 300)
    expect(w.text()).toContain('config.modelli_documenti.versioni.asset.troncati')
  })

  it('le miniature: /miniatura/ per le immagini, mai il file intero', async () => {
    const w = await montaCon([
      asset(1, 'LOGO', 'image/png'),
      asset(2, 'FIRMA', 'image/svg+xml'),
      asset(3, 'CONDIZIONI', 'application/pdf'),
    ])
    expect(miniaturaTemplateAssetDocumento.mock.calls.map(([id]) => id).sort()).toEqual([1, 2])
    expect(downloadTemplateAssetDocumento).not.toHaveBeenCalled()
    expect(w.findAll('img')).toHaveLength(2)
  })
})
