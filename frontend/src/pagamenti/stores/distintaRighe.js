// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: store della lista RIGHE DI UNA DISTINTA CONTABILE
//        (`pagamenti.distinta_righe`, lista 69), consumata dal drawer della
//        distinta attraverso `useDrawerTabLista`.
//
// PERCHE' ESISTE (2026-09-18, rilievo in-app di Tid). Il drawer teneva le
// righe dentro il dettaglio (`dettaglio.righe`) e le disegnava con una
// `DataTable` grezza: la lista non paginava, non si ricaricava da sola, non si
// potevano scegliere le colonne e non si poteva scaricare niente — nessuna
// delle caratteristiche di una lista standard. La ragione scritta era «sono le
// righe di un documento», ma le righe contabili hanno endpoint propri, una
// macchina a stati propria e una coda propria (`pagamenti.righe`): sono
// un'entita' con vita propria, cioe' la prima domanda del criterio in tre
// domande (piano PrimeVue 5 §Gruppo B), come i titoli IVA il 02/09.
//
// ⭐ NON E' SCRITTO A MANO. Il corpo — filtri, fetch paginata, cancello
//    empty-state, sospensione, reset, e la distinzione fra «vuota» e «non
//    letta» — vive in `createListaStore` / `useListaStoreCore`. Qui restano
//    solo le tre cose che sono DI QUESTA lista: quale endpoint, come si chiama
//    il padre, e come si legge.
//
// ⭐ IL PADRE E' NELLO STORE, NON NEI FILTRI: `contabileId` e' il contesto
//    (arriva dal path dell'endpoint), i filtri sono le scelte dell'operatore —
//    e al cambio padre i secondi si azzerano mentre il primo si riscrive.
//
// ⛔ NESSUN `orderBy` di partenza, ed e' voluto: senza indicazioni il backend
//    ordina `id DESC`, cioe' l'ULTIMA RIGA DIGITATA IN CIMA — la scelta di Tid
//    del 02/09 sugli atti di sistemazione, per la stessa ragione: da quando la
//    lista impagina, una riga appena scritta in ordine crescente finirebbe
//    nell'ultima pagina e chi l'ha appena digitata non la vedrebbe. Scrivere
//    qui una colonna cambierebbe l'ordine di apertura senza che nessuno
//    l'abbia chiesto, e lo farebbe divergere dal default del backend.
import { createListaStore } from '../../core/stores/createListaStore'
import { listRigheDistinta } from '../api/pagamenti'

export const useDistintaRigheStore = createListaStore(
  'pagamenti-distinta-righe',
  {
    fetchPage: listRigheDistinta,
    parentField: 'contabileId',
    // La distinta e' gia' scelta quando il drawer si apre: non e' una lista che
    // parte vuota in attesa di una ricerca.
    startsEmpty: false,
    orderDir: null,
  },
)
