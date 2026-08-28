// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Store Pinia della CODA DEL RICONCILIATORE — le righe contabili da
//        lavorare, viste attraverso le distinte (lista `pagamenti.righe`).
// Note: ⭐ UNA LISTA, DUE PORTE (Q-4 -> c): «da abbinare» e «sospese» sono la
//       stessa lista con il filtro `coda` gia' impostato, ed e' il motivo per
//       cui a catalogo il seed e' UNO. Chi apre la voce di menu passa la coda
//       che gli compete.
//       ⛔ `coda` NON e' opzionale come gli altri filtri: e' un vocabolario
//       CHIUSO (`DA_ABBINARE` | `SOSPESE` | `TUTTE`) e un valore inventato e'
//       un **400**, non una lista vuota — su elenchi che esistono per non far
//       sparire del denaro, «nessun risultato» sarebbe la risposta piu'
//       rassicurante e piu' falsa.
//       ⭐ Nessun pavimento temporale: e' una coda di lavoro, e la riga vecchia
//       e' quella che pesa di piu'.
// ------------------------------------------------------------

import { defineStore } from 'pinia'
import { ref } from 'vue'

import { useListaEmptyStateFetch } from '../../core/composables/useListaEmptyStateFetch'
import { PAGINATION } from '../../core/constants'
import { paramsPagina } from '../../core/utils/listParams'
import { CODE } from '../vocabolari'
import { listCodaRighe } from '../api/pagamenti'


function buildParams(f) {
  const p = paramsPagina(f)
  // ⚠️ Sempre inviata: senza, il backend non saprebbe quale coda serve.
  p.coda = f.coda || CODE.DA_ABBINARE
  if (f.billing_account_id != null) p.billing_account_id = f.billing_account_id
  if (f.data_da) p.data_da = f.data_da
  if (f.data_a) p.data_a = f.data_a
  return p
}

export const useCodaRigheStore = defineStore(
  'pagamenti-coda-righe',
  () => {
    const filters = ref({
      coda: CODE.DA_ABBINARE,
      billing_account_id: null,
      data_da: null,
      data_a: null,
      // ⚠️ NON si inoltra al backend (questa lista non ha ricerca testuale), ma
      // la chiave si DICHIARA: fa parte del contratto di `useSearchTable`, che
      // la scrive su ricerca universale / deep-link `?search=` — e una chiave
      // che nasce per assegnazione e' una chiave che nessuno ha deciso.
      search: '',
      limit: PAGINATION.DEFAULT_ROWS,
      offset: 0,
      order_by: 'data_pagamento',
      order_dir: 'desc',
    })

    const { items, totalRecords, loading, hasSearched, fetchList } =
      useListaEmptyStateFetch({
        filters,
        buildParams,
        fetchPage: listCodaRighe,
        alwaysFetch: true,
      })

    // Scopo: la voce di menu sceglie la coda e ricarica.
    // Note: ⚠️ Azzera l'offset: restare a pagina 3 passando da una coda
    //       all'altra mostrerebbe una pagina che in quella coda non esiste, e
    //       l'elenco risulterebbe vuoto senza motivo apparente.
    function apriCoda(coda) {
      filters.value.coda = coda || CODE.DA_ABBINARE
      filters.value.offset = 0
      return fetchList()
    }

    return { items, totalRecords, loading, hasSearched, filters, fetchList, apriCoda }
  },
  { userScoped: true },
)
