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
import { storePerIstanza } from '../../core/stores/storePerIstanza'

// ⭐ Uno store per ISTANZA del drawer (`storePerIstanza`, 2026-09-27): due
//    drawer dello stesso tipo vivi insieme non si scrivono addosso la lista.
export const useEmittentiFiscaliBAStore = storePerIstanza('amm-emittenti-fiscali-ba', (id) => createListaStore(id, {
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

    // Scopo: Carica il summary BA per l'emittente corrente.
    // ⛔ L'errore RISALE a chi chiama, che lo dice (`execute` nel tab). Fino al
    //    2026-10-23 lo inghiottiva qui, «l'interceptor mostra l'errore HTTP»: ma
    //    l'interceptor di `core/api.js` non mostra toast, e un summary che non
    //    arrivava lasciava `hasDefault` vecchio senza un motivo.
    // ⚠️ Per lo stesso motivo le scritture qui sotto NON lo rileggono: un
    //    summary che fallisce dopo un POST riuscito farebbe sembrare fallita la
    //    scrittura. Lo rilegge il tab, dopo l'esito.
    async function fetchSummary() {
      if (!emittenteId.value) {
        hasDefaultMapping.value = false
        countSpecifici.value = 0
        return
      }
      const res = await getEmittenteBillingAccountSummary(emittenteId.value)
      const data = res.data.data
      hasDefaultMapping.value = !!data.has_default
      countSpecifici.value = data.count_specifici || 0
    }

    // Scopo: Aggiunge mapping e ricarica la lista (il summary lo rilegge il
    //        chiamante: vedi `fetchSummary`).
    async function addMapping(payload) {
      const res = await createEmittenteBillingAccount(emittenteId.value, payload)
      await fetchList()
      return res.data.data
    }

    // Scopo: Elimina mapping e ricarica la lista (il summary: vedi sopra).
    async function removeMapping(mappingId) {
      await deleteEmittenteBillingAccount(emittenteId.value, mappingId)
      await fetchList()
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
}))
