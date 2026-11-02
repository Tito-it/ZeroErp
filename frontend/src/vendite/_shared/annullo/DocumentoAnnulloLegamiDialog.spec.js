// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
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
//  6-bis) offerta: la revisione precedente torna emessa
//  7) commessa: righe contate per documento, oneri a parte, dichiara il numero del lettore
//  8) commessa: documenti senza nome dal lineage restano distinti
//  8-bis) commessa: i consumi si nominano dall'origine (codice della sorgente)
//  9) dentro un drawer bloccato per STATO la conferma c'e' (AppDialog vero)
// ------------------------------------------------------------
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { defineComponent, ref } from 'vue'
import { flushPromises } from '@vue/test-utils'

import DocumentoAnnulloLegamiDialog from './DocumentoAnnulloLegamiDialog.vue'
import { monta } from '../../../../test/montaggio'
import { READONLY_KEY } from '../../../core/composables/useReadonlyMode'

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

// `documento` col codice di `config.sorgenti` (lotto 2a della grammatica unica,
// 2026-10-19); l'`origine` dei legami resta coi codici corti fino al 2b.
function legami(righe, documento = 'ORDINE_VENDITA') {
  return Promise.resolve({ data: { data: { documento, id: 7, legami: righe.length, righe } } })
}

function legame(extra) {
  return {
    riga_id: null, riga_nr: null, origine: 'ORDINE_VENDITA', natura: 'CONSUMO', origine_id: 12,
    origine_riga_id: 5, origine_tipo_codice_interno: 'ORDINE_VENDITA', origine_codice: 'ORD1', qta: '10',
    ...extra,
  }
}

async function montaDialog(messages = {}) {
  const wrapper = monta(
    DocumentoAnnulloLegamiDialog,
    {
      visible: true, basePath: '/vendite/ordini', docId: 7, header: 'Annulla', readonly: false,
      domanda: { messaggio: 'Annullando ORD 7 si riaprono 2 legami' },
    },
    { messages, global: { stubs: { AppDialog: CorniceFinta, DocumentoDrawerHost: true } } },
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
      legame({ riga_nr: 1, origine: 'RESO_VENDITA', origine_tipo_codice_interno: 'RESO_VENDITA', origine_id: 9 }),
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

  // ⭐ L'offerta (brief-modello-documento-vendita §13, O-4): il legame e' la
  //    revisione precedente, una PROVENIENZA che non «torna trasformabile» ma
  //    «torna emessa»; senza nome dal lineage, senza link.
  it('offerta: la revisione precedente torna emessa', async () => {
    rispostaLegami = legami([
      legame({ origine: 'OFFERTA_COMMERCIALE', natura: 'PROVENIENZA', origine_id: 5, origine_riga_id: null,
        origine_tipo_codice_interno: 'OFFERTA_COMMERCIALE', origine_codice: null, qta: null }),
    ], 'OFFERTA_COMMERCIALE')
    const wrapper = await montaDialog()
    const testo = wrapper.text()
    expect(testo).toContain('vendite.annullo_legami.revisione_precedente')
    expect(testo).not.toContain('vendite.annullo_legami.provenienza')
    expect(testo).toContain('vendite.annullo_legami.spiegazione_offerta')
    wrapper.findComponent(CorniceFinta).vm.$emit('save')
    expect(wrapper.emitted('conferma')).toEqual([[{ legami_confermati: 1 }]])
  })

  it('le tre forme: riga, provenienza, commessa', async () => {
    rispostaLegami = legami([
      legame({ riga_nr: 1, origine: 'PREVENTIVO', origine_tipo_codice_interno: 'PREVENTIVO' }),
      legame({ origine: 'OFFERTA_COMMERCIALE', natura: 'PROVENIENZA', origine_tipo_codice_interno: 'OFFERTA_COMMERCIALE', qta: null }),
      legame({ origine: 'COMMESSA', origine_tipo_codice_interno: 'COMMESSA', qta: null }),
    ])
    const wrapper = await montaDialog()
    const testo = wrapper.text()
    expect(testo).toContain('vendite.annullo_legami.riga')
    expect(testo).toContain('vendite.annullo_legami.provenienza')
    expect(testo).toContain('vendite.annullo_legami.commessa')
  })

  // ⭐ La commessa (brief-db-annullo-a-valle-riapre-a-monte D-2): un legame
  //    per riga di commessa non emessa. A video le righe si contano per
  //    documento d'origine, gli oneri si dicono a parte («si annulla»), ma la
  //    dichiarazione resta il numero del LETTORE, oneri compresi.
  it('commessa: righe contate per documento, oneri a parte, dichiara il numero del lettore', async () => {
    rispostaLegami = legami([
      legame({ riga_id: 1, origine: 'PREVENTIVO', origine_id: 3, origine_riga_id: null,
        origine_tipo_codice_interno: 'PREVENTIVO', origine_codice: 'PRV3', qta: '1' }),
      legame({ riga_id: 2, origine: 'PREVENTIVO', origine_id: 3, origine_riga_id: null,
        origine_tipo_codice_interno: 'PREVENTIVO', origine_codice: 'PRV3', qta: '2' }),
      legame({ riga_id: 3, origine: 'RESO_VENDITA', origine_id: 9, origine_riga_id: 4,
        origine_tipo_codice_interno: 'RESO_VENDITA', origine_codice: null, qta: '1' }),
      legame({ riga_id: 4, origine: 'ONERE', natura: 'ANNULLO', origine_id: null,
        origine_riga_id: null, origine_tipo_codice_interno: null, origine_codice: null, qta: '1' }),
      legame({ riga_id: 5, origine: 'ONERE', natura: 'ANNULLO', origine_id: null,
        origine_riga_id: null, origine_tipo_codice_interno: null, origine_codice: null, qta: '1' }),
    ], 'COMMESSA')
    const wrapper = await montaDialog()
    const voci = wrapper.findAll('li')
    // Preventivo (due righe in una voce), reso, e la voce degli oneri.
    expect(voci).toHaveLength(3)
    const testo = wrapper.text()
    expect(testo).toContain('vendite.annullo_legami.commessa_da_mandare')
    expect(testo).toContain('vendite.annullo_legami.commessa_da_accreditare')
    expect(testo).toContain('vendite.annullo_legami.si_annulla')
    expect(testo).toContain('vendite.annullo_legami.oneri_annullati')
    expect(testo).toContain('vendite.annullo_legami.spiegazione_commessa')
    expect(testo).not.toContain('vendite.annullo_legami.commessa ')
    wrapper.findComponent(CorniceFinta).vm.$emit('save')
    expect(wrapper.emitted('conferma')).toEqual([[{ legami_confermati: 5 }]])
  })

  // ⚠️ La voce e' il DOCUMENTO (tipo + id), non il suo nome: due preventivi che
  //    il lineage non nomina restano due voci, e i consumi (fuori dal lineage)
  //    una sola.
  it('commessa: documenti senza nome dal lineage restano distinti', async () => {
    const senzaNome = { origine: 'PREVENTIVO', origine_riga_id: null,
      origine_tipo_codice_interno: 'PREVENTIVO', origine_codice: null, qta: '1' }
    rispostaLegami = legami([
      legame({ ...senzaNome, riga_id: 1, origine_id: 3 }),
      legame({ ...senzaNome, riga_id: 2, origine_id: 4 }),
      legame({ riga_id: 3, origine: 'ATTIVITA_CONSUMI', origine_id: 41, origine_riga_id: null,
        origine_tipo_codice_interno: null, origine_codice: null, qta: '1' }),
      legame({ riga_id: 4, origine: 'ATTIVITA_CONSUMI', origine_id: 42, origine_riga_id: null,
        origine_tipo_codice_interno: null, origine_codice: null, qta: '1' }),
    ], 'COMMESSA')
    const wrapper = await montaDialog()
    expect(wrapper.findAll('li')).toHaveLength(3)
  })

  // ⭐ Un'origine che non e' un documento da aprire (il backend non da' il
  //    tipo) si nomina dal codice della sorgente, col vocabolario del lineage
  //    (`vendite.lineage.tipo_attivita_consumi`): dal lotto 2b della grammatica
  //    unica non c'e' piu' un secondo vocabolario delle origini. Una chiave
  //    sbagliata non da' errore: a video uscirebbe il codice grezzo, e questo
  //    test lo vede.
  it('commessa: i consumi si nominano dal codice della sorgente', async () => {
    rispostaLegami = legami([
      legame({ riga_id: 1, origine: 'ATTIVITA_CONSUMI', origine_id: 41, origine_riga_id: null,
        origine_tipo_codice_interno: null, origine_codice: null, qta: '1' }),
    ], 'COMMESSA')
    const wrapper = await montaDialog({
      vendite: { lineage: { tipo_attivita_consumi: 'Consumi' } },
    })
    const testo = wrapper.text()
    expect(testo).toContain('Consumi')
    expect(testo).not.toContain('ATTIVITA_CONSUMI')
  })
})

