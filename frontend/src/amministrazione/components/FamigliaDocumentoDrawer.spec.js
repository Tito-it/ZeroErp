// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: la creazione di una famiglia di documento SCEGLIE una sorgente
//        (dal 2026-10-20, brief-db-grammatica-unica-documenti 2c, G-5): le
//        voci che non si possono scegliere sono spente col motivo, la tabella
//        si legge dalla sorgente, e il payload non porta piu' schema e tabella.
// Note: si monta il drawer vero; sono finti l'API (che risponde come axios,
//       `{ data: { data } }`), lo store della lista e il guscio `AppDrawer`.
//
// Indice test:
//   1) le sorgenti con famiglia o con la tabella gia' numerata sono spente, col motivo
//   2) la tabella mostrata e' quella della sorgente scelta
//   3) il payload di creazione: il codice della sorgente, niente schema ne' tabella
//   4) in modifica la tabella viene dal dettaglio, e le sorgenti non si caricano
//   5) riaperto per una nuova creazione, rilegge le sorgenti (niente cache)
//   6) famiglia propria E tabella presa da un'altra: vince il secondo motivo
//   7) un rifiuto del guard col campo: l'input si accende e il drawer resta aperto
// ------------------------------------------------------------

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises } from '@vue/test-utils'

const listSorgentiFamiglie = vi.fn()
const getFamiglia = vi.fn()
const crea = vi.fn()
const aggiorna = vi.fn()

vi.mock('../api/famiglieDocumento', () => ({
  listSorgentiFamiglie: (...a) => listSorgentiFamiglie(...a),
  getFamiglia: (...a) => getFamiglia(...a),
}))
vi.mock('../stores/famiglieDocumento', () => ({
  useFamiglieDocumentoStore: () => ({ crea, aggiorna }),
}))

const { monta } = await import('../../../test/montaggio')
const { default: FamigliaDocumentoDrawer } = await import('./FamigliaDocumentoDrawer.vue')

const comeAxios = (data) => ({ data: { data } })

const AppDrawerFinto = defineComponent({
  name: 'AppDrawerFinto',
  emits: ['save', 'update:visible'],
  setup(_, { slots }) {
    return () => h('div', slots.default?.())
  },
})

const SORGENTI = [
  {
    codice_interno: 'PREVENTIVO', etichetta: 'Preventivo', descrizione: 'Preventivo (testata)',
    tabella_documento: 'vendite.preventivi', famiglia_esistente: false, tabella_numerata_da: null,
  },
  {
    codice_interno: 'DDT_VENDITA', etichetta: 'DDT', descrizione: 'DDT vendita (testata)',
    tabella_documento: 'vendite.ddt', famiglia_esistente: true, tabella_numerata_da: null,
  },
  {
    codice_interno: 'DDT_ALTRO', etichetta: 'Altro DDT', descrizione: 'Sorgente sulla stessa tabella',
    tabella_documento: 'vendite.ddt', famiglia_esistente: false, tabella_numerata_da: 'Documento di trasporto',
  },
]

// Il watch del drawer parte all'APERTURA: si monta chiuso e si apre.
async function apri(props = {}) {
  const w = monta(FamigliaDocumentoDrawer, { visible: false, ...props }, {
    global: { stubs: { AppDrawer: AppDrawerFinto } },
  })
  await w.setProps({ visible: true })
  await flushPromises()
  return w
}

const tendina = (w) => w.findComponent({ name: 'Select' })

