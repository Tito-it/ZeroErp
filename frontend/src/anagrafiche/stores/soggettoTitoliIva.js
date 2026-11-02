// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: store della lista TITOLI IVA DI UN SOGGETTO
//        (`anagrafiche.soggetto_titoli_iva`, lista 62), consumata dal drawer
//        omonimo attraverso `useDrawerTabLista`.
//
// PERCHE' ESISTE (2026-09-02). Il drawer teneva le righe in due `ref` locali e
// chiamava l'endpoint senza parametri: la lista non paginava, non si potevano
// scegliere le colonne e non si poteva scaricare niente — cioe' era fuori dallo
// standard delle altre quaranta liste, ma senza che niente lo dicesse. Lo
// scaffolding `useDrawerTabLista` quelle tre cose le porta gia', e in cambio
// vuole il contratto di `useSearchTable`: e' questo store.
//
// ⭐ IL PADRE E' NELLO STORE, NON NEI FILTRI, ed e' la distinzione che il BB
//    fa sua: `soggettoId` e' il contesto (arriva dal path dell'endpoint), i
//    filtri sono le scelte dell'operatore — e al cambio padre i secondi si
//    azzerano mentre il primo si riscrive.
//
// ⚠️ `userScoped: true`: la lista porta dati che l'operatore vede per il suo
//    perimetro emittente (la RLS filtra i titoli per emittente in whitelist).
//    Senza, al logout resterebbero in memoria (`feedback_pinia_userscoped`).
//
// ⭐ NON E' PIU' SCRITTO A MANO (2026-09-02, regola del 2 · ok Tid): il corpo —
//    filtri, fetch paginata, cancello empty-state, sospensione, reset — vive in
//    `createListaStore` / `useListaStoreCore`. Era la seconda di TRE copie, e le
//    tre avevano gia' lo stesso difetto: nessuna esponeva `fetchSospesa`, quindi
//    col cancello di perimetro emittente alzato la lista continuava a chiedere
//    pagine che il backend rifiuta con 422. Il BB la espone per tutte.
import { createListaStore } from '../../core/stores/createListaStore'
import { listSoggettoTitoliIva } from '../api/anagrafiche'
import { storePerIstanza } from '../../core/stores/storePerIstanza'

// ⭐ Uno store per ISTANZA del drawer (`storePerIstanza`, 2026-09-27): due
//    drawer dello stesso tipo vivi insieme non si scrivono addosso la lista.
export const useSoggettoTitoliIvaStore = storePerIstanza('anagrafiche-soggetto-titoli-iva', (id) => createListaStore(id,
  {
    fetchPage: listSoggettoTitoliIva,
    parentField: 'soggettoId',
    // Il soggetto e' gia' scelto quando il drawer si apre.
    startsEmpty: false,
    // ⛔ NESSUN ordinamento di partenza: senza indicazioni il backend applica
    //    quello STORICO — validita' piu' lunga per prima, titoli senza scadenza
    //    in cima. Scrivere qui una colonna cambierebbe l'ordine di apertura di
    //    una lista che tutti leggono dall'alto.
    orderDir: null,
  },
))
