// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il pannello permessi PER AREA (brief-db-permessi-tetto-area §7,
//        2026-10-04): elenco delle aree a sinistra, l'area scelta a destra
//        coi suoi oggetti e le sue azioni, ricerca e «solo con override», e
//        UN Salva che manda le sole sezioni modificate.
// Note: si monta la scheda vera; sono finte solo le API (rispondono come
//       axios, `{ data: { data } }`).
//
// Indice test:
//   1) l'elenco porta tutte le aree; il dettaglio e' la prima, con le SUE
//      azioni e i SUOI oggetti (non quelli di un'altra area). Lo scope
//      emittenti non e' piu' qui (sta nei Dati dal 2026-10-06)
//   2) il click su un'area cambia il dettaglio
//   3) «Solo con override» lascia le sole aree con un override
//   4) la ricerca di un'azione lascia la sola area che la contiene
//   5) un'area con una voce limitata dal tetto lo dice nell'elenco
//   6) senza modifiche non si salva niente
//   7) il Salva unico manda la SOLA sezione modificata, e ricarica gli effettivi
//   8) su un super admin il pannello e' in sola lettura: tendine spente, niente
//      reset, niente Salva — ma l'elenco delle aree resta navigabile
//   9) il numero di override di un'area viene dal DB (sede unica); un'area con
//      modifiche non salvate lo conta a video, come anteprima
// ------------------------------------------------------------

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

const api = {
  getOperatore: vi.fn(),
  getOverrideAree: vi.fn(),
  getOverrideAzioni: vi.fn(),
  getOverrideOggetti: vi.fn(),
  putOverrideAree: vi.fn(),
  putOverrideAzioni: vi.fn(),
  putOverrideOggetti: vi.fn(),
  getPermessiEreditati: vi.fn(),
  getPermessiEffettivi: vi.fn(),
  getPermessiRiepilogo: vi.fn(),
  getEmittentiScope: vi.fn(),
  putEmittentiScope: vi.fn(),
  listAreeFunzionali: vi.fn(),
  listAzioniProcesso: vi.fn(),
  getModelOverridesLookup: vi.fn(),
}

vi.mock('../api/amministrazione', async (originale) => ({
  ...(await originale()),
  ...Object.fromEntries(Object.keys(api).map(k => [k, (...a) => api[k](...a)])),
}))

const { monta } = await import('../../../test/montaggio')
const { default: OperatorePermessiTab } = await import('./OperatorePermessiTab.vue')
const { default: Select } = await import('primevue/select')
const { default: Badge } = await import('primevue/badge')

const ID = 42
function comeAxios(data) { return { data: { data } } }

const AREE = [
  { id: 1, codice: 'vendite', descrizione: 'Vendite' },
  { id: 2, codice: 'magazzino', descrizione: 'Magazzino' },
  { id: 3, codice: 'storico', descrizione: 'Storico' },
]
const AZIONI = [
  { id: 10, area_id: 1, permission_codename: 'genera_fatture_lotti', descrizione: 'Genera fatture' },
  { id: 20, area_id: 2, permission_codename: 'registra_magazzino', descrizione: 'Registra movimento' },
]
const OGGETTI = [
  { app_label: 'vendite', model_name: 'fattura', area_id: 1, area_descrizione: 'Vendite', can_override: true },
]

