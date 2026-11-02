// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il LEGAME RITIRATO nella finestra «Passaggi»
//        (brief-db-annullo-a-valle-riapre-a-monte §11): da un preventivo
//        annullato la commessa resta viva e la tappa mostra il suo stato —
//        senza l'indicazione si leggeva che il preventivo stava in una
//        commessa pronta da fatturare (collaudo di Tid, 2026-10-13).
// Note: il dato e' a TRE stati (true / false / NULL = arco non censito):
//       l'indicazione compare solo con `true`.
//
// Indice test:
//  1) legame ritirato: la tappa resta, con stato del documento E indicazione
//  2) legame vivo o non censito (NULL): nessuna indicazione
// ------------------------------------------------------------

import { describe, it, expect } from 'vitest'

import LineagePassaggiContenuto from './LineagePassaggiContenuto.vue'
import { monta } from '../../../../test/montaggio'

function arco(extra) {
  return {
    livello: 1, ordine: 1, arco: 'B', ruolo: 'COLLEGATO',
    from_tipo_codice_interno: 'PREVENTIVO', from_codice: 'PRV0000144', from_doc_id: 302,
    to_tipo_codice_interno: 'COMMESSA', to_codice: 'CMM-1', to_doc_id: 113,
    to_stato_codice_interno: 'PRONTA_FATTURAZIONE', to_fase: 'IN_CORSO', to_is_abortito: false,
    is_ramo_inverso: false, is_legame_ritirato: false,
    ...extra,
  }
}

function montaCon(avanti) {
  return monta(LineagePassaggiContenuto, {
    loaded: true,
    data: { nodo: {}, pratica: null, frontiera: null, avanti, indietro: [] },
  }, { global: { directives: { tooltip: {} } } })
}

describe('LineagePassaggiContenuto — il legame ritirato', () => {
  it('legame ritirato: la tappa resta, con lo stato del documento E l\'indicazione', () => {
    const testo = montaCon([arco({ is_legame_ritirato: true })]).text()
    expect(testo).toContain('CMM-1')
    expect(testo).toContain('PRONTA_FATTURAZIONE')
    expect(testo).toContain('vendite.lineage.legame_ritirato')
  })

  it('legame vivo o non censito (NULL): nessuna indicazione', () => {
    const testo = montaCon([
      arco({ is_legame_ritirato: false }),
      arco({ ordine: 2, to_codice: 'CMM-2', is_legame_ritirato: null }),
    ]).text()
    expect(testo).toContain('CMM-2')
    expect(testo).not.toContain('vendite.lineage.legame_ritirato')
  })
})
