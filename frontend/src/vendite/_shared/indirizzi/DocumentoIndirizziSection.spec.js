// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: QUANDO gli indirizzi di un documento si cambiano — la sezione
//        condivisa `DocumentoIndirizziSection`, montata da cinque drawer
//        (DDT, ordine, preventivo, offerta, contratto).
// Note: ⭐ PERCHE' QUESTO TEST. Dal 2026-10-11 la sezione legge da se' la
//       capability `can_edit_indirizzi` dal blob che il drawer le passa
//       (`capabilities`): prima ogni drawer ricomponeva lo stesso OR, cinque
//       copie (regola del 2). Un drawer che dimentica di passare il blob non
//       rompe niente: la sezione diventa di sola lettura (fail-closed) e a
//       video sembra una regola. Il test 6 lo prende dal sorgente.
//       ⚠️ Si monta la sezione VERA; si fingono i suoi contorni: l'API (la
//       risposta della lista) e il drawer di gestione, di cui si legge solo
//       il `readonly` ricevuto.
//
// Indice test:
//  1) capability accesa, permessi pieni -> si modifica
//  2) capability spenta -> sola lettura
//  3) blob assente -> sola lettura (fail-closed)
//  4) permessi in sola lettura vincono sulla capability accesa
//  5) ⭐ la catena readonly del padre (il readonly di STATO) NON passa
//  6) i cinque drawer passano il blob alla sezione
//  7) il cliente del documento cambia (detail salvato): la sezione ricarica
//  8) all'apertura l'identita' da vuota a valorizzata non ricarica una seconda volta
// ------------------------------------------------------------
import { describe, it, expect, vi } from 'vitest'
import { defineComponent, nextTick, ref } from 'vue'
import { flushPromises } from '@vue/test-utils'

import DocumentoIndirizziSection from './DocumentoIndirizziSection.vue'
import { READONLY_KEY } from '../../../core/composables/useReadonlyMode'
import { monta } from '../../../../test/montaggio'
import sorgenteDdt from '../../ddt/components/DdtDrawer.vue?raw'
import sorgenteOrdine from '../../ordini/components/OrdiniDrawer.vue?raw'
import sorgentePreventivo from '../../preventivi/components/PreventiviDrawer.vue?raw'
import sorgenteOfferta from '../../offerte/components/OffertaDrawer.vue?raw'
import sorgenteContratto from '../../components/ContrattoDrawer.vue?raw'

// Contorno: la lista degli indirizzi (un tipo CON ammesso, nessuna riga).
// `list` e' una spia: i test 7 e 8 contano le ricariche.
const { list } = vi.hoisted(() => ({ list: vi.fn() }))
vi.mock('./documentoIndirizziApi', async (importOriginal) => ({
  ...(await importOriginal()),
  makeIndirizziDocumentoApi: () => ({ list }),
}))
list.mockImplementation(async () => ({
  data: {
    data: {
      tipi_ammessi: [{ tipo_indirizzo_id: 1, tipo_indirizzo_codice_interno: 'CON', obbligatorio: true }],
      indirizzi: [],
    },
  },
}))

// Contorno: il drawer di gestione. Si legge solo il readonly che riceve.
const DrawerFinto = defineComponent({
  name: 'DocumentoIndirizziDrawer',
  props: { readonly: { type: Boolean, default: false } },
  template: '<div />',
})

// Scopo: monta la sezione e ritorna il readonly arrivato al drawer di gestione.
async function readonlyRicevuto(props, provide = {}) {
  const wrapper = monta(
    DocumentoIndirizziSection,
    { dominio: 'ddt', docId: 7, ...props },
    { provide, global: { stubs: { DocumentoIndirizziDrawer: DrawerFinto } } },
  )
  await flushPromises()
  await nextTick()
  return wrapper.findComponent(DrawerFinto).props('readonly')
}

