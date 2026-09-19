// Pinia store per la gestione account email (lista, dettaglio, CRUD).
//
// ⭐ Dal 2026-09-18 la lista e' `createListaStore`: era uno store scritto a mano
//    su `useListaEmptyStateFetch` con la copia del `buildParams`. Non e'
//    `createCrudStore` perche' il contratto del dettaglio e' diverso — il
//    drawer legge `currentAccount` dallo store, e `update` lo riallinea — e un
//    `fetchDetail` che ritorna il dato sarebbe un contratto che qui nessuno
//    legge.

import { ref } from 'vue'
import { createListaStore } from '../../core/stores/createListaStore'
import {
  listEmailAccounts,
  getEmailAccount,
  createEmailAccount,
  updateEmailAccount,
} from '../api/amministrazione'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../core/constants'

export const useEmailAccountsStore = createListaStore('amm-email-accounts', {
  fetchPage: listEmailAccounts,
  // Parte piena: e' una configurazione, non una ricerca.
  startsEmpty: false,
  orderBy: 'codice',
  extend: () => {
    const { emitDataChanged } = useTabEvents()
    const currentAccount = ref(null)
    const loadingDetail = ref(false)

    // Scopo: carica il dettaglio nello store (il drawer legge `currentAccount`).
    async function fetchDetail(id) {
      loadingDetail.value = true
      try {
        const res = await getEmailAccount(id)
        currentAccount.value = res.data.data
      } finally {
        loadingDetail.value = false
      }
    }

    async function create(payload) {
      const res = await createEmailAccount(payload)
      emitDataChanged(TAB_ENTITIES.EMAIL_ACCOUNTS, res.data.data.id)
      return res.data.data
    }

    // Scopo: aggiorna l'account, riallinea il dettaglio e notifica le tab.
    async function update(id, payload) {
      const res = await updateEmailAccount(id, payload)
      currentAccount.value = res.data.data
      emitDataChanged(TAB_ENTITIES.EMAIL_ACCOUNTS, id)
      return res.data.data
    }

    return { currentAccount, loadingDetail, fetchDetail, create, update }
  },
})
