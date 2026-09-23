// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Store Pinia dell'elenco RATE FUORI CAPIENZA (lista
//        `pagamenti.rate_fuori_capienza`, vista `vw_rate_fuori_capienza`).
// Note: ⭐ E' l'elenco che rende ONESTA la forzatura: senza, forzare la
//        capienza di una rata **nasconde** invece di registrare. Per questo la
//        prima colonna e' il MOTIVO.
//        ⚠️ Le popolazioni sono DUE e non vanno confuse: sovra-incasso e
//        movimento contrario. Il filtro `motivo` le separa, e il vocabolario e'
//        chiuso — un valore sbagliato darebbe una lista vuota, cioe' «non c'e'
//        niente da sistemare», che qui e' la bugia peggiore.
// ------------------------------------------------------------

import { defineStore } from 'pinia'
import { ref } from 'vue'

import { useListaEmptyStateFetch } from '../../core/composables/useListaEmptyStateFetch'
import { PAGINATION } from '../../core/constants'
import { paramsPagina } from '../../core/utils/listParams'
import { listRateFuoriCapienza } from '../api/pagamenti'
import { useContrattoFiltriLista } from '../../core/composables/useContrattoFiltriLista'

function buildParams(f) {
  const p = paramsPagina(f)
  if (f.motivo) p.motivo = f.motivo
  if (f.billing_account_id != null) p.billing_account_id = f.billing_account_id
  return p
}

export const useRateFuoriCapienzaStore = defineStore(
  'pagamenti-rate-fuori-capienza',
  () => {
    // ⭐ I FILTRI DI DOMINIO IN UNA SEDE SOLA (2026-09-23): da qui nascono i valori
    //    di partenza della lista E il contratto che `FiltriLista` legge per il segno
    //    dei filtri attivi (`useContrattoFiltriLista`). ⛔ Due letterali divergono
    //    al primo filtro aggiunto da una parte sola, e il segno si spegnerebbe su
    //    una lista che filtra — senza nessun errore.
    const FILTRI_DEFAULT = {
      motivo: null,
      billing_account_id: null,
    }

    const filters = ref({
      ...FILTRI_DEFAULT,
      // ⚠️ NON si inoltra al backend (questa lista non ha ricerca testuale), ma
      // la chiave si DICHIARA: fa parte del contratto di `useSearchTable`, che
      // la scrive su ricerca universale / deep-link `?search=` — e una chiave
      // che nasce per assegnazione e' una chiave che nessuno ha deciso.
      search: '',
      limit: PAGINATION.DEFAULT_ROWS,
      offset: 0,
      order_by: 'data_scadenza',
      order_dir: 'desc',
    })

    const { items, totalRecords, loading, hasSearched, fetchList } =
      useListaEmptyStateFetch({
        filters,
        buildParams,
        fetchPage: listRateFuoriCapienza,
        alwaysFetch: true,
      })

    // Il contratto che `FiltriLista` legge: chi sono i filtri, com'erano alla
    // nascita, e come si riportano li' («Pulisci filtri»).
    const { chiaviFiltro, filtriDefault, azzeraFiltri } = useContrattoFiltriLista({
      filters, filterDefaults: FILTRI_DEFAULT, fetchList,
    })

    return {
      items, totalRecords, loading, hasSearched, filters, fetchList,
      chiaviFiltro, filtriDefault, azzeraFiltri,
    }
  },
  { userScoped: true },
)
