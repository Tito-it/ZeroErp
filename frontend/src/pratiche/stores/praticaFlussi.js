// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: store della lista FLUSSI DI UNA PRATICA (`pratiche.flussi`, lista
//        85), consumata dal tab «Flussi» del drawer pratica attraverso
//        `useDrawerTabLista`.
// Note: ⭐ PERCHE' ESISTE (2026-09-27, brief-db-liste-datatable-grezze riga
//       3). Il tab teneva i flussi in un `ref` locale e li mostrava in una
//       `DataTable` grezza: niente pagine, niente scelta colonne, niente
//       export, e l'esito a video era il CODICE grezzo. Ora e' la lista a
//       catalogo, con l'esito come descrizione (§8 punto 3, Tid).
//       ⭐ IL PADRE E' COMPOSTO — la pratica (nel path) e il suo EMITTENTE
//       (in query, `emittente_fiscale_id`, il `lista_emittente_param` della
//       view): la lista non e' `multi_emittente`, e senza chi ha piu'
//       emittenti nello scope riceverebbe il 422 dentro una pratica gia'
//       aperta. E' il padre composto del core (`emittenteParam`, 2026-09-27):
//       finche' manca l'emittente la lista non legge ed e' in `attesaPadre`.
//       E' contesto come la pratica, non un filtro: per questo non sta in
//       `filterDefaults`, dove «Pulisci filtri» lo toglierebbe e il segno dei
//       filtri lo conterebbe.
// ------------------------------------------------------------
import { createListaStore } from '../../core/stores/createListaStore'
import { storePerIstanza } from '../../core/stores/storePerIstanza'
import { listFlussi } from '../api/pratiche-api'

// Uno store per tab (`storePerIstanza`): due pratiche aperte insieme (la
// dashboard sotto KeepAlive e una pratica dalla cella lineage) non si
// scrivono addosso i flussi.
export const usePraticaFlussiStore = storePerIstanza(
  'pratiche-pratica-flussi',
  (id) => createListaStore(id, {
    fetchPage: listFlussi,
    parentField: 'praticaId',
    emittenteParam: 'emittente_fiscale_id',
    // La pratica e' gia' aperta quando il tab compare.
    startsEmpty: false,
    // L'ordine di lettura di un percorso: la posizione del flusso nella
    // pratica. E' anche il default del backend — qui serve a far vedere la
    // freccia sulla colonna giusta.
    orderBy: 'sequenza',
    orderDir: 'asc',
  }),
)
