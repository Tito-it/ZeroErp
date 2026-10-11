// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: LA DICHIARAZIONE della conferma d'annullo di un documento con
//        legami (brief-db-annullo-documento-con-legami R-1): che cosa
//        `DocumentoAnnulloLegamiDialog` manda al chiamante quando l'operatore
//        conferma, e che cosa mostra.
// Note: ⭐ Il numero dichiarato dev'essere quello LETTO dal dialog
//       (`GET …/legami/`): il `count(*)` del lettore del DB, non le righe del
//       documento. Il caso dei legami spariti fra la domanda del DB e la
//       lettura (zero) non deve lasciare l'operatore bloccato: si conferma
//       SENZA dichiarazione.
//       ⚠️ Si monta il dialog VERO; si fingono i contorni: l'API dei legami,
//       la cornice `AppDialog` (se ne leggono `saveDisabled` e l'evento
//       `save`) e l'host del drawer del documento.
//       Nata come spec di `DdtAnnulloLegamiDialog` (ritirato nell'estrazione).
//
// Indice test:
//  1) con legami: la conferma dichiara il numero letto
//  2) due legami sulla stessa riga contano due (la ri-consegna da ordine)
//  3) legami spariti: conferma attiva, nessuna dichiarazione, frase propria
//  4) finche' la lettura non arriva, la conferma e' spenta
//  5) la lettura va al documento del chiamante (basePath + id)
//  6) le tre forme: riga, provenienza, commessa
// ------------------------------------------------------------
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { defineComponent } from 'vue'
import { flushPromises } from '@vue/test-utils'

import DocumentoAnnulloLegamiDialog from './DocumentoAnnulloLegamiDialog.vue'
import { monta } from '../../../../test/montaggio'

let rispostaLegami = null
const chiamate = []
vi.mock('./legamiApi', () => ({
  getLegami: (basePath, id) => { chiamate.push([basePath, id]); return rispostaLegami },
}))

const CorniceFinta = defineComponent({
  name: 'AppDialog',
  props: { saveDisabled: { type: Boolean, default: false } },
  emits: ['save', 'cancel'],
  template: '<div><slot /></div>',
})

function legami(righe) {
  return Promise.resolve({ data: { data: { documento: 'ORDINE', id: 7, legami: righe.length, righe } } })
}

function legame(extra) {
  return {
    riga_id: null, riga_nr: null, origine: 'ORDINE', natura: 'CONSUMO', origine_id: 12,
    origine_riga_id: 5, origine_tipo_codice_interno: 'ORDINE_VENDITA', origine_codice: 'ORD1', qta: '10',
    ...extra,
  }
}

async function montaDialog() {
  const wrapper = monta(
    DocumentoAnnulloLegamiDialog,
    {
      visible: true, basePath: '/vendite/ordini', docId: 7, header: 'Annulla',
      domanda: { messaggio: 'Annullando ORD 7 si riaprono 2 legami' },
    },
    { global: { stubs: { AppDialog: CorniceFinta, DocumentoDrawerHost: true } } },
  )
  await flushPromises()
  return wrapper
}

describe('DocumentoAnnulloLegamiDialog — la dichiarazione', () => {
  beforeEach(() => {
    rispostaLegami = null
    chiamate.length = 0
  })

  it('con legami: la conferma dichiara il numero letto', async () => {
    rispostaLegami = legami([legame({ riga_nr: 1 }), legame({ riga_nr: 2, origine_riga_id: 6 })])
    const wrapper = await montaDialog()
    const cornice = wrapper.findComponent(CorniceFinta)
    expect(cornice.props('saveDisabled')).toBe(false)
    cornice.vm.$emit('save')
    expect(wrapper.emitted('conferma')).toEqual([[{ legami_confermati: 2 }]])
  })

  it('due legami sulla stessa riga contano due', async () => {
    rispostaLegami = legami([
      legame({ riga_nr: 1 }),
      legame({ riga_nr: 1, origine: 'RESO', origine_tipo_codice_interno: 'RESO_VENDITA', origine_id: 9 }),
    ])
    const wrapper = await montaDialog()
    wrapper.findComponent(CorniceFinta).vm.$emit('save')
    expect(wrapper.emitted('conferma')).toEqual([[{ legami_confermati: 2 }]])
  })

  it('legami spariti: si conferma senza dichiarazione', async () => {
    rispostaLegami = legami([])
    const wrapper = await montaDialog()
    const cornice = wrapper.findComponent(CorniceFinta)
    expect(cornice.props('saveDisabled')).toBe(false)
    expect(wrapper.text()).toContain('vendite.annullo_legami.nessun_legame')
    expect(wrapper.text()).not.toContain('si riaprono 2 legami')
    cornice.vm.$emit('save')
    expect(wrapper.emitted('conferma')).toEqual([[{}]])
  })

  it('finche\' la lettura non arriva, la conferma e\' spenta', async () => {
    rispostaLegami = new Promise(() => {})
    const wrapper = await montaDialog()
    expect(wrapper.findComponent(CorniceFinta).props('saveDisabled')).toBe(true)
  })

  it('la lettura va al documento del chiamante', async () => {
    rispostaLegami = legami([legame({ riga_nr: 1 })])
    await montaDialog()
    expect(chiamate).toEqual([['/vendite/ordini', 7]])
  })

  it('le tre forme: riga, provenienza, commessa', async () => {
    rispostaLegami = legami([
      legame({ riga_nr: 1, origine: 'PREVENTIVO', origine_tipo_codice_interno: 'PREVENTIVO' }),
      legame({ origine: 'OFFERTA', natura: 'PROVENIENZA', origine_tipo_codice_interno: 'OFFERTA_COMMERCIALE', qta: null }),
      legame({ origine: 'COMMESSA', origine_tipo_codice_interno: 'COMMESSA', qta: null }),
    ])
    const wrapper = await montaDialog()
    const testo = wrapper.text()
    expect(testo).toContain('vendite.annullo_legami.riga')
    expect(testo).toContain('vendite.annullo_legami.provenienza')
    expect(testo).toContain('vendite.annullo_legami.commessa')
  })
})