function preparaApi({ limitata = false, superAdmin = false } = {}) {
  api.getOperatore.mockResolvedValue(comeAxios({ auth_user_id: ID, is_super_admin: superAdmin, veste_attiva: true }))
  api.getOverrideAree.mockResolvedValue(comeAxios({ results: [] }))
  // Magazzino ha un override sull'azione: e' l'area «con override».
  api.getOverrideAzioni.mockResolvedValue(comeAxios({ results: [{ azione_id: 20, abilitata: true }] }))
  api.getOverrideOggetti.mockResolvedValue(comeAxios({ results: [] }))
  api.putOverrideAzioni.mockImplementation((_id, items) => Promise.resolve(comeAxios({ results: items })))
  api.getPermessiEreditati.mockResolvedValue(comeAxios({
    aree: [{ area_id: 1, livello: 'TUTTO', profilo_nome: 'Back-office' }], azioni: [],
  }))
  api.getPermessiEffettivi.mockResolvedValue(comeAxios({
    azioni: [
      { azione_id: 10, area_id: 1, abilitata_specifica: false, livello_area: 'TUTTO',
        livello_minimo_area: 'TUTTO', abilitata: false, limitata_da_area: false },
      { azione_id: 20, area_id: 2, abilitata_specifica: true, livello_area: 'BLOCCATO',
        livello_minimo_area: 'TUTTO', abilitata: !limitata, limitata_da_area: limitata },
    ],
    oggetti: [
      { app_label: 'vendite', model_name: 'fattura', area_schema_db: 'vendite', livello_override: null,
        livello_area: 'TUTTO', livello_specifico: 'TUTTO', livello: 'TUTTO', limitato_da_area: false },
    ],
  }))
  // Il numero di override per area, dalla sede unica a DB: Magazzino ha l'override
  // sull'azione 20.
  api.getPermessiRiepilogo.mockResolvedValue(comeAxios({ results: [
    { auth_user_id: ID, area_id: 1, livello: 'TUTTO', override_count: 0, voci_limitate: 0 },
    { auth_user_id: ID, area_id: 2, livello: 'BLOCCATO', override_count: 1, voci_limitate: limitata ? 1 : 0 },
    { auth_user_id: ID, area_id: 3, livello: 'BLOCCATO', override_count: 0, voci_limitate: 0 },
  ] }))
  api.listAreeFunzionali.mockResolvedValue(comeAxios({ results: AREE }))
  api.listAzioniProcesso.mockResolvedValue(comeAxios({ results: AZIONI }))
  api.getModelOverridesLookup.mockResolvedValue(comeAxios({ results: OGGETTI }))
}

async function montaScheda() {
  const w = monta(OperatorePermessiTab, { authUserId: ID, visible: true })
  await flushPromises()
  return w
}

const vociElenco = (w) => w.findAll('.app-elenco-dettaglio-voce')
const nomiElenco = (w) => vociElenco(w).map(v => v.find('.app-elenco-dettaglio-voce-testo').text())
const titoloDettaglio = (w) => w.find('.app-elenco-dettaglio-dettaglio h4').text()
const testoDettaglio = (w) => w.find('.app-elenco-dettaglio-dettaglio').text()

