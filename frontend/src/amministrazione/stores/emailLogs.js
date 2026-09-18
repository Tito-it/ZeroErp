// Pinia store per la consultazione log email (sola lettura).
//
// ⭐ Dal 2026-09-18 la lista e' `createListaStore`: era uno store scritto a mano
//    su `useListaEmptyStateFetch` con la copia del `buildParams`. Qui resta
//    solo cio' che e' di dominio — il dettaglio corrente (`currentLog`), che il
//    drawer legge dallo store e non dal valore di ritorno.

import { ref } from 'vue'
import { createListaStore } from '../../core/stores/createListaStore'
import { defaultFiltroDataDaString } from '../../core/utils/date'
import { listEmailLogs, getEmailLog } from '../api/amministrazione'

export const useEmailLogsStore = createListaStore('amm-email-logs', {
  fetchPage: listEmailLogs,
  // Parte piena: e' un registro, non una ricerca.
  startsEmpty: false,
  filterDefaults: {
    stato: null,
    // Floor temporale standard delle liste (oggi-60gg al 1° del mese,
    // `feedback_filtro_data_liste`). ⚠️ Fino al 2026-09-18 questo store si
    // calcolava a mano «30 giorni fa»: era l'unica lista con date fuori dalla
    // regola, e la regola dice che il calcolo NON si riscrive nello store.
    data_da: defaultFiltroDataDaString(),
    data_a: null,
  },
  // Il piu' recente in cima; il ripiego del verso segue, e' un registro.
  orderBy: 'data_insert',
  orderDir: 'desc',
  orderDirDefault: 'desc',
  extend: () => {
    const currentLog = ref(null)
    const loadingDetail = ref(false)

    // Scopo: carica il dettaglio nello store (il drawer legge `currentLog`).
    async function fetchDetail(id) {
      loadingDetail.value = true
      try {
        const res = await getEmailLog(id)
        currentLog.value = res.data.data
      } finally {
        loadingDetail.value = false
      }
    }

    return { currentLog, loadingDetail, fetchDetail }
  },
})
