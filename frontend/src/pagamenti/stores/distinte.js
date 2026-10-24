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
import { paramsFinestra, paramsRicerca } from '../../core/utils/listParams'
import { listDistinte } from '../api/pagamenti'
import { useContrattoFiltriLista } from '../../core/composables/useContrattoFiltriLista'
import { USO_MISURA, misuraDefault } from '../../core/misurePagina'

// Scopo: filtri dello store -> query param dell'endpoint.
// Note: la `search` si inoltra con `paramsRicerca` (brief-be-ricerca-full-liste-
//       residue §5.3): colonne dal catalogo, casella solo se `ricerca_full`.
function buildParams(f, _termine, ricerca) {
  const p = paramsFinestra(f)
  // La ricerca libera con la regola comune (`paramsRicerca`: trim, soglia della
  // lista — `ricerca` = `{ minCaratteri }`, passato dal BB di stato).
  Object.assign(p, paramsRicerca(f, ricerca))
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
      // La ricerca libera: la scrive `useSearchTable` (casella nel `#sempre`
      // di `FiltriLista`, ricerca universale, deep-link `?search=`), la
      // inoltra `buildParams` (`paramsRicerca`). Le colonne le decide il
      // catalogo (brief-be-ricerca-full-liste-residue §5.3).
      search: '',
      limit: misuraDefault(USO_MISURA.PAGINA),
      offset: 0,
      // Il giorno piu' recente in cima: e' il default del backend, quindi la
      // lista non si riordina sotto gli occhi al primo caricamento.
      order_by: 'data_contabile',
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
      fetchPage: listDistinte,
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
