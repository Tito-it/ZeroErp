// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: Store della lista delle FAMIGLIE DI DOCUMENTO. Contratto
//        `useSearchTable` (filters, items, totalRecords, loading, fetchList),
//        consumato da `useListaConfigurabilePage`.
//
// ⭐ Dal 2026-09-18 e' `createListaStore`: era uno store scritto a mano su
//    `useListaEmptyStateFetch` con la copia del `buildParams`. Era pero' anche
//    l'UNICO che aveva gia' capito una cosa: i parametri di filtro devono avere
//    una sede sola per la lista E per l'export (`paramsFiltro`), perche' un
//    export che se li ricostruisce esporta un insieme DIVERSO da quello a video
//    appena se ne aggiunge uno. Quella funzione oggi la espone il core con lo
//    stesso nome, e la view continua a chiamare `store.paramsFiltro()`.
//
// ⚠️ `userScoped: true` (default della factory) anche se il catalogo e'
//    globale: lo store tiene comunque cio' che QUESTO utente ha caricato e i
//    suoi filtri, e al logout non deve restare in memoria per il prossimo
//    (`feedback_pinia_userscoped`).

import { createListaStore } from '../../core/stores/createListaStore'
import {
  createFamiglia,
  listFamiglie,
  setFamigliaAttiva,
  updateFamiglia,
} from '../api/famiglieDocumento'

export const useFamiglieDocumentoStore = createListaStore('amm-famiglie-documento', {
  fetchPage: listFamiglie,
  // Parte piena: e' un catalogo, non una ricerca.
  startsEmpty: false,
  orderBy: 'codice_interno',
  filterDefaults: {
    // ⛔ `null` = TUTTE, spente comprese, ed e' il default voluto: una famiglia
    //    spenta e' la riga che spiega perche' una tabella non e' disponibile.
    //    ⚠️ E il core confronta con `!= null`: `false` («solo le spente») e'
    //    un filtro legittimo che un truthy-check tratterebbe come «nessuno».
    attivo: null,
    gestisce_serie: null,
  },
  extend: ({ fetchList }) => {
    // Scopo: crea la famiglia e ricarica. ⭐ Ritorna la riga PIU'
    //        `registri_creati`, che il drawer mostra: la madre ha appena
    //        provveduto i registri su ogni emittente, e chi ha premuto «salva»
    //        deve saperlo.
    async function crea(payload) {
      const res = await createFamiglia(payload)
      await fetchList()
      return res.data.data
    }

    async function aggiorna(id, payload) {
      const res = await updateFamiglia(id, payload)
      await fetchList()
      return res.data.data
    }

    // Scopo: il verbo `attivo`, usato sia per spegnere sia per riaccendere.
    async function cambiaAttivo(id, attivo) {
      const res = await setFamigliaAttiva(id, attivo)
      await fetchList()
      return res.data.data
    }

    return { crea, aggiorna, cambiaAttivo }
  },
})
