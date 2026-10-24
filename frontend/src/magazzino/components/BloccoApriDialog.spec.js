// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa `BloccoApriDialog` (Lotto 3 R-5, piano-be-fe-magazzino-lotto-3
//        C1): il blocco porta articolo e magazzino della riga, il soggetto
//        scelto come id e la nota ripulita; lotto, seriale e scaffale compaiono
//        solo se il loro lookup propone qualcosa.
// Indice test:
//   1) senza lotti, seriali ne' scaffali proposti: solo quantita', per chi, nota
//   2) con lotti proposti compare il lotto
//   3) «Blocca» manda riga, quantita', soggetto (id) e nota ripulita
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises } from '@vue/test-utils'

const risposte = { lotti: [], assets: [], ubicazioni: [] }
const chiamate = { apri: [] }
const lista = (r) => Promise.resolve({ data: { data: { results: r } } })
vi.mock('../api/magazzino', () => ({
  lookupLotti: () => lista(risposte.lotti),
  lookupAssets: () => lista(risposte.assets),
  lookupUbicazioni: () => lista(risposte.ubicazioni),
  apriBlocco: (p) => { chiamate.apri.push(p); return Promise.resolve({ data: { data: { blocco_id: 7 } } }) },
}))

import BloccoApriDialog from './BloccoApriDialog.vue'
import { monta } from '../../../test/montaggio'

const RIGA = { articolo_id: 'a-1', articolo_codice: 'ART', magazzino_id: 5, magazzino_codice: 'MAG' }
const selects = (w) => w.findAllComponents({ name: 'Select' })

async function apri(props = {}) {
  const w = monta(BloccoApriDialog, { visible: false, riga: RIGA, ...props })
  await w.setProps({ visible: true })
  await flushPromises()
  return w
}

describe('BloccoApriDialog', () => {
  beforeEach(() => {
    risposte.lotti = []; risposte.assets = []; risposte.ubicazioni = []
    chiamate.apri.length = 0
  })

  it('senza lotti, seriali ne\' scaffali proposti: solo quantita\', per chi, nota', async () => {
    const w = await apri()
    expect(selects(w).filter((s) => s.props('optionValue') === 'id')).toHaveLength(0)
  })

  it('con lotti proposti compare il lotto', async () => {
    risposte.lotti = [{ id: 3, codice: 'L1' }]
    const w = await apri()
    const lotto = selects(w).find((s) => s.props('optionLabel') === 'codice')
    expect(lotto.props('options')).toEqual([{ id: 3, codice: 'L1' }])
  })

  it('«Blocca» manda riga, quantita\', soggetto (id) e nota ripulita', async () => {
    const w = await apri()
    w.vm.$.setupState.form.qta = 2
    w.vm.$.setupState.form.soggetto_obj = { soggetto_ruolo_id: 44 }
    w.vm.$.setupState.form.nota = '  fiera  '
    await w.vm.$.setupState.onSave()
    await flushPromises()
    expect(chiamate.apri).toEqual([{
      magazzino_id: 5, articolo_id: 'a-1', qta: 2, soggetto_ruolo_id: 44, nota: 'fiera',
      lotto_id: null, asset_id: null, ubicazione_id: null,
    }])
    expect(w.emitted('aperto')).toEqual([[7]])
  })
})
