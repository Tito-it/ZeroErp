// @vitest-environment jsdom
// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: IL CONTENITORE DEI FILTRI DI UNA LISTA a video — quali comandi
//        nascono, che cosa dice il segno, e quando «Pulisci filtri» c'e'.
//        Settanta liste passano da qui.
//
// ⭐ PERCHE' ESISTE, E PERCHE' SOLO ORA. Di questo building block erano gia'
//    provate le parti che DECIDONO — `segnoFiltri`, `clonaFiltri` e i due
//    contratti dei filtri: 47 asserzioni su funzioni pure. Restava scoperto
//    cio' che si vede solo MONTANDO, e il cantiere lo ha pagato quattro volte
//    in due giorni, sempre nello stesso modo: un pulsante che non compare, o
//    che compare dove non serve, non rompe niente e non accende nessun lint.
//    ⚠️ Tre di quei quattro si vedevano **solo sotto i 1024px**, dove nessuno
//    guarda mentre scrive il codice. Sono i test 1, 7 e 10 di questo file.
//
// ⛔ CIO' CHE QUESTO FILE NON VEDE, e va detto perche' e' meta' del conto:
//    jsdom **non calcola il CSS**. Il badge che copriva il glifo, il drawer che
//    si apriva alto 10rem, il movimento «meccanico» — cioe' sei dei dodici
//    rilievi del §9.3 del brief — qui non si distinguono. Quella meta' la
//    presidia **solo il collaudo a video (L6)**, e questo file non la sostituisce.
//    ⇒ Le asserzioni parlano di COSA c'e' nel DOM (un pulsante, una classe, una
//    severity), mai di come appare.
//
// ⚠️ La modalita' compatta NON e' una media query: e' `ui.isCompatto`, cioe'
//    uno store. E' il motivo per cui il ramo compatto e' montabile — bastano i
//    due `finestra()` qui sotto — mentre le varianti CSS di altri componenti
//    non lo sono.
//
// ⚠️ Il DRAWER e' teleportato sul `body` da PrimeVue, quindi non sta nel
//    wrapper: qui si prova cio' che decide se esiste e chi lo apre. Il suo
//    CONTENUTO e' lo slot del chiamante, che il chiamante rende comunque.
//
// Note: `store` e' un oggetto SEMPLICE, non uno store Pinia, ed e' voluto: il
//       componente legge un contratto (`filters`, `chiaviFiltro`,
//       `filtriDefault`, `filtriNeutri`, `azzeraFiltri`), non un'istanza. Chi
//       quel contratto lo produce ha le sue spec (`useContrattoFiltriLista`).
//
// Indice test:
//   1) ⭐ con la SOLA ricerca non nasce l'imbuto (e nemmeno il drawer)
//   2) su desktop i filtri stanno in linea, senza nessun imbuto
//   3) nessun filtro valorizzato -> segno spento
//   4) tutti al default -> numero GRIGIO (`secondary`)
//   5) uno diverso dal default -> numero BLU (`info`), e conta anche i default
//   6) un valore NEUTRO non conta: il segno si spegne quando la lista si allarga
//   7) ⭐ «Pulisci» c'e' anche SENZA segno, se c'e' da riportare al default
//   8) tutto al suo posto e niente da pulire -> nessun «Pulisci»
//   9) il click chiama `azzeraFiltri` dello store
//  10) ⭐ senza store, «Pulisci» compare solo se qualcuno ascolta `@pulisci`
//  11) uno store che non dichiara le chiavi lo GRIDA in console
//  12) la ricerca resta a video anche in compatta (D2)
//  13) ⭐ una lista che NON cerca (`ricercaFull === false`) non ha casella,
//      su entrambe le rese; `null` (non si sa ancora) la lascia
// ------------------------------------------------------------

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

import FiltriLista from './FiltriLista.vue'
import { useUiStore } from '../../stores/ui'
import { monta } from '../../../test/montaggio'

// Scopo: la finestra, cioe' l'unica cosa che decide quale dei due rami si rende.
// ⚠️ Si scrive `windowWidth` sullo store e non `window.innerWidth`: la soglia
//    ha UNA sede (`ui.isCompatto`), e un test che passasse dalla finestra vera
//    proverebbe il listener di resize invece del componente.
function finestra(larghezza) {
  useUiStore().windowWidth = larghezza
}

const DESKTOP = 1400
const COMPATTO = 800

// Scopo: il contratto dei filtri come lo offre uno store-lista, nella forma
//        minima che il componente legge.
function storeFinto({ filters = {}, defaults = {}, neutri = {}, azzera = () => {} } = {}) {
  return {
    filters,
    chiaviFiltro: Object.keys(defaults),
    filtriDefault: defaults,
    filtriNeutri: neutri,
    azzeraFiltri: azzera,
  }
}

// Gli slot nella forma in cui li scrive una view: la ricerca in `#sempre`, i
// filtri nel default.
const RICERCA = '<input class="finta-ricerca">'
const FILTRO = '<select class="finto-filtro"></select>'

