// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: store della lista ATTI DI SISTEMAZIONE DI UNA FATTURA
//        (`pagamenti.sistemazioni_fattura`, lista 61), consumata dal drawer
//        dell'eccedenza attraverso `useDrawerTabLista`.
//
// PERCHE' ESISTE (2026-09-02). Il drawer teneva gli atti in tre `ref` locali
// (righe, totale, «letti») e chiamava l'endpoint senza parametri: la lista non
// paginava, non si potevano scegliere le colonne e non si poteva scaricare
// niente. La ragione scritta era «gli atti di UNA fattura sono pochi per
// modello» — che e' una previsione sui DATI, e una previsione sui dati non
// decide la forma di una lista (regola zero). Decisione di Tid: sullo standard.
//
// ⭐ NON E' PIU' SCRITTO A MANO. Il corpo — filtri, fetch paginata, cancello
//    empty-state, sospensione, reset, e la distinzione fra «vuota» e «non
//    letta» — vive in `createListaStore` / `useListaStoreCore` dal 2026-09-02
//    (regola del 2, ok Tid). Qui restano solo le tre cose che sono DI QUESTA
//    lista: quale endpoint, come si chiama il padre, e come si legge.
//
// ⭐ IL PADRE E' NELLO STORE, NON NEI FILTRI: `fatturaId` e' il contesto (arriva
//    dal path dell'endpoint), i filtri sono le scelte dell'operatore — e al
//    cambio padre i secondi si azzerano mentre il primo si riscrive.
//
// ⛔ NESSUN `orderBy` di partenza, ed e' voluto: senza indicazioni il backend
//    ordina `s.id DESC`, cioe' l'ultimo atto deciso in cima — il verso del
//    registro gemello dei movimenti, e quello che fa vedere subito un atto
//    appena registrato anche quando la lista impagina. Scrivere qui una colonna
//    qualsiasi cambierebbe l'ordine di apertura senza che nessuno l'abbia
//    chiesto, e lo farebbe divergere dal default del backend.
import { createListaStore } from '../../core/stores/createListaStore'
import { listSistemazioniFattura } from '../api/pagamenti'
import { storePerIstanza } from '../../core/stores/storePerIstanza'

// ⭐ Uno store per ISTANZA del drawer (`storePerIstanza`, 2026-09-27): due
//    drawer dello stesso tipo vivi insieme non si scrivono addosso la lista.
export const useSistemazioniFatturaStore = storePerIstanza('pagamenti-sistemazioni-fattura', (id) => createListaStore(id,
  {
    fetchPage: listSistemazioniFattura,
    parentField: 'fatturaId',
    // La fattura e' gia' scelta quando il drawer si apre: non e' una lista che
    // parte vuota in attesa di una ricerca.
    startsEmpty: false,
    orderDir: null,
  },
))
