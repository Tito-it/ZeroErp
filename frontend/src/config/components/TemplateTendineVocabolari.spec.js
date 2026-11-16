// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Fissa le CINQUE tendine dei vocabolari dei modelli di stampa
//        (2026-11-16, BE13/BE5 di brief-db-revisione-documenti): tipo di
//        documento (drawer del modello e filtro della lista), tipo di risorsa
//        (drawer della risorsa e filtro della lista), motore di stampa
//        (drawer della versione). Tutte leggono il lookup del loro `rel`,
//        scrivono l'ID (la FK e' sull'id) e mostrano l'etichetta che il DB
//        dichiara riga per riga, col ripiego sul valore grezzo (fail-visible)
//        quando la chiave non e' nei locales. Il drawer della risorsa mostra i
//        formati del tipo scelto, ne fa l'`accept` del selettore e dice il
//        limite di dimensione letto dal parametro. Le due liste traducono la
//        colonna del tipo con la stessa etichetta del filtro.
// Note: si montano i componenti VERI; sono finti i contorni — l'API del
//       lookup (`lookupCodici`, che risponde come axios), gli store, il
//       guscio `AppDrawer`, la `ListaPaginaSemplice` (rende il filtro e le
//       celle su una riga data) e i figli pesanti che qui non si provano.
//       `useLookupCodici`/`useGlobalLookup`/`useLookupEtichettato` sono veri:
//       e' la catena che le tendine usano.
//
// Indice test:
//  1. TemplateDocumentoDrawer: tipo di documento dal suo rel, valore id,
//     etichetta del DB; chiave assente dai locales → il CODICE, mai l'id
//  2. TemplateDocumentiSearchTable: stesso filtro, e la colonna tradotta come il filtro
//  3. la colonna senza chiave nei locales ripiega sulla descrizione del seed
//  4. TemplateAssetDrawer: tipo di risorsa, formati del tipo scelto, accept, limite in MB
//  5. TemplateAssetDrawer: senza tipo scelto (o senza formati) il selettore non restringe
//  6. TemplateAssetSearchTable: filtro del tipo di risorsa e colonna tradotta
//  7. TemplateVersioneDrawer: motore di stampa dal suo rel, valore id
// ------------------------------------------------------------

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { computed, defineComponent, h } from 'vue'
import { flushPromises } from '@vue/test-utils'

const lookupCodici = vi.fn()
vi.mock('../../core/apiCore', async (importOriginal) => ({
  ...(await importOriginal()),
  lookupCodici: (...a) => lookupCodici(...a),
  listEmittentiFiscali: vi.fn(() => Promise.resolve({ data: { data: { results: [] } } })),
}))
vi.mock('../stores/templateDocumenti', () => ({
  useTemplateDocumentiStore: () => ({ filters: {}, fetchDetail: vi.fn() }),
}))
vi.mock('../stores/templateAssetDocumenti', () => ({
  useTemplateAssetDocumentiStore: () => ({ filters: {}, fetchDetail: vi.fn() }),
}))
vi.mock('../stores/templateVersioni', () => ({
  useTemplateVersioniStore: () => ({ fetchDetail: vi.fn() }),
}))
vi.mock('../api/templateDocumenti', () => ({
  listContextBuilders: vi.fn(() => Promise.resolve({ data: { data: { results: [] } } })),
}))
// Il parametro del limite di upload, come lo legge il drawer della risorsa.
vi.mock('../../core/composables/useParameterDefaults', () => ({
  useParameterDefaults: () => ({
    defaults: computed(() => ({ documenti_asset_upload_max_mb: '25' })),
    load: vi.fn(),
  }),
}))

const { monta } = await import('../../../test/montaggio')
const { invalidateAllLookups } = await import('../../core/composables/useGlobalLookup')
const { default: Select } = await import('primevue/select')
const { default: FileUpload } = await import('primevue/fileupload')
const { default: TemplateDocumentoDrawer } = await import('./TemplateDocumentoDrawer.vue')
const { default: TemplateDocumentiSearchTable } = await import('./TemplateDocumentiSearchTable.vue')
const { default: TemplateAssetDrawer } = await import('./TemplateAssetDrawer.vue')
const { default: TemplateAssetSearchTable } = await import('./TemplateAssetSearchTable.vue')
const { default: TemplateVersioneDrawer } = await import('./TemplateVersioneDrawer.vue')