describe('OperatorePermessiTab — il pannello per area', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    Object.values(api).forEach(f => f.mockReset())
    preparaApi()
  })

  it('1) elenco di tutte le aree; il dettaglio e\' la prima, con le sue sole voci', async () => {
    const w = await montaScheda()
    expect(nomiElenco(w)).toEqual(['Vendite', 'Magazzino', 'Storico'])
    expect(titoloDettaglio(w)).toBe('Vendite')
    expect(testoDettaglio(w)).toContain('Genera fatture')
    expect(testoDettaglio(w)).toContain('vendite.fattura')
    expect(testoDettaglio(w)).not.toContain('Registra movimento')
    expect(api.getEmittentiScope).not.toHaveBeenCalled()
  })

  it('2) il click su un\'area cambia il dettaglio', async () => {
    const w = await montaScheda()
    await vociElenco(w)[1].trigger('click')
    expect(titoloDettaglio(w)).toBe('Magazzino')
    expect(testoDettaglio(w)).toContain('Registra movimento')
    expect(testoDettaglio(w)).not.toContain('Genera fatture')
  })

  it('3) «Solo con override» lascia le sole aree con un override', async () => {
    const w = await montaScheda()
    w.vm.$.setupState.soloOverride = true
    await flushPromises()
    expect(nomiElenco(w)).toEqual(['Magazzino'])
    expect(titoloDettaglio(w)).toBe('Magazzino')
  })

  it('4) la ricerca di un\'azione lascia la sola area che la contiene', async () => {
    const w = await montaScheda()
    await w.find('.app-elenco-dettaglio-filtri input').setValue('registra')
    expect(nomiElenco(w)).toEqual(['Magazzino'])
  })

  it('5) un\'area con una voce limitata dal tetto lo dice nell\'elenco', async () => {
    preparaApi({ limitata: true })
    const w = await montaScheda()
    const [vendite, magazzino] = vociElenco(w)
    expect(magazzino.find('.app-permessi-tetto-icona').exists()).toBe(true)
    expect(vendite.find('.app-permessi-tetto-icona').exists()).toBe(false)
  })

  it('6) senza modifiche non si salva niente', async () => {
    const w = await montaScheda()
    expect(w.vm.puoSalvare).toBe(false)
    expect(await w.vm.salva()).toBe(false)
    expect(api.putOverrideAree).not.toHaveBeenCalled()
    expect(api.putOverrideAzioni).not.toHaveBeenCalled()
    expect(api.putOverrideOggetti).not.toHaveBeenCalled()
    expect(api.putEmittentiScope).not.toHaveBeenCalled()
  })

  it('7) il Salva unico manda la SOLA sezione modificata e ricarica gli effettivi', async () => {
    const w = await montaScheda()
    // Vendite e' l'area a vista: le tendine sono livello area, oggetto, azione.
    const tendine = w.find('.app-elenco-dettaglio-dettaglio').findAllComponents(Select)
    tendine[tendine.length - 1].vm.$emit('update:modelValue', true)
    await flushPromises()
    expect(w.vm.puoSalvare).toBe(true)
    expect(vociElenco(w)[0].classes()).toContain('app-elenco-dettaglio-voce--modificata')

    api.getPermessiEffettivi.mockClear()
    expect(await w.vm.salva()).toBe(true)

    expect(api.putOverrideAzioni).toHaveBeenCalledTimes(1)
    const [, items] = api.putOverrideAzioni.mock.calls[0]
    expect(items.map(i => [i.azione_id, i.abilitata]).sort()).toEqual([[10, true], [20, true]])
    expect(api.putOverrideAree).not.toHaveBeenCalled()
    expect(api.putOverrideOggetti).not.toHaveBeenCalled()
    expect(api.putEmittentiScope).not.toHaveBeenCalled()
    expect(api.getPermessiEffettivi).toHaveBeenCalledWith(ID)
    expect(w.vm.modificato).toBe(false)
  })

  it('8) su un super admin il pannello e\' in sola lettura, ma navigabile', async () => {
    // Magazzino ha un override: senza il blocco avrebbe il pulsante di reset.
    preparaApi({ superAdmin: true })
    const w = await montaScheda()
    expect(w.text()).toContain('amministrazione.admin_full_access')
    await vociElenco(w)[1].trigger('click')
    expect(titoloDettaglio(w)).toBe('Magazzino')
    const tendine = w.find('.app-elenco-dettaglio-dettaglio').findAllComponents(Select)
    expect(tendine.length).toBeGreaterThan(0)
    tendine.forEach(s => expect(s.props('disabled')).toBe(true))
    expect(w.find('.app-elenco-dettaglio-dettaglio button').exists()).toBe(false)
    expect(w.vm.puoSalvare).toBe(false)
  })

  it('9) il numero di un\'area viene dal DB; con modifiche non salvate, a video', async () => {
    // Il DB conta 4 override su Vendite (es. oggetti che il catalogo a video non
    // elenca): vale il DB, non le mappe locali (che ne hanno zero).
    const righe = (await api.getPermessiRiepilogo()).data.data.results
    api.getPermessiRiepilogo.mockResolvedValue(comeAxios({ results: righe.map(r =>
      r.area_id === 1 ? { ...r, override_count: 4 } : r) }))
    const w = await montaScheda()
    expect(api.getPermessiRiepilogo).toHaveBeenCalledWith([ID])
    expect(vociElenco(w)[0].findComponent(Badge).props('value')).toBe(4)

    // Modifica non salvata su Vendite: ora conta l'anteprima a video (1).
    const tendine = w.find('.app-elenco-dettaglio-dettaglio').findAllComponents(Select)
    tendine[tendine.length - 1].vm.$emit('update:modelValue', true)
    await flushPromises()
    expect(vociElenco(w)[0].findComponent(Badge).props('value')).toBe(1)
  })
})
