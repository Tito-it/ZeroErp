// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Store Pinia dell'elenco ECCEDENZE DA SISTEMARE (lista
//        `pagamenti.eccedenze`, vista `vw_eccedenze_da_sistemare`).
// Note: ⭐ Ordinato per CLIENTE di default (D15-b), non per documento: la
//        decisione — rimborsare, compensare, riportare — si prende guardando il
//        cliente, perche' compensare significa mettere insieme due documenti
//        SUOI. Un elenco per documento la nasconde.
//        ⭐ L'elenco PRESENTA, non sana: nessuna riga ha un gemello automatico
//        che la corregge, perche' sanarla vorrebbe dire muovere denaro senza
//        che nessuno l'abbia deciso.
//        ⚠️ `chi_e_in_credito` non e' un dettaglio: sbagliare il verso significa
//        rimborsare cio' che si deve incassare.
// ------------------------------------------------------------

import { defineStore } from 'pinia'
import { ref } from 'vue'

import { useListaEmptyStateFetch } from '../../core/composables/useListaEmptyStateFetch'
import { PAGINATION } from '../../core/constants'
import { paramsPagina } from '../../core/utils/listParams'
import { listEccedenze } from '../api/pagamenti'

function buildParams(f) {
  const p = paramsPagina(f)
  if (f.chi_e_in_credito) p.chi_e_in_credito = f.chi_e_in_credito
  if (f.billing_account_id != null) p.billing_account_id = f.billing_account_id
  return p
}

export const useEccedenzeStore = defineStore(
  'pagamenti-eccedenze',
  () => {
    const filters = ref({
      chi_e_in_credito: null,
      billing_account_id: null,
      // ⚠️ NON si inoltra al backend (questa lista non ha ricerca testuale), ma
      // la chiave si DICHIARA: fa parte del contratto di `useSearchTable`, che
      // la scrive su ricerca universale / deep-link `?search=` — e una chiave
      // che nasce per assegnazione e' una chiave che nessuno ha deciso.
      search: '',
      limit: PAGINATION.DEFAULT_ROWS,
      offset: 0,
      // ⭐ Il default e' il totale del CLIENTE, non quello del documento: e' il
      // numero su cui si decide.
      order_by: 'eccedenza_cliente',
      order_dir: 'desc',
    })

    const { items, totalRecords, loading, hasSearched, fetchList } =
      useListaEmptyStateFetch({
        filters,
        buildParams,
        fetchPage: listEccedenze,
        alwaysFetch: true,
      })

    return { items, totalRecords, loading, hasSearched, filters, fetchList }
  },
  { userScoped: true },
)
