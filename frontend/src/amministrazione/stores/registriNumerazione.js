// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: Store della lista registri di numerazione di UN emittente fiscale.
//        Contratto `useSearchTable` (filters, items, totalRecords, loading,
//        fetchList), consumato da `useDrawerTabLista`.
//
// ⚠️ `userScoped: true`: lo store porta dati dell'utente (i registri che il suo
//    scope emittente gli fa vedere). Senza, al logout resterebbero in memoria e
//    il prossimo login vedrebbe la lista del precedente
//    (`feedback_pinia_userscoped`).

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useListaEmptyStateFetch } from '../../core/composables/useListaEmptyStateFetch'
import {
  createRegistro,
  listRegistri,
  setRegistroAttivo,
  updateRegistro,
} from '../api/registriNumerazione'

export const useRegistriNumerazioneStore = defineStore('amm-registri-numerazione', () => {
  // L'emittente corrente, scritto dal tab (via `parentField` del BB).
  // ⚠️ E' il SOGGETTO-RUOLO, non la PK di `anagrafiche.emittenti_fiscali`, ed
  //    e' per questo che il nome lo dice per intero. Un nome che dichiara una
  //    famiglia di id e ne contiene un'altra e' il modo in cui questo difetto
  //    si ripete: non solleva niente, filtra su numeri che non corrispondono e
  //    la lista esce vuota (`feedback_emittente_pk_vs_soggetto_ruolo`).
  const emittenteSoggettoRuoloId = ref(null)

  const filters = ref({
    search: '',
    limit: 25,
    offset: 0,
    order_by: 'codice',
    order_dir: 'asc',
    // ⛔ `null` = TUTTI, ed e' il default voluto (§FE-3): la lista deve
    //    mostrare anche gli spenti, perche' sono le righe che spiegano il
    //    rifiuto su una terna gia' occupata. Un default «solo attivi»
    //    nasconderebbe proprio quelle.
    attivo: null,
    famiglia_documento: null,
  })

  const {
    items, totalRecords, loading, fetchList: fetchListBase, svuota,
  } = useListaEmptyStateFetch({
    filters,
    alwaysFetch: true,
    buildParams: (f) => {
      const params = { limit: f.limit, offset: f.offset }
      if (f.search) params.search = f.search
      if (f.order_by) {
        params.order_by = f.order_by
        params.order_dir = f.order_dir || 'asc'
      }
      // ⚠️ Il confronto e' con `null`, non `if (f.attivo)`: `false` e' un
      //    filtro legittimo («solo i disattivati») e un truthy-check lo
      //    tratterebbe come «nessun filtro», mostrando anche gli attivi.
      if (f.attivo !== null && f.attivo !== undefined) params.attivo = f.attivo
      if (f.famiglia_documento) params.famiglia_documento = f.famiglia_documento
      params.emittente_soggetto_ruolo_id = emittenteSoggettoRuoloId.value
      return params
    },
    fetchPage: (params) => listRegistri(params),
  })

  async function fetchList() {
    if (!emittenteSoggettoRuoloId.value) return
    await fetchListBase()
  }

  // Scopo: crea il registro e ricarica. L'emittente NON viene dal form: lo
  //        porta il contesto del tab.
  async function crea(payload) {
    const res = await createRegistro({
      ...payload,
      emittente_soggetto_ruolo_id: emittenteSoggettoRuoloId.value,
    })
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

  function reset() {
    // `svuota` del BB e non un clear a mano: invalida anche le fetch in volo,
    // cosi' la risposta dell'emittente precedente non ripopola la lista.
    svuota()
    emittenteSoggettoRuoloId.value = null
    filters.value.search = ''
    filters.value.offset = 0
    filters.value.attivo = null
    filters.value.famiglia_documento = null
  }

  return {
    items, totalRecords, loading, filters, emittenteSoggettoRuoloId,
    fetchList, crea, aggiorna, cambiaAttivo, reset,
  }
}, { userScoped: true })
