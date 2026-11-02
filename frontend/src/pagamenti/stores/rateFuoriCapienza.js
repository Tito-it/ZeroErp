// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
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
import { paramsFinestra, paramsRicerca } from '../../core/utils/listParams'
import { listRateFuoriCapienza } from '../api/pagamenti'
import { useContrattoFiltriLista } from '../../core/composables/useContrattoFiltriLista'
import { USO_MISURA, misuraDefault } from '../../core/misurePagina'

function buildParams(f, _termine, ricerca) {
  const p = paramsFinestra(f)
  // La ricerca libera con la regola comune (`paramsRicerca`: trim, soglia della
  // lista — `ricerca` = `{ minCaratteri }`, passato dal BB di stato).
  Object.assign(p, paramsRicerca(f, ricerca))
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
      // La ricerca libera: la scrive `useSearchTable` (casella nel `#sempre`
      // di `FiltriLista`, ricerca universale, deep-link `?search=`), la
      // inoltra `buildParams` (`paramsRicerca`). Le colonne le decide il
      // catalogo (brief-be-ricerca-full-liste-residue §5.3).
      search: '',
      limit: misuraDefault(USO_MISURA.PAGINA),
      offset: 0,
      order_by: 'data_scadenza',
      order_dir: 'desc',
    })

    // `lista`: lo stato del BB, esposto INTERO nel `return` (`...lista`).
    // ⛔ Non si elencano i suoi ref a mano: un ref nuovo del BB (com'e'
    //    successo con `ricercaFull`, `ricercaMinCaratteri`,
    //    `ricercaCambiaLaRichiesta`) arriverebbe solo agli store che lo
    //    ricordano — e senza errore sugli altri.
    const lista = useListaEmptyStateFetch({
      filters,
      buildParams,
      fetchPage: listRateFuoriCapienza,
      alwaysFetch: true,
    })
    const { fetchList } = lista

    // Il contratto che `FiltriLista` legge: chi sono i filtri, com'erano alla
    // nascita, e come si riportano li' («Pulisci filtri»).
    const { chiaviFiltro, filtriDefault, azzeraFiltri } = useContrattoFiltriLista({
      filters, filterDefaults: FILTRI_DEFAULT, fetchList,
    })

    return {
      ...lista,
      filters,
      chiaviFiltro, filtriDefault, azzeraFiltri,
    }
  },
  { userScoped: true },
)
