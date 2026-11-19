// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: `IndirizziSoggettoDrawer` — «Aggiungi» compare solo se il picker del
//        DB (R-2 di brief-db-copia-indirizzo-soggetto) ammette almeno un tipo,
//        anche nel contesto ruolo. Fino al 2026-11-15 il ruolo non leggeva i
//        tipi all'apertura e il pulsante c'era sempre: con il picker letto,
//        un ruolo senza tipi ammessi apriva un form senza tipi.
// Note: si monta il drawer vero; finti solo i contorni — le API, il registro
//       delle azioni di riga (`useAzioneRiga`), il guscio `AppDrawer`, il form
//       dell'indirizzo, il kebab e il dialog della copia.
//
// Indice test:
//   1) ruolo, nessun tipo ammesso: niente «Aggiungi»
//   2) ruolo, un tipo ammesso: «Aggiungi» c'e', e i tipi vengono dal picker
//      della chiave del drawer (l'istanza)
//   3) soggetto, nessun tipo ammesso: niente «Aggiungi»
//   4) ruolo, «Cambia» di un indirizzo del ruolo: UNA `PUT`, niente DELETE +
//      POST. Fino al 2026-11-18 erano due richieste, e la DELETE dell'unico
//      obbligatorio, giudicata da sola, era rifiutata (giro 4 di
//      brief-db-fornitore-privato-indirizzi)
//   5) «Copia come…» sul servizio, di una riga del ruolo: la dialog dice da
//      dove e che la copia va sul RUOLO (il verbo copia sulla chiave della
//      sorgente), non sul servizio aperto
// ------------------------------------------------------------

import { describe, expect, it, vi, beforeEach } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises } from '@vue/test-utils'
import Button from 'primevue/button'

const api = vi.hoisted(() => ({
  listSoggettoIndirizzi: vi.fn(),
  listRuoloIndirizzi: vi.fn(),
  listSoggettoTipiIndirizzo: vi.fn(),
  listRuoloTipiIndirizzo: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {}, fullPath: '/anagrafiche/clienti' }),
}))
const scritture = vi.hoisted(() => ({
  createRuoloIndirizzo: vi.fn(),
  replaceRuoloIndirizzo: vi.fn(),
  deleteRuoloIndirizzo: vi.fn(),
}))
vi.mock('../api/anagrafiche', () => ({
  ...api,
  ...scritture,
  createSoggettoIndirizzo: vi.fn(),
  replaceSoggettoIndirizzo: vi.fn(),
  copiaSoggettoIndirizzo: vi.fn(),
  copiaRuoloIndirizzo: vi.fn(),
  lookupStati: vi.fn(async () => ({ data: { data: { results: [] } } })),
}))
vi.mock('../../core/composables/useAzioneRiga', () => ({
  useAzioneRiga: () => ({ bloccata: () => false, motivo: () => undefined, pronta: { value: true } }),
}))

const { monta } = await import('../../../test/montaggio')
const { default: IndirizziSoggettoDrawer } = await import('./IndirizziSoggettoDrawer.vue')

const AppDrawerFinto = defineComponent({
  name: 'AppDrawerFinto',
  setup(_, { slots }) {
    return () => h('div', [slots.default?.(), slots.footer?.()])
  },
})
// I contorni che il caso 4 aziona: il kebab (le azioni della riga), il form
// (il `form` condiviso, da compilare) e il footer (il «Salva»).
const KebabFinto = defineComponent({
  name: 'RowActionsMenu', props: { row: Object, actions: Array }, render: () => null,
})
const FormFinto = defineComponent({
  name: 'IndirizzoSoggettoForm', props: { form: Object }, render: () => null,
})
const FooterFinto = defineComponent({ name: 'FormFooter', emits: ['save'], render: () => null })
const CopiaFinta = defineComponent({
  name: 'CopiaIndirizzoDialog', props: { visible: Boolean, origine: Object, destinazione: String }, render: () => null,
})

const risposta = (data) => ({ data: { data } })
const TIPO_SPENTO = {
  codice_interno: 'SEDELEG', descrizione: 'Sede legale', obbligatorio: false, ammesso: false,
  reason_key: 'anagrafiche.indirizzi.tipo_blocco.gia_presente', reason_valori: ['Sede legale'],
}
const TIPO_AMMESSO = { codice_interno: 'FATT', descrizione: 'Fatturazione', obbligatorio: false, ammesso: true }

async function apri(props) {
  const w = monta(IndirizziSoggettoDrawer, { visible: false, ...props }, {
    global: {
      stubs: {
        AppDrawer: AppDrawerFinto, IndirizzoSoggettoForm: FormFinto,
        RowActionsMenu: KebabFinto, CopiaIndirizzoDialog: CopiaFinta, FormFooter: FooterFinto,
      },
    },
  })
  await w.setProps({ visible: true })
  await flushPromises()
  return w
}