// Scopo: i pulsanti che il componente rende nella toolbar (il drawer e'
//        teleportato: qui non c'e').
function pulsanti(w) {
  return w.findAll('button')
}

// Scopo: il segno, letto come lo legge il DOM. `null` quando non c'e' badge.
// ⚠️ Si guarda la CLASSE della severity (`p-badge-secondary`/`p-badge-info`),
//    non un colore: il colore e' CSS, e qui il CSS non esiste.
function segno(w) {
  const badge = w.find('.app-filtri-segno .p-badge')
  if (!badge.exists()) return null
  const spento = w.find('.app-filtri-senza-segno').exists()
  return {
    testo: badge.text(),
    grigio: badge.classes().includes('p-badge-secondary'),
    blu: badge.classes().includes('p-badge-info'),
    spento,
  }
}

describe('FiltriLista', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  // ⭐ IL DIFETTO CHE HA FATTO NASCERE QUESTO FILE (brief §10.4): su una lista
  //    con la sola casella di ricerca comparivano l'imbuto e un drawer VUOTO —
  //    un gesto che non porta da nessuna parte. Da desktop non si vedeva
  //    affatto, perche' il ramo compatto non si rende.
  it('1) con la SOLA ricerca non nasce l`imbuto', () => {
    finestra(COMPATTO)
    const w = monta(FiltriLista, { store: storeFinto() }, { slots: { sempre: RICERCA } })
    expect(w.find('.finta-ricerca').exists()).toBe(true)
    expect(w.find('.app-filtri-btn').exists()).toBe(false)
    expect(segno(w)).toBe(null)
  })

  it('2) su desktop i filtri stanno in linea, senza imbuto', () => {
    finestra(DESKTOP)
    const w = monta(FiltriLista, { store: storeFinto({ defaults: { stato: null } }) }, { slots: { sempre: RICERCA, default: FILTRO } })
    expect(w.find('.app-page-filters').exists()).toBe(true)
    expect(w.find('.app-page-filters--compatta').exists()).toBe(false)
    expect(w.find('.finto-filtro').exists()).toBe(true)
    expect(segno(w)).toBe(null)
  })

  it('3) nessun filtro valorizzato: segno spento', () => {
    finestra(COMPATTO)
    const w = monta(FiltriLista, {
      store: storeFinto({ filters: { stato: null }, defaults: { stato: null } }),
    }, { slots: { default: FILTRO } })
    expect(w.find('.app-filtri-btn').exists()).toBe(true)
    expect(segno(w).spento).toBe(true)
  })

  it('4) tutti al default: numero GRIGIO', () => {
    finestra(COMPATTO)
    const w = monta(FiltriLista, {
      store: storeFinto({
        filters: { data_da: '2026-07-01' },
        defaults: { data_da: '2026-07-01' },
      }),
    }, { slots: { default: FILTRO } })
    expect(segno(w)).toMatchObject({ testo: '1', grigio: true, blu: false, spento: false })
  })

  // ⚠️ Il numero conta TUTTI i filtri che restringono, default compresi (D4):
  //    con `data_da` al default piu' uno stato scelto si legge 2, ed e' giusto.
  it('5) uno diverso dal default: numero BLU, e i default contano lo stesso', () => {
    finestra(COMPATTO)
    const w = monta(FiltriLista, {
      store: storeFinto({
        filters: { data_da: '2026-07-01', stato: 'APERTA' },
        defaults: { data_da: '2026-07-01', stato: null },
      }),
    }, { slots: { default: FILTRO } })
    expect(segno(w)).toMatchObject({ testo: '2', grigio: false, blu: true })
  })

  // ⛔ Il valore che NON restringe, dichiarato (brief §11.9): «mostra storico»
  //    acceso scrive `false`, che deve viaggiare sul filo ma non filtra niente.
  //    Senza questa riga il numero SALIVA mentre la lista si allargava.
  it('6) un valore NEUTRO non conta: il segno si spegne', () => {
    finestra(COMPATTO)
    const w = monta(FiltriLista, {
      store: storeFinto({
        filters: { solo_ultima_revisione: false },
        defaults: { solo_ultima_revisione: true },
        neutri: { solo_ultima_revisione: false },
      }),
    }, { slots: { default: FILTRO } })
    expect(segno(w).spento).toBe(true)
  })

  // 🔴 IL DIFETTO DEL §11.10, e si vedeva solo nel drawer compatto: il pulsante
  //    era appeso al SEGNO invece che a «c'e' qualcosa da riportare al
  //    default». Portando un filtro al valore neutro la lista resta intera —
  //    nessun segno — ed e' esattamente lo stato in cui «Pulisci» e' l'unico
  //    gesto che riporta indietro.
  it('7) «Pulisci» c`e` anche senza segno, se c`e` da riportare al default', () => {
    finestra(DESKTOP)
    const w = monta(FiltriLista, {
      store: storeFinto({
        filters: { attivo: null },
        defaults: { attivo: true },
      }),
    }, { slots: { default: FILTRO } })
    expect(segno(w)).toBe(null)
    expect(pulsanti(w)).toHaveLength(1)
  })

  it('8) niente da pulire: nessun pulsante', () => {
    finestra(DESKTOP)
    const w = monta(FiltriLista, {
      store: storeFinto({ filters: { stato: null }, defaults: { stato: null } }),
    }, { slots: { default: FILTRO } })
    expect(pulsanti(w)).toHaveLength(0)
  })

  it('9) il click chiama `azzeraFiltri` dello store', async () => {
    finestra(DESKTOP)
    const azzera = vi.fn()
    const w = monta(FiltriLista, {
      store: storeFinto({
        filters: { stato: 'APERTA' }, defaults: { stato: null }, azzera,
      }),
    }, { slots: { default: FILTRO } })
    await pulsanti(w)[0].trigger('click')
    expect(azzera).toHaveBeenCalledOnce()
  })

  // 🔴 IL DIFETTO DEL §11 (il listener cercato in `useAttrs()`): Vue TOGLIE da
  //    `$attrs` gli handler degli eventi DICHIARATI in `defineEmits`, quindi
  //    `attrs.onPulisci` era `undefined` SEMPRE e sulle superfici senza
  //    store-lista — cruscotti, giornale: l'unica ragione per cui quel ramo
  //    esiste — «Pulisci filtri» non compariva mai.
  it('10) senza store il pulsante compare solo se qualcuno ascolta `@pulisci`', async () => {
    finestra(DESKTOP)
    const segnoModificato = { stato: 'modificato', conteggio: 1, modificato: true }

    const muto = monta(FiltriLista, { segno: segnoModificato }, {
      slots: { default: FILTRO },
    })
    expect(pulsanti(muto)).toHaveLength(0)

    const ascoltato = vi.fn()
    const w = monta(FiltriLista, { segno: segnoModificato, onPulisci: ascoltato }, {
      slots: { default: FILTRO },
    })
    expect(pulsanti(w)).toHaveLength(1)
    await pulsanti(w)[0].trigger('click')
    expect(ascoltato).toHaveBeenCalledOnce()
  })

  // ⛔ FAIL-VISIBLE: uno store che non dichiara le chiavi non fa fallire niente
  //    — il segno direbbe «nessun filtro» su una lista che filtra, ed e'
  //    esattamente la cosa che questo componente esiste per impedire.
  it('11) uno store senza `chiaviFiltro` lo grida in console', () => {
    finestra(COMPATTO)
    const spia = vi.spyOn(console, 'error').mockImplementation(() => {})
    const w = monta(FiltriLista, { store: { filters: { stato: 'APERTA' } } }, {
      slots: { default: FILTRO },
    })
    expect(spia).toHaveBeenCalled()
    expect(String(spia.mock.calls[0][0])).toContain('chiaviFiltro')
    expect(segno(w).spento).toBe(true)
    spia.mockRestore()
  })

  // ⚠️ D2: la ricerca NON e' un filtro, ed e' il gesto principale della lista —
  //    nasconderla dietro due tocchi proprio dove digitare costa di piu' e' il
  //    contrario di cio' che serve. Resta nella toolbar anche in compatta.
  it('12) la ricerca resta a video anche in compatta', () => {
    finestra(COMPATTO)
    const w = monta(FiltriLista, {
      store: storeFinto({ filters: { stato: 'APERTA' }, defaults: { stato: null } }),
    }, { slots: { sempre: RICERCA, default: FILTRO } })
    expect(w.find('.app-page-filters--compatta .finta-ricerca').exists()).toBe(true)
    // ...e i filtri no: quelli sono scesi nel drawer (teleportato fuori da qui).
    expect(w.find('.finto-filtro').exists()).toBe(false)
  })

  // ⭐ La casella dice la stessa cosa del catalogo (brief ricerca full §7-bis):
  //    su una lista senza colonne accese la ricerca non troverebbe niente.
  //    ⚠️ Solo `false` la toglie: `null` e' «configurazione non ancora
  //    arrivata», e una casella che sparisce e ricompare a ogni apertura
  //    sarebbe peggio di una che arriva un istante dopo.
  it('13) una lista che non cerca non ha la casella; `null` la lascia', () => {
    for (const larghezza of [DESKTOP, COMPATTO]) {
      finestra(larghezza)
      const non = monta(FiltriLista, { store: { ...storeFinto(), ricercaFull: false } },
        { slots: { sempre: RICERCA, default: FILTRO } })
      expect(non.find('.finta-ricerca').exists()).toBe(false)
      const ignoto = monta(FiltriLista, { store: { ...storeFinto(), ricercaFull: null } },
        { slots: { sempre: RICERCA } })
      expect(ignoto.find('.finta-ricerca').exists()).toBe(true)
      const si = monta(FiltriLista, { store: { ...storeFinto(), ricercaFull: true } },
        { slots: { sempre: RICERCA } })
      expect(si.find('.finta-ricerca').exists()).toBe(true)
    }
  })
})
