// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: il drawer profilo reparto (2026-10-31): la sola lettura, la
//        navigazione PER AREA (`ElencoDettaglio`, come il pannello
//        dell'operatore), il tetto d'area e il Salva che manda il profilo
//        INTERO anche con la vista filtrata.
//
// ⚠️ Si fingono i CONTORNI: lo store dei reparti, i due lookup, la conferma e
//    il guscio AppDrawer (il vero monta il contenuto a fine animazione, che
//    jsdom non esegue). Il finto dichiara `readonly` per provare che il drawer
//    la passa, ed emette `save` a comando.
//
// Indice test:
//   1) editabile: i controlli dell'area mostrata sono accesi
//   2) ⭐ prop `readonly`: tutti i controlli spenti, e il guscio la riceve
//   3) ⭐ sola lettura ereditata dalla vista (catena), senza la prop
//   4) per area: il dettaglio e' la prima area, il clic porta alla seconda con le SUE azioni
//   5) ⭐ tetto sui valori SALVATI: lo dice il DB (`limitata_da_area`), anche contro la copia
//   5b) ⭐ tetto in ANTEPRIMA: l'admin abbassa l'area → avviso col suffisso «anteprima»
//   6) ⭐ la ricerca restringe la vista, il Salva manda il profilo intero
// ------------------------------------------------------------

