// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
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
// ⛔ IL PADRE E' UNA COPPIA DI ID, non uno solo, e la chiave e' una STRINGA
//    COMPOSTA (`soggettoId|titoloId`). Due ragioni, e la seconda e' un difetto
//    evitato:
//      1. l'endpoint e' annidato due volte (`/soggetti/{s}/titoli-iva/{t}/...`),
//         e il building block conosce UN solo `parentField`;
//      2. `useDrawerTabLista` mette un `watch` sul valore del padre. Un OGGETTO
//         `{soggettoId, titoloId}` sarebbe nuovo a ogni render — identita'
//         diversa, stesso contenuto — e il watch rifarebbe la fetch a ogni
//         ridisegno, senza che niente segnali il giro a vuoto. Una stringa e'
//         un primitivo: cambia solo quando cambia davvero.
//
// ⚠️ Il separatore e' `|` e non `/`: un id di soggetto e' un UUID e un id di
//    titolo un intero, quindi nessuno dei due puo' contenerlo — la `split` non
//    ha casi limite.
import { createListaStore } from '../../core/stores/createListaStore'
import { listTitoloIvaAmbiti, listTitoloIvaMovimenti } from '../api/anagrafiche'

const SEP = '|'

// Scopo: la chiave del padre, nella forma che le due fetch sanno sciogliere.
//        Esportata perche' la compone il drawer: se la componesse a mano,
//        drawer e store userebbero due separatori diversi il giorno che uno
//        cambia.
export function chiaveTitolo(soggettoId, titoloId) {
  return `${soggettoId}${SEP}${titoloId}`
}

function sciogli(chiave) {
  const [soggettoId, titoloId] = String(chiave).split(SEP)
  return [soggettoId, Number(titoloId)]
}

export const useTitoloIvaAmbitiStore = createListaStore(
  'anagrafiche-titolo-iva-ambiti',
  {
    fetchPage: (chiave, params) => {
      const [soggettoId, titoloId] = sciogli(chiave)
      return listTitoloIvaAmbiti(soggettoId, titoloId, params)
    },
    parentField: 'chiaveTitolo',
    // Il titolo e' gia' scelto quando la sezione compare.
    startsEmpty: false,
    // ⛔ Nessun ordinamento di partenza: a catalogo NESSUNA colonna della 64 e'
    //    `ordinabile`, e l'ordine lo decide il backend (livello, poi id).
    //    Chiederne uno significherebbe chiedere al server una cosa che scarta.
    orderDir: null,
  },
)

export const useTitoloIvaMovimentiStore = createListaStore(
  'anagrafiche-titolo-iva-movimenti',
  {
    fetchPage: (chiave, params) => {
      const [soggettoId, titoloId] = sciogli(chiave)
      return listTitoloIvaMovimenti(soggettoId, titoloId, params)
    },
    parentField: 'chiaveTitolo',
    startsEmpty: false,
    // ⛔ Nessun ordinamento di partenza, ed e' voluto: senza indicazioni il
    //    backend serve il piu' RECENTE per primo, che e' come si legge un
    //    registro. Scrivere qui una colonna cambierebbe quell'ordine senza che
    //    nessuno l'abbia chiesto.
    orderDir: null,
  },
)
