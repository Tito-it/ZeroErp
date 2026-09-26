// Store Pinia della coda approvazioni prezzo (workflow L3, pratiche tipo
// APPROVAZIONE_PREZZO in stato APERTA), promossa a lista configurabile
// (<ListaConfigurabile codice="vendite.approvazioni_prezzo">,
// ui.lista_definizione id 36 — 7° lotto, 2026-08-03).
//
// Interfaccia useSearchTable-compatibile (items/totalRecords/loading/filters/
// fetchList/hasSearched) via useListaEmptyStateFetch.
//
// Semantica CODA DI LAVORO: niente floor temporale, `alwaysFetch: true` —
// il lavoro pendente e' sempre visibile al mount. L'endpoint non ha search
// ne' filtri: passano solo paginazione e ordinamento (whitelist BE
// PRATICHE_ORDER_COLS, inchiodatura rimossa il 2026-08-02).
//
// userScoped: true → reset al logout (memoria feedback_pinia_userscoped).

import { defineStore } from 'pinia'
import { ref } from 'vue'

import { useListaEmptyStateFetch } from '../../core/composables/useListaEmptyStateFetch'
import { listCodaApprovazioni } from '../api/approvazioniPrezzo'

// Scopo: mappa filtri store → query params dell'endpoint coda (solo
//        paginazione + ordinamento: l'endpoint non legge altro).
function buildParams(f) {
  return {
    limit: f.limit,
    offset: f.offset,
    order_by: f.order_by,
    order_dir: f.order_dir,
  }
}

export const useApprovazioniPrezzoStore = defineStore(
  'vendite-approvazioni-prezzo',
  () => {
    const filters = ref({
      limit: 25,
      offset: 0,
      // Default sort allineato al default storico del BE e al preset del
      // seed (data_insert desc): al primo caricamento la lista non si
      // riordina sotto gli occhi dell'operatore.
      order_by: 'data_insert',
      order_dir: 'desc',
    })

    // `lista`: lo stato del BB, esposto INTERO nel `return` (`...lista`).
    // ⛔ Non si elencano i suoi ref a mano: un ref nuovo del BB (com'e'
    //    successo con `ricercaFull`, `ricercaMinCaratteri`,
    //    `ricercaCambiaLaRichiesta`) arriverebbe solo agli store che lo
    //    ricordano — e senza errore sugli altri.
    const lista = useListaEmptyStateFetch({
      filters,
      buildParams,
      fetchPage: listCodaApprovazioni,
      alwaysFetch: true,
    })

    return { ...lista, filters }
  },
  {
    userScoped: true,
  },
)
