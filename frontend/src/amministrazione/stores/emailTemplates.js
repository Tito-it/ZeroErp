// Pinia store per la gestione template email (lista, dettaglio, modifica).
//
// ⭐ Dal 2026-09-18 la lista e' `createListaStore`: era uno store scritto a mano
//    su `useListaEmptyStateFetch` con la copia del `buildParams`. Non e'
//    `createCrudStore` perche' il contratto del dettaglio e' diverso — il
//    drawer legge `currentTemplate` dallo store, non il valore di ritorno — e
//    non c'e' `create`: i template nascono dal seed, qui si modificano soltanto.

import { ref } from 'vue'
import { createListaStore } from '../../core/stores/createListaStore'
import { listEmailTemplates, getEmailTemplate, updateEmailTemplate } from '../api/amministrazione'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../core/constants'

export const useEmailTemplatesStore = createListaStore('amm-email-templates', {
  fetchPage: listEmailTemplates,
  // Parte piena: e' un catalogo, non una ricerca.
  startsEmpty: false,
  orderBy: 'codice',
  extend: () => {
    const { emitDataChanged } = useTabEvents()
    const currentTemplate = ref(null)
    const loadingDetail = ref(false)

    // Scopo: carica il dettaglio nello store (il drawer legge `currentTemplate`).
    async function fetchDetail(id) {
      loadingDetail.value = true
      try {
        const res = await getEmailTemplate(id)
        currentTemplate.value = res.data.data
      } finally {
        loadingDetail.value = false
      }
    }

    // Scopo: aggiorna il template, riallinea il dettaglio e notifica le tab.
    async function update(id, payload) {
      const res = await updateEmailTemplate(id, payload)
      currentTemplate.value = res.data.data
      emitDataChanged(TAB_ENTITIES.EMAIL_TEMPLATES, id)
      return res.data.data
    }

    return { currentTemplate, loadingDetail, fetchDetail, update }
  },
})
