// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: I chip della barra collegamenti e i legami SPENTI (D-15, Tid,
//        2026-10-13): un arco col legame ritirato (nei due versi) o con la
//        destinazione annullata non conta nel chip dei vivi, ma fa un chip
//        suo (icona ed etichetta del motivo) — senza, un documento col solo arco spento perdeva la
//        barra e l'accesso alla storia.
// Note: l'API dei passaggi e' finta; la barra legge quando arriva la
//       `versione` del drawer ospite (useLetturaDocumento).
//
// Indice test:
//  1) in avanti: l'unico arco ritirato fa un chip spento — la barra resta
//  2) all'indietro: vivi e ritirati in due chip (NULL = vivo per il conteggio)
//  3) annullato e ritirato insieme: vince «annullato»
// ------------------------------------------------------------

import { describe, it, expect, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'

let risposta = null
vi.mock('./lineageApi', () => ({
  getPassaggi: () => Promise.resolve({ data: { data: risposta } }),
}))

const { default: DocumentoCollegamentiBar } = await import('./DocumentoCollegamentiBar.vue')
const { monta } = await import('../../../../test/montaggio')

function arco(extra) {
  return {
    livello: 1, ordine: 1, arco: 'B', ruolo: 'COLLEGATO',
    from_tipo_codice_interno: 'PREVENTIVO', from_natura_doc_codice_interno: null,
    to_tipo_codice_interno: 'COMMESSA', to_natura_doc_codice_interno: null,
    to_is_abortito: false, is_ramo_inverso: false, is_legame_ritirato: false,
    ...extra,
  }
}

async function montaBarra(payload) {
  risposta = { nodo: {}, pratica: null, frontiera: null, avanti: [], indietro: [], ...payload }
  const w = monta(DocumentoCollegamentiBar, {
    basePath: '/vendite/preventivi', docId: 302, versione: { id: 302 },
  }, {
    global: {
      directives: { tooltip: {} },
      stubs: { PraticaDrawer: true, DocumentoDrawerHost: true, LineagePassaggiDialog: true },
    },
  })
  await flushPromises()
  return w
}

const vivi = (w) => w.findAll('.app-collegamento-chip:not([data-spento])')
const spenti = (w) => w.findAll('.app-collegamento-chip[data-spento]')

describe('DocumentoCollegamentiBar — i legami spenti (D-15)', () => {
  it('in avanti: l\'unico arco ritirato fa un chip spento, e la barra resta', async () => {
    const w = await montaBarra({ avanti: [arco({ is_legame_ritirato: true })] })
    expect(vivi(w)).toHaveLength(0)
    expect(spenti(w)).toHaveLength(1)
    expect(spenti(w)[0].text()).toContain('vendite.lineage.chip_ritirato')
  })

  it('all\'indietro: vivi e ritirati in due chip, contati a parte', async () => {
    const w = await montaBarra({
      indietro: [
        arco({ ordine: 1, is_legame_ritirato: false }),
        arco({ ordine: 2, is_legame_ritirato: true }),
        arco({ ordine: 3, is_legame_ritirato: null }),
      ],
    })
    expect(vivi(w)).toHaveLength(1)
    expect(vivi(w)[0].text()).toMatch(/^2 /)
    expect(spenti(w)).toHaveLength(1)
    expect(spenti(w)[0].text()).not.toMatch(/^2 /)
  })

  it('annullato e ritirato insieme (commessa annullata): vince «annullato»', async () => {
    const w = await montaBarra({ avanti: [arco({ to_is_abortito: true, is_legame_ritirato: true })] })
    expect(spenti(w)).toHaveLength(1)
    expect(spenti(w)[0].text()).toContain('vendite.lineage.chip_annullato')
  })
})