const comeAxios = (results) => Promise.resolve({ data: { data: { results, count: results.length } } })

// Le righe come le porta la lookup specializzata (`dbops_repository`).
const TIPI_OUTPUT = [
  { id: 4, codice: 'PREVENTIVO', etichetta_key: 'documenti.tipi_documento_output.preventivo' },
  // Chiave dichiarata ma ASSENTE dai locales del test: deve uscire il codice.
  { id: 9, codice: 'NUOVO_TIPO', etichetta_key: 'documenti.tipi_documento_output.nuovo_tipo' },
]
const TIPI_ASSET = [
  {
    id: 1, codice: 'LOGO', etichetta_key: 'documenti.tipi_asset_documento.logo',
    formati: [
      { mime_type: 'image/png', estensione: 'png', etichetta_key: 'config.formati_file.png' },
      { mime_type: 'image/svg+xml', estensione: 'svg', etichetta_key: 'config.formati_file.svg' },
    ],
  },
  { id: 2, codice: 'CSS', etichetta_key: 'documenti.tipi_asset_documento.css', formati: [] },
]
const MOTORI = [
  { id: 7, codice: 'WEASYPRINT', etichetta_key: 'documenti.render_engine_documento.weasyprint' },
]
const PER_REL = {
  'documenti.tipi_documento_output': TIPI_OUTPUT,
  'documenti.tipi_asset_documento': TIPI_ASSET,
  'documenti.render_engine_documento': MOTORI,
}

// I locales del test: le etichette che il DB dichiara (tranne `nuovo_tipo`).
const MESSAGGI = {
  documenti: {
    tipi_documento_output: { preventivo: 'Preventivo tradotto' },
    tipi_asset_documento: { logo: 'Logo tradotto', css: 'CSS tradotto' },
    render_engine_documento: { weasyprint: 'WeasyPrint tradotto' },
  },
  config: {
    formati_file: { png: 'PNG tradotto' },
    modelli_documenti: {
      asset: {
        formati_ammessi: 'Formati: {formati}',
        max_file_mb: 'Massimo {mb} MB',
      },
    },
  },
}

const AppDrawerFinto = defineComponent({
  name: 'AppDrawerFinto',
  setup(_, { slots }) {
    return () => h('div', slots.default?.())
  },
})

// La lista finta: il filtro e le celle `#cell-*` resi su una riga data.
let rigaLista = {}
const ListaFinta = defineComponent({
  name: 'ListaFinta',
  setup(_, { slots, expose }) {
    expose({ applyFilters: vi.fn() })
    return () => h('div', [
      h('div', { class: 'filtri' }, slots.filtri?.()),
      ...Object.keys(slots)
        .filter((nome) => nome.startsWith('cell-'))
        .map((nome) => h('span', { class: nome }, slots[nome]({ data: rigaLista }))),
    ])
  },
})

const stubs = {
  AppDrawer: AppDrawerFinto,
  ListaPaginaSemplice: ListaFinta,
  EmittenteFiscaleField: true,
  LookupSelect: true,
  TemplateVersioniSection: true,
  TemplateAssetRiferimenti: true,
}

// Monta chiuso e apre: i watch dei drawer partono all'apertura.
async function apri(componente, props = {}) {
  const w = monta(componente, { visible: false, ...props }, { messages: MESSAGGI, global: { stubs } })
  await w.setProps({ visible: true })
  await flushPromises()
  return w
}

async function montaLista(componente, riga) {
  rigaLista = riga
  const w = monta(componente, {}, { messages: MESSAGGI, global: { stubs } })
  await flushPromises()
  return w
}

const tendinaPer = (w, placeholder) =>
  w.findAllComponents(Select).find((s) => s.props('placeholder') === placeholder)
const relChiesti = () => lookupCodici.mock.calls.map(([rel]) => rel)