const haAggiungi = (w) => w.findAllComponents(Button)
  .some(b => b.props('label') === 'anagrafiche.indirizzo_soggetto.aggiungi_indirizzo')

describe('IndirizziSoggettoDrawer — «Aggiungi» dal picker dei tipi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.listRuoloIndirizzi.mockResolvedValue(risposta({ indirizzi_ruolo: [], indirizzi_soggetto: [] }))
    api.listSoggettoIndirizzi.mockResolvedValue(risposta({ results: [] }))
  })

  it('1) ruolo, nessun tipo ammesso: niente «Aggiungi»', async () => {
    api.listRuoloTipiIndirizzo.mockResolvedValue(risposta({ results: [TIPO_SPENTO] }))
    const w = await apri({ context: 'ruolo', soggettoId: 50 })
    expect(haAggiungi(w)).toBe(false)
  })

  it('2) ruolo, un tipo ammesso: «Aggiungi» c\'e\', dal picker della chiave del drawer', async () => {
    api.listRuoloTipiIndirizzo.mockResolvedValue(risposta({ results: [TIPO_SPENTO, TIPO_AMMESSO] }))
    const w = await apri({ context: 'ruolo', soggettoId: 50, istanzaUtilityId: 9 })
    expect(haAggiungi(w)).toBe(true)
    expect(api.listRuoloTipiIndirizzo).toHaveBeenCalledWith(50, { istanza_utility_id: 9 })
  })

  it('3) soggetto, nessun tipo ammesso: niente «Aggiungi»', async () => {
    api.listSoggettoTipiIndirizzo.mockResolvedValue(risposta({ results: [TIPO_SPENTO] }))
    const w = await apri({ soggettoId: '019d-uuid' })
    expect(haAggiungi(w)).toBe(false)
  })

  it('4) ruolo, «Cambia» di un indirizzo del ruolo: una PUT, niente DELETE + POST', async () => {
    const riga = {
      id: 31, fonte: 'ruolo', tipo_indirizzo_codice_interno: 'FATT', tipo_indirizzo_descrizione: 'Fatturazione',
      indirizzo_libero: 'Via vecchia 1',
    }
    api.listRuoloIndirizzi.mockResolvedValue(risposta({ indirizzi_ruolo: [riga], indirizzi_soggetto: [] }))
    api.listRuoloTipiIndirizzo.mockResolvedValue(risposta({ results: [TIPO_AMMESSO] }))
    scritture.replaceRuoloIndirizzo.mockResolvedValue(risposta({ id: 32 }))
    const w = await apri({ context: 'ruolo', soggettoId: 50 })

    w.findComponent(KebabFinto).props('actions').find(a => a.key === 'cambia').command()
    await flushPromises()
    w.findComponent(FormFinto).props('form').indirizzo_libero = 'Via nuova 2'
    w.findComponent(FooterFinto).vm.$emit('save')
    await flushPromises()

    expect(scritture.replaceRuoloIndirizzo).toHaveBeenCalledTimes(1)
    const [ruolo, indirizzoId, payload] = scritture.replaceRuoloIndirizzo.mock.calls[0]
    expect([ruolo, indirizzoId, payload.tipo_indirizzo_codice_interno]).toEqual([50, 31, 'FATT'])
    expect(scritture.deleteRuoloIndirizzo).not.toHaveBeenCalled()
    expect(scritture.createRuoloIndirizzo).not.toHaveBeenCalled()
  })

  it('5) copia di una riga del ruolo, dal servizio: la destinazione e\' il ruolo', async () => {
    const riga = {
      id: 41, fonte: 'ruolo', tipo_indirizzo_codice_interno: 'SPED', tipo_indirizzo_descrizione: 'Spedizione',
      indirizzo_display: 'Via Roma 1, Milano',
    }
    api.listRuoloIndirizzi.mockResolvedValue(risposta({ indirizzi_ruolo: [riga], indirizzi_soggetto: [] }))
    api.listRuoloTipiIndirizzo.mockResolvedValue(risposta({ results: [TIPO_AMMESSO] }))
    const w = await apri({ context: 'ruolo', soggettoId: 50, istanzaUtilityId: 9 })

    w.findComponent(KebabFinto).props('actions').find(a => a.key === 'copia').command()
    await flushPromises()

    const dialog = w.findComponent(CopiaFinta)
    expect(dialog.props('visible')).toBe(true)
    expect(dialog.props('origine')).toEqual({
      tipo: 'Spedizione', indirizzo: 'Via Roma 1, Milano', titolare: 'anagrafiche.indirizzi.copia.titolare_ruolo',
    })
    expect(dialog.props('destinazione')).toBe('anagrafiche.indirizzi.copia.verso_come_origine')
  })
})