// 🔴 Il difetto del collaudo di Tid (2026-10-13): l'annullo con legami arriva
//    per costruzione su un documento USCITO DALLA BOZZA, e il drawer di quel
//    documento fornisce READONLY_KEY=true (lock di stato). Ereditandolo,
//    FormFooter nascondeva la conferma: la finestra offriva solo «Annulla».
//    Qui la cornice e' quella VERA — la cornice finta sopra non poteva vederlo.
describe('DocumentoAnnulloLegamiDialog — readonly dal chiamante, non dalla catena', () => {
  async function montaInDrawerBloccato(readonly) {
    rispostaLegami = legami([legame({ riga_nr: 1 })])
    const wrapper = monta(
      DocumentoAnnulloLegamiDialog,
      {
        visible: true, basePath: '/vendite/preventivi', docId: 7, header: 'Annulla preventivo', readonly,
        domanda: { messaggio: 'Annullando PRV 7 si riapre 1 legame' },
      },
      {
        provide: { [READONLY_KEY]: ref(true) },
        global: { stubs: { DocumentoDrawerHost: true } },
        attachTo: document.body,
      },
    )
    await flushPromises()
    return wrapper
  }

  function pulsanti() {
    return [...document.body.querySelectorAll('button')].map((b) => b.textContent.trim())
  }

  it('lock di stato nel drawer, readonly puro false: la conferma c\'e\'', async () => {
    const wrapper = await montaInDrawerBloccato(false)
    expect(pulsanti()).toContain('Annulla preventivo')
    wrapper.unmount()
  })

  it('readonly puro (permessi): la conferma non c\'e\'', async () => {
    const wrapper = await montaInDrawerBloccato(true)
    expect(pulsanti()).not.toContain('Annulla preventivo')
    wrapper.unmount()
  })
})
