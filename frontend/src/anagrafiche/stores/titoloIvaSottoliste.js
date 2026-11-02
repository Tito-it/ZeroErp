// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: gli store delle DUE sotto-liste di `TitoloIvaDrawer` — gli ambiti
//        (lista 64) e il registro dei movimenti (lista 65), seminate col
//        lotto 3 il 2026-09-02.
//
// PERCHE' ESISTONO. Le due tabelle erano `DataTable` grezze alimentate dal
// payload del DETTAGLIO (`detail.ambiti`, `detail.movimenti`): nessuna pagina,
// nessuna scelta delle colonne, e per il registro nemmeno un limite — cresce a
// ogni fattura. Ora leggono i loro endpoint, che sono sempre esistiti.
//
// ⭐ IL PADRE E' UNA COPPIA DI ID — l'endpoint e' annidato due volte
//    (`/soggetti/{s}/titoli-iva/{t}/...`) — ed e' il PADRE COMPOSTO del core
//    (`parentField: ['soggettoId', 'titoloId']`, 2026-09-27): le due parti
//    arrivano alla `fetchPage` nell'ordine del path, e il drawer le passa a
//    `useDrawerTabLista` una per una. ⚠️ Fino a quel giorno era una chiave-
//    stringa `soggettoId|titoloId` con la sua `sciogli`, e da qui la forma si
//    era ricopiata in altri tre store: il perche' della chiave (un oggetto nel
//    `watch` rifarebbe la fetch a ogni render) ora lo scioglie il watch
//    multi-sorgente del BB.
// ⚠️ Nessun `emittenteParam`: le due view non dichiarano
//    `lista_emittente_param`, il perimetro vale come sul padre.
import { createListaStore } from '../../core/stores/createListaStore'
import { listTitoloIvaAmbiti, listTitoloIvaMovimenti } from '../api/anagrafiche'
import { storePerIstanza } from '../../core/stores/storePerIstanza'

// ⭐ Uno store per ISTANZA del drawer (`storePerIstanza`, 2026-09-27): due
//    drawer dello stesso tipo vivi insieme non si scrivono addosso la lista.
export const useTitoloIvaAmbitiStore = storePerIstanza('anagrafiche-titolo-iva-ambiti', (id) => createListaStore(id,
  {
    fetchPage: listTitoloIvaAmbiti,
    parentField: ['soggettoId', 'titoloId'],
    // Il titolo e' gia' scelto quando la sezione compare.
    startsEmpty: false,
    // ⛔ Nessun ordinamento di partenza: a catalogo NESSUNA colonna della 64 e'
    //    `ordinabile`, e l'ordine lo decide il backend (livello, poi id).
    //    Chiederne uno significherebbe chiedere al server una cosa che scarta.
    orderDir: null,
  },
))

export const useTitoloIvaMovimentiStore = storePerIstanza('anagrafiche-titolo-iva-movimenti', (id) => createListaStore(id,
  {
    fetchPage: listTitoloIvaMovimenti,
    parentField: ['soggettoId', 'titoloId'],
    startsEmpty: false,
    // ⛔ Nessun ordinamento di partenza, ed e' voluto: senza indicazioni il
    //    backend serve il piu' RECENTE per primo, che e' come si legge un
    //    registro. Scrivere qui una colonna cambierebbe quell'ordine senza che
    //    nessuno l'abbia chiesto.
    orderDir: null,
  },
))
