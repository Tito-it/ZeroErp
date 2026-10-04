// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il building block su cui poggia OGNI lista del progetto — 63 file lo
//        montano, ed e' la voce D1-d-bis di
//        `migliorie-generali-BE-FE-da-test-valutazione.md`, aperta dal
//        2026-09-09 e chiusa il 2026-09-23.
//
// ⭐ COSA SI E' SCELTO DI ASSERIRE, perche' D1-d-bis diceva che andava deciso:
//    i **contratti fra il caller e il BB**, cioe' le promesse che un file
//    qualunque delle 63 liste fa senza saperlo. Non la resa grafica (jsdom non
//    calcola il CSS), non la configurazione (e' dato, vive a catalogo e la
//    provano i presidi del seed), non la paginazione di PrimeVue (e' di
//    PrimeVue).
//
// ⭐ IL TEST CHE VALE PIU' DI TUTTI E' IL PRIMO: il gate anti-troncamento.
//    Con `paginata: false` il caller dichiara «queste righe sono TUTTE»; se
//    non lo sono, la lista mostrerebbe un sottoinsieme **facendolo passare per
//    l'insieme** — che e' il difetto muto peggiore di una lista: nessun
//    errore, nessuna riga rossa, e chi guarda conclude «il documento non
//    c'e'». Il BB rifiuta di disegnare la tabella, e questo file lo pinna.
//
// ⚠️ La config arriva da un'API: qui si finge `useListaConfig`, che e' il
//    CONTORNO del componente. Il componente sotto esame resta quello vero —
//    un test che stubba cio' che deve provare prova lo stub.
//
// Indice test:
//   1) ⭐ `paginata:false` con righe incomplete: la tabella NON si disegna
//   2) ...e al suo posto c'e' il messaggio d'errore, con i due numeri
//   3) righe complete: la tabella si disegna
//   4) lista vuota e dichiarata vuota: nessun falso allarme
//   5) mentre carica non si accusa nessun troncamento
//   6) `paginata:true` (il default): il gate non si applica mai
//   7) le colonne rese vengono dalla CONFIG, non dal caller
//   8) una colonna `visibile:false` non si rende
//   9) la riga aperta nel form (`riga-attiva`) e' evidenziata, le altre no
//  10) `righe-cliccabili:false`: ogni riga lo dichiara (niente hover)
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'
import { setActivePinia, createPinia } from 'pinia'

// ⚠️ Il mock va dichiarato PRIMA dell'import del componente: `vi.mock` e'
//    issato, ma il valore che restituisce si costruisce qui dentro.
vi.mock('../composables/useListaConfig', () => ({
  useListaConfig: () => ({
    config: ref({
      colonne: [
        { codice: 'codice', visibile: true, etichetta: 'Codice' },
        { codice: 'descrizione', visibile: true, etichetta: 'Descrizione' },
        { codice: 'nascosta', visibile: false, etichetta: 'Nascosta' },
      ],
      ordinamento: [],
      filtri: {},
      pagina_dimensione: 25,
    }),
    catalogo: ref([]),
    savedSnapshot: ref(null),
    dirty: ref(false),
    loading: ref(false),
    colonneNuove: ref([]),
    presetAggiornato: ref(false),
    load: vi.fn().mockResolvedValue(undefined),
    ensureCatalogo: vi.fn().mockResolvedValue(undefined),
    applyChange: vi.fn(),
    save: vi.fn(),
    reset: vi.fn(),
    ignorePresetUpdate: vi.fn(),
  }),
}))

import ListaConfigurabile from './ListaConfigurabile.vue'
import { monta } from '../../../test/montaggio'

const RIGHE = [
  { id: 1, codice: 'A-1', descrizione: 'Prima', nascosta: 'x' },
  { id: 2, codice: 'A-2', descrizione: 'Seconda', nascosta: 'y' },
]

function montaLista(props = {}) {
  return monta(ListaConfigurabile, { codice: 'prova.lista', ...props })
}

