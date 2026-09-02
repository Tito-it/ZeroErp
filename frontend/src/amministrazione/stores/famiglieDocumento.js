// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: Store della lista delle FAMIGLIE DI DOCUMENTO. Contratto
//        `useSearchTable` (filters, items, totalRecords, loading, fetchList),
//        consumato da `useListaConfigurabilePage`.
//
// ⚠️ `userScoped: true` anche se il catalogo e' globale: lo store tiene
//    comunque cio' che QUESTO utente ha caricato e i suoi filtri, e al logout
//    non deve restare in memoria per il prossimo (`feedback_pinia_userscoped`).

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useListaEmptyStateFetch } from '../../core/composables/useListaEmptyStateFetch'
import {
  createFamiglia,
  listFamiglie,
  setFamigliaAttiva,
  updateFamiglia,
} from '../api/famiglieDocumento'

export const useFamiglieDocumentoStore = defineStore('amm-famiglie-documento', () => {
  const filters = ref({
    search: '',
    limit: 25,
    offset: 0,
    order_by: 'codice_interno',
    order_dir: 'asc',
    // ⛔ `null` = TUTTE, spente comprese, ed e' il default voluto: una famiglia
    //    spenta e' la riga che spiega perche' una tabella non e' disponibile.
    attivo: null,
    gestisce_serie: null,
  })

  // Scopo: i parametri di FILTRO — quelli che decidono QUALI righe, non quante.
  // ⭐ Sede unica per la lista e per l'export, e non e' pulizia: l'export che si
  //    costruisce i propri filtri esporta un insieme DIVERSO da quello a video
  //    appena se ne aggiunge uno, e nessuno se ne accorge finche' qualcuno non
  //    confronta un file con la schermata.
  function paramsFiltro(f = filters.value) {
    const params = {}
    if (f.search) params.search = f.search
    if (f.order_by) {
      params.order_by = f.order_by
      params.order_dir = f.order_dir || 'asc'
    }
    // ⚠️ Il confronto e' con `null`, non `if (f.attivo)`: `false` e' un filtro
    //    legittimo («solo le spente») e un truthy-check lo tratterebbe come
    //    «nessun filtro».
    if (f.attivo !== null && f.attivo !== undefined) params.attivo = f.attivo
    if (f.gestisce_serie !== null && f.gestisce_serie !== undefined) {
      params.gestisce_serie = f.gestisce_serie
    }
    return params
  }

  const {
    items, totalRecords, loading, fetchList, svuota,
  } = useListaEmptyStateFetch({
    filters,
    alwaysFetch: true,
    // ⚠️ La paginazione e' l'UNICA cosa che la lista aggiunge ai filtri:
    //    l'export non la manda: il suo limite lo impone il backend.
    buildParams: (f) => ({ limit: f.limit, offset: f.offset, ...paramsFiltro(f) }),
    fetchPage: (params) => listFamiglie(params),
  })

  // Scopo: crea la famiglia e ricarica. ⭐ Ritorna la riga PIU'
  //        `registri_creati`, che il drawer mostra: la madre ha appena
  //        provveduto i registri su ogni emittente, e chi ha premuto «salva»
  //        deve saperlo.
  async function crea(payload) {
    const res = await createFamiglia(payload)
    await fetchList()
    return res.data.data
  }

  async function aggiorna(id, payload) {
    const res = await updateFamiglia(id, payload)
    await fetchList()
    return res.data.data
  }

  // Scopo: il verbo `attivo`, usato sia per spegnere sia per riaccendere.
  async function cambiaAttivo(id, attivo) {
    const res = await setFamigliaAttiva(id, attivo)
    await fetchList()
    return res.data.data
  }

  function reset() {
    svuota()
    filters.value.search = ''
    filters.value.offset = 0
    filters.value.attivo = null
    filters.value.gestisce_serie = null
  }

  return {
    items, totalRecords, loading, filters, paramsFiltro,
    fetchList, crea, aggiorna, cambiaAttivo, reset,
  }
}, { userScoped: true })
