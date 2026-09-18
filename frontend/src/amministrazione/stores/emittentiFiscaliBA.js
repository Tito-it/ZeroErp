// Pinia store per lista paginata mapping BA -> emittente fiscale.
// Separato dallo store principale emittentiFiscali perche' la lista BA
// usa useSearchTable (contratto: filters, items, totalRecords, loading, fetchList).
//
// ⭐ Dal 2026-09-18 e' `createListaStore` con il padre nel PATH
//    (`parentField: 'emittenteId'`): era uno store scritto a mano su
//    `useListaEmptyStateFetch` con la copia del `buildParams` e un wrapper di
//    `fetchList` che rifaceva a mano il guard «senza padre non si chiama» —
//    che il core ha gia'. Il tab lo pilota con `useDrawerTabLista`, che scrive
//    `store.emittenteId` e chiama `reset()` quando il padre sparisce.

import { ref } from 'vue'
import { createListaStore } from '../../core/stores/createListaStore'
import {
  listEmittenteBillingAccount,
  createEmittenteBillingAccount,
  deleteEmittenteBillingAccount,
  getEmittenteBillingAccountSummary,
} from '../api/emittentiFiscali'

export const useEmittentiFiscaliBAStore = createListaStore('amm-emittenti-fiscali-ba', {
  fetchPage: (emittenteId, params) => listEmittenteBillingAccount(emittenteId, params),
  parentField: 'emittenteId',
  // Parte piena: e' la lista dei mapping di QUESTO emittente.
  startsEmpty: false,
  orderBy: 'billing_account_codice',
  extend: (lista) => {
    const { emittenteId, fetchList, reset: resetLista } = lista

    // Summary BA mapping (has_default + count_specifici): indipendente dalla
    // pagina corrente. Bypassa il bug della derivazione da `items` con liste
    // paginate. Aggiornato dopo ogni write + al cambio emittenteId.
    const hasDefaultMapping = ref(false)
    const countSpecifici = ref(0)

    // Scopo: Carica il summary BA per l'emittente corrente. Best-effort:
    //        in caso di errore lascia i valori precedenti senza notificare
    //        (l'interceptor mostra l'errore HTTP, lo stato UX e' coerente).
    async function fetchSummary() {
      if (!emittenteId.value) {
        hasDefaultMapping.value = false
        countSpecifici.value = 0
        return
      }
      try {
        const res = await getEmittenteBillingAccountSummary(emittenteId.value)
        const data = res.data.data
        hasDefaultMapping.value = !!data.has_default
        countSpecifici.value = data.count_specifici || 0
      } catch {
        // Errore gia' notificato dall'interceptor axios globale.
      }
    }

    // Scopo: Aggiunge mapping e ricarica la lista + summary.
    async function addMapping(payload) {
      const res = await createEmittenteBillingAccount(emittenteId.value, payload)
      await Promise.all([fetchList(), fetchSummary()])
      return res.data.data
    }

    // Scopo: Elimina mapping e ricarica la lista + summary.
    async function removeMapping(mappingId) {
      await deleteEmittenteBillingAccount(emittenteId.value, mappingId)
      await Promise.all([fetchList(), fetchSummary()])
    }

    // Scopo: il reset del core (lista, padre, filtri) piu' il summary, che il
    //        core non conosce: e' stato di dominio, e lo azzera chi l'ha scritto.
    function reset() {
      resetLista()
      hasDefaultMapping.value = false
      countSpecifici.value = 0
    }

    return { hasDefaultMapping, countSpecifici, fetchSummary, addMapping, removeMapping, reset }
  },
})
