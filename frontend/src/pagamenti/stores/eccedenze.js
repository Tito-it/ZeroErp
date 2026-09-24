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
import { paramsPagina, paramsRicerca } from '../../core/utils/listParams'
import { listEccedenze } from '../api/pagamenti'
import { useContrattoFiltriLista } from '../../core/composables/useContrattoFiltriLista'

function buildParams(f) {
  const p = paramsPagina(f)
  // La ricerca libera con la regola comune (`paramsRicerca`: trim, soglia unica).
  Object.assign(p, paramsRicerca(f))
  if (f.chi_e_in_credito) p.chi_e_in_credito = f.chi_e_in_credito
  if (f.billing_account_id != null) p.billing_account_id = f.billing_account_id
  return p
}

export const useEccedenzeStore = defineStore(
  'pagamenti-eccedenze',
  () => {
    // ⭐ I FILTRI DI DOMINIO IN UNA SEDE SOLA (2026-09-23): da qui nascono i valori
    //    di partenza della lista E il contratto che `FiltriLista` legge per il segno
    //    dei filtri attivi (`useContrattoFiltriLista`). ⛔ Due letterali divergono
    //    al primo filtro aggiunto da una parte sola, e il segno si spegnerebbe su
    //    una lista che filtra — senza nessun errore.
    const FILTRI_DEFAULT = {
      chi_e_in_credito: null,
      billing_account_id: null,
    }

    const filters = ref({
      ...FILTRI_DEFAULT,
      // La ricerca libera: la scrive `useSearchTable` (casella nel `#sempre`
      // di `FiltriLista`, ricerca universale, deep-link `?search=`), la
      // inoltra `buildParams` (`paramsRicerca`). Le colonne le decide il
      // catalogo (brief-be-ricerca-full-liste-residue §5.3).
      search: '',
      limit: PAGINATION.DEFAULT_ROWS,
      offset: 0,
      // ⭐ Il default e' il totale del CLIENTE, non quello del documento: e' il
      // numero su cui si decide.
      order_by: 'eccedenza_cliente',
      order_dir: 'desc',
    })

    // `ricercaFull` (la lista cerca?) la dichiara il BB di stato.
    const { items, totalRecords, loading, hasSearched, ricercaFull, fetchList } =
      useListaEmptyStateFetch({
        filters,
        buildParams,
        fetchPage: listEccedenze,
        alwaysFetch: true,
      })

    // Il contratto che `FiltriLista` legge: chi sono i filtri, com'erano alla
    // nascita, e come si riportano li' («Pulisci filtri»).
    const { chiaviFiltro, filtriDefault, azzeraFiltri } = useContrattoFiltriLista({
      filters, filterDefaults: FILTRI_DEFAULT, fetchList,
    })

    return {
      items, totalRecords, loading, hasSearched, filters, fetchList, ricercaFull,
      chiaviFiltro, filtriDefault, azzeraFiltri,
    }
  },
  { userScoped: true },
)
