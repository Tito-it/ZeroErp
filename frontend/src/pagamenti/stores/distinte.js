// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Store Pinia della lista DISTINTE CONTABILI (lista configurabile
//        `pagamenti.distinte`, seed del lotto 9).
// Note: ⭐ Semantica CODA DI LAVORO, non lista storica: `alwaysFetch: true` e
//       NESSUN pavimento temporale. Il floor standard delle liste (oggi-60gg al
//       1° del mese) qui nasconderebbe proprio l'arretrato — una distinta in
//       bozza di tre mesi fa e' quella che pesa di piu', non quella che conta
//       meno. Stessa scelta delle code resi, delle code Strumenti e dei fondi
//       fattura da decidere.
//       ⚠️ `userScoped: true`: filtri e pagina sono dell'operatore, non del
//       browser (memoria feedback_pinia_userscoped).
// ------------------------------------------------------------

import { defineStore } from 'pinia'
import { ref } from 'vue'

import { useListaEmptyStateFetch } from '../../core/composables/useListaEmptyStateFetch'
import { PAGINATION } from '../../core/constants'
import { paramsPagina } from '../../core/utils/listParams'
import { listDistinte } from '../api/pagamenti'
import { useContrattoFiltriLista } from '../../core/composables/useContrattoFiltriLista'

// Scopo: filtri dello store -> query param dell'endpoint.
// Note: ⚠️ La `search` NON si inoltra: questa lista non ha ricerca testuale a
//       contratto. Passarla sarebbe un parametro ignorato in silenzio —
//       l'operatore digiterebbe e vedrebbe la lista intera, convinto di aver
//       cercato. Per la stessa ragione il campo non e' montato nella pagina.
function buildParams(f) {
  const p = paramsPagina(f)
  if (f.stato) p.stato = f.stato
  if (f.origine) p.origine = f.origine
  if (f.centro_riscossione_id != null) p.centro_riscossione_id = f.centro_riscossione_id
  if (f.ente_incasso_id != null) p.ente_incasso_id = f.ente_incasso_id
  if (f.data_da) p.data_da = f.data_da
  if (f.data_a) p.data_a = f.data_a
  return p
}

export const useDistinteStore = defineStore(
  'pagamenti-distinte',
  () => {
    // ⭐ I FILTRI DI DOMINIO IN UNA SEDE SOLA (2026-09-23): da qui nascono i valori
    //    di partenza della lista E il contratto che `FiltriLista` legge per il segno
    //    dei filtri attivi (`useContrattoFiltriLista`). ⛔ Due letterali divergono
    //    al primo filtro aggiunto da una parte sola, e il segno si spegnerebbe su
    //    una lista che filtra — senza nessun errore.
    const FILTRI_DEFAULT = {
      // Vocabolari chiusi (null = tutti). ⛔ I valori NON si cablano nel
      // frontend: gli stati arrivano dal catalogo che il dettaglio porta con
      // se', e il filtro li offre da li'.
      stato: null,
      origine: null,
      centro_riscossione_id: null,
      ente_incasso_id: null,
      data_da: null,
      data_a: null,
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
      // Il giorno piu' recente in cima: e' il default del backend, quindi la
      // lista non si riordina sotto gli occhi al primo caricamento.
      order_by: 'data_contabile',
      order_dir: 'desc',
    })

    const { items, totalRecords, loading, hasSearched, fetchList } =
      useListaEmptyStateFetch({
        filters,
        buildParams,
        fetchPage: listDistinte,
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