describe('ListaConfigurabile', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    // Il gate scrive in console per chi sviluppa: qui si zittisce, ma il
    // test 2 verifica che il messaggio a VIDEO ci sia comunque.
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  it('1) `paginata:false` con righe incomplete: la tabella NON si disegna', async () => {
    // 🔴 IL CASO CHE QUESTO FILE ESISTE PER PRESIDIARE. Il caller dichiara
    //    «non pagino, queste sono tutte» e ne passa due su sette: mostrare la
    //    tabella vorrebbe dire presentare un sottoinsieme come l'insieme.
    const w = montaLista({ rows: RIGHE, total: 7, paginata: false })
    await w.vm.$nextTick()
    expect(w.find('table').exists()).toBe(false)
    expect(w.find('.lista-troncamento-gate').exists()).toBe(true)
  })

  it('2) al posto della tabella c`e` il messaggio, coi due numeri', async () => {
    const w = montaLista({ rows: RIGHE, total: 7, paginata: false })
    await w.vm.$nextTick()
    // Le frasi vivono nei locales: qui si verifica che il BB passi i NUMERI,
    // che sono la parte che dice quanto manca.
    expect(console.error).toHaveBeenCalled()
    const detto = console.error.mock.calls[0][0]
    expect(detto).toContain('prova.lista')
    expect(detto).toContain('(2)')
    expect(detto).toContain('(7)')
  })

  it('3) righe complete: la tabella si disegna', async () => {
    const w = montaLista({ rows: RIGHE, total: 2, paginata: false })
    await w.vm.$nextTick()
    expect(w.find('.lista-troncamento-gate').exists()).toBe(false)
    expect(w.find('table').exists()).toBe(true)
  })

  it('4) lista vuota e dichiarata vuota: nessun falso allarme', async () => {
    // ⚠️ `0 !== 0` e' falso, ma il caso va pinnato lo stesso: e' lo stato in
    //    cui ogni lista nasce, e un gate che scattasse qui renderebbe il BB
    //    inservibile al primo montaggio.
    const w = montaLista({ rows: [], total: 0, paginata: false })
    await w.vm.$nextTick()
    expect(w.find('.lista-troncamento-gate').exists()).toBe(false)
  })

  it('5) mentre carica non si accusa nessun troncamento', async () => {
    // ⭐ Durante il fetch le righe sono quelle vecchie (o nessuna) e `total`
    //    quello nuovo: un gate che guardasse anche qui lampeggerebbe a ogni
    //    pagina, e un allarme che si accende sempre smette di essere letto.
    const w = montaLista({ rows: RIGHE, total: 7, paginata: false, loading: true })
    await w.vm.$nextTick()
    expect(w.find('.lista-troncamento-gate').exists()).toBe(false)
  })

  it('6) `paginata:true` (il default): il gate non si applica mai', async () => {
    // Qui `rows` e' UNA PAGINA e `total` il conteggio del server: che siano
    // diversi e' la normalita', non un difetto.
    const w = montaLista({ rows: RIGHE, total: 7 })
    await w.vm.$nextTick()
    expect(w.find('.lista-troncamento-gate').exists()).toBe(false)
    expect(w.find('table').exists()).toBe(true)
  })

  it('7) le colonne rese vengono dalla CONFIG, non dal caller', async () => {
    // ⭐ E' la regola zero della lista: la configurazione e' DATO (una riga in
    //    `ui.lista_definizione` + N in `ui.lista_colonna`), non codice. Il
    //    caller passa le righe e basta — se le colonne venissero da lui,
    //    personalizzarle vorrebbe dire toccare 63 file.
    const w = montaLista({ rows: RIGHE, total: 2, paginata: false })
    await w.vm.$nextTick()
    const intestazioni = w.findAll('th').map((th) => th.text())
    expect(intestazioni.some((h) => h.includes('Codice'))).toBe(true)
    expect(intestazioni.some((h) => h.includes('Descrizione'))).toBe(true)
  })

  it('8) una colonna `visibile:false` non si rende', async () => {
    const w = montaLista({ rows: RIGHE, total: 2, paginata: false })
    await w.vm.$nextTick()
    const intestazioni = w.findAll('th').map((th) => th.text())
    expect(intestazioni.some((h) => h.includes('Nascosta'))).toBe(false)
  })

  // §9.6 punto 2 del brief-db-liste-righe-documento (Tid, 2026-10-04): col form
  // sotto la lista si deve vedere QUALE riga si sta modificando.
  it('9) la riga aperta nel form (`riga-attiva`) e\' evidenziata, le altre no', async () => {
    const w = montaLista({ rows: RIGHE, total: 2, paginata: false, rigaAttiva: 2 })
    await w.vm.$nextTick()
    const righe = w.findAll('tbody tr')
    expect(righe[0].classes()).not.toContain('app-riga-attiva')
    expect(righe[1].classes()).toContain('app-riga-attiva')
  })

  it('10) `righe-cliccabili:false`: ogni riga lo dichiara (niente hover)', async () => {
    const w = montaLista({ rows: RIGHE, total: 2, paginata: false, righeCliccabili: false })
    await w.vm.$nextTick()
    const righe = w.findAll('tbody tr')
    expect(righe.length).toBe(2)
    righe.forEach((r) => expect(r.classes()).toContain('app-riga-non-cliccabile'))
    const cliccabili = montaLista({ rows: RIGHE, total: 2, paginata: false })
    await cliccabili.vm.$nextTick()
    cliccabili.findAll('tbody tr').forEach((r) => expect(r.classes()).not.toContain('app-riga-non-cliccabile'))
  })
})
