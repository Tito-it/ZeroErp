// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: Store della lista registri di numerazione di UN emittente fiscale.
//        Contratto `useSearchTable` (filters, items, totalRecords, loading,
//        fetchList), consumato da `useDrawerTabLista`.
//
// ⭐ Dal 2026-09-18 e' `createListaStore` col padre dichiarato
//    (`parentField`): era uno store scritto a mano su `useListaEmptyStateFetch`
//    con la copia del `buildParams`, un wrapper di `fetchList` per il guard
//    «senza emittente non si chiama» e un `reset()` parziale — tutte cose che
//    il core fa da se'. ⚠️ Qui il padre NON sta nel path ma in QUERY
//    (`emittente_soggetto_ruolo_id`): lo aggiunge la `fetchPage`, che e'
//    l'unico punto che conosce il contratto dell'endpoint.
//
// ⚠️ `userScoped: true` (default della factory): lo store porta dati
//    dell'utente (i registri che il suo scope emittente gli fa vedere). Senza,
//    al logout resterebbero in memoria e il prossimo login vedrebbe la lista
//    del precedente (`feedback_pinia_userscoped`).

import { createListaStore } from '../../core/stores/createListaStore'
import {
  createRegistro,
  listRegistri,
  setRegistroAttivo,
  updateRegistro,
} from '../api/registriNumerazione'

export const useRegistriNumerazioneStore = createListaStore('amm-registri-numerazione', {
  // Il padre in query, non nel path: e' il SOGGETTO-RUOLO dell'emittente, non
  // la PK di `anagrafiche.emittenti_fiscali` — ed e' per questo che il campo lo
  // dice per intero. Un nome che dichiara una famiglia di id e ne contiene
  // un'altra non solleva niente: filtra su numeri che non corrispondono e la
  // lista esce vuota (`feedback_emittente_pk_vs_soggetto_ruolo`).
  fetchPage: (emittenteSoggettoRuoloId, params) => (
    listRegistri({ ...params, emittente_soggetto_ruolo_id: emittenteSoggettoRuoloId })
  ),
  parentField: 'emittenteSoggettoRuoloId',
  // Parte piena: sono i registri di QUESTO emittente.
  startsEmpty: false,
  orderBy: 'codice',
  filterDefaults: {
    // ⛔ `null` = TUTTI, ed e' il default voluto (§FE-3): la lista deve
    //    mostrare anche gli spenti, perche' sono le righe che spiegano il
    //    rifiuto su una terna gia' occupata. Un default «solo attivi»
    //    nasconderebbe proprio quelle. ⚠️ E il core confronta con `!= null`,
    //    non con un truthy-check: `false` («solo i disattivati») e' un filtro
    //    legittimo che un `if (f.attivo)` butterebbe via.
    attivo: null,
    famiglia_documento: null,
  },
  extend: ({ emittenteSoggettoRuoloId, fetchList }) => {
    // Scopo: crea il registro e ricarica. L'emittente NON viene dal form: lo
    //        porta il contesto del tab.
    async function crea(payload) {
      const emittente = { emittente_soggetto_ruolo_id: emittenteSoggettoRuoloId.value }
      const res = await createRegistro({ ...payload, ...emittente }, emittente)
      await fetchList()
      return res.data.data
    }

    async function aggiorna(id, payload) {
      const res = await updateRegistro(id, payload)
      await fetchList()
      return res.data.data
    }

    // Scopo: il verbo `attivo`, usato sia per spegnere sia per RIATTIVARE.
    async function cambiaAttivo(id, attivo) {
      const res = await setRegistroAttivo(id, attivo)
      await fetchList()
      return res.data.data
    }

    return { crea, aggiorna, cambiaAttivo }
  },
})
