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
vi.mock('../api/anagrafiche', () => ({
  ...api,
  createSoggettoIndirizzo: vi.fn(),
  replaceSoggettoIndirizzo: vi.fn(),
  createRuoloIndirizzo: vi.fn(),
  deleteRuoloIndirizzo: vi.fn(),
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
const Vuoto = defineComponent({ render: () => null })

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
        AppDrawer: AppDrawerFinto, IndirizzoSoggettoForm: Vuoto,
        RowActionsMenu: Vuoto, CopiaIndirizzoDialog: Vuoto, FormFooter: Vuoto,
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
})