describe('DocumentoIndirizziSection — quando si modificano', () => {
  it('capability accesa e permessi pieni: si modifica', async () => {
    expect(await readonlyRicevuto({ capabilities: { can_edit_indirizzi: true } })).toBe(false)
  })

  it('capability spenta: sola lettura', async () => {
    expect(await readonlyRicevuto({ capabilities: { can_edit_indirizzi: false } })).toBe(true)
  })

  it('blob assente: sola lettura (fail-closed)', async () => {
    expect(await readonlyRicevuto({ capabilities: null })).toBe(true)
  })

  it('i permessi in sola lettura vincono sulla capability', async () => {
    expect(await readonlyRicevuto({
      readonly: true, capabilities: { can_edit_indirizzi: true },
    })).toBe(true)
  })

  // Il corpo del drawer e' protetto dal readonly di STATO, che e' una copia
  // della regola del DB: la sezione non lo eredita, decide la capability.
  it('la catena readonly del padre non passa', async () => {
    expect(await readonlyRicevuto(
      { capabilities: { can_edit_indirizzi: true } },
      { [READONLY_KEY]: ref(true) },
    )).toBe(false)
  })

  it('i cinque drawer passano il blob alla sezione', () => {
    const drawer = {
      DdtDrawer: sorgenteDdt,
      OrdiniDrawer: sorgenteOrdine,
      PreventiviDrawer: sorgentePreventivo,
      OffertaDrawer: sorgenteOfferta,
      ContrattoDrawer: sorgenteContratto,
    }
    const senza = Object.entries(drawer)
      .filter(([, sorgente]) => {
        const sezione = sorgente.match(/<DocumentoIndirizziSection[\s\S]*?\/>/)
        return !sezione || !sezione[0].includes(':capabilities="capabilities"')
      })
      .map(([nome]) => nome)
    expect(senza).toEqual([])
  })

  // R-FE-2 (brief-db-indirizzi-documento-seguono-il-cliente): cambiato il
  // cliente in bozza, il DB ha tolto gli indirizzi di prima e riempito lo
  // slot di default dal nuovo. Il drawer ricarica `detail`, e la sezione
  // deve ricaricare la lista.
  it('il cliente cambia: la sezione ricarica', async () => {
    list.mockClear()
    const wrapper = monta(
      DocumentoIndirizziSection,
      { dominio: 'ddt', docId: 7, soggettoRuoloId: 10, istanzaUtilityId: null },
      { global: { stubs: { DocumentoIndirizziDrawer: DrawerFinto } } },
    )
    await flushPromises()
    expect(list).toHaveBeenCalledTimes(1)
    await wrapper.setProps({ soggettoRuoloId: 20, istanzaUtilityId: 5 })
    await flushPromises()
    expect(list).toHaveBeenCalledTimes(2)
  })

  // All'apertura `detail` arriva dopo il `docId`: l'identita' passa da vuota
  // a valorizzata, e il caricamento l'ha gia' fatto il watch sul documento.
  it("all'apertura l'identita' che arriva non ricarica", async () => {
    list.mockClear()
    const wrapper = monta(
      DocumentoIndirizziSection,
      { dominio: 'ddt', docId: 7, soggettoRuoloId: null, istanzaUtilityId: null },
      { global: { stubs: { DocumentoIndirizziDrawer: DrawerFinto } } },
    )
    await flushPromises()
    await wrapper.setProps({ soggettoRuoloId: 10, istanzaUtilityId: 5 })
    await flushPromises()
    expect(list).toHaveBeenCalledTimes(1)
  })

  // Cambio di documento: cambia `docId` e, con lui, il cliente. Carica il
  // watch sul documento, una volta sola: una seconda `load()` dal watch sul
  // cliente sarebbe una richiesta doppia in gara con la prima.
  it('il cambio di documento carica una volta sola', async () => {
    list.mockClear()
    const wrapper = monta(
      DocumentoIndirizziSection,
      { dominio: 'ddt', docId: 7, soggettoRuoloId: 10, istanzaUtilityId: 5 },
      { global: { stubs: { DocumentoIndirizziDrawer: DrawerFinto } } },
    )
    await flushPromises()
    await wrapper.setProps({ docId: 8, soggettoRuoloId: 20, istanzaUtilityId: null })
    await flushPromises()
    expect(list).toHaveBeenCalledTimes(2)
    expect(list).toHaveBeenLastCalledWith(8)
  })
})