describe('Le cinque tendine dei vocabolari dei modelli di stampa', () => {
  beforeEach(() => {
    invalidateAllLookups()
    lookupCodici.mockReset().mockImplementation((rel) => comeAxios(PER_REL[rel] ?? []))
  })

  it('TemplateDocumentoDrawer: tipo di documento dal suo rel, valore id, etichetta del DB', async () => {
    const w = await apri(TemplateDocumentoDrawer)
    expect(relChiesti()).toContain('documenti.tipi_documento_output')
    const tendina = tendinaPer(w, 'config.modelli_documenti.filter_tipo_output')
    expect(tendina.props('options')).toEqual([
      { value: 4, label: 'Preventivo tradotto' },
      { value: 9, label: 'NUOVO_TIPO' },
    ])
  })

  it('TemplateDocumentiSearchTable: stesso filtro, e la colonna tradotta come il filtro', async () => {
    const w = await montaLista(TemplateDocumentiSearchTable, {
      tipo_documento_output_descrizione: 'Preventivo (seed)',
      tipo_documento_output_etichetta_key: 'documenti.tipi_documento_output.preventivo',
    })
    const tendina = tendinaPer(w, 'config.modelli_documenti.filter_tipo_output')
    expect(tendina.props('options')[0]).toEqual({ value: 4, label: 'Preventivo tradotto' })
    expect(w.find('.cell-tipo_documento_output_descrizione').text()).toBe('Preventivo tradotto')
  })

  it('la colonna senza chiave nei locales ripiega sulla descrizione del seed', async () => {
    const w = await montaLista(TemplateDocumentiSearchTable, {
      tipo_documento_output_descrizione: 'Nuovo tipo (seed)',
      tipo_documento_output_etichetta_key: 'documenti.tipi_documento_output.nuovo_tipo',
    })
    expect(w.find('.cell-tipo_documento_output_descrizione').text()).toBe('Nuovo tipo (seed)')
  })

  it('TemplateAssetDrawer: tipo di risorsa, formati del tipo scelto, accept, limite in MB', async () => {
    const w = await apri(TemplateAssetDrawer)
    expect(relChiesti()).toContain('documenti.tipi_asset_documento')
    const tendina = tendinaPer(w, 'config.modelli_documenti.asset.filter_tipo')
    expect(tendina.props('options')).toEqual([
      { value: 1, label: 'Logo tradotto' },
      { value: 2, label: 'CSS tradotto' },
    ])
    // Il limite c'e' anche prima di scegliere il tipo: viene dal parametro.
    expect(w.text()).toContain('Massimo 25 MB')
    expect(w.findComponent(FileUpload).props('maxFileSize')).toBe(25 * 1024 * 1024)

    tendina.vm.$emit('update:modelValue', 1)
    await flushPromises()
    expect(w.findComponent(FileUpload).props('accept')).toBe('image/png,image/svg+xml')
    // PNG tradotto; SVG senza chiave nei locales → l'estensione.
    expect(w.text()).toContain('Formati: PNG tradotto, svg')
  })

  it('TemplateAssetDrawer: senza tipo scelto (o senza formati) il selettore non restringe', async () => {
    const w = await apri(TemplateAssetDrawer)
    // Nessun `accept` (il default di FileUpload, null): decide il DB.
    expect(w.findComponent(FileUpload).props('accept')).toBeFalsy()
    tendinaPer(w, 'config.modelli_documenti.asset.filter_tipo').vm.$emit('update:modelValue', 2)
    await flushPromises()
    expect(w.findComponent(FileUpload).props('accept')).toBeFalsy()
    expect(w.text()).toContain('config.modelli_documenti.asset.field_file_hint')
  })

  it('TemplateAssetSearchTable: filtro del tipo di risorsa e colonna tradotta', async () => {
    const w = await montaLista(TemplateAssetSearchTable, {
      asset_tipo_descrizione: 'Logo (seed)',
      asset_tipo_etichetta_key: 'documenti.tipi_asset_documento.logo',
      file_size_bytes: 10,
    })
    expect(relChiesti()).toContain('documenti.tipi_asset_documento')
    const tendina = tendinaPer(w, 'config.modelli_documenti.asset.filter_tipo')
    expect(tendina.props('options').map((o) => o.value)).toEqual([1, 2])
    expect(w.find('.cell-asset_tipo_descrizione').text()).toBe('Logo tradotto')
  })

  it('TemplateVersioneDrawer: motore di stampa dal suo rel, valore id', async () => {
    const w = await apri(TemplateVersioneDrawer, { templateId: 3, versioneId: null })
    expect(relChiesti()).toContain('documenti.render_engine_documento')
    const tendina = tendinaPer(w, 'config.modelli_documenti.versioni.field_render_engine_placeholder')
    expect(tendina.props('options')).toEqual([{ value: 7, label: 'WeasyPrint tradotto' }])
  })
})
