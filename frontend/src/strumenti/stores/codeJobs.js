// Store Pinia delle due code di lavoro Strumenti (coda lavori dbops /
// coda stampa outbox PDF), promosse a liste configurabili
// (<ListaConfigurabile codice="dbops.coda_lavori" | "vendite.fatture_stampa_coda">,
// ui.lista_definizione id 34/35 — 7° lotto, 2026-08-03). UNA factory per non
// duplicare l'interfaccia useSearchTable-compatibile
// (items/totalRecords/loading/filters/fetchList/hasSearched), come i gemelli
// resi (stores/resiCoda.js).
//
// I filtri di dominio (ambito miei/tutti, stato, range date col floor
// standard) restano con i NOMI della CodaFiltriToolbar condivisa
// (ambito/stato/dataDa/dataA — la toolbar muta l'oggetto per riferimento);
// qui si mappano ai query param del BE. L'ordinamento viaggia come
// `sort_by`/`sort_dir` (convenzione endpoint tracciamento, whitelist BE
// ELENCA_SORT_SQL / CODA_STAMPA_SORT_SQL).
//
// Semantica CODA: `alwaysFetch: true` — il lavoro pendente e' visibile al
// mount senza ricerca. userScoped: reset al logout (feedback_pinia_userscoped).

import { defineStore } from 'pinia'
import { ref } from 'vue'

import { useListaEmptyStateFetch } from '../../core/composables/useListaEmptyStateFetch'
import { listCodaLavori, listCodaStampa } from '../../core/api/tracciamento'
import { defaultFiltroDataDa, toDateString } from '../../core/utils/date'

// Scopo: mappa filtri store → query param degli endpoint coda (limit/offset +
//        filtri opzionali + sort_by/sort_dir maiuscolo come da contratto BE).
function buildCodaParams(f) {
  const p = { limit: f.limit, offset: f.offset }
  if (f.ambito === 'tutti') p.ambito = 'tutti'
  if (f.stato) p.stato = f.stato
  if (f.dataDa) p.data_da = toDateString(f.dataDa)
  if (f.dataA) p.data_a = toDateString(f.dataA)
  if (f.order_by) {
    p.sort_by = f.order_by
    p.sort_dir = f.order_dir === 'asc' ? 'ASC' : 'DESC'
  }
  return p
}

// Factory: crea uno store coda con l'interfaccia standard delle liste
// configurabili. `id` = id Pinia univoco; `fetchPage` = endpoint API;
// `statoDefault` = stato preselezionato (lavori → IN_CORSO: la domanda
// primaria e' «cosa sta girando ora»); `orderBy` = preset del seed, che
// replica il default gia' applicato dal BE (la lista non si riordina sotto
// gli occhi dell'operatore al primo caricamento).
function createCodaJobsStore(id, fetchPage, { statoDefault = null, orderBy }) {
  return defineStore(id, () => {
    const filters = ref({
      ambito: 'miei',
      stato: statoDefault,
      // Floor temporale di default, regola unica di progetto (core/utils/date).
      dataDa: defaultFiltroDataDa(),
      dataA: null,
      limit: 25,
      offset: 0,
      order_by: orderBy,
      order_dir: 'desc',
    })

    const { items, totalRecords, loading, hasSearched, fetchList } =
      useListaEmptyStateFetch({
        filters,
        buildParams: buildCodaParams,
        fetchPage,
        alwaysFetch: true,
      })

    return { items, totalRecords, loading, hasSearched, filters, fetchList }
  }, {
    userScoped: true,
  })
}

export const useCodaLavoriStore = createCodaJobsStore(
  'strumenti-coda-lavori', listCodaLavori,
  { statoDefault: 'IN_CORSO', orderBy: 'started_at' },
)
export const useCodaStampaStore = createCodaJobsStore(
  'strumenti-coda-stampa', listCodaStampa,
  { orderBy: 'data_update' },
)