describe('FamigliaDocumentoDrawer — la famiglia è quella di una sorgente', () => {
  beforeEach(() => {
    listSorgentiFamiglie.mockReset().mockResolvedValue(comeAxios({ results: SORGENTI }))
    getFamiglia.mockReset()
    crea.mockReset().mockResolvedValue({ id: 9, registri_creati: 0 })
    aggiorna.mockReset()
  })

  it('le sorgenti con famiglia o con la tabella già numerata sono spente, col motivo', async () => {
    const w = await apri()
    const opzioni = tendina(w).props('options')
    expect(opzioni.map((o) => [o.value, o.disabled])).toEqual([
      ['PREVENTIVO', false],
      ['DDT_VENDITA', true],
      ['DDT_ALTRO', true],
    ])
    // Nel test le chiavi non hanno traduzione: si legge la chiave, che basta a
    // dire QUALE dei due motivi e' stato scelto.
    expect(opzioni[1].motivo).toBe('amministrazione.famiglie_documento.sorgente_ha_famiglia')
    expect(opzioni[2].motivo).toBe('amministrazione.famiglie_documento.sorgente_tabella_numerata')
  })

  it('la tabella mostrata è quella della sorgente scelta', async () => {
    const w = await apri()
    expect(w.text()).not.toContain('vendite.preventivi')
    tendina(w).vm.$emit('update:modelValue', 'PREVENTIVO')
    await flushPromises()
    expect(w.text()).toContain('vendite.preventivi')
  })

  it('il payload di creazione: il codice della sorgente, niente schema né tabella', async () => {
    const w = await apri()
    tendina(w).vm.$emit('update:modelValue', 'PREVENTIVO')
    await flushPromises()
    w.findComponent(AppDrawerFinto).vm.$emit('save')
    await flushPromises()
    expect(crea).toHaveBeenCalledTimes(1)
    const payload = crea.mock.calls[0][0]
    expect(payload.codice_interno).toBe('PREVENTIVO')
    expect(payload).not.toHaveProperty('schema_tabella')
    expect(payload).not.toHaveProperty('nome_tabella')
  })

  it('in modifica la tabella viene dal dettaglio, e le sorgenti non si caricano', async () => {
    getFamiglia.mockResolvedValue(comeAxios({
      id: 3, codice_interno: 'DDT_VENDITA', codice: 'DDT', descrizione: 'Documento di trasporto',
      tabella_documento: 'vendite.ddt', colonna_numero: 'numero', lunghezza_default: 7,
      struttura_blocco_reason: null,
    }))
    const w = await apri({ famigliaId: 3 })
    expect(listSorgentiFamiglie).not.toHaveBeenCalled()
    expect(tendina(w).exists()).toBe(false)
    expect(w.text()).toContain('vendite.ddt')
  })

  it('riaperto per una nuova creazione, rilegge le sorgenti (niente cache)', async () => {
    const w = await apri()
    await w.setProps({ visible: false })
    await flushPromises()
    await w.setProps({ visible: true })
    await flushPromises()
    expect(listSorgentiFamiglie).toHaveBeenCalledTimes(2)
  })

  it("famiglia propria E tabella presa da un'altra: vince il secondo motivo", async () => {
    listSorgentiFamiglie.mockResolvedValue(comeAxios({ results: [{
      codice_interno: 'DDT_VENDITA', etichetta: 'DDT', descrizione: 'DDT vendita (testata)',
      tabella_documento: 'vendite.ddt', famiglia_esistente: true, tabella_numerata_da: 'Altra famiglia',
    }] }))
    const w = await apri()
    expect(tendina(w).props('options')[0].motivo)
      .toBe('amministrazione.famiglie_documento.sorgente_tabella_numerata')
  })

  // ⭐ D1 di brief-be-verifica-documentazione-api (2026-10-23): il guard dei
  //    riferimenti risponde 400 col campo. Prima il drawer inghiottiva ogni
  //    errore in un `catch` vuoto: nessun toast, nessun campo.
  it("un rifiuto del guard col campo: l'input si accende e il drawer resta aperto", async () => {
    crea.mockRejectedValue({ response: { status: 400, data: { error: {
      code: 'E_FAMIGLIA_DOCUMENTO_RIFERIMENTO_INESISTENTE',
      message: 'La famiglia di documento dichiara un riferimento che non esiste.',
      fields: ['colonna_numero'],
    } } } })
    const w = await apri()
    tendina(w).vm.$emit('update:modelValue', 'PREVENTIVO')
    await flushPromises()
    w.findComponent(AppDrawerFinto).vm.$emit('save')
    await flushPromises()
    const invalidi = w.findAllComponents({ name: 'InputText' })
      .filter((c) => c.props('invalid'))
    expect(invalidi).toHaveLength(1)
    expect(invalidi[0].props('modelValue')).toBe('')
    expect(w.emitted('saved')).toBeUndefined()
    expect(w.emitted('update:visible')).toBeUndefined()
  })
})
