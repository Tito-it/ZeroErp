// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il LUCCHETTO del drawer offerta sezione per sezione (FE-V2,
//        brief-db-stati-documento-dal-vocabolario §6.10): il corpo si chiude da
//        `can_edit_utility`, le righe dalla SOLA `can_edit_eccezioni` (piu' i
//        permessi), non dal codice dello stato e non dal lock del corpo.
// Note: si monta il drawer vero; sono finti solo i contorni — lo store (il
//       dettaglio con le sue capability), il guscio `AppDrawer` (rende il
//       corpo e ripete la catena readonly come il vero: OR fra `readonly` e il
//       padre, fornita a cio' che sta dentro), il sotto-drawer delle righe (una
//       sonda che legge la catena e le props), e i figli che parlano col
//       backend (vuoti).
//       ⚠️ Le capability qui sono costruite, non lette dal seed: col
//       vocabolario di oggi `can_edit_utility` e `can_edit_eccezioni`
//       coincidono, ma il modello le ammette separate (V-2), e il caso si
//       costruisce.
//
// Indice test:
//   1) righe aperte e fornitura chiusa: il corpo e' chiuso, le righe no —
//      la catena che le righe ereditano porta i soli permessi
//   2) righe chiuse e fornitura aperta: le righe si chiudono dalla loro chiave
//   3) i permessi d'area arrivano alle righe anche fuori dal corpo
//   4) capability vuota (fail-closed): corpo chiuso, righe chiuse
// ------------------------------------------------------------

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, inject, provide, computed, ref } from 'vue'
import { flushPromises } from '@vue/test-utils'

const fetchDetail = vi.fn()

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {}, fullPath: '/vendite/offerte' }),
}))
vi.mock('../stores/offerte', () => ({
  useOfferteStore: () => ({ fetchDetail: (...a) => fetchDetail(...a) }),
}))
vi.mock('../stores/offertaRevisioni', () => ({
  useOffertaRevisioniStore: () => ({
    reset: vi.fn(), rileggiSeAgganciato: vi.fn(), totalRecords: 0,
  }),
}))
vi.mock('../../api/formDefaults', () => ({
  getOffertaFormDefaults: vi.fn().mockResolvedValue({ data: { data: {} } }),
}))

const { monta } = await import('../../../../test/montaggio')
const { READONLY_KEY } = await import('../../../core/composables/useReadonlyMode')
const { default: OffertaDrawer } = await import('./OffertaDrawer.vue')

// Il guscio: la catena readonly del vero `AppDrawer` (OR con il padre, mai
// sostituzione), e il corpo nello slot.
const AppDrawerFinto = defineComponent({
  name: 'AppDrawerFinto',
  props: { readonly: { type: Boolean, default: false } },
  setup(props, { slots }) {
    const padre = inject(READONLY_KEY, ref(false))
    provide(READONLY_KEY, computed(() => props.readonly || padre.value))
    return () => h('div', { class: 'drawer-finto' }, slots.default?.())
  },
})
const Vuoto = defineComponent({ render: () => null })
// La sonda delle righe: cio' che il sotto-drawer vero legge per chiudersi.
const RigheSonda = defineComponent({
  name: 'RigheSonda',
  props: { righeModificabili: { type: Boolean, default: false } },
  setup(props) {
    const catena = inject(READONLY_KEY, ref(false))
    return () => h('div', {
      class: 'righe-sonda',
      'data-catena': String(catena.value),
      'data-modificabili': String(props.righeModificabili),
    })
  },
})

function offerta(capabilities) {
  return {
    id: 7, codice: 'OFF-7', stato_codice_interno: 'EMESSA', stato_descrizione: 'Emessa',
    emittente_fiscale_id: 1, billing_account_id: 3, utility: null, eccezioni: [],
    capabilities,
  }
}

async function apri(capabilities, { readonlyPadre = false } = {}) {
  fetchDetail.mockResolvedValue(offerta(capabilities))
  const w = monta(OffertaDrawer, { visible: false, mode: 'edit', offertaId: 7 }, {
    provide: { [READONLY_KEY]: ref(readonlyPadre) },
    global: {
      stubs: {
        AppDrawer: AppDrawerFinto, OffertaRigheDrawer: RigheSonda,
        DrawerActionsBar: Vuoto, DrawerEntityHeader: Vuoto, DocumentoCollegamentiBar: Vuoto,
        DocumentoIndirizziSection: Vuoto, EmittenteFiscaleField: Vuoto, BillingAccountLookup: Vuoto,
        UtilityPerRuoloSelect: Vuoto, LookupSelect: Vuoto, ListinoDocumentoSelect: Vuoto,
        TipoVariazioneSelect: Vuoto, CampiCanoneTestata: Vuoto, RevisioniTab: Vuoto,
        VenditeNoteDrawer: Vuoto, OffertaEmissioneDialog: Vuoto, OffertaEsitoDialog: Vuoto,
        OffertaPushDialog: Vuoto, OffertaSuccessioneDialog: Vuoto,
        DocumentoAnnulloLegamiDialog: Vuoto, ContrattoDrawer: Vuoto, EntityPdfButton: Vuoto,
        AppDialog: Vuoto,
      },
    },
  })
  await w.setProps({ visible: true })
  await flushPromises()
  return w
}

const corpo = (w) => w.findComponent(AppDrawerFinto).props('readonly')
const righe = (w) => {
  const s = w.find('.righe-sonda')
  return { catena: s.attributes('data-catena'), modificabili: s.attributes('data-modificabili') }
}

describe('OffertaDrawer — il lucchetto per sezione (FE-V2)', () => {
  beforeEach(() => fetchDetail.mockReset())

  it('1) righe aperte e fornitura chiusa: corpo chiuso, righe aperte', async () => {
    const w = await apri({
      can_edit_eccezioni: true, can_edit_utility: false, can_edit_indirizzi: false,
    })
    expect(fetchDetail).toHaveBeenCalledWith(7)
    expect(corpo(w)).toBe(true)
    expect(righe(w)).toEqual({ catena: 'false', modificabili: 'true' })
  })

  it('2) righe chiuse e fornitura aperta: le righe dalla loro chiave', async () => {
    const w = await apri({
      can_edit_eccezioni: false, can_edit_utility: true, can_edit_indirizzi: true,
    })
    expect(corpo(w)).toBe(false)
    expect(righe(w)).toEqual({ catena: 'false', modificabili: 'false' })
  })

  it('3) i permessi d\'area arrivano alle righe', async () => {
    const w = await apri({
      can_edit_eccezioni: true, can_edit_utility: true, can_edit_indirizzi: true,
    }, { readonlyPadre: true })
    expect(righe(w).catena).toBe('true')
  })

  it('4) capability vuota: corpo e righe chiusi (fail-closed)', async () => {
    const w = await apri({})
    expect(corpo(w)).toBe(true)
    expect(righe(w).modificabili).toBe('false')
  })
})
