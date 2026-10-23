// Pinia store per gestione emittenti fiscali (admin only).
// Lista + CRUD via createCrudStore (regola del 2) — lista parte piena.
// Sub-resource utilities via `extend`. fetchDetail della factory ritorna il
// dato (niente detail-storato → evita race condition dai consumatori).
//
// NB: il mapping Billing Account NON e' qui — e' gestito dallo store dedicato
// `emittentiFiscaliBA.js` (consumato da EmittenteFiscaleBillingAccountTab). I
// vecchi metodi BA-mapping di questo store erano codice morto (zero consumer):
// rimossi nella migrazione a createCrudStore (2026-06-05).

import { ref } from 'vue'
import {
  listEmittentiFiscali,
  getEmittenteFiscale,
  createEmittenteFiscale,
  updateEmittenteFiscale,
  listEmittenteUtilities,
  createEmittenteUtility,
  updateEmittenteUtility,
  deleteEmittenteUtility
} from '../api/emittentiFiscali'
import { createCrudStore } from '../../core/stores/createCrudStore'
import { TAB_ENTITIES } from '../../core/constants'

export const useEmittentiFiscaliStore = createCrudStore('amm-emittenti-fiscali', {
  api: {
    list: listEmittentiFiscali,
    detail: getEmittenteFiscale,
    create: createEmittenteFiscale,
    update: updateEmittenteFiscale,
  },
  tabEntity: TAB_ENTITIES.EMITTENTE_FISCALE,
  // Allineato all'`ordinamento_default` del preset `emittenti_fiscali_default`
  // (seed lista 18): era `descrizione`, colonna droppata il 2026-08-02.
  // Lo store e' la verita' sull'ordine iniziale — il `defaultSortField` del
  // componente e' dormiente quando lo store preimposta `order_by`.
  orderBy: 'ragione_sociale_completa',
  startsEmpty: false,
  filterDefaults: { attivo: null },
  // Sotto-risorsa utilities caricata on demand dal tab e tenuta qui (il tab
  // pulisce lo state in unmount/reload).
  // ⛔ Le scritture NON rileggono la matrice: la rilegge il tab, dopo l'esito.
  //    Una rilettura fallita dopo un POST riuscito faceva sembrare fallito il
  //    POST, e l'operatore lo rimandava (stessa regola del summary BA,
  //    `emittentiFiscaliBA.js`).
  extend: () => {
    const utilitiesRecords = ref([])

    async function fetchUtilitiesRecords(emittenteId) {
      const res = await listEmittenteUtilities(emittenteId)
      utilitiesRecords.value = res.data.data.results
    }
    function clearUtilitiesRecords() {
      utilitiesRecords.value = []
    }
    async function addUtilityRecord(emittenteId, payload) {
      const res = await createEmittenteUtility(emittenteId, payload)
      return res.data.data
    }
    async function patchUtilityRecord(emittenteId, recordId, payload) {
      const res = await updateEmittenteUtility(emittenteId, recordId, payload)
      return res.data.data
    }
    async function removeUtilityRecord(emittenteId, recordId) {
      await deleteEmittenteUtility(emittenteId, recordId)
    }

    return {
      utilitiesRecords,
      fetchUtilitiesRecords,
      clearUtilitiesRecords,
      addUtilityRecord,
      patchUtilityRecord,
      removeUtilityRecord,
    }
  },
})