import { describe, it, expect, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'
import { flushPromises } from '@vue/test-utils'

vi.mock('../api/amministrazione', () => ({
  listAreeFunzionali: () => Promise.resolve({ data: { data: { results: [
    { id: 1, codice: 'VEN', descrizione: 'Vendite' },
    { id: 2, codice: 'ACQ', descrizione: 'Acquisti' },
  ] } } }),
  listAzioniProcesso: () => Promise.resolve({ data: { data: { results: [
    { id: 9, permission_codename: 'genera_fatture', descrizione: 'Genera fatture',
      area_id: 1, area_codice: 'VEN', livello_minimo_area: 'TUTTO', pericolosa: false },
    { id: 10, permission_codename: 'chiudi_ordini', descrizione: 'Chiudi ordini',
      area_id: 2, area_codice: 'ACQ', livello_minimo_area: 'TUTTO', pericolosa: false },
  ] } } }),
}))

const profilo = ref(null)
const profiloDb = ref({ aree: [], azioni: [], richiede_secondo_fattore: false })
const saveProfilo = vi.fn(async () => ({}))
vi.mock('../stores/reparti', () => ({
  useRepartiStore: () => ({
    get currentProfilo() { return profilo.value },
    fetchProfilo: async () => { profilo.value = profiloDb.value },
    saveProfilo: (...a) => saveProfilo(...a),
  }),
}))
vi.mock('../../core/composables/useConfirmAction', () => ({
  useConfirmAction: () => ({ confirmSave: (cb) => cb() }),
}))

const { monta } = await import('../../../test/montaggio')
const { default: RepartoProfiloEditor } = await import('./RepartoProfiloEditor.vue')
const { READONLY_KEY } = await import('../../core/composables/useReadonlyMode')

const AppDrawerFinto = defineComponent({
  name: 'AppDrawerFinto',
  props: { readonly: { type: Boolean, default: false } },
  emits: ['save'],
  setup(props, { slots, emit }) {
    return () => h('div', { class: 'drawer-finto', 'data-readonly': String(props.readonly) }, [
      slots.default?.(),
      h('button', { class: 'salva-finto', onClick: () => emit('save') }, 'salva'),
    ])
  },
})

const MESSAGGI = {
  amministrazione: { profilo_reparto_limitata_da_area: 'limitata {minimo} {area}', tetto_anteprima: '(anteprima)' },
}

async function apri(props = {}, provide = {}, db = { aree: [], azioni: [], richiede_secondo_fattore: false }) {
  profilo.value = null
  profiloDb.value = db
  const w = monta(RepartoProfiloEditor, { visible: false, uoId: 3, uoNome: 'Ufficio', ...props }, {
    provide,
    messages: MESSAGGI,
    global: { stubs: { AppDrawer: AppDrawerFinto } },
  })
  await flushPromises()
  await w.setProps({ visible: true })
  await flushPromises()
  return w
}

// I controlli: l'interruttore del secondo fattore, il Select del livello
// dell'area mostrata e gli interruttori delle sue azioni.
const interruttori = (w) => w.findAll('.p-toggleswitch')
const selettori = (w) => w.findAll('.p-select')
const vociElenco = (w) => w.findAll('.app-elenco-dettaglio-voce')
const dettaglio = (w) => w.find('.app-elenco-dettaglio-dettaglio')

describe('RepartoProfiloEditor', () => {
  it('1) editabile: i controlli dell\'area mostrata sono accesi', async () => {
    const w = await apri()
    expect(selettori(w)).toHaveLength(1)
    expect(interruttori(w)).toHaveLength(2)
    expect(w.findAll('.p-disabled')).toHaveLength(0)
    expect(w.find('.drawer-finto').attributes('data-readonly')).toBe('false')
  })

  it('2) prop `readonly`: tutti i controlli spenti, e il guscio la riceve', async () => {
    const w = await apri({ readonly: true })
    expect(selettori(w)[0].classes()).toContain('p-disabled')
    for (const s of interruttori(w)) expect(s.classes()).toContain('p-disabled')
    expect(w.find('.drawer-finto').attributes('data-readonly')).toBe('true')
  })

  it('3) sola lettura ereditata dalla vista (catena), senza la prop', async () => {
    const w = await apri({}, { [READONLY_KEY]: ref(true) })
    expect(selettori(w)[0].classes()).toContain('p-disabled')
    for (const s of interruttori(w)) expect(s.classes()).toContain('p-disabled')
  })

  it('4) per area: il dettaglio e\' la prima area, il clic porta alla seconda con le SUE azioni', async () => {
    const w = await apri()
    expect(vociElenco(w).map(v => v.find('.app-elenco-dettaglio-voce-testo').text())).toEqual(['Vendite', 'Acquisti'])
    expect(dettaglio(w).text()).toContain('Genera fatture')
    expect(dettaglio(w).text()).not.toContain('Chiudi ordini')
    await vociElenco(w)[1].trigger('click')
    expect(dettaglio(w).text()).toContain('Chiudi ordini')
    expect(dettaglio(w).text()).not.toContain('Genera fatture')
  })

  it('5) tetto sui valori SALVATI: lo dice il DB (`limitata_da_area`), anche contro la copia', async () => {
    const w = await apri({}, {}, {
      aree: [{ area_id: 1, livello: 'TUTTO' }, { area_id: 2, livello: 'BLOCCATO' }],
      // Il DB dice limitata la 9 (area TUTTO, che per la copia CONSENTIREBBE)
      // e non la 10 (area BLOCCATO, che per la copia la limiterebbe): vince il DB.
      azioni: [
        { azione_id: 9, abilitata: true, limitata_da_area: true },
        { azione_id: 10, abilitata: true, limitata_da_area: false },
      ],
      richiede_secondo_fattore: false,
    })
    expect(dettaglio(w).find('.app-permessi-tetto').text()).toMatch(/^limitata /)
    expect(dettaglio(w).find('.app-permessi-tetto').text()).not.toContain('(anteprima)')
    expect(vociElenco(w)[0].find('.app-permessi-tetto-icona').exists()).toBe(true)
    expect(vociElenco(w)[1].find('.app-permessi-tetto-icona').exists()).toBe(false)
    await vociElenco(w)[1].trigger('click')
    expect(dettaglio(w).find('.app-permessi-tetto').exists()).toBe(false)
  })

  it('5b) tetto in ANTEPRIMA: l\'admin abbassa l\'area → avviso col suffisso «anteprima»', async () => {
    const w = await apri({}, {}, {
      aree: [{ area_id: 1, livello: 'TUTTO' }],
      azioni: [{ azione_id: 9, abilitata: true, limitata_da_area: false }],
      richiede_secondo_fattore: false,
    })
    expect(dettaglio(w).find('.app-permessi-tetto').exists()).toBe(false)
    w.findComponent({ name: 'Select' }).vm.$emit('update:modelValue', 'BLOCCATO')
    await flushPromises()
    expect(dettaglio(w).find('.app-permessi-tetto').text()).toContain('(anteprima)')
  })

  it('6) la ricerca restringe la vista, il Salva manda il profilo intero', async () => {
    saveProfilo.mockClear()
    const w = await apri()
    await w.find('.app-elenco-dettaglio-filtri input').setValue('chiudi')
    expect(vociElenco(w)).toHaveLength(1)
    await w.find('.salva-finto').trigger('click')
    await flushPromises()
    expect(saveProfilo).toHaveBeenCalledTimes(1)
    const [, aree, azioni] = saveProfilo.mock.calls[0]
    expect(aree.map(a => a.area_id)).toEqual([1, 2])
    expect(azioni.map(a => a.azione_id)).toEqual([9, 10])
  })
})
