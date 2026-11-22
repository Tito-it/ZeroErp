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
import { USO_MISURA, misuraDefault } from '../../core/misurePagina'

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
      limit: misuraDefault(USO_MISURA.PAGINA),
      offset: 0,
      // ⭐ Nessun ordinamento di partenza qui (residuo di BE25 (2) di
      //    brief-db-revisione-ui): lo dichiara il preset della lista, il backend
      //    lo applica e lo dice in `meta.ordinamento`, da cui la tabella accende
      //    l'intestazione.
      order_by: null,
      order_dir: null,
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
